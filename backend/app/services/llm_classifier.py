import asyncio
import json
import re
from typing import Any
import httpx

from groq import AsyncGroq

from app.config import settings


import time

LAST_CALL_TIME = 0.0
RATE_LIMIT_DELAY = 15.0  # Spacing between Groq calls to respect the 6,000 TPM limit
RATE_LIMIT_LOCK = asyncio.Lock()


class GeminiMockMessage:
    def __init__(self, content: str):
        self.content = content


class GeminiMockChoice:
    def __init__(self, content: str):
        self.message = GeminiMockMessage(content)


class GeminiMockCompletion:
    def __init__(self, content: str):
        self.choices = [GeminiMockChoice(content)]


async def call_gemini_api(
    messages: list[dict],
    temperature: float | None = None,
    response_format: dict | None = None,
) -> str:
    system_prompt = None
    contents = []

    for msg in messages:
        role = msg.get("role")
        content = msg.get("content", "")
        if role == "system":
            system_prompt = content
        elif role == "user":
            contents.append({
                "role": "user",
                "parts": [{"text": content}]
            })
        elif role in ("assistant", "model"):
            contents.append({
                "role": "model",
                "parts": [{"text": content}]
            })

    payload = {
        "contents": contents
    }
    if system_prompt:
        payload["systemInstruction"] = {
            "parts": [{"text": system_prompt}]
        }

    generation_config = {}
    if temperature is not None:
        generation_config["temperature"] = temperature
    if response_format and response_format.get("type") == "json_object":
        generation_config["responseMimeType"] = "application/json"

    if generation_config:
        payload["generationConfig"] = generation_config

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-flash-lite-latest:generateContent?key={settings.google_api_key}"

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(url, json=payload)
        response.raise_for_status()
        res_data = response.json()

        candidates = res_data.get("candidates", [])
        if not candidates:
            raise ValueError("No candidates returned from Gemini API")

        parts = candidates[0].get("content", {}).get("parts", [])
        if not parts:
            raise ValueError("No parts returned in candidate content from Gemini API")

        return parts[0].get("text", "")


async def chat_with_retry(client: AsyncGroq, **kwargs) -> Any:
    global LAST_CALL_TIME
    max_attempts = 5
    backoff = 3.0

    async with RATE_LIMIT_LOCK:
        elapsed = asyncio.get_event_loop().time() - LAST_CALL_TIME
        if elapsed < RATE_LIMIT_DELAY:
            wait_time = RATE_LIMIT_DELAY - elapsed
            await asyncio.sleep(wait_time)
        LAST_CALL_TIME = asyncio.get_event_loop().time()

    for attempt in range(max_attempts):
        try:
            return await client.chat.completions.create(**kwargs)
        except Exception as exc:
            # Check if it is a rate limit or 429 error
            is_rate_limit = False
            exc_str = str(exc)
            if "rate_limit" in exc_str.lower() or "429" in exc_str or "rate limit" in exc_str.lower():
                is_rate_limit = True

            if is_rate_limit:
                if settings.google_api_key and settings.google_api_key != "your_google_key":
                    print("Groq Rate Limit (429) hit. Attempting fallback to Google Gemini...")
                    try:
                        gemini_content = await call_gemini_api(
                            messages=kwargs.get("messages", []),
                            temperature=kwargs.get("temperature"),
                            response_format=kwargs.get("response_format"),
                        )
                        print("Google Gemini fallback succeeded!")
                        return GeminiMockCompletion(gemini_content)
                    except Exception as gemini_exc:
                        print(f"Google Gemini fallback failed: {gemini_exc}. Continuing with Groq retry...")

            if is_rate_limit and attempt < max_attempts - 1:
                # Parse retry time if available, e.g. "try again in 7.97s" or "24m32.25s"
                wait_time = backoff
                match = re.search(r"try again in (\d+(?:\.\d+)?)s", exc_str)
                if match:
                    wait_time = float(match.group(1)) + 0.5
                else:
                    minute_match = re.search(r"try again in (?:(\d+)m)?(?:(\d+(?:\.\d+)?)s)?", exc_str)
                    if minute_match:
                        minutes = float(minute_match.group(1) or 0)
                        seconds = float(minute_match.group(2) or 0)
                        wait_time = (minutes * 60) + seconds + 0.5

                wait_time = min(30.0, max(1.0, wait_time))
                print(f"Groq Rate Limit (429) hit. Retrying in {wait_time:.2f} seconds... (Attempt {attempt + 1}/{max_attempts})")
                await asyncio.sleep(wait_time)
                backoff *= 2
            else:
                raise exc


