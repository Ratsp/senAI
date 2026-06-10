# SenAI Solutions — Service Level Agreement (SLA) Policy

## Document Metadata

| Field            | Value                                      |
|------------------|--------------------------------------------|
| Version          | 4.1                                        |
| Last Updated     | 2024-10-01                                 |
| Owner            | VP of Engineering — Rachel Chen            |
| Classification   | Internal                                   |
| Approved By      | CTO — James Whitfield                      |
| Next Review Date | 2025-04-01                                 |

---

## 1. Uptime Service Level Agreement

### 1.1 Uptime Guarantee

SenAI Solutions guarantees a **monthly uptime of 99.9%** for customers on the **Professional and Enterprise tiers**. Customers on the Starter and Standard tiers receive a **99.5% monthly uptime guarantee**.

**Uptime** is defined as the percentage of total minutes in a calendar month during which the SenAI platform core services (API endpoints, dashboard, data processing pipeline) are operational and accessible. Uptime is calculated as:

```
Uptime % = ((Total Minutes in Month − Downtime Minutes) / Total Minutes in Month) × 100
```

**Downtime** is defined as any period exceeding 5 consecutive minutes during which the SenAI API returns HTTP 5xx errors for more than 50% of requests, as measured by SenAI's internal monitoring infrastructure (Datadog).

### 1.2 Uptime Tiers

| Tier          | Uptime Guarantee | Monthly Allowed Downtime |
|---------------|------------------|--------------------------|
| Starter       | 99.5%            | ~219 minutes (3h 39m)    |
| Standard      | 99.5%            | ~219 minutes (3h 39m)    |
| Professional  | 99.9%            | ~43 minutes              |
| Enterprise    | 99.9% (default)  | ~43 minutes              |

Enterprise customers may negotiate enhanced uptime SLAs (e.g., **99.95%** or **99.99%**) as part of their Master Service Agreement. Enhanced SLAs are subject to additional infrastructure fees.

---

## 2. Incident Severity Levels

SenAI classifies all platform incidents into four severity levels. The severity level determines response time commitments, escalation procedures, and resolution targets.

### 2.1 Severity Level Definitions

#### P0 — Critical (Service Down)

**Definition:** Complete platform outage affecting all customers, or a security breach involving customer data. The core SenAI API is unreachable or returning errors for 100% of requests. No workaround is available.

**Examples:**
- Total API outage: all endpoints returning HTTP 503
- Database failure causing complete data inaccessibility
- Confirmed data breach or unauthorized access to customer data
- Payment processing system failure affecting all billing operations

**Impact:** All customers are affected. Revenue-impacting. Requires immediate all-hands response.

#### P1 — High (Major Degradation)

**Definition:** A major feature or service is non-functional or severely degraded for a significant subset of customers. A workaround may exist but is not acceptable for sustained use.

**Examples:**
- Email classification pipeline producing incorrect results for >10% of emails
- Dashboard loading times exceeding 30 seconds for all users
- Webhook delivery failure for all Professional and Enterprise customers
- SSO authentication failures preventing login for an entire organization
- RAG pipeline returning zero results for all knowledge base queries

**Impact:** Multiple customers affected. Significant functionality loss. Workaround may exist.

#### P2 — Medium (Partial Degradation)

**Definition:** A non-critical feature is impaired, or a critical feature is degraded for a small number of customers. A reasonable workaround is available.

**Examples:**
- Analytics dashboard charts failing to render for a subset of users
- Intermittent API timeout errors (< 5% of requests)
- Email sentiment scoring returning inconsistent results
- Single customer's webhook configuration failing to save
- Sandbox environment unavailable

**Impact:** Limited customer impact. Core functionality intact. Workaround available.

#### P3 — Low (Minor Issue)

**Definition:** A cosmetic issue, documentation error, minor UI bug, or feature request. No impact on core platform functionality.

