# SenAI Solutions — Compliance and Security FAQ

## Document Metadata

| Field            | Value                                           |
|------------------|-------------------------------------------------|
| Version          | 3.0                                             |
| Last Updated     | 2024-10-25                                      |
| Owner            | Chief Information Security Officer — Lin Zhao   |
| Classification   | Internal                                        |
| Approved By      | General Counsel — Sarah Mitchell                |
| Next Review Date | 2025-04-25                                      |

---

## 1. HIPAA Compliance

### 1.1 HIPAA Business Associate Agreement (BAA) Availability

SenAI Solutions offers a **HIPAA Business Associate Agreement (BAA)** for customers on the **Professional and Enterprise tiers**. The BAA establishes SenAI as a Business Associate under the Health Insurance Portability and Accountability Act (HIPAA) and outlines the responsibilities of both parties regarding Protected Health Information (PHI).

**Key requirements for HIPAA BAA eligibility:**

1. **Tier requirement:** The customer must be on the **Professional tier ($199/user/month) or Enterprise tier (custom pricing)**. HIPAA BAA is **not available** on Starter or Standard tiers because these tiers do not include the infrastructure isolation, encryption controls, and audit logging required for HIPAA compliance.
2. **BAA must be signed before PHI processing.** Under no circumstances may a customer begin processing, storing, or transmitting PHI through the SenAI platform until the BAA has been fully executed (signed by both parties). Processing PHI without a signed BAA is a violation of HIPAA regulations and may result in immediate account suspension.
3. **BAA signing process:**
   - Customer contacts **compliance@senai.io** or their dedicated Account Manager to request the BAA.
   - SenAI's Legal team sends the standard BAA template within **3 business days**.
   - Customer reviews and signs the BAA. Redline negotiations are accepted for Enterprise customers; Professional tier customers receive the standard BAA without modification.
   - SenAI countersigns within **5 business days** of receiving the signed document.
   - Total process timeline: typically **10–15 business days** from initial request to fully executed BAA.

### 1.2 HIPAA Technical Safeguards

When a BAA is in place, SenAI enables the following additional technical safeguards:

- **Data encryption at rest:** AES-256 encryption for all stored data, including database records, file attachments, and backups.
- **Data encryption in transit:** TLS 1.2 or higher for all data transmitted between the customer and SenAI infrastructure.
- **Access controls:** Role-based access control (RBAC) with mandatory multi-factor authentication (MFA) for all users accessing PHI.
- **Audit logging:** Comprehensive, tamper-evident audit logs of all access to and modifications of PHI. Audit logs are retained for **6 years** per HIPAA requirements.
- **Dedicated infrastructure:** Enterprise HIPAA customers are provisioned on isolated infrastructure (dedicated database instances and compute nodes) to prevent data commingling.
- **BAA with subprocessors:** SenAI maintains BAAs with all subprocessors that may access PHI (see Section 7 for subprocessor list).

### 1.3 HIPAA Incident Response

In the event of a breach involving PHI:
1. SenAI will notify the affected customer within **24 hours** of discovering the breach.
2. SenAI will provide a detailed incident report within **72 hours** of discovery.
3. SenAI will cooperate with the customer's breach notification obligations under HIPAA Breach Notification Rule (45 CFR §§ 164.400-414).
4. All HIPAA security incidents are managed by the Security Team (security@senai.io) and reviewed by the CISO.

### 1.4 HIPAA for Large Deployments

For customers with **50+ seats** requiring HIPAA BAA (such as healthcare organizations, health tech companies, and clinical research firms), SenAI offers a **dedicated onboarding track** that includes:
- A dedicated Compliance Engineer assigned to the account
- Custom data flow mapping and risk assessment
- Pre-deployment compliance review (typically 2–3 weeks)
- Annual compliance review meetings with the customer's compliance team

To initiate a HIPAA-compliant large deployment, contact **sales@senai.io** with subject line "HIPAA Enterprise Deployment — [Organization Name]".

---

## 2. GDPR Compliance

### 2.1 Data Processing Agreement (DPA)

SenAI Solutions provides a **Data Processing Agreement (DPA)** to all customers processing personal data of individuals in the European Union, European Economic Area, or the United Kingdom, in compliance with the **General Data Protection Regulation (GDPR)**.

**DPA availability:**
- Available for **all tiers** (Starter, Standard, Professional, Enterprise).
- The DPA is available for download at `https://senai.io/legal/dpa` or by request to **dpo@senai.io**.

**DPA signing process:**
1. Customer downloads the DPA from the website or requests it via email.
2. Customer reviews, signs, and returns the DPA to **dpo@senai.io**.
3. SenAI countersigns and returns the fully executed DPA within **5 business days**.
4. The DPA becomes effective upon the date of SenAI's countersignature.

