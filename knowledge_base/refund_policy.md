# SenAI Solutions — Refund and Retention Policy

## Document Metadata

| Field            | Value                                       |
|------------------|---------------------------------------------|
| Version          | 2.8                                         |
| Last Updated     | 2024-10-10                                  |
| Owner            | VP of Customer Success — Priya Kapoor       |
| Classification   | Internal                                    |
| Approved By      | CFO — Daniel Ortega                         |
| Next Review Date | 2025-04-10                                  |

---

## 1. Refund Eligibility Window

### 1.1 Standard Refund Policy

SenAI Solutions offers a **14-day refund window** from the date of initial purchase or renewal. Customers who request a refund within this 14-day period are entitled to a **full refund** of the subscription fee paid for that billing cycle, processed to the original payment method.

**After 14 days from the purchase or renewal date, no refunds will be issued.** This is a firm policy with limited exceptions (see Section 3 below). After the 14-day window, customers may be eligible for **account credits** instead of cash refunds (see Section 2).

### 1.2 Refund Eligibility by Subscription Type

| Subscription Type | Refund Window            | Refund Method         | Notes                                   |
|--------------------|--------------------------|-----------------------|------------------------------------------|
| Monthly            | 14 days from charge date | Original payment method | Full refund of current month's charge   |
| Annual (first year)| 14 days from charge date | Original payment method | Full refund of annual payment           |
| Annual (renewal)   | 14 days from renewal date| Original payment method | Full refund of renewal payment          |
| Enterprise (MSA)   | Per MSA terms            | Per MSA terms          | Typically 30-day cancellation notice     |

### 1.3 What Qualifies for a Refund Within 14 Days

Refunds within the 14-day window are granted for **any reason**, including but not limited to:
- Product does not meet expectations
- Customer signed up in error
- Duplicate subscription purchase
- Feature requirements not available in the subscribed tier

No justification is required for refund requests made within the 14-day window. The support team should process these requests promptly without requiring the customer to explain their reasoning.

---

## 2. Credits vs. Cash Refunds

### 2.1 When Account Credits Apply

After the **14-day refund window** has closed, customers are **not eligible for cash refunds** but may receive **account credits** under the following circumstances:

- **Service disruption:** If the customer experienced a documented platform outage that exceeded the SLA uptime guarantee (see sla_policy.md for SLA credit calculation).
- **Billing error:** If SenAI incorrectly charged the customer (e.g., duplicate charge, wrong tier billed). Billing error credits are processed within 5 business days.
- **Feature unavailability:** If a paid feature documented in the customer's subscription tier was unavailable for more than 48 consecutive hours and the issue was confirmed by SenAI engineering.

### 2.2 How Credits Work

- Account credits are applied as a **line-item deduction** on the customer's next invoice.
- Credits **do not expire** as long as the customer maintains an active subscription.
- Credits are **not transferable** to another account and are **not redeemable for cash**.
- If a customer cancels their subscription with unused credits, the credits are **forfeited**.
- Credits cannot exceed **100% of a single month's subscription fee** unless approved by the VP of Customer Success.

### 2.3 When Cash Refunds Apply (Post-14-Day Window)

Cash refunds after the 14-day window are **only** issued under the following conditions:
1. SenAI determines that a **billing error** resulted in an overcharge exceeding **$500**.
2. A critical SLA breach (>4 hours of P0 downtime) affects the customer and the customer specifically requests a cash refund instead of credits. This requires VP of Customer Success approval.
3. A VP or C-level executive explicitly approves a discretionary refund as part of an escalation resolution (see Section 3).

---

## 3. Refund Exception Process

### 3.1 Who Can Approve Exceptions

Refund exceptions (i.e., refunds issued after the 14-day window or exceeding standard credit limits) require explicit approval from designated personnel:

| Exception Type                         | Approval Authority                    | Maximum Amount          |
|----------------------------------------|---------------------------------------|--------------------------|
| Refund after 14-day window (≤ $500)    | Customer Success Manager              | $500                     |
| Refund after 14-day window (> $500)    | VP of Customer Success — Priya Kapoor | $5,000                   |
| Refund after 14-day window (> $5,000)  | CFO — Daniel Ortega                   | Unlimited                |
| Enterprise partial refund (unused seats)| VP of Sales                          | Pro-rated seat value     |
| Discretionary retention refund         | VP of Customer Success                | 1 month's subscription   |

