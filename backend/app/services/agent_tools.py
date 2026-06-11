import json
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any
from uuid import UUID

import httpx
from bs4 import BeautifulSoup
from groq import AsyncGroq
from sqlalchemy import text

from app.config import settings
from app.services.rag_pipeline import retrieve_relevant_chunks
from app.services.web_scraper import scrape_trustpilot, scrape_g2
from app.services.llm_classifier import chat_with_retry


async def search_knowledge_base(query: str, db, embedder: Any) -> dict[str, Any]:
    chunks = await retrieve_relevant_chunks(query, embedder, db, top_k=3)
    return {"query": query, "chunks": chunks}


async def get_thread_history(sender_email: str, db) -> dict[str, Any]:
    result = await db.execute(
        text(
            """
            SELECT id, message_id, thread_id, subject, body, timestamp, category, urgency, sentiment_score, requires_human, confidence, status
            FROM emails
            WHERE sender = :sender
            ORDER BY timestamp ASC
            """
        ),
        {"sender": sender_email},
    )
    emails = result.fetchall()
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


async def get_contact_profile(email: str, db) -> dict[str, Any]:
    contact = (
        await db.execute(
            text(
                "SELECT id, email, name, company, status, account_value, churn_risk_score, last_contact_at FROM contacts WHERE email = :email"
            ),
            {"email": email},
        )
    ).fetchone()

    open_thread_count = await db.scalar(
        text("SELECT COUNT(id) FROM threads WHERE sender_email = :email AND status = 'Open'"),
        {"email": email},
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


async def check_account_status(email: str, db) -> dict[str, Any]:
    contact = (
        await db.execute(
            text("SELECT status, account_value FROM contacts WHERE email = :email"),
            {"email": email},
        )
    ).fetchone()

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


async def draft_reply(context: str, tone: str, policy_refs: list[str], db) -> dict[str, Any]:
    try:
        if not settings.groq_api_key or settings.groq_api_key == "your_groq_key":
            raise ValueError("Groq API key is not configured")
        client = AsyncGroq(api_key=settings.groq_api_key)
        response = await chat_with_retry(
            client,
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


async def escalate_to_human(email_id: str, reason: str, priority: str, db) -> dict[str, Any]:
    email = (
        await db.execute(
            text("SELECT id FROM emails WHERE id = :id"),
            {"id": _uuid(email_id)},
        )
    ).fetchone()
    if email is None:
        return {"ok": False, "error": "Email not found", "email_id": email_id}

    await db.execute(
        text("UPDATE emails SET status = 'Escalated' WHERE id = :id"),
        {"id": email.id},
    )

    action_id = uuid.uuid4()
    await db.execute(
        text(
            """
            INSERT INTO actions (id, email_id, action_type, agent_reasoning_log, proposed_content, is_approved, approved_by, executed_at)
            VALUES (:id, :email_id, 'Escalate', :reasoning, NULL, FALSE, NULL, NULL)
            """
        ),
        {
            "id": action_id,
            "email_id": email.id,
            "reasoning": json.dumps({"reason": reason, "priority": priority}),
        },
    )

    audit_id = uuid.uuid4()
    await db.execute(
        text(
            """
            INSERT INTO audit_log (id, entity_type, entity_id, action, performed_by, timestamp, diff)
            VALUES (:id, 'email', :entity_id, 'escalated_to_human', 'agent', :timestamp, :diff)
            """
        ),
        {
            "id": audit_id,
            "entity_id": email.id,
            "timestamp": datetime.now(timezone.utc),
            "diff": json.dumps({"reason": reason, "priority": priority, "action_id": str(action_id)}),
        },
    )
    await db.commit()
    return {"ok": True, "email_id": str(email.id), "action_id": str(action_id), "priority": priority, "reason": reason}


async def create_internal_ticket(title: str, body: str, assignee: str, db, email_id: str | None = None) -> dict[str, Any]:
    action_id = uuid.uuid4()
    email_uuid = _uuid(email_id) if email_id else None
    await db.execute(
        text(
            """
            INSERT INTO actions (id, email_id, action_type, proposed_content, agent_reasoning_log, is_approved, approved_by, executed_at)
            VALUES (:id, :email_id, 'Ticket-Created', :body, :reasoning, FALSE, NULL, NULL)
            """
        ),
        {
            "id": action_id,
            "email_id": email_uuid,
            "body": body,
            "reasoning": json.dumps({"title": title, "assignee": assignee}),
        },
    )

    audit_id = uuid.uuid4()
    await db.execute(
        text(
            """
            INSERT INTO audit_log (id, entity_type, entity_id, action, performed_by, timestamp, diff)
            VALUES (:id, 'action', :entity_id, 'internal_ticket_created', 'agent', :timestamp, :diff)
            """
        ),
        {
            "id": audit_id,
            "entity_id": action_id,
            "timestamp": datetime.now(timezone.utc),
            "diff": json.dumps({"title": title, "assignee": assignee}),
        },
    )
    await db.commit()
    return {"ok": True, "ticket_id": str(action_id), "title": title, "assignee": assignee}


async def scrape_public_sentiment(company_name: str, db) -> dict[str, Any]:
    now = datetime.now(timezone.utc)
    cached = (
        await db.execute(
            text("SELECT scraped_data FROM web_intelligence_cache WHERE target_entity = :company AND expires_at > :now"),
            {"company": company_name, "now": now},
        )
    ).fetchone()
    if cached:
        return {"company_name": company_name, "cached": True, "data": cached.scraped_data}

    try:
        data = await _scrape_review_sites(company_name)
    except Exception as exc:
        return {"company_name": company_name, "cached": False, "error": str(exc), "data": {"mentions": []}}

    cache_id = uuid.uuid4()
    await db.execute(
        text(
            """
            INSERT INTO web_intelligence_cache (id, target_entity, source_url, scraped_data, scraped_at, expires_at)
            VALUES (:id, :target_entity, :source_url, :scraped_data, :scraped_at, :expires_at)
            """
        ),
        {
            "id": cache_id,
            "target_entity": company_name,
            "source_url": "trustpilot,g2",
            "scraped_data": json.dumps(data),
            "scraped_at": now,
            "expires_at": now + timedelta(hours=settings.scrape_cache_ttl_hours),
        },
    )
    await db.commit()
    return {"company_name": company_name, "cached": False, "data": data}


async def flag_for_legal(email_id: str, issue_type: str, db) -> dict[str, Any]:
    email = (
        await db.execute(
            text("SELECT id FROM emails WHERE id = :id"),
            {"id": _uuid(email_id)},
        )
    ).fetchone()
    if email is None:
        return {"ok": False, "error": "Email not found", "email_id": email_id}

    await db.execute(
        text("UPDATE emails SET urgency = 'Critical' WHERE id = :id"),
        {"id": email.id},
    )

    action_id = uuid.uuid4()
    await db.execute(
        text(
            """
            INSERT INTO actions (id, email_id, action_type, agent_reasoning_log, proposed_content, is_approved, approved_by, executed_at)
            VALUES (:id, :email_id, 'Legal-Flag', :reasoning, NULL, FALSE, NULL, NULL)
            """
        ),
        {
            "id": action_id,
            "email_id": email.id,
            "reasoning": json.dumps({"issue_type": issue_type}),
        },
    )

    audit_id = uuid.uuid4()
    await db.execute(
        text(
            """
            INSERT INTO audit_log (id, entity_type, entity_id, action, performed_by, timestamp, diff)
            VALUES (:id, 'email', :entity_id, 'flagged_for_legal', 'agent', :timestamp, :diff)
            """
        ),
        {
            "id": audit_id,
            "entity_id": email.id,
            "timestamp": datetime.now(timezone.utc),
            "diff": json.dumps({"issue_type": issue_type, "action_id": str(action_id)}),
        },
    )
    await db.commit()
    return {"ok": True, "email_id": str(email.id), "action_id": str(action_id), "issue_type": issue_type}


async def send_auto_reply(email_id: str, draft_id: str, db) -> dict[str, Any]:
    email = (
        await db.execute(
            text("SELECT id FROM emails WHERE id = :id"),
            {"id": _uuid(email_id)},
        )
    ).fetchone()
    if email is None:
        return {"ok": False, "error": "Email not found", "email_id": email_id}
    action = (
        await db.execute(
            text("SELECT id FROM actions WHERE id = :id"),
            {"id": _uuid(draft_id)},
        )
    ).fetchone()
    if action is None:
        return {"ok": False, "error": "Draft action not found", "draft_id": draft_id}

    now = datetime.now(timezone.utc)
    await db.execute(
        text("UPDATE actions SET is_approved = TRUE, executed_at = :now WHERE id = :id"),
        {"now": now, "id": action.id},
    )
    await db.execute(
        text("UPDATE emails SET status = 'Replied' WHERE id = :id"),
        {"id": email.id},
    )

    audit_id = uuid.uuid4()
    await db.execute(
        text(
            """
            INSERT INTO audit_log (id, entity_type, entity_id, action, performed_by, timestamp, diff)
            VALUES (:id, 'email', :entity_id, 'auto_reply_sent', 'agent', :timestamp, :diff)
            """
        ),
        {
            "id": audit_id,
            "entity_id": email.id,
            "timestamp": now,
            "diff": json.dumps({"draft_id": draft_id}),
        },
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
    trustpilot_res = await scrape_trustpilot(company_name)
    g2_res = await scrape_g2(company_name)
    return {
        "trustpilot": trustpilot_res,
        "g2": g2_res,
        "scraped_at": datetime.now(timezone.utc).isoformat(),
    }

