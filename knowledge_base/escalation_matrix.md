# SenAI Solutions — Escalation Matrix and Incident Response Procedures

## Document Metadata

| Field            | Value                                           |
|------------------|-------------------------------------------------|
| Version          | 5.0                                             |
| Last Updated     | 2024-10-30                                      |
| Owner            | VP of Customer Success — Priya Kapoor           |
| Classification   | Internal                                        |
| Approved By      | CEO — Michael Torres                            |
| Next Review Date | 2025-04-30                                      |

---

## 1. Escalation Tier Framework

SenAI uses a three-tier escalation framework to ensure that issues are routed to the right team with the appropriate level of authority and urgency. Each tier has defined triggers, contacts, and response expectations.

### 1.1 Tier 1 — Standard Escalation

**Scope:** Routine customer issues that require attention beyond what the frontline support agent or AI agent can handle, but do not involve legal, security, or reputational risk.

**Triggers:**
- Customer requests to speak with a manager
- Support agent or AI agent is unable to resolve the issue within the standard workflow
- Customer satisfaction score drops below 3/10 on a post-interaction survey
- Email remains unresolved for more than **48 hours**

**Response SLA:** Within **4 hours** during business hours (9 AM – 6 PM ET, Monday–Friday)

**Contact:** Customer Success Team — **support-escalations@senai.io**

**Action:** Assigned to a Senior Customer Success Agent for review and resolution. The Senior Agent has authority to offer Tier 1 retention incentives (see refund_policy.md, Section 5.2, Tier 1 Retention).

---

### 1.2 Tier 2 — Elevated Escalation

**Scope:** Issues involving significant financial impact, VIP customers, potential churn of high-value accounts, or operational failures affecting multiple customers.

**Triggers:**
- Customer account value exceeds **$10,000 ARR** and the customer expresses dissatisfaction or churn intent
- Customer has sent **3 or more emails with zero replies** from SenAI (response gap escalation)
- Negative sentiment trend: 3 or more consecutive emails with sentiment_score < -0.3
- SLA breach affecting multiple customers (P1 or above)
- Customer requests refund exceeding **$1,000**
- Customer mentions specific competitors as alternatives

**Response SLA:** Within **2 hours** during business hours; within **4 hours** after hours for accounts > $50K ARR

**Contact:** VP of Customer Success — **cs-vp@senai.io** and Account Management Team — **vip@senai.io**

**Action:** VP of Customer Success or designated Account Manager takes ownership. Has authority to offer Tier 2 retention incentives and escalate internally to executive leadership if needed.

---

### 1.3 Tier 3 — Executive / Critical Escalation

**Scope:** Issues involving legal threats, security incidents, regulatory compliance violations, public reputation crises, or the potential loss of a strategic account (>$100K ARR).

**Triggers:**
- Customer explicitly threatens legal action (lawsuit, cease and desist, regulatory complaint)
- Confirmed or suspected security breach involving customer data
- GDPR, HIPAA, or other regulatory compliance violation
- Customer threatens negative public reviews on platforms with >10,000 audience reach
- Media inquiry or press coverage about SenAI
- P0 incident lasting more than 2 hours
- Customer account value exceeds **$100,000 ARR** and customer threatens to churn
- Ransomware, extortion, or social engineering attack

**Response SLA:** Within **1 hour**, 24/7 (no business hours restriction)

**Contact:** C-suite (CEO, CTO, or General Counsel as appropriate) + relevant functional team lead

**Action:** Executive sponsor assigned. Cross-functional war room convened if needed. All communications reviewed by Legal before sending.

---

## 2. Functional Escalation Contacts

### 2.1 Legal Threats

**Who Handles:** Legal Team

**Contact:** **legal@senai.io**

**Response SLA:** **4 business hours** from initial escalation

**When to Escalate:**
- Customer uses language such as "legal counsel," "attorney," "lawsuit," "breach of contract," "cease and desist," or "regulatory complaint"
- Customer references specific laws or regulations (GDPR, HIPAA, CCPA, etc.) in the context of a complaint or demand
- Customer claims SenAI has violated a contractual obligation (e.g., SLA breach, data handling violation)
- Customer forwards or attaches communication from their legal representative

**What to Include in the Escalation Email:**
1. Customer name, email, company, and account ID
2. Full email thread (all messages in the thread, not just the latest)
3. Summary of the customer's claim or demand
4. Relevant contract or MSA details (if Enterprise customer)
5. Any SLA credits or refunds already offered or issued
6. Internal assessment of the claim's validity (from Support or Account Management)

