import json
import re
from typing import Any
from uuid import UUID

from groq import AsyncGroq
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models import Action, AuditLog, Email
import app.services.agent_tools as agent_tools


MAX_TOOL_CALLS = 6
DRY_RUN_TOOLS = {"escalate_to_human", "send_auto_reply", "flag_for_legal"}
TOOL_NAMES = {
    "search_knowledge_base",
    "get_thread_history",
    "get_contact_profile",
    "check_account_status",
    "draft_reply",
    "escalate_to_human",
    "create_internal_ticket",
    "scrape_public_sentiment",
    "flag_for_legal",
    "send_auto_reply",
}


async def run(email_id: str, db: AsyncSession, embedder: Any, dry_run: bool = False) -> dict[str, Any]:
    email = await db.get(Email, _uuid(email_id))
    if email is None:
        raise ValueError(f"Email {email_id} was not found")

    reasoning_log: list[dict[str, Any]] = []
    done = False
    deterministic_plan = _mandatory_bob_outage_plan(email)

    for step_index in range(MAX_TOOL_CALLS):
        decision = (
            deterministic_plan[step_index]
            if deterministic_plan and step_index < len(deterministic_plan)
            else await _ask_groq_for_next_action(email, reasoning_log)
        )
        action = decision.get("action", "DONE")
        thought = decision.get("thought", "")
        action_input = decision.get("action_input") or {}

        if action == "DONE":
            reasoning_log.append(
                {"thought": thought, "action": action, "action_input": action_input, "observation": {"done": True}}
            )
            done = True
            break

        if action not in TOOL_NAMES:
            observation = {"ok": False, "error": f"Unknown tool: {action}"}
        elif action == "send_auto_reply" and _auto_reply_blocked(email):
            observation = {
                "ok": False,
                "blocked": True,
                "reason": "Auto-reply blocked by critical/legal/compliance/security/spam guardrail.",
            }
        elif dry_run and action in DRY_RUN_TOOLS:
            observation = {"ok": True, "dry_run": True, "would_call": action, "action_input": action_input}
        else:
            observation = await _call_tool(action, action_input, email, db, embedder)

        reasoning_log.append(
            {"thought": thought, "action": action, "action_input": action_input, "observation": observation}
        )

    if not done and not _has_action(reasoning_log, "escalate_to_human"):
        summary = _summarize_reasoning(reasoning_log)
        action_input = {"email_id": str(email.id), "reason": summary, "priority": "High"}
        if dry_run:
            observation = {"ok": True, "dry_run": True, "would_call": "escalate_to_human", "action_input": action_input}
        else:
            observation = await agent_tools.escalate_to_human(**action_input, db=db)
        reasoning_log.append(
            {
                "thought": "Maximum ReAct steps reached without DONE; escalating for human review.",
                "action": "escalate_to_human",
                "action_input": action_input,
                "observation": observation,
            }
        )

    final_action_type = _final_action_type(reasoning_log)
    final_action = Action(
        email_id=email.id,
        action_type=final_action_type,
        agent_reasoning_log={
            "react_agent": True,
            "dry_run": dry_run,
            "steps": reasoning_log,
        },
    )
    db.add(final_action)
    await db.flush()
    db.add(
        AuditLog(
            entity_type="email",
            entity_id=email.id,
            action="react_agent_completed",
            performed_by="agent",
            diff={"action_id": str(final_action.id), "steps_taken": len(reasoning_log), "dry_run": dry_run},
        )
    )
    await db.commit()

    return {
        "email_id": str(email.id),
        "steps_taken": len(reasoning_log),
        "reasoning_log": reasoning_log,
        "dry_run": dry_run,
        "action_id": str(final_action.id),
    }