VALID_CATEGORIES = {
    "Complaint",
    "Inquiry",
    "Bug Report",
    "Feature Request",
    "Compliance",
    "Legal",
    "Billing",
    "Spam",
    "Internal",
    "Other",
}
VALID_SENTIMENTS = {"Positive", "Neutral", "Negative", "Mixed"}
VALID_URGENCIES = {"Critical", "High", "Medium", "Low"}
NO_AUTO_REPLY_CATEGORIES = {"Spam", "Compliance", "Legal"}
SECURITY_TERMS = {"ransomware", "suspicious login", "unauthorized access", "bitcoin", "btc", "hack", "breach"}
GDPR_TERMS = {"gdpr", "article 17", "article 20", "right to erasure", "right to be forgotten", "data portability"}


async def classify_email(
    email: Any,
    thread_history: list[Any],
    rag_chunks: list[dict[str, Any]],
) -> dict[str, Any]:
    if not settings.groq_api_key or settings.groq_api_key == "your_groq_key":
        return _fallback_result("Groq API key is not configured")

    try:
        client = AsyncGroq(api_key=settings.groq_api_key)
        completion = await chat_with_retry(
            client,
            model=settings.llm_model,
            messages=[
                {"role": "system", "content": _system_prompt()},
                {"role": "user", "content": _user_prompt(email, thread_history, rag_chunks)},
            ],
            temperature=0,
            response_format={"type": "json_object"},
        )
        content = completion.choices[0].message.content or ""
        return _normalize_result(json.loads(_strip_markdown_fences(content)), email)
    except Exception as exc:
        return _fallback_result(f"LLM classification failed: {exc}")


def _system_prompt() -> str:
    return """
You are SenAI's CRM email intelligence classifier.
Return ONLY raw JSON. Do not include markdown, comments, or prose.
The JSON must match exactly this schema:
{
  "category": "Complaint|Inquiry|Bug Report|Feature Request|Compliance|Legal|Billing|Spam|Internal|Other",
  "sentiment": "Positive|Neutral|Negative|Mixed",
  "sentiment_score": -1.0,
  "urgency": "Critical|High|Medium|Low",
  "requires_human": true,
  "escalation_reason": "string or null",
  "suggested_reply": "string or null",
  "confidence": 0.0,
  "detected_entities": {
    "order_ids": [],
    "ticket_ids": [],
    "monetary_amounts": [],
    "deadlines": [],
    "products_mentioned": []
  }
}

Rules:
- If confidence < 0.70, set requires_human=true.
- If requires_human=true, set suggested_reply=null.
- Never auto-reply for spam, security threats, legal, or GDPR/compliance requests.
- For mixed signals, set sentiment=Mixed, lower confidence, and choose the most urgent/actionable category.
- Use Policy Context when relevant, but do not invent policy terms.
""".strip()


def _user_prompt(email: Any, thread_history: list[Any], rag_chunks: list[dict[str, Any]]) -> str:
    return "\n\n".join(
        [
            "Thread History (chronological):\n" + _format_thread_history(thread_history),
            "Current Email:\n" + _format_email(email),
            "Policy Context:\n" + _format_policy_context(rag_chunks),
        ]
    )