**Critical Rule:** Once a legal threat is identified, **all further customer communications must be reviewed and approved by Legal before sending**. The AI agent must set `requires_human = true` and must not auto-reply.

---

### 2.2 Security Incidents

**Who Handles:** Security Team

**Contact:** **security@senai.io**

**Response SLA:** **15 minutes** for confirmed incidents; **1 hour** for suspected incidents

**When to Escalate:**
- Suspicious login attempts or unauthorized access reports
- Customer reports a potential data breach
- Ransomware or extortion threats (see Section 5 for ransomware protocol)
- Phishing or social engineering attempts targeting SenAI or its customers
- Vulnerability reports from customers or external researchers
- Anomalous API usage patterns suggesting credential compromise

**Immediate Escalation Path:**
1. Page the Security On-Call Engineer via PagerDuty
2. Email **security@senai.io** with subject line "SECURITY INCIDENT — [Brief Description]"
3. Post in the internal `#security-incidents` Slack channel
4. If the incident involves customer data, notify the CISO — **Lin Zhao** — directly via phone

**Critical Rule:** **Never auto-reply to security threats, ransomware demands, or attacker communications.** Any response to an attacker may escalate the situation, provide information useful to the attacker, or create legal complications.

---

### 2.3 PR / Reputation Crises

**Who Handles:** PR Team + VP of Customer Success

**Contact:** **pr@senai.io**

**Response SLA:** **2 hours** for potential crises; **30 minutes** for active crises (media coverage, viral social media posts)

**When to Escalate:**
- Customer threatens to post negative reviews on G2, Trustpilot, Twitter/X, LinkedIn, Reddit, or Hacker News
- Negative media coverage or press inquiries about SenAI
- Viral social media post mentioning SenAI negatively (>100 engagements)
- Customer complaint posted on a public forum that gains traction
- Internal employee publicly criticizes company practices

**Escalation Path:**
1. Email **pr@senai.io** with subject line "PR ALERT — [Brief Description]"
2. Include: customer details, platform(s) mentioned, estimated audience reach, and the specific complaint or threat
3. For **Tier 1 PR crises** (media coverage, viral posts, or complaints from customers at publicly traded companies): notify the **CEO — Michael Torres** via the `#exec-alerts` Slack channel immediately
4. PR Team assesses the situation and provides a response strategy within 2 hours
5. VP of Customer Success coordinates the customer-facing response, with PR reviewing all external communications

**Critical Rule:** Do not offer retention incentives specifically conditioned on the customer not posting a review. This is unethical and potentially illegal under FTC guidelines. Offers must be based on standard retention policy.

---

### 2.4 VIP Churn Threats

**Who Handles:** Account Management Team

**Contact:** **vip@senai.io**

**Response SLA:** **1 hour** during business hours; **2 hours** after hours

**When to Escalate:**
- Customer with ARR **>$50,000** explicitly states intent to cancel, switch providers, or not renew
- Customer with ARR **>$50,000** sends **3 or more negative-sentiment emails** within a 30-day period
- Enterprise customer's executive sponsor (C-level) directly contacts SenAI expressing dissatisfaction
- Customer references active evaluation of a named competitor for replacement
- Churn risk score exceeds **0.8** (on 0–1 scale) for any account with ARR > $10,000

**What to Include in the Escalation:**
1. Customer profile: name, company, account value, contract renewal date
2. Full communication history (last 30 days minimum)
3. Churn risk score and contributing factors
4. List of open/unresolved issues
5. Previous retention offers made and their outcomes
6. Recommended retention strategy based on the churn playbook (see refund_policy.md, Section 5)

**Escalation Authority:**
- Accounts $50K–$100K ARR: VP of Sales
- Accounts $100K–$500K ARR: VP of Sales + CEO notification
- Accounts >$500K ARR: CEO direct involvement required

---

### 2.5 GDPR Requests

**Who Handles:** Data Protection Officer (DPO)

**Contact:** **dpo@senai.io**

**Response SLA:** Acknowledge within **72 hours**; fulfill within **30 calendar days** (statutory requirement)

**When to Escalate:**
- Any request invoking GDPR rights (data access, portability, erasure, rectification, restriction of processing)
- Any communication referencing "GDPR," "data protection," "Article 17," "Article 20," "right to be forgotten," or "data subject request"
- Any communication from a data protection authority (DPA) or supervisory authority
- Any request from an EU/EEA/UK-based customer regarding their personal data rights