### 2.2 GDPR Article 20 — Right to Data Portability

Under GDPR **Article 20**, data subjects have the right to receive their personal data in a structured, commonly used, and machine-readable format, and to transmit that data to another controller.

**SenAI's data portability process:**

1. **Request submission:** The customer (acting as the data controller) or the data subject directly submits a data portability request to **dpo@senai.io** with:
   - The data subject's identity verification (government-issued ID or other acceptable proof)
   - Specific description of the data requested
   - Preferred export format (see below)

2. **Acknowledgement:** SenAI acknowledges receipt of the data portability request within **72 hours** via email.

3. **Statutory fulfillment window:** SenAI will fulfill the data portability request within **30 calendar days** of receipt. This is the statutory window mandated by GDPR. In complex cases (e.g., large data volumes exceeding 10 GB or requests requiring manual data extraction from archived systems), SenAI may extend this by an additional **60 days** with written notice to the requestor explaining the reason for the extension.

4. **Data included in portability export:**
   - All emails sent by or associated with the data subject
   - Contact profile information (name, email, company, account metadata)
   - Classification and sentiment data generated from the data subject's communications
   - Action logs and agent reasoning traces associated with the data subject's emails
   - Webhook event logs related to the data subject

5. **Export formats available:**
   - **JSON** (recommended) — structured, machine-readable
   - **CSV** — tabular format for contact and email metadata
   - **PDF** — human-readable summary report (not machine-readable, provided as a supplement)

6. **Delivery method:** Exported data is delivered via a **secure, time-limited download link** (expires after 72 hours) sent to the requestor's verified email address. The download is encrypted with a one-time passphrase communicated separately.

### 2.3 GDPR Article 17 — Right to Erasure

Under GDPR **Article 17**, data subjects have the right to request the deletion of their personal data. SenAI processes erasure requests as follows:

1. **Request submission:** Submit erasure requests to **dpo@senai.io**.
2. **Acknowledgement:** Within **72 hours** of receipt.
3. **Erasure timeline:** SenAI will erase all personal data associated with the data subject within **30 calendar days** of receipt, unless a legal exception applies (e.g., data required for legal defense, regulatory compliance, or contract fulfillment).
4. **Scope of erasure:**
   - Contact profile: permanently deleted
   - Emails: permanently deleted from primary databases and search indices
   - Embeddings: vectors associated with the data subject's data are deleted from the vector database
   - Backups: data subject's data is excluded from future backup cycles. Existing backups are purged within **90 days** per the backup retention schedule.
   - Audit logs: Audit log entries referencing the data subject are anonymized (personal identifiers replaced with pseudonyms) rather than deleted, to maintain system integrity.
5. **Confirmation:** SenAI provides written confirmation of erasure completion to the requestor.

### 2.4 GDPR Article 33 — Breach Notification

In the event of a personal data breach, SenAI will:
1. Notify the affected customer (data controller) within **72 hours** of becoming aware of the breach, as required by GDPR Article 33.
2. Include in the notification: nature of the breach, categories and approximate number of data subjects affected, likely consequences, and measures taken or proposed to address the breach.
3. Cooperate with the customer's supervisory authority notification obligations.
4. Maintain an internal breach register documenting all breaches, including those that do not require customer notification.

---

## 3. SOC 2 Type II Certification

### 3.1 Certification Status

SenAI Solutions holds a current **SOC 2 Type II** certification, audited by **Deloitte LLP**. The certification covers the following Trust Service Criteria:
- **Security** — Protection of information and systems against unauthorized access
- **Availability** — Accessibility of the system as stipulated by the SLA
- **Confidentiality** — Protection of information designated as confidential
- **Processing Integrity** — Completeness, accuracy, and timeliness of system processing

### 3.2 Audit Period

The most recent SOC 2 Type II audit covers the period **July 1, 2023 through June 30, 2024**. The next audit period is **July 1, 2024 through June 30, 2025**, with the report expected to be available by **September 2025**.

### 3.3 How to Request the SOC 2 Report

The SOC 2 Type II report is available to current and prospective customers under a **Non-Disclosure Agreement (NDA)**.

**Request process:**
1. Email **compliance@senai.io** with subject line "SOC 2 Report Request — [Company Name]".
2. If an NDA is not already in place, SenAI will send a mutual NDA for execution.
3. Upon NDA execution, the SOC 2 report is delivered via a secure download link within **3 business days**.
4. The report is provided in PDF format and may not be redistributed without SenAI's written consent.

---

## 4. Data Residency

### 4.1 Available Regions

SenAI offers data residency options in the following regions:

| Region         | Data Center Location      | Tier Availability       | Default |
|----------------|---------------------------|-------------------------|---------|
| **US**         | AWS us-east-1 (Virginia)  | All tiers               | ✓       |
| **EU**         | AWS eu-west-1 (Ireland)   | Professional, Enterprise| ✗       |
| **APAC**       | AWS ap-southeast-1 (Singapore) | Enterprise only    | ✗       |