**Examples:**
- Typo in API error messages
- Dashboard UI alignment issues in specific browser versions
- Documentation referencing deprecated API v1 endpoints
- Feature request for additional export formats
- Minor CSS rendering issue on mobile devices

**Impact:** Minimal. No functional degradation. Informational or cosmetic.

---

## 3. Response Time SLAs

### 3.1 Response Time Commitments by Severity

Response time is measured from the moment SenAI's monitoring system detects the incident (for platform-wide issues) or from the moment a customer reports the incident via the designated support channel (for customer-specific issues).

| Severity | Initial Response Time | Update Frequency     | Resolution Target       |
|----------|-----------------------|----------------------|-------------------------|
| **P0**   | **15 minutes**        | Every 30 minutes     | **4 hours**             |
| **P1**   | **1 hour**            | Every 2 hours        | **8 hours**             |
| **P2**   | **4 hours**           | Every 24 hours       | **48 hours (2 business days)** |
| **P3**   | **24 hours**          | As needed            | **5 business days**     |

### 3.2 Initial Response Definition

The **initial response** is defined as an acknowledgement from a qualified SenAI engineer or support agent that includes:
1. Confirmation that the issue has been received and logged
2. The assigned severity level
3. The name or ID of the responding engineer
4. A brief initial assessment or request for additional information

Automated ticket acknowledgements (e.g., "Your ticket has been received") do **not** qualify as an initial response.

### 3.3 Resolution Definition

**Resolution** means the incident is resolved and the affected service is restored to normal operation, or a permanent workaround has been implemented and accepted by the customer. Temporary workarounds that do not restore full functionality do not constitute resolution.

---

## 4. Root Cause Analysis (RCA) Delivery SLA

### 4.1 RCA Requirements by Severity

SenAI commits to delivering a formal Root Cause Analysis (RCA) report after the resolution of P0 and P1 incidents.

| Severity | RCA Delivery Deadline                              | Distribution                          |
|----------|-----------------------------------------------------|---------------------------------------|
| **P0**   | **Within 24 hours** after incident resolution       | All affected Enterprise customers + VP Engineering + CTO |
| **P1**   | **Within 72 hours** after incident resolution       | Affected customers who submitted tickets + VP Engineering |
| **P2**   | Upon customer request (5 business days)             | Requesting customer only              |
| **P3**   | Not applicable                                      | N/A                                   |

### 4.2 RCA Report Contents

Every RCA report must include the following sections:

1. **Incident Summary:** Date, duration, severity, number of affected customers
2. **Timeline of Events:** Chronological sequence of events from detection to resolution
3. **Root Cause:** Technical explanation of the underlying cause
4. **Impact Assessment:** Quantified impact (e.g., number of failed API calls, affected accounts, data integrity status)
5. **Corrective Actions:** Specific steps taken or planned to prevent recurrence, with owners and deadlines
6. **Preventive Measures:** Systemic improvements to monitoring, alerting, or architecture

### 4.3 RCA Delivery for Legal-Sensitive Incidents

If an incident involves an **SLA breach that has triggered a legal threat** from a customer, the RCA must be reviewed by SenAI Legal (legal@senai.io) before delivery to the customer. In such cases, the RCA delivery deadline is extended to **48 hours** after resolution, and the document must not include language that could be construed as an admission of liability beyond the contractual SLA credit obligations.

---

## 5. SLA Credit Calculation

### 5.1 Credit Formula

When SenAI fails to meet the uptime guarantee for a given calendar month, affected customers are entitled to **SLA credits** applied to their next invoice. Credits are calculated as follows:

| Monthly Uptime      | Service Credit (% of Monthly Fee) |
|---------------------|------------------------------------|
| 99.9% – 99.0%      | **5%** of monthly subscription fee |
| 99.0% – 98.0%      | **10%** of monthly subscription fee|
| 98.0% – 95.0%      | **20%** of monthly subscription fee|
| Below 95.0%         | **30%** of monthly subscription fee (maximum credit) |