**Escalation Path:**
1. Email **dpo@senai.io** with subject line "GDPR Request — [Request Type] — [Customer Name]"
2. Include: the customer's request verbatim, customer identity verification status, and the specific GDPR articles referenced
3. The DPO will log the request in the GDPR request register and assign it to the Compliance Engineering team
4. For requests from data protection authorities, additionally notify **legal@senai.io** immediately

**Critical Rule:** GDPR requests have a **30-day statutory deadline**. Failure to respond within this window exposes SenAI to regulatory fines of up to **€20 million or 4% of annual global turnover** (whichever is greater). All GDPR requests must be treated as time-critical regardless of other competing priorities.

---

### 2.6 P0 Outages with SLA Breach

**Who Handles:** Engineering On-Call + VP of Engineering

**Contact:** Engineering On-Call (via PagerDuty) + **vp-eng@senai.io**

**Response SLA:** **15 minutes** (P0 response SLA per sla_policy.md)

**When to Escalate:**
- Any P0 incident (see sla_policy.md, Section 2.1 for P0 definition)
- Any incident that has breached or is at risk of breaching the response time SLA
- Any incident where the resolution time SLA has been exceeded

**Escalation Path:**
1. PagerDuty automatically pages the Engineering On-Call Engineer within **5 minutes** of P0 detection
2. If no acknowledgement within **10 minutes**, PagerDuty escalates to the Engineering On-Call Lead
3. **CTO — James Whitfield** and **VP of Engineering** are notified within **1 hour** of any P0 incident
4. If the incident results in an SLA breach, the VP of Customer Success is notified to begin proactive customer communication
5. For P0 incidents lasting more than **2 hours**, a cross-functional war room is convened (Engineering, Customer Success, and Communications)

**Post-Incident:**
- RCA delivery within **24 hours** of resolution (see sla_policy.md, Section 4)
- SLA credit calculation and proactive communication to affected customers
- Post-mortem meeting within 5 business days, documented and shared with the engineering organization

---

### 2.7 RFP and Large Enterprise Deals

**Who Handles:** Sales Engineering Team

**Contact:** **sales@senai.io**

**Response SLA:** **24 hours** for initial engagement; **5 business days** for full RFP response

**When to Escalate:**
- Inbound RFP or RFI (Request for Information) from a prospective customer
- Existing customer expansion opportunity exceeding **$500,000** in contract value
- Competitive displacement opportunity (prospect currently using a competitor)
- Requests involving custom integrations, dedicated infrastructure, or bespoke SLA terms
- Multi-year contract negotiations (2+ year terms)

**Escalation Path:**
1. Email **sales@senai.io** with subject line "RFP/Deal Escalation — [Company Name] — [Estimated Value]"
2. Include: RFP document (if available), prospect contact information, estimated deal value, timeline, and competitive context
3. A Sales Engineer is assigned within **1 business day**
4. For deals exceeding **$1 million**, the VP of Sales and CEO are briefed within 48 hours

---

## 3. On-Call Rotation

### 3.1 On-Call Structure

SenAI maintains a 24/7 on-call rotation for Engineering, Security, and Customer Success.

| Function              | On-Call Coverage | Rotation Duration | Escalation Tool |
|-----------------------|------------------|-------------------|-----------------|
| Engineering           | 24/7             | 1 week            | PagerDuty       |
| Security              | 24/7             | 1 week            | PagerDuty       |
| Customer Success      | Business hours + on-call for VIP (24/7) | 1 week | PagerDuty |

### 3.2 On-Call Responsibilities

- **Engineering On-Call:** Respond to platform incidents (P0, P1), infrastructure alerts, and deployment issues. First responder for all automated monitoring alerts.
- **Security On-Call:** Respond to security incidents, vulnerability reports, and suspicious activity alerts. First responder for all security-related PagerDuty alerts.
- **Customer Success On-Call:** Respond to VIP customer escalations after business hours. Monitors the `#vip-escalations` Slack channel.

### 3.3 On-Call Handoff

On-call handoffs occur every **Monday at 10:00 AM ET**. The outgoing on-call engineer briefs the incoming engineer on:
- Active incidents and their status
- Ongoing investigations
- Scheduled maintenance or deployments during the upcoming week
- Any customer-specific alerts or sensitivities

---

## 4. Chatbot-Caused Misinformation Protocol

### 4.1 When This Protocol Applies