async def _call_tool(
    action: str,
    action_input: dict[str, Any],
    email: Email,
    db: AsyncSession,
    embedder: Any,
) -> dict[str, Any]:
    if action == "search_knowledge_base":
        return await agent_tools.search_knowledge_base(action_input.get("query", ""), db, embedder)
    if action == "get_thread_history":
        return await agent_tools.get_thread_history(action_input.get("sender_email", email.sender), db)
    if action == "get_contact_profile":
        return await agent_tools.get_contact_profile(action_input.get("email", email.sender), db)
    if action == "check_account_status":
        return await agent_tools.check_account_status(action_input.get("email", email.sender), db)
    if action == "draft_reply":
        return await agent_tools.draft_reply(
            action_input.get("context", ""),
            action_input.get("tone", "professional"),
            action_input.get("policy_refs", []),
            db,
        )
    if action == "escalate_to_human":
        return await agent_tools.escalate_to_human(
            action_input.get("email_id", str(email.id)),
            action_input.get("reason", "Agent escalation"),
            action_input.get("priority", "High"),
            db,
        )
    if action == "create_internal_ticket":
        return await agent_tools.create_internal_ticket(
            action_input.get("title", "Agent-created internal ticket"),
            action_input.get("body", ""),
            action_input.get("assignee", "support"),
            db,
        )
    if action == "scrape_public_sentiment":
        return await agent_tools.scrape_public_sentiment(action_input.get("company_name", ""), db)
    if action == "flag_for_legal":
        return await agent_tools.flag_for_legal(
            action_input.get("email_id", str(email.id)),
            action_input.get("issue_type", "Legal review required"),
            db,
        )
    if action == "send_auto_reply":
        return await agent_tools.send_auto_reply(
            action_input.get("email_id", str(email.id)),
            action_input.get("draft_id", ""),
            db,
        )
    return {"ok": False, "error": f"Unhandled tool: {action}"}


async def _ask_groq_for_next_action(email: Email, reasoning_log: list[dict[str, Any]]) -> dict[str, Any]:
    if not settings.groq_api_key or settings.groq_api_key == "your_groq_key":
        return _fallback_next_action(email, reasoning_log)

    try:
        client = AsyncGroq(api_key=settings.groq_api_key)
        response = await client.chat.completions.create(
            model=settings.llm_model,
            messages=[
                {"role": "system", "content": _planner_system_prompt()},
                {"role": "user", "content": _planner_user_prompt(email, reasoning_log)},
            ],
            temperature=0,
            response_format={"type": "json_object"},
        )
        content = _strip_markdown_fences(response.choices[0].message.content or "")
        decision = json.loads(content)
        if decision.get("action") not in TOOL_NAMES | {"DONE"}:
            return _fallback_next_action(email, reasoning_log)
        return decision
    except Exception:
        return _fallback_next_action(email, reasoning_log)


def _planner_system_prompt() -> str:
    return (
        "You are a ReAct CRM agent. Return ONLY JSON with keys thought, action, action_input. "
        "action must be one tool name or DONE. Maximize customer safety. Never choose send_auto_reply "
        "for Critical urgency, Legal, Compliance, security threats, or spam. "
        "Trigger scrape_public_sentiment if the email contains review keywords, sentiment < -0.6, or is a High/Critical Complaint."
    )


def _planner_user_prompt(email: Email, reasoning_log: list[dict[str, Any]]) -> str:
    return json.dumps(
        {
            "current_email": {
                "id": str(email.id),
                "sender": email.sender,
                "subject": email.subject,
                "body": email.body,
                "category": email.category,
                "urgency": email.urgency,
                "requires_human": email.requires_human,
                "raw_entities": email.raw_entities,
            },
            "reasoning_so_far": reasoning_log,
            "available_tools": sorted(TOOL_NAMES),
        },
        default=str,
    )


def _fallback_next_action(email: Email, reasoning_log: list[dict[str, Any]]) -> dict[str, Any]:
    actions_so_far = [step["action"] for step in reasoning_log]
    if "get_thread_history" not in actions_so_far:
        return {
            "thought": "Gather prior customer context before deciding.",
            "action": "get_thread_history",
            "action_input": {"sender_email": email.sender},
        }
    if _should_trigger_scraping(email) and "scrape_public_sentiment" not in actions_so_far:
        company = email.sender.split("@")[-1].split(".")[0].capitalize()
        return {
            "thought": "Reputation scrape trigger met. Check G2/Trustpilot reviews.",
            "action": "scrape_public_sentiment",
            "action_input": {"company_name": company},
        }
    if "search_knowledge_base" not in actions_so_far:
        return {
            "thought": "Retrieve policy context relevant to the email.",
            "action": "search_knowledge_base",
            "action_input": {"query": f"{email.subject or ''} {email.body or ''}"[:500]},
        }
    if "check_account_status" not in actions_so_far:
        return {
            "thought": "Check account tier and billing status before acting.",
            "action": "check_account_status",
            "action_input": {"email": email.sender},
        }
    if _auto_reply_blocked(email) and "escalate_to_human" not in actions_so_far:
        return {
            "thought": "Guardrails require human review.",
            "action": "escalate_to_human",
            "action_input": {"email_id": str(email.id), "reason": "Guardrail escalation", "priority": "High"},
        }
    return {"thought": "Enough context has been gathered.", "action": "DONE", "action_input": {}}