### 3.2 What Qualifies for an Exception

Exceptions to the 14-day refund policy may be considered when:
- The customer experienced a **documented critical service disruption** (P0 or P1 incident) that directly impacted their business operations.
- SenAI's own **AI chatbot or support agent provided incorrect information** about refund eligibility, leading the customer to believe a refund was available when it was not (see Section 7 for chatbot misinformation protocol).
- The customer is a **high-value Enterprise account** (>$10,000 ARR) and the refund is part of a broader retention strategy.
- A **billing system error** on SenAI's side resulted in incorrect charges.

### 3.3 Exception Request Process

1. Support agent documents the exception request in the CRM with: customer details, refund amount, reason for exception, and relevant incident/ticket numbers.
2. Support agent emails the appropriate approval authority (per the table above) with the subject line "Refund Exception Request — [Customer Name] — [Amount]".
3. Approval authority reviews and responds within **2 business days**.
4. If approved, the Finance team processes the refund within **5–10 business days**.
5. All exceptions are logged in the audit trail for quarterly review.

---

## 4. Partial Refund Conditions

### 4.1 Enterprise Seat-Based Partial Refunds

Enterprise customers on annual agreements who reduce their seat count during the contract term may be eligible for a **partial refund** on unused seats, subject to the following conditions:

1. The seat reduction must be **10 seats or more** (or >20% of total seats, whichever is greater).
2. The partial refund is calculated on a **pro-rata basis** for the remaining months in the contract term.
3. Partial refund formula: `(Seats Removed × Per-Seat Monthly Rate × Remaining Months) × 0.75` — the 25% reduction accounts for the early termination adjustment.
4. Partial refunds require **VP of Sales approval** and must be formally documented as an amendment to the MSA.

### 4.2 Feature Downgrade Partial Credits

Customers who downgrade from a higher tier to a lower tier mid-annual-commitment are not eligible for partial cash refunds. However, they receive an **account credit** for the difference between the two tiers, pro-rated for the remaining months. The credit is applied to future invoices at the lower tier rate.

---

## 5. Churn Retention Playbook

### 5.1 Overview

When a customer indicates intent to cancel or churn, the support team and AI agent should follow this retention playbook before processing the cancellation. The goal is to understand the customer's reasons for leaving and offer targeted retention incentives.

### 5.2 Retention Offer Tiers

Retention offers are tiered based on the customer's account value and history:

#### Tier 1 Retention — Accounts < $1,000/month

| Offer                       | Description                                                   | Approval Required |
|-----------------------------|---------------------------------------------------------------|-------------------|
| **1 month free**            | Waive the next month's subscription fee                       | Support Manager   |
| **Tier downgrade with price lock** | Downgrade to a lower tier and lock the price for 6 months | Support Manager   |
| **Extended trial of features** | Unlock Professional features for 30 days on Standard plan  | Automatic         |

#### Tier 2 Retention — Accounts $1,000–$10,000/month

| Offer                         | Description                                                    | Approval Required       |
|-------------------------------|----------------------------------------------------------------|--------------------------|
| **2 months free**             | Waive the next 2 months' subscription fees                     | VP Customer Success      |
| **Custom discount (10–20%)** | Offer a recurring discount on the current tier for 12 months   | VP Customer Success      |
| **Dedicated onboarding session** | Free 2-hour onboarding/training session with a Solutions Engineer | Support Manager     |
| **Priority support upgrade**  | Upgrade support SLA to Professional tier for 6 months          | Support Manager          |

#### Tier 3 Retention — Accounts > $10,000/month (Enterprise)