This protocol applies when a customer reports that SenAI's **customer-facing AI chatbot** provided incorrect, misleading, or outdated information. Common scenarios include:
- Chatbot quoted an incorrect refund window (e.g., said 30 days instead of 14 days)
- Chatbot stated a feature is available on a tier that does not include it
- Chatbot provided incorrect pricing information
- Chatbot gave compliance or legal guidance that contradicts SenAI's official policies

### 4.2 Escalation Path

1. **AI Agent Detection:** If the AI triage agent detects keywords such as "your chatbot said," "I was told by your bot," "the automated response said," or "your AI assistant told me," it should flag the email with `requires_human = true` and category = "Complaint".

2. **Escalate to Product Team:** Email **product@senai.io** with subject line "Chatbot Misinformation Report — [Topic]"
   - Include: the customer's verbatim claim about what the chatbot said, the actual policy from the knowledge base, and the customer's email thread.

3. **Escalate to Legal (conditional):** If the customer demands compensation, threatens legal action, or claims financial harm based on the chatbot's incorrect information, additionally escalate to **legal@senai.io**.

4. **Response Team:** The Customer Success team drafts the customer response, reviewed by Product (for accuracy) and Legal (if legal implications exist).

### 4.3 Response Guidelines

**DO:**
- Acknowledge the customer's frustration and the discrepancy with empathy
- State the **correct policy** clearly and cite the specific policy document
- Offer a goodwill gesture (e.g., account credit) framed as discretionary, not obligatory
- Commit to investigating and correcting the chatbot's responses
- Offer to connect the customer with a human agent for further assistance

**DO NOT:**
- Admit legal liability (e.g., "we were wrong and owe you compensation")
- Promise to honor the chatbot's incorrect statement as binding
- Blame the customer for relying on the chatbot
- Auto-reply without human review — all chatbot misinformation cases require human oversight
- Ignore the report — every chatbot misinformation incident must be logged and investigated by the Product team

### 4.4 Internal Follow-Up

After resolving the customer-facing issue:
1. Product team investigates the root cause of the chatbot misinformation within **5 business days**
2. Product team updates the chatbot's knowledge base or response logic to prevent recurrence
3. Product team files an internal incident report with: what the chatbot said, what the correct answer is, root cause, and corrective action taken
4. Quarterly review of all chatbot misinformation incidents by Product and Legal teams

---

## 5. Ransomware / Extortion Protocol

### 5.1 Identification

Ransomware and extortion communications are identified by the presence of:
- Demands for cryptocurrency (Bitcoin, Ethereum, etc.) or untraceable payment
- Threats to publish, encrypt, or destroy SenAI or customer data
- Claims of having already exfiltrated data, with or without proof
- Ultimatums with specific deadlines for payment
- Keywords: "ransom," "BTC," "bitcoin," "encrypt," "publish your data," "pay or else"

### 5.2 Immediate Response Protocol

**Step 1: ISOLATE**
- Do **not** click any links or download any attachments in the communication
- Do **not** respond to the attacker — **never reply to ransomware or extortion emails**
- If the email contains links to a "proof" page, do not visit it from any corporate device
- Quarantine the email in the security queue

**Step 2: ALERT**
- Page the Security On-Call Engineer immediately via PagerDuty
- Email **security@senai.io** with subject line "RANSOMWARE ALERT — URGENT"
- Notify the **CISO — Lin Zhao** via phone (emergency contact number available in PagerDuty)
- Post in `#security-incidents` Slack channel with `@here` mention

**Step 3: ENGAGE LEGAL**
- Email **legal@senai.io** with subject line "EXTORTION THREAT — LEGAL REVIEW REQUIRED"
- Legal will coordinate with law enforcement (FBI IC3, local authorities) as appropriate
- Legal will advise on notification obligations to affected customers (if any)

**Step 4: INVESTIGATE**
- Security team assesses whether a breach has actually occurred
- Review access logs, data exfiltration indicators, and system integrity
- If a breach is confirmed, activate the full Incident Response Plan (see Section 5.4)

**Step 5: NEVER PAY**
- SenAI's policy is to **never pay ransoms or extortion demands**. Paying ransoms:
  - Does not guarantee data recovery or prevention of data publication
  - Funds criminal organizations
  - May violate US sanctions laws (OFAC regulations)
  - Increases the likelihood of future attacks

### 5.3 Communication Blackout