### 4.2 Data Residency Guarantees

When a customer selects a specific data residency region:
- All primary data (emails, contacts, classifications, agent logs) is stored exclusively in the selected region.
- Database replicas for high availability remain within the same region.
- Backups are stored in a secondary availability zone within the same region.
- **Cross-region data transfer** does not occur for customer data. Platform telemetry and anonymized usage metrics may be processed in the US region regardless of customer data residency selection.

### 4.3 Changing Data Residency

Customers on Enterprise plans may request a data residency migration by contacting their Account Manager. Data residency migrations typically take **2–4 weeks** and involve a planned maintenance window for the customer's account. There is a one-time migration fee of **$5,000** for data residency changes.

---

## 5. Subprocessor List

### 5.1 Current Subprocessors

SenAI uses the following subprocessors to provide its services:

| Subprocessor        | Purpose                               | Data Processed            | Location      |
|---------------------|---------------------------------------|---------------------------|---------------|
| **Amazon Web Services (AWS)** | Infrastructure hosting, compute, storage | All customer data   | US, EU, APAC  |
| **OpenAI**          | LLM inference for email classification | Email body text (anonymized where possible) | US |
| **Stripe**          | Payment processing                    | Billing and payment data  | US            |
| **Datadog**         | Infrastructure monitoring             | System telemetry (no customer PII) | US   |
| **PagerDuty**       | Incident management and on-call       | Incident metadata (no customer PII) | US   |
| **SendGrid**        | Transactional email delivery          | Email addresses, notification content | US  |
| **Cloudflare**      | CDN and DDoS protection               | Request metadata, IP addresses | Global  |

### 5.2 Subprocessor Change Notification

SenAI notifies customers of changes to the subprocessor list as follows:
- **Notification method:** Email to the account's designated data protection contact and posting on `https://senai.io/legal/subprocessors`.
- **Notification timeline:** At least **30 days before** the new subprocessor begins processing customer data.
- **Objection right:** Customers may object to a new subprocessor within the 30-day notice period by contacting **dpo@senai.io**. If the objection cannot be resolved, the customer may terminate their agreement without penalty.

---

## 6. Penetration Testing Policy

### 6.1 Customer-Initiated Penetration Testing

Customers who wish to conduct penetration testing or vulnerability assessments against SenAI's infrastructure must obtain **written approval** from SenAI's Security Team before commencing any testing.

**Approval process:**
1. Submit a pen test request to **security@senai.io** at least **15 business days** before the planned test date.
2. Include: testing scope, methodology, tools to be used, testing dates and times, IP addresses from which testing will originate.
3. SenAI's Security Team will review the request and respond within **5 business days** with approval, conditions, or denial.
4. All approved tests must be conducted during agreed-upon windows and must not target production infrastructure without explicit consent.
5. Post-test, the customer must provide SenAI with a copy of the pen test report within **10 business days** of completion.

### 6.2 SenAI's Internal Security Testing

SenAI conducts its own security testing program:
- **External penetration testing:** Annually, by a third-party security firm (currently NCC Group).
- **Internal vulnerability scanning:** Weekly automated scans using Qualys.
- **Bug bounty program:** SenAI operates a private bug bounty program via HackerOne for Professional and Enterprise customers. Details at `https://hackerone.com/senai`.

---

## 7. Data Encryption

### 7.1 Encryption at Rest

All customer data stored by SenAI is encrypted at rest using **AES-256 encryption**. This includes:
- Database records (PostgreSQL with Transparent Data Encryption)
- File attachments and document uploads
- Vector embeddings in the pgvector database
- Backup files (encrypted before storage in S3)
- Audit logs

Encryption keys are managed using **AWS Key Management Service (KMS)** with automatic key rotation every **365 days**. Enterprise customers may optionally use **Customer Managed Keys (CMK)** for additional control over encryption key lifecycle.

### 7.2 Encryption in Transit

All data transmitted between customers and SenAI infrastructure is encrypted using **TLS 1.2 or higher**. SenAI does not support TLS 1.0 or TLS 1.1.

