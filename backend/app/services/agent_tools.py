from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any
from uuid import UUID

import httpx
from bs4 import BeautifulSoup
from groq import AsyncGroq
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models import Action, AuditLog, Contact, Email, Thread, WebIntelligenceCache
from app.services.rag_pipeline import retrieve_relevant_chunks


async def search_knowledge_base(query: str, db: AsyncSession, embedder: Any) -> dict[str, Any]:
    chunks = await retrieve_relevant_chunks(query, embedder, db, top_k=3)
    return {"query": query, "chunks": chunks}


async def get_thread_history(sender_email: str, db: AsyncSession) -> dict[str, Any]:
    result = await db.execute(
        select(Email)
        .where(Email.sender == sender_email)
        .order_by(Email.timestamp.asc())
    )
    emails = result.scalars().all()
    return {
        "sender_email": sender_email,
        "emails": [
            {
                "id": str(email.id),
                "message_id": email.message_id,
                "thread_id": str(email.thread_id),
                "subject": email.subject,
                "body": email.body,
                "timestamp": email.timestamp.isoformat(),
                "category": email.category,
                "urgency": email.urgency,
                "sentiment_score": email.sentiment_score,
                "requires_human": email.requires_human,
                "confidence": email.confidence,
                "status": email.status,
            }
            for email in emails
        ],
    }


async def get_contact_profile(email: str, db: AsyncSession) -> dict[str, Any]:
    contact = await db.scalar(select(Contact).where(Contact.email == email))
    open_thread_count = await db.scalar(
        select(func.count(Thread.id)).where(Thread.sender_email == email, Thread.status == "Open")
    )
    if contact is None:
        return {
            "email": email,
            "found": False,
            "open_thread_count": int(open_thread_count or 0),
            "risk_level": "Unknown",
        }

    risk_level = _risk_level(contact.churn_risk_score, int(open_thread_count or 0))
    return {
        "found": True,
        "id": str(contact.id),
        "email": contact.email,
        "name": contact.name,
        "company": contact.company,
        "status": contact.status,
        "account_value": float(contact.account_value or 0),
        "churn_risk_score": contact.churn_risk_score,
        "last_contact_at": contact.last_contact_at.isoformat() if contact.last_contact_at else None,
        "open_thread_count": int(open_thread_count or 0),
        "risk_level": risk_level,
    }


async def check_account_status(email: str, db: AsyncSession) -> dict[str, Any]:
    contact = await db.scalar(select(Contact).where(Contact.email == email))
    account_value = Decimal(contact.account_value or 0) if contact else Decimal("0")
    if account_value > Decimal("100000"):
        tier = "Enterprise"
    elif account_value > Decimal("10000"):
        tier = "Standard"
    else:
        tier = "Starter"

    status = contact.status if contact else "Unknown"
    billing_notes = []
    if status in {"Blocked", "Churned"}:
        billing_notes.append(f"Account status is {status}; do not auto-reply without review.")
    if tier == "Enterprise":
        billing_notes.append("Enterprise account; prioritize senior support and renewal risk.")
    return {
        "email": email,
        "tier": tier,
        "account_value": float(account_value),
        "status": status,
        "billing_notes": billing_notes,
    }


async def draft_reply(context: str, tone: str, policy_refs: list[str], db: AsyncSession) -> dict[str, Any]:
    try:
        if not settings.groq_api_key or settings.groq_api_key == "your_groq_key":
            raise ValueError("Groq API key is not configured")
        client = AsyncGroq(api_key=settings.groq_api_key)
        response = await client.chat.completions.create(
            model=settings.llm_model,
            messages=[
                {
                    "role": "system",
                    "content": "Draft a concise CRM support reply. Cite specific policy names provided by the user.",
                },
                {
                    "role": "user",
                    "content": f"Tone: {tone}\nPolicy refs: {policy_refs}\nContext:\n{context}",
                },
            ],
            temperature=0.2,
        )
        draft = response.choices[0].message.content or ""
    except Exception as exc:
        draft = (
            "Thank you for raising this. We understand the impact and are escalating this for urgent human review. "
            f"We will reference {', '.join(policy_refs) if policy_refs else 'the applicable policy documents'} "
            "while preparing the next response."
        )
        return {"draft_text": draft, "policy_refs_used": policy_refs, "fallback": True, "error": str(exc)}

    return {"draft_text": draft, "policy_refs_used": policy_refs, "fallback": False}