**Maximum credit cap:** SLA credits shall not exceed **30% of the customer's monthly subscription fee** in any single calendar month. SLA credits are the sole and exclusive remedy for uptime SLA breaches under this policy.

### 5.2 Credit Calculation Example

A Professional tier customer paying $199/user/month with 20 users ($3,980/month total) experiences 99.3% uptime in a calendar month (approximately 5 hours of downtime).

- Uptime falls in the 99.0%–99.9% bracket → **5% credit**
- Credit amount: $3,980 × 0.05 = **$199.00**
- Credit is applied as a line-item deduction on the next invoice

### 5.3 Enterprise Enhanced SLA Credits

Enterprise customers with negotiated enhanced SLAs (e.g., 99.95% uptime) may have custom credit schedules defined in their Master Service Agreement. The standard credit formula above applies unless explicitly superseded by the MSA terms.

---

## 6. How to Claim SLA Credits

### 6.1 Credit Request Process

1. **Submit a request** by emailing **sla-credits@senai.io** with the following information:
   - Account name and billing email
   - Date(s) and time(s) of the downtime event (in UTC)
   - Incident ticket number (if available)
   - Brief description of the impact on your operations
2. **Deadline:** Credit requests must be submitted within **30 calendar days** of the end of the month in which the downtime occurred. Requests submitted after this window will not be honored.
3. **Verification:** SenAI will verify the reported downtime against internal monitoring data within **5 business days** of receiving the request.
4. **Credit issuance:** Approved credits are applied as a line-item deduction on the customer's next invoice. Credits are **not redeemable for cash** and cannot be transferred to another account.

### 6.2 Dispute Resolution

If a customer disagrees with SenAI's determination of uptime or credit eligibility, the customer may escalate the dispute to the VP of Customer Success (cs-vp@senai.io). The VP will review the case and issue a final determination within 10 business days.

---

## 7. SLA Exclusions

The uptime guarantee and SLA credits do **not** apply to downtime caused by the following:

### 7.1 Scheduled Maintenance

SenAI performs scheduled maintenance during a designated maintenance window: **Sundays 02:00–06:00 UTC**. Customers are notified at least **72 hours in advance** of any scheduled maintenance that may result in downtime. Scheduled maintenance windows are excluded from uptime calculations.

### 7.2 Customer-Caused Issues

Downtime resulting from:
- Customer misconfiguration of API integrations, webhooks, or SSO settings
- Customer-initiated actions that exceed documented rate limits or resource quotas
- Customer failure to implement recommended security patches or SDK updates
- Unauthorized modifications to customer-provisioned infrastructure that interacts with SenAI APIs

### 7.3 Force Majeure

Downtime caused by events beyond SenAI's reasonable control, including but not limited to:
- Natural disasters (earthquakes, floods, hurricanes)
- Acts of war, terrorism, or civil unrest
- Government actions or regulatory changes
- Internet backbone failures or DNS infrastructure outages
- Pandemic-related disruptions

### 7.4 Third-Party Dependencies

Downtime caused by outages in third-party services upon which SenAI depends (e.g., cloud provider outages, payment processor downtime) are excluded, provided SenAI can demonstrate that the root cause originated with the third-party provider.

---

## 8. Escalation Path for SLA Breaches

### 8.1 Internal Escalation Procedure

When an incident results in an SLA breach (i.e., response time or uptime commitment is not met), the following escalation path is triggered automatically:

| Escalation Level | Trigger                                             | Notified Parties                        | Action Required              |
|-------------------|-----------------------------------------------------|-----------------------------------------|-------------------------------|
| **Level 1**       | Response time SLA missed by >10 minutes (P0/P1)     | Engineering On-Call Lead                | Immediate assessment          |
| **Level 2**       | Resolution time SLA missed by >1 hour               | VP of Engineering + VP Customer Success | Customer communication plan   |
| **Level 3**       | Customer escalation or legal threat received         | CTO + VP of Sales + Legal Team          | Executive review within 1 hour|