- API traffic: TLS 1.2+ with forward secrecy (ECDHE key exchange)
- Dashboard (web application): TLS 1.2+ with HSTS enabled
- Webhook deliveries: TLS 1.2+ (SenAI validates the recipient server's TLS certificate)
- Internal service-to-service communication: mTLS (mutual TLS) within the SenAI infrastructure

### 7.3 Encryption Key Management

- Production encryption keys are stored in AWS KMS and are never accessible to SenAI personnel in plaintext.
- Key access is logged and monitored. Any unauthorized key access attempt triggers an immediate security alert.
- Enterprise customers using CMK can revoke SenAI's access to their encryption keys at any time, which will render their data inaccessible to SenAI.

---

## 8. Data Retention Policy

### 8.1 During Active Subscription

While a customer's subscription is active, SenAI retains all customer data (emails, contacts, classifications, agent logs, analytics) in accordance with the data retention period specified by the customer's subscription tier:
- **Starter:** 30 days
- **Standard:** 90 days
- **Professional:** 1 year
- **Enterprise:** Custom (defined in MSA, typically 2–7 years)

Data beyond the retention period is automatically archived and eventually purged per the tier's archival policy.

### 8.2 After Account Closure

When a customer closes their account (either by cancellation or non-renewal):

1. **Grace period:** Customer data is retained for **90 days** after account closure. During this period, the customer may request data export (see GDPR Article 20, Section 2.2) or account reactivation.
2. **After 90 days:** All customer data is **permanently deleted** from primary databases, search indices, and vector databases.
3. **Backups:** Customer data in backup systems is purged within **90 days** of deletion from primary systems (i.e., up to **180 days** total from account closure).
4. **Immediate deletion on request:** Customers may request immediate deletion of all data upon account closure by emailing **dpo@senai.io**. Immediate deletion requests are processed within **30 days** and bypass the 90-day grace period.

### 8.3 Audit Log Retention

Audit logs are retained for a minimum of **2 years** after account closure for regulatory compliance and dispute resolution purposes. Audit log entries are anonymized (personal identifiers removed) **90 days** after account closure.

---

## 9. Security Certifications and Standards

### 9.1 Certifications Held

| Certification          | Status      | Auditor       | Valid Through   |
|------------------------|-------------|---------------|-----------------|
| SOC 2 Type II          | ✅ Current   | Deloitte LLP  | June 30, 2025   |
| ISO 27001              | ✅ Current   | BSI Group     | December 31, 2025|
| HIPAA (BAA available)  | ✅ Available | N/A (self-assessed with BAA) | Ongoing |
| GDPR (DPA available)   | ✅ Compliant | N/A           | Ongoing         |
| PCI DSS Level 1        | ✅ Current (via Stripe) | Stripe  | Ongoing      |

### 9.2 Security Practices Summary

- **Employee background checks:** All SenAI employees undergo background checks before hire.
- **Security training:** Mandatory annual security awareness training for all employees.
- **Access control:** Principle of least privilege. Production access requires MFA and is audited quarterly.
- **Incident response plan:** Documented and tested annually via tabletop exercises.
- **Disaster recovery:** RPO (Recovery Point Objective) = 1 hour; RTO (Recovery Time Objective) = 4 hours for Professional/Enterprise tiers.

---

## 10. Frequently Asked Questions

### Q: Can I use SenAI for processing health-related data?
**A:** Yes, but only on the **Professional or Enterprise tier** with a signed **HIPAA Business Associate Agreement (BAA)** in place. You must not process any Protected Health Information (PHI) until the BAA is fully executed. Contact compliance@senai.io to initiate the BAA process.

### Q: How do I submit a GDPR data subject request?
**A:** Send all GDPR requests (data portability, right to erasure, right of access) to **dpo@senai.io**. SenAI will acknowledge receipt within **72 hours** and fulfill the request within the **30-day statutory window**.

### Q: Is SenAI SOC 2 certified?
**A:** Yes. SenAI holds a current **SOC 2 Type II** certification covering Security, Availability, Confidentiality, and Processing Integrity. The report is available under NDA — contact compliance@senai.io to request it.

### Q: Where is my data stored?
**A:** By default, data is stored in the **US (AWS us-east-1)**. Professional tier customers can select **EU (AWS eu-west-1)**. Enterprise customers can additionally select **APAC (AWS ap-southeast-1)** or request custom data residency arrangements.

### Q: Does SenAI encrypt my data?
**A:** Yes. All data is encrypted **at rest using AES-256** and **in transit using TLS 1.2+**. Enterprise customers may use Customer Managed Keys (CMK) for additional encryption key control.

### Q: Can I run a penetration test against SenAI?
**A:** Yes, with prior written approval from our Security Team. Submit your request to **security@senai.io** at least 15 business days before the planned test. See Section 6 for the full approval process.

### Q: How does SenAI handle data breaches?
**A:** SenAI notifies affected customers within **72 hours** of discovering a breach, per GDPR Article 33. For HIPAA-covered accounts, notification is provided within **24 hours**. See Section 2.4 and Section 1.3 for details.

### Q: What happens to my data when I close my account?
**A:** Your data is retained for **90 days** after closure for export or reactivation purposes. After 90 days, all data is permanently deleted. You may request immediate deletion at any time by contacting dpo@senai.io. See Section 8 for full details.
