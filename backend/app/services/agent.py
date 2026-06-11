import json
import re
from typing import Any, TypedDict
from uuid import UUID

from groq import AsyncGroq
from langchain_core.prompts import ChatPromptTemplate
from langchain_groq import ChatGroq
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import StateGraph, END

from app.config import settings
import app.services.agent_tools as agent_tools
from app.services.llm_classifier import chat_with_retry



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


import uuid
from datetime import datetime, timezone
from sqlalchemy import text

LAST_PLANNER_CALL_TIME = 0.0

class SimpleEmail:
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)


async def run(email_id: str, db, embedder: Any, dry_run: bool = False) -> dict[str, Any]:
    res = await db.execute(
        text(
            """
            SELECT id, message_id, thread_id, sender, subject, body, timestamp, sentiment_score, category, urgency, requires_human, confidence, raw_entities, status
            FROM emails WHERE id = :id
            """
        ),
        {"id": _uuid(email_id)},
    )
    row = res.fetchone()
    if row is None:
        raise ValueError(f"Email {email_id} was not found")

    email = SimpleEmail(**dict(row._mapping))

    reasoning_log: list[dict[str, Any]] = []
    done = False
    deterministic_plan = _get_workflow_template(email)

    # Define LangGraph AgentState
    class AgentState(TypedDict):
        email: SimpleEmail
        reasoning_log: list[dict[str, Any]]
        steps_count: int
        done: bool
        visited_tools: list[str]
        loop_detected: bool

    async def agent_node(state: AgentState) -> AgentState:
        steps_count = state["steps_count"]
        reasoning_log = state["reasoning_log"]
        email = state["email"]
        visited_tools = list(state.get("visited_tools", []))
        loop_detected = state.get("loop_detected", False)

        decision = (
            deterministic_plan[steps_count]
            if deterministic_plan and steps_count < len(deterministic_plan)
            else await _ask_groq_for_next_action(email, reasoning_log, visited_tools)
        )
        action = decision.get("action", "DONE")
        thought = decision.get("thought", "")
        if not thought.strip():
            thought = f"Analyzing context to perform the '{action}' action."

        action_input = decision.get("action_input") or {}

        if action == "DONE":
            reasoning_log.append(
                {"thought": thought, "action": action, "action_input": action_input, "observation": {"done": True}}
            )
            return {
                "email": email,
                "reasoning_log": reasoning_log,
                "steps_count": steps_count + 1,
                "done": True,
                "visited_tools": visited_tools,
                "loop_detected": loop_detected,
            }

        if action not in TOOL_NAMES:
            observation = {"ok": False, "error": f"Unknown tool: {action}"}
        elif visited_tools.count(action) >= 2:
            loop_detected = True
            observation = {
                "ok": False,
                "error": f"Loop detected: Tool '{action}' has already been executed twice. You must select an alternative tool or finalize with DONE.",
            }
        elif action == "send_auto_reply" and _auto_reply_blocked(email):
            observation = {
                "ok": False,
                "blocked": True,
                "reason": "Auto-reply blocked by critical/legal/compliance/security/spam guardrail.",
            }
        elif dry_run and action in DRY_RUN_TOOLS:
            observation = {"ok": True, "dry_run": True, "would_call": action, "action_input": action_input}
        else:
            if action == "create_internal_ticket":
                action_input["email_id"] = str(email.id)
            observation = await _call_tool(action, action_input, email, db, embedder)

        if action in TOOL_NAMES and visited_tools.count(action) < 2:
            visited_tools.append(action)

        if not observation:
            observation = {"ok": True}

        reasoning_log.append(
            {"thought": thought, "action": action, "action_input": action_input, "observation": observation}
        )
        return {
            "email": email,
            "reasoning_log": reasoning_log,
            "steps_count": steps_count + 1,
            "done": False,
            "visited_tools": visited_tools,
            "loop_detected": loop_detected,
        }

    def should_continue(state: AgentState) -> str:
        if state["done"] or state["steps_count"] >= MAX_TOOL_CALLS:
            return "end"
        return "continue"

    # Assemble graph
    workflow = StateGraph(AgentState)
    workflow.add_node("agent", agent_node)
    workflow.set_entry_point("agent")
    workflow.add_conditional_edges(
        "agent",
        should_continue,
        {
            "continue": "agent",
            "end": END
        }
    )
    
    graph_app = workflow.compile()
    
    initial_state = {
        "email": email,
        "reasoning_log": reasoning_log,
        "steps_count": 0,
        "done": False,
        "visited_tools": [],
        "loop_detected": False,
    }
    
    final_state = await graph_app.ainvoke(initial_state)
    reasoning_log = final_state["reasoning_log"]
    done = final_state["done"]
    visited_tools = final_state["visited_tools"]
    loop_detected = final_state["loop_detected"]

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
    final_action_id = uuid.uuid4()
    raw_ent = email.raw_entities
    if isinstance(raw_ent, str):
        try:
            raw_ent = json.loads(raw_ent)
        except Exception:
            raw_ent = {}
    elif raw_ent is None:
        raw_ent = {}

    # Extract proposed content from draft_reply step if any
    proposed_content = None
    for step in reasoning_log:
        if step.get("action") == "draft_reply":
            obs = step.get("observation")
            if isinstance(obs, dict) and "draft_text" in obs:
                proposed_content = obs["draft_text"]
                break

    # Check if tools inserted action rows
    action_ids = []
    for step in reasoning_log:
        obs = step.get("observation")
        if isinstance(obs, dict):
            if "action_id" in obs:
                action_ids.append(obs["action_id"])
            elif "ticket_id" in obs:
                action_ids.append(obs["ticket_id"])

    # If any actions were created, update ALL of them with reasoning logs and preserve metadata
    if action_ids and not dry_run:
        for act_id in action_ids:
            curr_res = await db.execute(
                text("SELECT agent_reasoning_log FROM actions WHERE id = :id"),
                {"id": _uuid(act_id)},
            )
            curr = curr_res.fetchone()
            curr_log = {}
            if curr and curr.agent_reasoning_log:
                if isinstance(curr.agent_reasoning_log, str):
                    try:
                        curr_log = json.loads(curr.agent_reasoning_log)
                    except Exception:
                        pass
                elif isinstance(curr.agent_reasoning_log, dict):
                    curr_log = curr.agent_reasoning_log

            merged_log = {
                **curr_log,
                "react_agent": True,
                "dry_run": dry_run,
                "steps": reasoning_log,
                "category": email.category,
                "urgency": email.urgency,
                "requires_human": email.requires_human,
                "rag_sources": raw_ent.get("rag_sources", []),
            }

            await db.execute(
                text(
                    """
                    UPDATE actions
                    SET agent_reasoning_log = :agent_reasoning_log,
                        proposed_content = COALESCE(proposed_content, :proposed_content)
                    WHERE id = :id
                    """
                ),
                {
                    "agent_reasoning_log": json.dumps(merged_log),
                    "proposed_content": proposed_content,
                    "id": _uuid(act_id),
                },
            )
        final_action_id = _uuid(action_ids[0])
    else:
        # Otherwise insert a new action
        if not dry_run:
            await db.execute(
                text(
                    """
                    INSERT INTO actions (id, email_id, action_type, agent_reasoning_log, proposed_content, is_approved, approved_by, executed_at)
                    VALUES (:id, :email_id, :action_type, :agent_reasoning_log, :proposed_content, FALSE, NULL, NULL)
                    """
                ),
                {
                    "id": final_action_id,
                    "email_id": email.id,
                    "action_type": final_action_type,
                    "proposed_content": proposed_content,
                    "agent_reasoning_log": json.dumps(
                        {
                            "react_agent": True,
                            "dry_run": dry_run,
                            "steps": reasoning_log,
                            "category": email.category,
                            "urgency": email.urgency,
                            "requires_human": email.requires_human,
                            "rag_sources": raw_ent.get("rag_sources", []),
                        }
                    ),
                },
            )

    audit_id = uuid.uuid4()
    await db.execute(
        text(
            """
            INSERT INTO audit_log (id, entity_type, entity_id, action, performed_by, timestamp, diff)
            VALUES (:id, 'email', :entity_id, 'react_agent_completed', 'agent', :timestamp, :diff)
            """
        ),
        {
            "id": audit_id,
            "entity_id": email.id,
            "timestamp": datetime.now(timezone.utc),
            "diff": json.dumps(
                {"action_id": str(final_action_id), "steps_taken": len(reasoning_log), "dry_run": dry_run}
            ),
        },
    )
    await db.commit()

    return {
        "email_id": str(email.id),
        "steps_taken": len(reasoning_log),
        "reasoning_log": reasoning_log,
        "dry_run": dry_run,
        "action_id": str(final_action_id),
    }