async def escalate_to_human(email_id: str, reason: str, priority: str, db: AsyncSession) -> dict[str, Any]:
    email = await db.get(Email, _uuid(email_id))
    if email is None:
        return {"ok": False, "error": "Email not found", "email_id": email_id}

    email.status = "Escalated"
    action = Action(
        email_id=email.id,
        action_type="Escalate",
        agent_reasoning_log={"reason": reason, "priority": priority},
        proposed_content=None,
    )
    db.add(action)
    await db.flush()
    db.add(
        AuditLog(
            entity_type="email",
            entity_id=email.id,
            action="escalated_to_human",
            performed_by="agent",
            diff={"reason": reason, "priority": priority, "action_id": str(action.id)},
        )
    )
    await db.commit()
    return {"ok": True, "email_id": str(email.id), "action_id": str(action.id), "priority": priority, "reason": reason}


async def create_internal_ticket(title: str, body: str, assignee: str, db: AsyncSession) -> dict[str, Any]:
    action = Action(
        email_id=None,
        action_type="Ticket-Created",
        proposed_content=body,
        agent_reasoning_log={"title": title, "assignee": assignee},
    )
    db.add(action)
    await db.flush()
    db.add(
        AuditLog(
            entity_type="action",
            entity_id=action.id,
            action="internal_ticket_created",
            performed_by="agent",
            diff={"title": title, "assignee": assignee},
        )
    )
    await db.commit()
    return {"ok": True, "ticket_id": str(action.id), "title": title, "assignee": assignee}


async def scrape_public_sentiment(company_name: str, db: AsyncSession) -> dict[str, Any]:
    now = datetime.now(timezone.utc)
    cached = await db.scalar(
        select(WebIntelligenceCache).where(
            WebIntelligenceCache.target_entity == company_name,
            WebIntelligenceCache.expires_at > now,
        )
    )
    if cached:
        return {"company_name": company_name, "cached": True, "data": cached.scraped_data}

    try:
        data = await _scrape_review_sites(company_name)
    except Exception as exc:
        return {"company_name": company_name, "cached": False, "error": str(exc), "data": {"mentions": []}}

    cache = WebIntelligenceCache(
        target_entity=company_name,
        source_url="trustpilot,g2",
        scraped_data=data,
        scraped_at=now,
        expires_at=now + timedelta(hours=settings.scrape_cache_ttl_hours),
    )
    db.add(cache)
    await db.commit()
    return {"company_name": company_name, "cached": False, "data": data}


async def flag_for_legal(email_id: str, issue_type: str, db: AsyncSession) -> dict[str, Any]:
    email = await db.get(Email, _uuid(email_id))
    if email is None:
        return {"ok": False, "error": "Email not found", "email_id": email_id}

    email.urgency = "Critical"
    action = Action(
        email_id=email.id,
        action_type="Legal-Flag",
        agent_reasoning_log={"issue_type": issue_type},
    )
    db.add(action)
    await db.flush()
    db.add(
        AuditLog(
            entity_type="email",
            entity_id=email.id,
            action="flagged_for_legal",
            performed_by="agent",
            diff={"issue_type": issue_type, "action_id": str(action.id)},
        )
    )
    await db.commit()
    return {"ok": True, "email_id": str(email.id), "action_id": str(action.id), "issue_type": issue_type}


async def send_auto_reply(email_id: str, draft_id: str, db: AsyncSession) -> dict[str, Any]:
    email = await db.get(Email, _uuid(email_id))
    if email is None:
        return {"ok": False, "error": "Email not found", "email_id": email_id}
    action = await db.get(Action, _uuid(draft_id))
    if action is None:
        return {"ok": False, "error": "Draft action not found", "draft_id": draft_id}

    action.is_approved = True
    action.executed_at = datetime.now(timezone.utc)
    email.status = "Replied"
    db.add(
        AuditLog(
            entity_type="email",
            entity_id=email.id,
            action="auto_reply_sent",
            performed_by="agent",
            diff={"draft_id": draft_id},
        )
    )
    await db.commit()
    return {"ok": True, "email_id": str(email.id), "draft_id": draft_id, "status": "Replied"}


def _risk_level(churn_risk_score: float, open_thread_count: int) -> str:
    if churn_risk_score >= 0.7 or open_thread_count >= 3:
        return "High"
    if churn_risk_score >= 0.35 or open_thread_count >= 1:
        return "Medium"
    return "Low"


def _uuid(value: str) -> UUID:
    return value if isinstance(value, UUID) else UUID(str(value))


async def _scrape_review_sites(company_name: str) -> dict[str, Any]:
    urls = [
        f"https://www.trustpilot.com/search?query={company_name}",
        f"https://www.g2.com/search?query={company_name}",
    ]
    mentions = []
    async with httpx.AsyncClient(timeout=settings.scrape_timeout_seconds, follow_redirects=True) as client:
        for url in urls:
            response = await client.get(url)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")
            text = " ".join(soup.get_text(" ").split())[:1200]
            mentions.append({"source_url": url, "summary_text": text})
    return {"mentions": mentions, "scraped_at": datetime.now(timezone.utc).isoformat()}