### 8.2 Customer-Facing Escalation

If a customer has experienced an SLA breach and is dissatisfied with the resolution or credit offered, they may escalate through the following channels:

1. **Support escalation:** Email **escalations@senai.io** with "SLA BREACH" in the subject line.
2. **Account Manager escalation:** Enterprise customers should contact their dedicated Account Manager directly.
3. **Executive escalation:** For unresolved disputes, customers may request a call with the VP of Customer Success by emailing **cs-vp@senai.io**.

---

## 9. Enterprise SLA vs. Standard SLA Differences

| Feature                      | Standard SLA (Starter/Standard) | Enterprise SLA (Professional/Enterprise) |
|------------------------------|----------------------------------|------------------------------------------|
| Uptime Guarantee             | 99.5%                            | 99.9% (negotiable up to 99.99%)          |
| P0 Response Time             | 30 minutes                       | **15 minutes**                           |
| P1 Response Time             | 2 hours                          | **1 hour**                               |
| RCA Delivery (P0)            | 72 hours                         | **24 hours**                             |
| Dedicated Incident Manager   | ✗                                | ✓ (for P0/P1)                            |
| Custom Maintenance Windows   | ✗                                | ✓ (negotiable)                           |
| Maximum SLA Credit           | 20% of monthly fee               | **30% of monthly fee**                   |
| Direct Engineering Escalation| ✗                                | ✓ (CTO-level for P0)                     |

---

## 10. Legal Escalation Process for SLA Breaches

### 10.1 When a Customer Threatens Legal Action

If a customer explicitly threatens legal action (e.g., references "legal counsel," "lawsuit," "breach of contract," or "cease and desist") in connection with an SLA breach, the following protocol is activated **immediately**:

1. **Stop all automated communications** to the customer. No auto-replies, no templated responses.
2. **Notify Legal Team** within **1 hour** by emailing **legal@senai.io** with:
   - Customer name, account ID, and contact information
   - Thread history of all communications related to the SLA breach
   - Incident timeline with downtime measurements
   - Current SLA credit calculation and any credits already offered
   - Verbatim text of the legal threat
3. **Notify CTO and VP of Engineering** via the internal `#sla-breaches` Slack channel.
4. **Do NOT:**
   - Admit fault or liability beyond the contractual SLA credit obligations
   - Make verbal promises about additional compensation outside of policy
   - Share internal RCA documents with the customer without Legal review
   - Ignore or delay responding to the customer — silence increases legal risk
5. **Legal Team Response:** Legal will review the case and provide guidance within **4 business hours**. Legal will draft or approve all subsequent customer-facing communications.
6. **Executive Involvement:** For Enterprise customers with contract values exceeding **$100,000/year**, the CEO is notified within 2 hours of the legal threat.

### 10.2 Proactive SLA Breach Communication

To reduce the likelihood of legal escalation, SenAI proactively communicates SLA breaches to affected customers:

1. **During the incident:** Status page updates every 30 minutes, email notification to affected accounts.
2. **After resolution:** Email notification with incident summary, expected RCA delivery date, and SLA credit eligibility notice.
3. **RCA delivery:** Formal RCA with corrective actions and credit calculation.

This proactive communication ensures customers feel heard and reduces the likelihood of adversarial escalation.

---

## 11. SLA Monitoring and Reporting

### 11.1 Internal Monitoring

SenAI uses the following tools to monitor SLA compliance:
- **Datadog:** Real-time API performance monitoring, error rate tracking, and alerting
- **PagerDuty:** On-call rotation management and incident escalation automation
- **StatusPage (status.senai.io):** Public-facing incident communication

### 11.2 Customer-Facing SLA Reports

Enterprise customers receive a **monthly SLA report** delivered via email within 5 business days of the end of each calendar month. The report includes:
- Actual uptime percentage for the month
- Number and severity of incidents
- Response and resolution times vs. SLA targets
- SLA credit eligibility (if applicable)
- Upcoming scheduled maintenance windows