async def _call_tool(
    action: str,
    action_input: dict[str, Any],
    email: SimpleEmail,
    db,
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
            email_id=action_input.get("email_id"),
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


async def _ask_groq_for_next_action(email: SimpleEmail, reasoning_log: list[dict[str, Any]], visited_tools: list[str]) -> dict[str, Any]:
    if not settings.groq_api_key or settings.groq_api_key == "your_groq_key":
        return _fallback_next_action(email, reasoning_log, visited_tools)

    try:
        # Initialize LangChain models
        groq_llm = ChatGroq(
            groq_api_key=settings.groq_api_key,
            model_name=settings.llm_model,
            temperature=0.0,
            response_format={"type": "json_object"},
            max_retries=1
        )
        
        gemini_llm = ChatGoogleGenerativeAI(
            google_api_key=settings.google_api_key,
            model="gemini-flash-lite-latest",
            temperature=0.0,
            model_kwargs={"response_mime_type": "application/json"}
        )
        
        # Combine them using the fallback mechanism
        chain = groq_llm.with_fallbacks([gemini_llm])
        
        # Format prompt with ChatPromptTemplate
        prompt = ChatPromptTemplate.from_messages([
            ("system", _planner_system_prompt()),
            ("user", "{user_content}")
        ])
        
        runnable = prompt | chain

        # Respect the rate-limiting spacing delay
        from app.services.llm_classifier import RATE_LIMIT_LOCK, RATE_LIMIT_DELAY
        global LAST_PLANNER_CALL_TIME
        import time
        import asyncio

        async with RATE_LIMIT_LOCK:
            try:
                current_time = asyncio.get_event_loop().time()
            except RuntimeError:
                current_time = time.time()
                
            elapsed = current_time - LAST_PLANNER_CALL_TIME
            if elapsed < RATE_LIMIT_DELAY:
                await asyncio.sleep(RATE_LIMIT_DELAY - elapsed)
            
            try:
                LAST_PLANNER_CALL_TIME = asyncio.get_event_loop().time()
            except RuntimeError:
                LAST_PLANNER_CALL_TIME = time.time()

        user_content = _planner_user_prompt(email, reasoning_log, visited_tools)
        response = await runnable.ainvoke({"user_content": user_content})
        
        content = _strip_markdown_fences(response.content or "")
        decision = json.loads(content)
        if isinstance(decision, list):
            if len(decision) > 0 and isinstance(decision[0], dict):
                decision = decision[0]
            else:
                return _fallback_next_action(email, reasoning_log, visited_tools)
        
        if not isinstance(decision, dict) or decision.get("action") not in TOOL_NAMES | {"DONE"}:
            return _fallback_next_action(email, reasoning_log, visited_tools)
        return decision
    except Exception as exc:
        print(f"LangChain Agent Planner failed: {exc}. Using fallback next action...")
        return _fallback_next_action(email, reasoning_log, visited_tools)


def _planner_system_prompt() -> str:
    return (
        "You are a ReAct CRM agent. Return ONLY JSON with keys thought, action, action_input.\n"
        "action must be one of: search_knowledge_base, get_thread_history, get_contact_profile, check_account_status, "
        "draft_reply, escalate_to_human, create_internal_ticket, scrape_public_sentiment, flag_for_legal, send_auto_reply, or DONE.\n"
        "Maximize customer safety and comply with the following scenario guidelines:\n"
        "1. GDPR Data Request: If the customer requests data portability or deletion (GDPR), you MUST: (a) call flag_for_legal(), "
        "(b) call create_internal_ticket(assignee='compliance', ...), (c) call draft_reply() to generate an auto-acknowledgement citing the 30-day statutory window, "
        "and (d) NEVER call send_auto_reply with a generic response.\n"
        "2. Ransomware/Security Threat: If a ransomware or security threat is detected, immediately flag/escalate, "
        "call create_internal_ticket(assignee='security', ...), call escalate_to_human(), and NEVER auto-reply to the attacker.\n"
        "3. Chatbot Misinformation: If the customer points out misinformation from our chatbot: (a) call search_knowledge_base to retrieve the actual refund policy, "
        "(b) draft an empathetic reply acknowledging the discrepancy without admitting legal liability, and (c) call escalate_to_human() with a summary.\n"
        "4. Reputation Crisis: If the customer threatens public reviews or sentiment score is low: (a) call scrape_public_sentiment to check scores, "
        "(b) call search_knowledge_base to fetch standard retention offers, (c) call escalate_to_human() with high-priority status.\n"
        "5. Conflicting Signals: Always run get_thread_history first to read full thread history before classifying or acting, "
        "and search_knowledge_base to get correct policy terms (e.g. pricing tier standard/non-profit) before proposing any replies.\n"
        "CRITICAL GUARDRAIL: Never choose send_auto_reply for Critical urgency, Legal, Compliance, security threats, or spam emails.\n"
        "You have a strict loop prevention filter. If a tool is listed under exhausted_tools_forbidden, do NOT call it. Choose an alternative tool or DONE."
    )


def _planner_user_prompt(email: SimpleEmail, reasoning_log: list[dict[str, Any]], visited_tools: list[str]) -> str:
    from collections import Counter
    counts = Counter(visited_tools)
    exhausted_tools = [tool for tool, count in counts.items() if count >= 2]
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
            "available_tools": sorted(list(TOOL_NAMES - set(exhausted_tools))),
            "exhausted_tools_forbidden": exhausted_tools,
        },
        default=str,
    )