| Offer                            | Description                                                         | Approval Required  |
|----------------------------------|---------------------------------------------------------------------|--------------------|
| **Dedicated Account Manager**    | Assign a named Account Manager for personalized support             | VP of Sales        |
| **Custom SLA enhancement**       | Offer enhanced SLA terms (e.g., 99.95% uptime) at no additional cost| VP Engineering     |
| **Contract restructuring**       | Renegotiate contract terms, payment schedule, or seat count         | VP of Sales        |
| **Executive sponsor assignment** | Assign a C-level executive as the account sponsor                   | CEO                |
| **Partial refund + renewal**     | Refund up to 1 month and extend the contract at a discounted rate   | CFO                |

### 5.3 Retention Conversation Guidelines

When engaging with a customer expressing churn intent:

1. **Acknowledge and empathize** — "I completely understand your frustration, and I'm sorry we haven't met your expectations."
2. **Ask open-ended questions** — "Can you tell me more about what prompted this decision?" / "What would need to change for you to continue with us?"
3. **Listen for root causes** — Is it pricing, product gaps, support quality, or a competitive switch?
4. **Present the most relevant retention offer** based on the customer's stated concern and account tier.
5. **Document the conversation** — Log the retention offer made, the customer's response, and the outcome in the CRM.
6. **Escalate if needed** — If the customer rejects the initial offer and the account is >$10,000 ARR, escalate to the Account Management team (vip@senai.io).

---

## 6. Handling Customers Who Threaten Public Reviews

### 6.1 Policy on Public Review Threats

When a customer explicitly threatens to post negative reviews on public platforms (e.g., G2, Trustpilot, Twitter/X, LinkedIn, Reddit), the support team and AI agent should follow this protocol:

1. **Do NOT dismiss or minimize** the customer's frustration. Acknowledge their feelings with empathy.
2. **Do NOT offer concessions specifically to prevent a review.** Offering incentives to suppress reviews is unethical and potentially illegal (violates FTC guidelines on review manipulation). Any retention offers must be based on standard policy, not conditioned on the customer retracting or not posting a review.
3. **Do escalate immediately** to the PR Team (pr@senai.io) and VP of Customer Success if:
   - The customer has a public platform following of >10,000 followers
   - The customer is a recognized industry figure or works for a publicly traded company
   - The customer's complaint involves a data breach, security incident, or compliance failure
4. **Offer standard retention incentives** (Section 5) based on the customer's account tier — present these as genuine goodwill, not as a quid pro quo for review suppression.
5. **Fast-track issue resolution** — Assign the highest priority to resolving the underlying complaint. The goal is to resolve the issue so thoroughly that the customer voluntarily reconsiders their review.
6. **Document everything** — Log the threat, the resolution offered, and the outcome. This documentation may be needed by Legal if the situation escalates.

### 6.2 AI Agent Behavior for Public Review Threats

The AI agent should:
- Classify the email as **urgency: High** and **category: Complaint**
- Trigger the `scrape_public_sentiment` tool to check current G2/Trustpilot ratings
- Set `requires_human = true` — the agent must **not auto-reply** to emails containing public review threats
- Include in the escalation brief: customer's account value, number of unanswered emails, sentiment trend, and specific review platforms mentioned
- Suggest a retention offer from the playbook (Section 5) based on the customer's account tier

---

## 7. AI Chatbot Refund Misinformation Protocol

### 7.1 Background

SenAI's customer-facing AI chatbot may occasionally provide incorrect information about refund policies. When a customer reports that the chatbot gave them incorrect refund information (e.g., the chatbot stated a full refund is available when it is not, or the chatbot quoted an incorrect refund window), the following protocol applies.

### 7.2 What the AI Agent Should Do