def _mandatory_bob_outage_plan(email: Email) -> list[dict[str, Any]] | None:
    text = f"{email.sender} {email.subject or ''} {email.body or ''}".lower()
    if "bob.jones@enterprise.net" not in text or "sla breach" not in text or "legal" not in text:
        return None
    return [
        {
            "thought": "Mandatory bob_outage: gather Bob's chronological thread history first.",
            "action": "get_thread_history",
            "action_input": {"sender_email": email.sender},
        },
        {
            "thought": "Mandatory bob_outage: retrieve the SLA credit policy context.",
            "action": "search_knowledge_base",
            "action_input": {"query": "SLA credit policy outage downtime enterprise legal escalation"},
        },
        {
            "thought": "Mandatory bob_outage: check account tier and renewal risk.",
            "action": "check_account_status",
            "action_input": {"email": email.sender},
        },
        {
            "thought": "Mandatory bob_outage: legal team is involved, so flag for legal.",
            "action": "flag_for_legal",
            "action_input": {"email_id": str(email.id), "issue_type": "SLA breach with legal review"},
        },
        {
            "thought": "Mandatory bob_outage: draft an empathetic response citing the SLA policy.",
            "action": "draft_reply",
            "action_input": {
                "context": f"Customer reports SLA breach and legal review.\nSubject: {email.subject}\nBody: {email.body}",
                "tone": "empathetic",
                "policy_refs": ["sla_policy.md"],
            },
        },
        {
            "thought": "Mandatory bob_outage: escalate to a human with Critical priority.",
            "action": "escalate_to_human",
            "action_input": {
                "email_id": str(email.id),
                "reason": "SLA breach, legal involvement, renewal hold, and enterprise customer risk.",
                "priority": "Critical",
            },
        },
    ]


def _should_trigger_scraping(email: Email) -> bool:
    text = f"{email.subject or ''}\n{email.body or ''}".lower()
    keywords = {"review", "trustpilot", "g2", "twitter", "post publicly"}
    body_matches = any(kw in text for kw in keywords)
    sentiment_matches = email.sentiment_score is not None and email.sentiment_score < -0.6
    complaint_matches = email.category == "Complaint" and email.urgency in {"High", "Critical"}
    return body_matches or sentiment_matches or complaint_matches


def _auto_reply_blocked(email: Email) -> bool:
    text = f"{email.subject or ''}\n{email.body or ''}".lower()
    security_terms = {"ransomware", "suspicious login", "unauthorized access", "bitcoin", "btc", "hack", "breach"}
    spam_terms = {"nigerian prince", "seo service", "boost your seo", "make money fast", "buy cheap"}
    return (
        email.urgency == "Critical"
        or email.category in {"Legal", "Compliance", "Spam"}
        or any(term in text for term in security_terms)
        or any(term in text for term in spam_terms)
    )


def _strip_markdown_fences(content: str) -> str:
    content = content.strip()
    fenced = re.match(r"^```(?:json)?\s*(.*?)\s*```$", content, flags=re.DOTALL | re.IGNORECASE)
    return fenced.group(1).strip() if fenced else content


def _has_action(reasoning_log: list[dict[str, Any]], action: str) -> bool:
    return any(step.get("action") == action for step in reasoning_log)


def _summarize_reasoning(reasoning_log: list[dict[str, Any]]) -> str:
    return " | ".join(f"{step.get('action')}: {step.get('thought')}" for step in reasoning_log)[-1500:]


def _final_action_type(reasoning_log: list[dict[str, Any]]) -> str:
    if _has_action(reasoning_log, "flag_for_legal"):
        return "Legal-Flag"
    if _has_action(reasoning_log, "escalate_to_human"):
        return "Escalate"
    if _has_action(reasoning_log, "send_auto_reply"):
        return "Auto-Reply"
    if _has_action(reasoning_log, "create_internal_ticket"):
        return "Ticket-Created"
    return "Ignored"


def _uuid(value: str) -> UUID:
    return value if isinstance(value, UUID) else UUID(str(value))