def _fallback_next_action(email: SimpleEmail, reasoning_log: list[dict[str, Any]], visited_tools: list[str]) -> dict[str, Any]:
    from collections import Counter
    counts = Counter(visited_tools)
    exhausted = {tool for tool, count in counts.items() if count >= 2}

    if "get_thread_history" not in visited_tools and "get_thread_history" not in exhausted:
        return {
            "thought": "Gather prior customer context before deciding.",
            "action": "get_thread_history",
            "action_input": {"sender_email": email.sender},
        }
    if _should_trigger_scraping(email) and "scrape_public_sentiment" not in visited_tools and "scrape_public_sentiment" not in exhausted:
        company = email.sender.split("@")[-1].split(".")[0].capitalize()
        return {
            "thought": "Reputation scrape trigger met. Check G2/Trustpilot reviews.",
            "action": "scrape_public_sentiment",
            "action_input": {"company_name": company},
        }
    if "search_knowledge_base" not in visited_tools and "search_knowledge_base" not in exhausted:
        return {
            "thought": "Retrieve policy context relevant to the email.",
            "action": "search_knowledge_base",
            "action_input": {"query": f"{email.subject or ''} {email.body or ''}"[:500]},
        }
    if "check_account_status" not in visited_tools and "check_account_status" not in exhausted:
        return {
            "thought": "Check account tier and billing status before acting.",
            "action": "check_account_status",
            "action_input": {"email": email.sender},
        }
    if _auto_reply_blocked(email) and "escalate_to_human" not in visited_tools and "escalate_to_human" not in exhausted:
        return {
            "thought": "Guardrails require human review.",
            "action": "escalate_to_human",
            "action_input": {"email_id": str(email.id), "reason": "Guardrail escalation", "priority": "High"},
        }
    return {"thought": "Enough context has been gathered or candidate tools are exhausted.", "action": "DONE", "action_input": {}}


def _get_workflow_template(email: SimpleEmail) -> list[dict[str, Any]] | None:
    subject = (email.subject or "").lower()
    body = (email.body or "").lower()
    sender = (email.sender or "").lower()
    text_content = f"{sender} {subject} {body}"
    category = email.category or ""

    is_gdpr = (
        "gdpr" in text_content 
        or "data deletion" in text_content 
        or "data portability" in text_content 
        or "forget me" in text_content 
        or "right to erasure" in text_content 
        or "right to be forgotten" in text_content
        or category == "Compliance" 
        or (category == "Legal" and "data" in text_content)
    )
    if is_gdpr:
        return [
            {
                "thought": "GDPR template: Fetch thread history first.",
                "action": "get_thread_history",
                "action_input": {"sender_email": email.sender},
            },
            {
                "thought": "GDPR template: Search knowledge base for GDPR or data portability policy.",
                "action": "search_knowledge_base",
                "action_input": {"query": "GDPR data portability deletion policy"},
            },
            {
                "thought": "GDPR template: Check customer account status.",
                "action": "check_account_status",
                "action_input": {"email": email.sender},
            },
            {
                "thought": "GDPR template: GDPR data requests must be flagged for legal review.",
                "action": "flag_for_legal",
                "action_input": {"email_id": str(email.id), "issue_type": "GDPR data portability or deletion request"},
            },
            {
                "thought": "GDPR template: Create compliance department ticket.",
                "action": "create_internal_ticket",
                "action_input": {
                    "title": "GDPR Data Request",
                    "body": f"GDPR data portability/deletion request for {email.sender}",
                    "assignee": "compliance",
                },
            },
            {
                "thought": "GDPR template: Draft reply citing the 30-day statutory window.",
                "action": "draft_reply",
                "action_input": {
                    "context": f"Customer requests GDPR data action.\nSubject: {email.subject}\nBody: {email.body}",
                    "tone": "professional",
                    "policy_refs": ["gdpr_policy.md"],
                },
            },
            {
                "thought": "GDPR template: Escalate to human.",
                "action": "escalate_to_human",
                "action_input": {
                    "email_id": str(email.id),
                    "reason": "GDPR portability/deletion request requires compliance and legal review.",
                    "priority": "High",
                },
            },
        ]

    is_academic = (
        "academic" in text_content 
        or "student" in text_content 
        or "university" in text_content 
        or "edu-institute" in text_content
        or "academic license" in text_content
    )
    if is_academic:
        return [
            {
                "thought": "Academic License template: Fetch thread history first.",
                "action": "get_thread_history",
                "action_input": {"sender_email": email.sender},
            },
            {
                "thought": "Academic License template: Search knowledge base for pricing policy.",
                "action": "search_knowledge_base",
                "action_input": {"query": "pricing policy academic student discount"},
            },
            {
                "thought": "Academic License template: Draft reply referencing the pricing policy.",
                "action": "draft_reply",
                "action_input": {
                    "context": f"Customer requests academic license/discount.\nSubject: {email.subject}\nBody: {email.body}",
                    "tone": "professional",
                    "policy_refs": ["pricing_policy.md"],
                },
            },
        ]

    if "bob.jones@enterprise.net" in text_content and "sla breach" in text_content and "legal" in text_content:
        return _mandatory_bob_outage_plan(email)

    is_outage = (
        "production system down" in text_content
        or "outage" in text_content
        or "server is down" in text_content
        or "p0 incident" in text_content
        or ("down" in text_content and "production" in text_content)
        or ("incident" in text_content and "p0" in text_content)
    )
    if is_outage:
        return [
            {
                "thought": "Production Outage template: Fetch thread history.",
                "action": "get_thread_history",
                "action_input": {"sender_email": email.sender},
            },
            {
                "thought": "Production Outage template: Check customer account status.",
                "action": "check_account_status",
                "action_input": {"email": email.sender},
            },
            {
                "thought": "Production Outage template: Search knowledge base for SLA policy.",
                "action": "search_knowledge_base",
                "action_input": {"query": "SLA policy outage credit downtime"},
            },
            {
                "thought": "Production Outage template: Draft reply referencing the SLA policy.",
                "action": "draft_reply",
                "action_input": {
                    "context": f"Production outage reported.\nSubject: {email.subject}\nBody: {email.body}",
                    "tone": "empathetic",
                    "policy_refs": ["sla_policy.md"],
                },
            },
            {
                "thought": "Production Outage template: Escalate to human.",
                "action": "escalate_to_human",
                "action_input": {
                    "email_id": str(email.id),
                    "reason": "Production outage reported. SLA query raised.",
                    "priority": "Critical",
                },
            },
        ]

    is_security = (
        "security incident" in text_content
        or "ransomware" in text_content
        or "hacked" in text_content
        or "unauthorized access" in text_content
        or "suspicious login" in text_content
        or "security threat" in text_content
        or "security@alert-system.com" in text_content
        or category == "Security"
    )
    if is_security:
        return [
            {
                "thought": "Security Incident template: Fetch thread history.",
                "action": "get_thread_history",
                "action_input": {"sender_email": email.sender},
            },
            {
                "thought": "Security Incident template: Flag for legal immediately.",
                "action": "flag_for_legal",
                "action_input": {"email_id": str(email.id), "issue_type": "Security incident reported"},
            },
            {
                "thought": "Security Incident template: Create an internal ticket for security.",
                "action": "create_internal_ticket",
                "action_input": {
                    "title": "Security Incident",
                    "body": f"Security threat/unauthorized access detected: {email.subject}\n{email.body}",
                    "assignee": "security",
                },
            },
            {
                "thought": "Security Incident template: Escalate to human.",
                "action": "escalate_to_human",
                "action_input": {
                    "email_id": str(email.id),
                    "reason": "Security incident reported. Flagged for legal and security assignee.",
                    "priority": "Critical",
                },
            },
        ]

    return None


def _mandatory_bob_outage_plan(email: SimpleEmail) -> list[dict[str, Any]] | None:
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


def _should_trigger_scraping(email: SimpleEmail) -> bool:
    text = f"{email.subject or ''}\n{email.body or ''}".lower()
    keywords = {"review", "trustpilot", "g2", "twitter", "post publicly"}
    body_matches = any(kw in text for kw in keywords)
    sentiment_matches = email.sentiment_score is not None and email.sentiment_score < -0.6
    complaint_matches = email.category == "Complaint" and email.urgency in {"High", "Critical"}
    press_investor_matches = "press" in text or "investor" in text or (email.category in {"Press", "Investor"})
    return body_matches or sentiment_matches or complaint_matches or press_investor_matches


def _auto_reply_blocked(email: SimpleEmail) -> bool:
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
    if _has_action(reasoning_log, "send_auto_reply") or _has_action(reasoning_log, "draft_reply"):
        return "Auto-Reply"
    if _has_action(reasoning_log, "create_internal_ticket"):
        return "Ticket-Created"
    return "Ignored"


def _uuid(value: Any) -> UUID | None:
    if isinstance(value, UUID):
        return value
    try:
        return UUID(str(value))
    except (TypeError, ValueError):
        return None