During an active ransomware/extortion incident:
- **No external communications** about the incident without Legal and PR approval
- **No social media posts** referencing the incident
- **No customer notifications** until the scope of the breach (if any) is understood
- All internal communications use the designated incident Slack channel, not email (in case email is compromised)

### 5.4 Post-Incident Actions

1. If a breach is confirmed, follow the breach notification procedures (GDPR Article 33: 72 hours; HIPAA: 24 hours for BAA customers)
2. Conduct a full forensic investigation
3. Engage an external incident response firm if needed (retainer with CrowdStrike)
4. File a report with FBI IC3 and relevant law enforcement
5. Produce an internal incident report within 7 days
6. Conduct a post-mortem and update security controls

---

## 6. Escalation Decision Flowchart

### 6.1 AI Agent Escalation Logic

The following decision tree is used by the AI triage agent to determine the correct escalation path:

```
START: New email received

├─ Contains ransomware/extortion keywords?
│  └─ YES → CRITICAL: Route to Security (security@senai.io) + Legal (legal@senai.io)
│           Set requires_human = true. NEVER auto-reply.
│
├─ Contains legal threat language?
│  └─ YES → Route to Legal Team (legal@senai.io)
│           Set requires_human = true. NEVER auto-reply.
│
├─ Contains GDPR/data protection request?
│  └─ YES → Route to DPO (dpo@senai.io)
│           Auto-acknowledge citing 30-day window. Create compliance ticket.
│
├─ Mentions public review threat (G2, Trustpilot, social media)?
│  └─ YES → Route to PR Team (pr@senai.io) + VP Customer Success
│           Trigger web intelligence scraping. Set requires_human = true.
│
├─ Customer ARR > $50K AND negative sentiment?
│  └─ YES → Route to Account Management (vip@senai.io)
│           Include churn risk score and retention recommendation.
│
├─ Reports chatbot misinformation?
│  └─ YES → Route to Product Team (product@senai.io) + Customer Success
│           Retrieve actual policy via RAG. Set requires_human = true.
│
├─ P0 outage or SLA breach reported?
│  └─ YES → Route to Engineering On-Call (PagerDuty) + VP Engineering
│           Retrieve SLA policy for credit calculation.
│
├─ RFP or deal > $500K?
│  └─ YES → Route to Sales Engineering (sales@senai.io)
│
└─ Standard issue
   └─ Route to Tier 1 Support (support-escalations@senai.io)
```

---

## 7. Escalation Contact Directory

| Function                | Contact Email              | Phone/Pager          | Slack Channel           |
|-------------------------|----------------------------|----------------------|--------------------------|
| Legal Team              | legal@senai.io             | Via PagerDuty        | #legal-escalations       |
| Security Team           | security@senai.io          | Via PagerDuty (24/7) | #security-incidents      |
| PR Team                 | pr@senai.io                | —                    | #pr-alerts               |
| Data Protection Officer | dpo@senai.io               | —                    | #compliance              |
| Account Management      | vip@senai.io               | Via PagerDuty        | #vip-escalations         |
| VP Customer Success     | cs-vp@senai.io             | Via PagerDuty        | #cs-leadership           |
| VP Engineering          | vp-eng@senai.io            | Via PagerDuty        | #eng-leadership          |
| CTO                     | cto@senai.io               | Via PagerDuty        | #exec-alerts             |
| CEO                     | ceo@senai.io               | Via PagerDuty        | #exec-alerts             |
| Sales Engineering       | sales@senai.io             | —                    | #sales-ops               |
| Product Team            | product@senai.io           | —                    | #product-feedback        |
| Finance / Billing       | billing@senai.io           | —                    | #billing-support         |
| SLA Credits             | sla-credits@senai.io       | —                    | #sla-tracking            |
| Compliance              | compliance@senai.io        | —                    | #compliance              |

---

## 8. Escalation Documentation Requirements

All escalations, regardless of tier, must be documented with the following minimum information:

1. **Escalation timestamp** (UTC)
2. **Customer details:** name, email, company, account ID, ARR
3. **Escalation trigger:** what prompted the escalation (specific customer statement, system alert, etc.)
4. **Escalation tier** (Tier 1, 2, or 3)
5. **Assigned team/individual**
6. **Summary of the issue** and any actions already taken
7. **Relevant context:** thread history, sentiment trend, account status, prior escalations
8. **Recommended next action**
9. **Resolution status** (updated as the escalation progresses)
10. **Resolution summary** (completed when the escalation is closed)

All escalation records are stored in the CRM audit log and retained for **2 years** for compliance and quality review purposes.