1. **Retrieve the actual refund policy** via RAG search (`search_knowledge_base("refund policy")`) to determine the correct policy position.
2. **Compare** what the chatbot allegedly told the customer against the actual policy.
3. **Draft an empathetic response** that:
   - Acknowledges the customer's frustration and the discrepancy
   - States the **correct policy** clearly (e.g., "Our refund policy provides a 14-day refund window from the date of purchase. After this period, we offer account credits rather than cash refunds.")
   - **Does NOT admit legal liability** — do not say "we were wrong and owe you a refund" or "our chatbot made a mistake that entitles you to compensation"
   - Offers to escalate to a human agent for further assistance
   - If appropriate, offers a goodwill **account credit** (up to 1 month's subscription) as a gesture of good faith, clearly framed as discretionary, not obligatory
4. **Escalate internally** to the Product team (product@senai.io) with a summary:
   - Subject: "Chatbot Misinformation Report — Refund Policy"
   - Include: What the chatbot allegedly said, what the actual policy states, customer details, and the email thread
5. **Escalate to Legal** (legal@senai.io) if the customer explicitly demands compensation or threatens legal action based on the chatbot's statements.

### 7.3 What the AI Agent Should NOT Do

- **Do NOT** promise a refund that contradicts the actual refund policy
- **Do NOT** say "our chatbot was wrong and we will honor what it said" — this creates a contractual obligation based on chatbot output
- **Do NOT** dismiss the customer's concern — even if the chatbot error was minor, the customer's trust has been damaged
- **Do NOT** auto-reply without human review — all chatbot misinformation cases must be flagged with `requires_human = true`
- **Do NOT** blame the customer for relying on the chatbot — the chatbot is SenAI's product and the customer's reliance was reasonable

### 7.4 Approved Response Templates

**Template for chatbot misinformation (within 14-day window):**

> Thank you for bringing this to our attention, [Customer Name]. I understand how frustrating it must be to receive conflicting information. I want to clarify our refund policy: we offer a full refund within 14 days of purchase. Since your purchase falls within this window, I'd be happy to process your refund right away. I've also escalated the chatbot discrepancy to our product team so we can improve the accuracy of our automated responses. Please let me know how you'd like to proceed.

**Template for chatbot misinformation (after 14-day window):**

> Thank you for reaching out, [Customer Name], and I sincerely apologize for the confusion caused by the information you received. I want to make sure you have the correct details: our standard refund policy provides a 14-day refund window from the date of purchase. After this period, we offer account credits rather than cash refunds. I understand this may differ from what you were previously told, and I take that seriously. As a gesture of good faith, I'd like to offer you a [credit amount] account credit toward your next billing cycle. I've also flagged this discrepancy with our product team for immediate review. Would you like me to connect you with a senior member of our Customer Success team to discuss your options further?

---

## 8. Escalation to Account Management

### 8.1 When to Escalate

The following situations require immediate escalation to the Account Management team:

- Customer's annual recurring revenue (ARR) exceeds **$10,000** and they are requesting a refund or threatening to churn
- Customer has sent **3 or more emails** with no response from SenAI (response gap escalation)
- Customer is tagged as **VIP** in the CRM
- Customer explicitly requests to speak with a manager or escalate
- The refund request involves a **billing dispute exceeding $1,000**

### 8.2 Escalation Process

1. Email **vip@senai.io** with subject line "Account Escalation — [Customer Name] — [ARR Value]"
2. Include in the escalation: full email thread, CRM contact profile, account value, churn risk score, and a brief summary of the customer's concern
3. The Account Management team will respond within **2 hours** during business hours (9 AM – 6 PM ET, Monday–Friday)
4. For after-hours escalations involving Enterprise accounts with ARR > $50,000, page the on-call Account Manager via PagerDuty

---

## 9. Refund Processing Timelines

| Refund Type                  | Processing Time             | Payment Method              |
|------------------------------|-----------------------------|-----------------------------|
| Credit card refund           | **5–10 business days**      | Original credit card        |
| ACH refund                   | **7–14 business days**      | Original bank account       |
| Wire transfer refund         | **10–15 business days**     | Original wire details       |
| Account credit               | **Immediate** (next invoice)| Applied to account balance  |

All refunds are processed by the Finance team (finance@senai.io). Refund status inquiries should be directed to **billing@senai.io**.

---

## 10. Quarterly Refund Review

The VP of Customer Success and CFO conduct a **quarterly review** of all refunds and credits issued, including:
- Total refund volume and dollar amount
- Refund exception approvals and their outcomes
- Churn retention offer effectiveness rates
- Chatbot misinformation incidents and corrective actions
- Trends in refund reasons to inform product and support improvements

This review is documented and shared with the executive team to inform pricing, product, and customer success strategy.
