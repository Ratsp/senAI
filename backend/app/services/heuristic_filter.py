from dataclasses import dataclass


SPAM_KEYWORDS = {
    "nigerian prince",
    "seo service",
    "boost your seo",
    "make money fast",
    "click here to unsubscribe",
    "limited time offer",
    "buy cheap",
}
SPAM_DOMAINS = {"spam.example", "cheap-seo.biz", "mailer-promo.ru"}
SECURITY_KEYWORDS = {
    "ransomware",
    "suspicious login",
    "unauthorized access",
    "bitcoin",
    "btc",
    "send 2 btc",
    "publish data",
    "hack",
    "breach",
    "unknown location",
}
GDPR_KEYWORDS = {
    "gdpr",
    "article 17",
    "article 20",
    "data portability",
    "right to erasure",
    "right to be forgotten",
}
CRITICAL_KEYWORDS = {
    "ransomware",
    "legal action",
    "cease and desist",
    "p0 incident",
    "lawsuit",
    "legal review",
    "data breach",
}
HIGH_URGENCY_KEYWORDS = {
    "urgent",
    "sla breach",
    "refund",
    "cancel my account",
    "no reply",
    "still no reply",
    "unacceptable",
    "asap",
    "immediately",
}
INTERNAL_DOMAINS = {"internal.com", "mycompany.com", "senai.io"}


@dataclass(frozen=True)
class HeuristicResult:
    is_spam: bool
    is_internal: bool
    is_security_threat: bool
    is_gdpr_request: bool
    urgency: str | None
    initial_category: str | None
    requires_human: bool


def _domain(email: str) -> str:
    return email.rsplit("@", 1)[-1].lower() if "@" in email else ""


def _contains_any(text: str, keywords: set[str]) -> bool:
    return any(keyword in text for keyword in keywords)


def run_heuristic_filter(sender: str, subject: str | None, body: str | None) -> HeuristicResult:
    text = f"{subject or ''}\n{body or ''}".lower()
    sender_domain = _domain(sender)

    is_internal = sender_domain in INTERNAL_DOMAINS
    is_spam = sender_domain in SPAM_DOMAINS or _contains_any(text, SPAM_KEYWORDS)
    is_security_threat = _contains_any(text, SECURITY_KEYWORDS)
    is_gdpr_request = _contains_any(text, GDPR_KEYWORDS)

    urgency = None
    if is_security_threat or _contains_any(text, CRITICAL_KEYWORDS):
        urgency = "Critical"
    elif is_gdpr_request or _contains_any(text, HIGH_URGENCY_KEYWORDS):
        urgency = "High"

    initial_category = None
    if is_internal:
        initial_category = "Internal"
    elif is_gdpr_request:
        initial_category = "Compliance"
    elif is_spam:
        initial_category = "Spam"
    elif is_security_threat:
        initial_category = "Security"

    requires_human = is_security_threat or is_gdpr_request or urgency in {"Critical", "High"}

    return HeuristicResult(
        is_spam=is_spam,
        is_internal=is_internal,
        is_security_threat=is_security_threat,
        is_gdpr_request=is_gdpr_request,
        urgency=urgency,
        initial_category=initial_category,
        requires_human=requires_human,
    )