def _format_thread_history(thread_history: list[Any]) -> str:
    if not thread_history:
        return "No prior thread history."
    return "\n\n".join(_format_email(item) for item in thread_history)


def _format_email(email: Any) -> str:
    return (
        f"Timestamp: {getattr(email, 'timestamp', None)}\n"
        f"Sender: {getattr(email, 'sender', '')}\n"
        f"Subject: {getattr(email, 'subject', '') or ''}\n"
        f"Body: {getattr(email, 'body', '') or ''}"
    )


def _format_policy_context(rag_chunks: list[dict[str, Any]]) -> str:
    if not rag_chunks:
        return "No relevant policy context found."
    return "\n\n".join(
        f"[{index}] Source: {chunk.get('source_doc')}\n{chunk.get('chunk_text')}"
        for index, chunk in enumerate(rag_chunks, start=1)
    )


def _strip_markdown_fences(content: str) -> str:
    content = content.strip()
    fenced = re.match(r"^```(?:json)?\s*(.*?)\s*```$", content, flags=re.DOTALL | re.IGNORECASE)
    return fenced.group(1).strip() if fenced else content


def _normalize_result(result: dict[str, Any], email: Any) -> dict[str, Any]:
    category = result.get("category") if result.get("category") in VALID_CATEGORIES else "Other"
    sentiment = result.get("sentiment") if result.get("sentiment") in VALID_SENTIMENTS else "Neutral"
    urgency = result.get("urgency") if result.get("urgency") in VALID_URGENCIES else "Medium"
    confidence = _bounded_float(result.get("confidence"), 0.0, 1.0)
    sentiment_score = _bounded_float(result.get("sentiment_score"), -1.0, 1.0)

    body_text = f"{getattr(email, 'subject', '') or ''}\n{getattr(email, 'body', '') or ''}".lower()
    has_security_signal = any(term in body_text for term in SECURITY_TERMS)
    has_gdpr_signal = any(term in body_text for term in GDPR_TERMS)
    requires_human = bool(result.get("requires_human"))
    if confidence < 0.70 or category in NO_AUTO_REPLY_CATEGORIES or has_security_signal or has_gdpr_signal:
        requires_human = True

    suggested_reply = result.get("suggested_reply")
    if requires_human:
        suggested_reply = None

    escalation_reason = result.get("escalation_reason")
    if requires_human and not escalation_reason:
        escalation_reason = "Human review required by confidence, category, or safety policy."

    detected_entities = result.get("detected_entities") if isinstance(result.get("detected_entities"), dict) else {}
    return {
        "category": category,
        "sentiment": sentiment,
        "sentiment_score": sentiment_score,
        "urgency": urgency,
        "requires_human": requires_human,
        "escalation_reason": escalation_reason,
        "suggested_reply": suggested_reply,
        "confidence": confidence,
        "detected_entities": {
            "order_ids": _list_value(detected_entities.get("order_ids")),
            "ticket_ids": _list_value(detected_entities.get("ticket_ids")),
            "monetary_amounts": _list_value(detected_entities.get("monetary_amounts")),
            "deadlines": _list_value(detected_entities.get("deadlines")),
            "products_mentioned": _list_value(detected_entities.get("products_mentioned")),
        },
    }


def _fallback_result(reason: str) -> dict[str, Any]:
    return {
        "category": "Other",
        "sentiment": "Neutral",
        "sentiment_score": 0.0,
        "urgency": "Medium",
        "requires_human": True,
        "escalation_reason": reason,
        "suggested_reply": None,
        "confidence": 0.0,
        "detected_entities": {
            "order_ids": [],
            "ticket_ids": [],
            "monetary_amounts": [],
            "deadlines": [],
            "products_mentioned": [],
        },
    }


def _bounded_float(value: Any, minimum: float, maximum: float) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        number = 0.0
    return max(minimum, min(maximum, number))


def _list_value(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []
