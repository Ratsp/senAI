# PRD: SenAI Agentic CRM Intelligence Platform

## Document Metadata

| Field | Value |
|---|---|
| Project Name | SenAI Agentic CRM Intelligence Platform |
| Version | 1.0 |
| Status | Ready for Implementation |
| Timeline | 2–3 days (take-home assessment) |
| Dataset | `email-data-advanced.json` (60 emails, 30 threads) |
| Deliverables | GitHub repo + Architecture diagram + Screen recording (5–10 min) |

---

## 1. SYSTEM OVERVIEW

### 1.1 What This System Is

A production-grade, AI-powered Customer Relationship Management (CRM) system that:

- Autonomously monitors a high-volume email inbox
- Triages emails using multi-dimensional intelligence (heuristics + LLM + RAG)
- Executes agentic workflows (classify, decide, act — not just classify)
- Surfaces real-time business insights via dashboards
- Handles the full email lifecycle: ingestion → classification → action → resolution

### 1.2 What Makes This "Advanced"

- The AI acts as an autonomous agent — it decides AND acts across multi-step workflows
- A RAG pipeline grounds the agent in internal knowledge (pricing, SLA, refund, compliance docs)
- A live web intelligence module scrapes public signals (reviews, competitor pricing) and injects them into context
- Emails form conversation threads — the agent must read full thread history before acting
- The system must handle conflicting signals, escalation chains, and GDPR/compliance edge cases

### 1.3 Tech Stack (Recommended — Justify Deviations)

| Layer | Recommended Choice | Alternatives |
|---|---|---|
| Backend | Python (FastAPI) or Node.js (Express/NestJS) | Go, Rust |
| Database | PostgreSQL with pgvector extension | SQLite + FAISS for dev |
| Vector DB | pgvector (collocated) or ChromaDB or FAISS | Pinecone, Weaviate |
| LLM | OpenAI GPT-4o / GPT-4o-mini or Anthropic Claude | Any LLM with structured output |
| Embeddings | OpenAI `text-embedding-3-small` or `sentence-transformers` | Cohere, Voyage |
| Frontend | React + TypeScript + Tailwind CSS | Next.js, Vue, Svelte |
| Real-time | WebSocket (Socket.IO) or SSE | Polling as fallback |
| Containerization | Docker Compose | Podman |

---

## 2. DATA MODEL

### 2.1 Input Dataset Schema

The file `email-data-advanced.json` contains 60 emails. Each email object has this structure:

```json
{
  "message_id": "msg_001",
  "thread_id": "thread_alice_pricing",
  "sender": "alice.smith@greenlight-npo.org",
  "recipient": "support@senai.io",
  "subject": "...",
  "body": "...",
  "timestamp": "2024-11-01T09:15:00Z",
  "labels": ["inquiry", "pricing"]
}
```

### 2.2 Critical Threads the Agent Must Handle

| Thread ID | Scenario | Email Count | Risk Level | Key Requirement |
|---|---|---|---|---|
| `thread_alice_pricing` | Multi-turn pricing negotiation → upgrade → billing question | 5 emails over 13 days | Medium | Read full thread before classifying msg_041 (pro-rata billing). Use correct pricing tier from RAG. |
| `thread_bob_outage` | P0 incident → SLA breach → RCA → legal escalation | 4 emails | Critical | msg_060: Agent must retrieve thread history, search SLA policy, check account status, flag_for_legal(), draft holding reply, escalate_to_human(). Show full reasoning trace. |
| `thread_karen_refund` | Complaint with 0 replies → escalating anger → churn threat → public review threat | 3+ emails | Critical | By msg_033: detect 3 emails with zero replies, trigger web scraping (G2/Trustpilot), generate high-priority escalation brief, suggest retention offer from refund policy KB. |
| `thread_eleanor_compliance` | Enterprise HIPAA compliance deal — 200 seats, deadline pressure | Variable | High | Must retrieve compliance_faq.md for HIPAA BAA info. |
| `thread_bigcorp_rfp` | RFP + compliance audit + new user registration — linked to $2.4M opportunity | Variable | Critical | Multi-faceted: handle RFP, compliance, and registration in one thread context. |
| `thread_security_*` | Suspicious login + ransomware threat | 2+ emails | Critical | msg_038 (ransomware): IMMEDIATELY flag Critical, escalate to security queue, NEVER auto-reply. |
| `thread_gdpr_001` | Formal GDPR Article 20 data portability request | 1+ emails | Legal | msg_052: detect legal nature, flag_for_legal(), auto-acknowledge citing 30-day statutory window, create compliance ticket. NEVER generic response. |
| `thread_spam_*` | SEO pitch, Nigerian prince, cold outreach | Multiple | Low | Must NOT auto-reply to any spam. |
| `thread_nadia_bug` | Silent data corruption — success message shown but data missing | Variable | High | Mission-critical bug report requiring engineering escalation. |
| `thread_chatbot_misinformation` | Own chatbot gave wrong refund info | 1+ emails | High | msg_056: retrieve actual refund policy via RAG, acknowledge discrepancy, escalate with chatbot-said-vs-policy summary, draft empathetic reply WITHOUT admitting legal liability. |

### 2.3 Database Schema (PostgreSQL)

Implement the following 7 tables. All tables require proper indexing.

#### Table: `contacts`

```sql
CREATE TABLE contacts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255),
    company VARCHAR(255),
    status VARCHAR(20) CHECK (status IN ('VIP', 'Blocked', 'Active', 'Churned')) DEFAULT 'Active',
    account_value DECIMAL(12,2),
    churn_risk_score FLOAT DEFAULT 0.0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    last_contact_at TIMESTAMPTZ
);
CREATE INDEX idx_contacts_email ON contacts(email);
CREATE INDEX idx_contacts_status ON contacts(status);
```

#### Table: `threads`

```sql
CREATE TABLE threads (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    thread_id VARCHAR(255) UNIQUE NOT NULL,
    subject VARCHAR(500),
    sender_email VARCHAR(255) REFERENCES contacts(email),
    first_seen_at TIMESTAMPTZ,
    last_updated_at TIMESTAMPTZ,
    status VARCHAR(20) CHECK (status IN ('Open', 'Resolved', 'Escalated', 'Ignored')) DEFAULT 'Open',
    assigned_to VARCHAR(255)
);
CREATE INDEX idx_threads_thread_id ON threads(thread_id);
CREATE INDEX idx_threads_sender ON threads(sender_email);
CREATE INDEX idx_threads_status ON threads(status);
```

#### Table: `emails`

```sql
CREATE TABLE emails (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    thread_id UUID REFERENCES threads(id),
    message_id VARCHAR(255) UNIQUE NOT NULL,
    sender VARCHAR(255) NOT NULL,
    subject VARCHAR(500),
    body TEXT,
    timestamp TIMESTAMPTZ NOT NULL,
    sentiment_score FLOAT,
    category VARCHAR(50),
    urgency VARCHAR(20),
    requires_human BOOLEAN DEFAULT FALSE,
    confidence FLOAT,
    raw_entities JSONB,
    status VARCHAR(20) CHECK (status IN ('Received', 'Processing', 'Replied', 'Escalated', 'Ignored')) DEFAULT 'Received'
);
CREATE INDEX idx_emails_message_id ON emails(message_id);
CREATE INDEX idx_emails_thread_id ON emails(thread_id);
CREATE INDEX idx_emails_sender ON emails(sender);
CREATE INDEX idx_emails_timestamp ON emails(timestamp);
CREATE INDEX idx_emails_sentiment ON emails(sender, timestamp, sentiment_score);
```

#### Table: `actions`

```sql
CREATE TABLE actions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email_id UUID REFERENCES emails(id),
    agent_reasoning_log JSONB,
    action_type VARCHAR(30) CHECK (action_type IN ('Auto-Reply', 'Escalate', 'Legal-Flag', 'Ticket-Created', 'Ignored')),
    proposed_content TEXT,
    is_approved BOOLEAN DEFAULT FALSE,
    approved_by VARCHAR(255),
    executed_at TIMESTAMPTZ
);
CREATE INDEX idx_actions_email_id ON actions(email_id);
```

#### Table: `knowledge_chunks`

```sql
CREATE TABLE knowledge_chunks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_doc VARCHAR(255) NOT NULL,
    chunk_text TEXT NOT NULL,
    embedding VECTOR(1536),
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_knowledge_chunks_embedding ON knowledge_chunks USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
```

#### Table: `web_intelligence_cache`

```sql
CREATE TABLE web_intelligence_cache (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_url VARCHAR(1000),
    target_entity VARCHAR(255),
    scraped_data JSONB,
    scraped_at TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ NOT NULL
);
CREATE INDEX idx_web_cache_entity ON web_intelligence_cache(target_entity);
CREATE INDEX idx_web_cache_expires ON web_intelligence_cache(expires_at);
```

#### Table: `audit_log`

```sql
CREATE TABLE audit_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    entity_type VARCHAR(50) NOT NULL,
    entity_id UUID NOT NULL,
    action VARCHAR(100) NOT NULL,
    performed_by VARCHAR(255) NOT NULL,
    timestamp TIMESTAMPTZ DEFAULT NOW(),
    diff JSONB
);
CREATE INDEX idx_audit_entity ON audit_log(entity_type, entity_id);
CREATE INDEX idx_audit_timestamp ON audit_log(timestamp);
```

### 2.4 Performance Requirements

| Query | Target | How to Achieve |
|---|---|---|
| `GET /threads/{contact_email}` — full thread with all emails | < 100ms for threads up to 50 emails | Index on `emails.thread_id`, join with `threads.sender_email` index |
| Sentiment trend query over 30 days | Sub-second | Composite index on `(sender, timestamp, sentiment_score)` |
| Vector similarity search — top 3 chunks | < 200ms | IVFFlat index on `knowledge_chunks.embedding` |

---

## 3. COMPONENT SPECIFICATIONS

### 3.1 Component 1: Email Ingestion & Streaming Pipeline [REQUIRED]

#### 3.1.1 Endpoint: `POST /api/ingest`

**Request Body:**
```json
{
  "message_id": "msg_001",
  "thread_id": "thread_alice_pricing",
  "sender": "alice.smith@greenlight-npo.org",
  "recipient": "support@senai.io",
  "subject": "Pricing for Non-Profit",
  "body": "Hello, I'd like to inquire about...",
  "timestamp": "2024-11-01T09:15:00Z",
  "labels": ["inquiry", "pricing"]
}
```

**Validation Rules:**
- `message_id` — REQUIRED, string, non-empty
- `thread_id` — REQUIRED, string, non-empty
- `sender` — REQUIRED, valid email format
- `recipient` — REQUIRED, valid email format
- `subject` — OPTIONAL (can be empty string)
- `body` — OPTIONAL (can be empty or whitespace-only)
- `timestamp` — REQUIRED, valid ISO 8601 datetime

**Success Response (201):**
```json
{
  "status": "accepted",
  "job_id": "job_abc123",
  "message_id": "msg_001",
  "thread_id": "thread_alice_pricing",
  "initial_priority": "Medium"
}
```

**Error Response (400/409/422):**
```json
{
  "error_code": "VALIDATION_ERROR",
  "message": "Missing required field: message_id",
  "details": { "field": "message_id", "reason": "required" }
}
```

#### 3.1.2 Deduplication Logic

```
ON INGEST:
  1. Check if message_id exists in emails table
  2. IF EXISTS → return 409 Conflict with body: { "error_code": "DUPLICATE", "message": "message_id already ingested", "existing_job_id": "..." }
  3. IF NOT EXISTS → proceed with ingestion
```

This MUST be idempotent. Re-sending the same `message_id` must NEVER create duplicates.

#### 3.1.3 Thread Linking Logic

```
ON INGEST:
  1. Query threads table for matching thread_id
  2. IF FOUND → link email to existing thread, update last_updated_at
  3. IF NOT FOUND → create new thread record, set first_seen_at = email timestamp
  4. Upsert contact record (create if new sender, update last_contact_at if existing)
```

#### 3.1.4 Priority Queue — Initial Heuristic Score

Assign an initial priority score BEFORE AI processing. This must be synchronous and fast (< 10ms).

```
PRIORITY RULES (evaluated in order, first match wins):
  - CRITICAL: body contains 'ransomware' OR 'cease and desist' OR 'data breach' OR 'BTC' → priority = "Critical"
  - CRITICAL: body contains 'P0' OR 'outage' AND 'SLA' → priority = "Critical"
  - HIGH: body contains 'URGENT' OR 'legal' OR 'lawsuit' OR 'GDPR' OR 'HIPAA' → priority = "High"
  - HIGH: body contains 'refund' AND ('cancel' OR 'churn' OR 'review') → priority = "High"
  - MEDIUM: body contains 'bug' OR 'error' OR 'broken' OR 'compliance' → priority = "Medium"
  - LOW: default → priority = "Low"
```

#### 3.1.5 Streaming Simulation

Build a utility/script that replays `email-data-advanced.json` by POSTing each email to `/api/ingest`:

- Configurable speed: 1 email/sec (dev), 10 email/sec (load test)
- Maintain chronological order by `timestamp`
- Log success/failure for each email
- CLI usage: `python simulate.py --speed 1` or `node simulate.js --speed 1`

#### 3.1.6 Edge Cases — MUST Handle

| Edge Case | Handling |
|---|---|
| Empty body or subject | Accept the email. Set body/subject to empty string. Log warning. Still process through pipeline. |
| Body with only whitespace or HTML entities | Treat as empty body. Strip whitespace/entities. Flag for human review due to empty content. |
| Duplicate `message_id` | Return 409 Conflict. Do NOT create duplicate. |
| Timestamps out of order within thread | Accept and store. Sort by timestamp when displaying thread. Do NOT reject. |
| Body > 10,000 characters | Truncate to first 10,000 chars for LLM processing. Store full body in DB. Add `[TRUNCATED]` marker in LLM context. |

---

### 3.2 Component 2: Multi-Layer Intelligence Engine [REQUIRED]

#### 3.2.1 Layer 1 — Heuristic Pre-filter (Synchronous, < 10ms)

Run on every email immediately at ingest BEFORE LLM processing.

**Spam Detection:**
```
SPAM RULES:
  - Keyword blocklist: ['Nigerian prince', 'SEO services', 'buy followers', 'lottery winner', 'investment opportunity', 'act now', 'click here', 'unsubscribe']
  - Sender domain reputation: maintain a blocklist of known spam domains
  - If SPAM detected → category = "Spam", status = "Ignored", STOP processing. NEVER auto-reply to spam.
```

**Urgency Detection:**
```
URGENCY KEYWORDS:
  - Critical: ['URGENT', 'P0', 'ransomware', 'cease and desist', 'data breach', 'legal action']
  - High: ['legal', 'lawsuit', 'GDPR', 'HIPAA', 'SLA breach', 'escalat']
  - Medium: ['bug', 'error', 'broken', 'compliance', 'refund']
```

**Security Flag:**
```
SECURITY TRIGGERS:
  - Keywords: ['suspicious login', 'unauthorized access', 'data breach', 'ransomware', 'BTC', 'bitcoin']
  - Action: Immediately route to security queue. Set urgency = "Critical". Flag requires_human = true.
```

**Internal Email Filter:**
```
INTERNAL DOMAINS: ['@internal.com', '@mycompany.com', '@senai.io']
  - If sender domain matches → category = "Internal", route to internal inbox
```

#### 3.2.2 Layer 2 — LLM Classification Engine (Async)

For every email that passes the heuristic pre-filter (not spam, not internal), call the LLM API.

**LLM Prompt Template:**

```
SYSTEM PROMPT:
You are an expert email classification agent for SenAI, an AI solutions company.
Analyze the email below and return a JSON classification.

THREAD HISTORY (oldest first):
{thread_history}

RELEVANT KNOWLEDGE BASE CONTEXT:
{rag_context}

CURRENT EMAIL TO CLASSIFY:
From: {sender}
Subject: {subject}
Body: {body}

Return ONLY valid JSON matching this schema:
{
  "category": "Complaint|Inquiry|Bug Report|Feature Request|Compliance|Legal|Billing|Spam|Internal|Other",
  "sentiment": "Positive|Neutral|Negative|Mixed",
  "sentiment_score": <float from -1.0 to 1.0>,
  "urgency": "Critical|High|Medium|Low",
  "requires_human": <boolean>,
  "escalation_reason": "<string if requires_human=true, else null>",
  "suggested_reply": "<string if requires_human=false, else null>",
  "confidence": <float from 0.0 to 1.0>,
  "detected_entities": {
    "order_ids": [],
    "ticket_ids": [],
    "monetary_amounts": [],
    "deadlines": [],
    "products_mentioned": []
  }
}

RULES:
- If confidence < 0.70 → set requires_human = true
- If urgency = "Critical" → set requires_human = true (agent must NEVER auto-reply to Critical)
- If category = "Legal" or "Compliance" → set requires_human = true
- If sentiment = "Mixed" (conflicting signals) → document the conflict in escalation_reason and lower confidence
- suggested_reply MUST cite the specific policy document that informed it (e.g., "Per our refund policy...")
- Read the FULL thread history before classifying — do not classify based on the latest email alone
```

**Conflicting Signal Strategy:**

When an email contains contradictory signals (e.g., "I love the product but hate the price and want a refund"):
1. Set `sentiment` = "Mixed"
2. Reduce `confidence` by 0.15 from what it would otherwise be
3. Set `requires_human` = true if confidence drops below 0.70
4. Document the conflict in `escalation_reason`: "Conflicting signals detected: positive product sentiment vs. negative pricing sentiment with refund intent"

#### 3.2.3 Layer 3 — Sentiment Trend Tracking

**Storage:** Each email's `sentiment_score` is stored with `sender` and `timestamp`.

**Escalation Rule:**
```
FOR each sender:
  Get last N emails ordered by timestamp DESC
  IF 3 or more consecutive emails have sentiment_score < -0.3:
    → Generate escalation alert
    → Update contact churn_risk_score += 0.2
    → If contact has open unresolved threads > 48h, mark as "At Risk"
```

**API Endpoint:** `GET /analytics/sentiment-trend?sender=X&days=30`

**Response:**
```json
{
  "sender": "karen.w@retail-co.com",
  "period_days": 30,
  "data_points": [
    { "date": "2024-11-01", "sentiment_score": -0.2, "message_id": "msg_010" },
    { "date": "2024-11-05", "sentiment_score": -0.6, "message_id": "msg_021" },
    { "date": "2024-11-08", "sentiment_score": -0.9, "message_id": "msg_033" }
  ],
  "moving_average": -0.57,
  "trend": "deteriorating",
  "alert": "3 consecutive negative emails — escalation triggered"
}
```

---

### 3.3 Component 3: RAG Knowledge Pipeline [ADVANCED]

#### 3.3.1 Knowledge Base Documents — CREATE THESE FILES

You must create the following 6 markdown files and seed them into the vector DB.

**File 1: `knowledge_base/pricing_policy.md`**
```
Contents to include:
- Pricing tiers: Free, Standard ($49/mo), Professional ($149/mo), Enterprise (custom)
- Non-profit discount: 30% off Standard tier
- Pro-rata billing rules for mid-cycle upgrades/downgrades
- Annual billing discount: 20% off monthly rate
- Enterprise custom pricing: requires Sales approval, minimum 50 seats
- Volume discounts for 100+ seats
```

**File 2: `knowledge_base/sla_policy.md`**
```
Contents to include:
- Uptime SLA: 99.9% for Professional and Enterprise tiers
- Incident response times: P0 = 15min, P1 = 1hr, P2 = 4hr, P3 = 24hr
- SLA credit calculation: each 0.1% below 99.9% = 5% service credit, max 30%
- RCA delivery SLA: 24 hours for P0, 72 hours for P1
- SLA does not cover: scheduled maintenance, force majeure, customer-caused issues
- Credit request process: email sla-credits@senai.io within 30 days of incident
```

**File 3: `knowledge_base/refund_policy.md`**
```
Contents to include:
- Refund window: 14 days from purchase
- After 14 days: no refunds, but account credits available
- Exception process: requires VP approval for refunds > $500 or after 14-day window
- Credits vs refunds: credits apply to next billing cycle, refunds return to payment method
- Churn retention playbook: offer 1-month free, offer tier downgrade, offer extended trial
- Retention offers require manager approval for accounts > $1000/mo
```

**File 4: `knowledge_base/api_docs.md`**
```
Contents to include:
- Rate limits by tier: Free = 100 req/hr, Standard = 1000 req/hr, Professional = 10,000 req/hr, Enterprise = custom
- API v1 deprecation: sunset date June 2025, migration guide available
- API v2 breaking changes: auth header changed from X-API-Key to Authorization: Bearer
- Webhook support: available on Professional and Enterprise tiers
- SDKs: Python, JavaScript, Go — all open source on GitHub
```

**File 5: `knowledge_base/compliance_faq.md`**
```
Contents to include:
- HIPAA BAA: available for Enterprise tier, requires signed BAA before data processing
- GDPR DPA: available for all tiers, 30-day response window for data requests, Article 20 portability supported
- SOC 2 Type II: certified, report available under NDA
- Data residency: US (default), EU (available on Enterprise), custom regions by request
- Data retention: 90 days after account deletion, immediate deletion on request
- GDPR Article 20 (data portability): must acknowledge within 72 hours, fulfill within 30 days
```

**File 6: `knowledge_base/escalation_matrix.md`**
```
Contents to include:
- Legal threats: → Legal team (legal@senai.io), response within 4 hours
- Security incidents: → Security team (security@senai.io), response within 15 minutes
- PR crises / public review threats: → VP Customer Success + PR team, response within 2 hours
- VIP churn threats: → Account Manager + VP Sales, response within 1 hour
- GDPR requests: → Legal + Compliance team, acknowledge within 72 hours
- P0 outages: → Engineering On-Call + VP Engineering, response within 15 minutes
- Chatbot misinformation: → Product team + Customer Success, response within 4 hours
```

#### 3.3.2 RAG Pipeline Implementation

**Step 1: Chunking**
```
FOR each .md file:
  1. Split into chunks of 300–500 tokens
  2. Use 50-token overlap between chunks
  3. Preserve section headers as metadata
  4. Store: { source_doc, chunk_text, section_header }
```

**Step 2: Embedding**
```
FOR each chunk:
  1. Generate embedding vector using chosen model (dimension depends on model)
  2. Store in knowledge_chunks table: { source_doc, chunk_text, embedding }
```

**Step 3: Retrieval (on each email classification)**
```
ON EMAIL CLASSIFICATION:
  1. Generate embedding of the email body + subject
  2. Perform cosine similarity search against knowledge_chunks
  3. Return top-3 most relevant chunks
  4. Inject into LLM prompt as "RELEVANT KNOWLEDGE BASE CONTEXT"
  5. The LLM must cite which policy document informed its suggested_reply
```

**Step 4: Debug Endpoint**

`GET /rag/search?q=refund+policy+after+14+days`

**Response:**
```json
{
  "query": "refund policy after 14 days",
  "results": [
    {
      "chunk_id": "chunk_001",
      "source_doc": "refund_policy.md",
      "chunk_text": "After 14 days: no refunds, but account credits available...",
      "similarity_score": 0.92
    },
    {
      "chunk_id": "chunk_002",
      "source_doc": "refund_policy.md",
      "chunk_text": "Exception process: requires VP approval for refunds > $500...",
      "similarity_score": 0.85
    },
    {
      "chunk_id": "chunk_003",
      "source_doc": "escalation_matrix.md",
      "chunk_text": "VIP churn threats: → Account Manager + VP Sales...",
      "similarity_score": 0.71
    }
  ]
}
```

#### 3.3.3 RAG Evaluation Scenario

**Test Case:** `karen.w@retail-co.com` sends "I want a refund"

The RAG pipeline MUST retrieve:
1. `refund_policy.md` — refund window, exception process
2. `refund_policy.md` — churn retention playbook section
3. `escalation_matrix.md` — PR crisis / public review threat handling (because Karen has threatened public reviews)

The LLM must synthesize ALL THREE and produce a specific escalation recommendation, NOT a generic "we'll look into it" reply.

---

### 3.4 Component 4: Autonomous Triage Agent [ADVANCED]

#### 3.4.1 Agent Architecture — ReAct Pattern

The agent follows a Thought → Action → Observation → Thought loop:

```
AGENT LOOP:
  max_steps = 6
  step_count = 0

  WHILE step_count < max_steps AND not resolved:
    THOUGHT: Agent reasons about what it knows and what it needs
    ACTION: Agent selects and calls one tool
    OBSERVATION: Agent receives tool output
    step_count += 1

  IF step_count >= max_steps AND not resolved:
    → escalate_to_human() with full reasoning summary

  STORE full reasoning trace as JSON in actions.agent_reasoning_log
```

#### 3.4.2 Agent Tools — Implement at Least 4

| # | Tool Name | Signature | Description |
|---|---|---|---|
| 1 | `search_knowledge_base` | `(query: string) → chunks[]` | RAG search across internal docs |
| 2 | `get_thread_history` | `(sender_email: string) → email[]` | All emails from this sender, ordered by time |
| 3 | `get_contact_profile` | `(email: string) → contact` | CRM profile: VIP status, account value, open tickets, churn risk |
| 4 | `check_account_status` | `(email: string) → account` | Billing status, subscription tier, overdue invoices |
| 5 | `draft_reply` | `(context: string, tone: string, policy_refs: string[]) → draft` | Generate contextual reply citing specific policies |
| 6 | `escalate_to_human` | `(email_id: string, reason: string, priority: string) → void` | Route to human with pre-filled brief |
| 7 | `create_internal_ticket` | `(title: string, body: string, assignee: string) → ticket` | Create support/engineering ticket |
| 8 | `scrape_public_sentiment` | `(company_name: string) → sentiment_data` | Check G2/Trustpilot score (Component 5) |
| 9 | `flag_for_legal` | `(email_id: string, issue_type: string) → void` | Route legal threats to legal team with context |
| 10 | `send_auto_reply` | `(email_id: string, draft_id: string) → void` | Approve and send an auto-reply |

#### 3.4.3 Agent Rules — HARD CONSTRAINTS

```
RULES:
  1. NEVER auto-reply to emails with urgency = "Critical"
  2. NEVER auto-reply to spam
  3. NEVER auto-reply to ransomware threats
  4. NEVER auto-reply to legal cease-and-desist emails
  5. Maximum 6 tool calls per email — if unresolved, escalate with reasoning summary
  6. Each run MUST produce structured reasoning log: { thoughts: [], actions: [], observations: [] }
  7. If confidence < 0.70, MUST escalate to human
  8. Dry-run mode: show plan without executing (POST /agent/dry-run/{email_id})
```

#### 3.4.4 Dry-Run Mode

`POST /agent/dry-run/{email_id}`

**Response:**
```json
{
  "email_id": "msg_060",
  "mode": "dry-run",
  "planned_steps": [
    { "step": 1, "thought": "This is a legal escalation about SLA breach. Need full thread context.", "action": "get_thread_history", "params": { "sender_email": "bob.jones@enterprise.net" } },
    { "step": 2, "thought": "Need to check SLA credit obligations.", "action": "search_knowledge_base", "params": { "query": "SLA breach credit policy" } },
    { "step": 3, "thought": "Need to verify account status and tier.", "action": "check_account_status", "params": { "email": "bob.jones@enterprise.net" } },
    { "step": 4, "thought": "Legal threat detected. Must flag for legal team.", "action": "flag_for_legal", "params": { "email_id": "msg_060", "issue_type": "SLA breach + legal review" } },
    { "step": 5, "thought": "Draft empathetic holding reply citing SLA credit policy.", "action": "draft_reply", "params": { "tone": "empathetic", "policy_refs": ["sla_policy.md"] } },
    { "step": 6, "thought": "Must escalate to human with full brief.", "action": "escalate_to_human", "params": { "email_id": "msg_060", "reason": "Legal escalation: SLA breach, Enterprise tier, renewal on hold", "priority": "Critical" } }
  ],
  "execution_status": "NOT_EXECUTED"
}
```

#### 3.4.5 Mandatory Test Case — Bob Jones Escalation

**Trigger:** `msg_060` — "Escalation: SLA Breach + Legal Review" from `bob.jones@enterprise.net`

**Required Agent Behavior (in order):**
1. `get_thread_history("bob.jones@enterprise.net")` → Retrieve all 4 prior emails in thread_bob_outage
2. `search_knowledge_base("SLA breach credit obligations")` → Retrieve SLA policy chunks
3. `check_account_status("bob.jones@enterprise.net")` → Enterprise tier, renewal on hold
4. Recognize the legal threat from thread context
5. `flag_for_legal("msg_060", "SLA breach + potential legal action")`
6. `draft_reply(context, tone="empathetic", policy_refs=["sla_policy.md"])` → Citing SLA credit policy
7. `escalate_to_human("msg_060", reason="Legal escalation: SLA breach, Enterprise tier, renewal on hold", priority="Critical")`

**The full reasoning trace must be visible in the demo.**

---

### 3.5 Component 5: Live Web Intelligence Module [ADVANCED]

#### 3.5.1 Scraping Targets — Implement at Least 2

| Target | What to Scrape | Output |
|---|---|---|
| G2 / Trustpilot | Current star rating, recent review count, common complaint themes | `{ rating: 4.2, review_count: 340, recent_complaints: ["slow support", "pricing"] }` |
| Competitor Pricing | Pricing pages of competitors | `{ competitor: "CompetitorX", plans: [...] }` |
| Social Listening (Optional) | Reddit mentions, HN posts | `{ mentions: [...], sentiment: "mixed" }` |
| Company News (Optional) | News articles about sender companies | `{ articles: [...] }` |

#### 3.5.2 Technical Requirements

```
SCRAPING RULES:
  1. Async — must NOT block main processing pipeline
  2. Cache layer — cache results for 6 hours (store in web_intelligence_cache table)
  3. Check cache BEFORE scraping: IF cached AND not expired → return cached
  4. robots.txt compliance — check before scraping any domain
  5. Graceful degradation — if scrape fails, agent proceeds without web data (log error, don't crash)
  6. Inject results into agent context as "MARKET INTELLIGENCE" block
```

#### 3.5.3 Trigger Conditions

```
TRIGGER WEB INTELLIGENCE IF ANY:
  - Email body contains: 'review', 'Trustpilot', 'G2', 'Twitter', 'post publicly'
  - Sentiment score < -0.6
  - Category = "Complaint" AND urgency IN ("High", "Critical")
  - Press or investor inquiry detected
```

#### 3.5.4 API Endpoint

`GET /intelligence/reputation`

**Response:**
```json
{
  "company": "SenAI",
  "last_updated": "2024-11-08T10:00:00Z",
  "g2": { "rating": 4.3, "review_count": 287, "trend": "stable" },
  "trustpilot": { "rating": 3.8, "review_count": 142, "trend": "declining" },
  "recent_themes": ["slow support response", "pricing concerns", "great product features"],
  "cache_expires_at": "2024-11-08T16:00:00Z"
}
```

---

### 3.6 Component 6: Backend API [REQUIRED]

#### 3.6.1 Full Endpoint Specification

| Method | Endpoint | Description | Auth | Response |
|---|---|---|---|---|
| POST | `/api/ingest` | Ingest new email | API Key | 201 with job_id |
| GET | `/api/status/{job_id}` | Check processing status | API Key | 200 with status object |
| GET | `/dashboard/stats` | Counts: Pending, Replied, Escalated, Critical, Spam filtered | None | 200 with stats |
| GET | `/threads/{contact_email}` | Full thread with all emails, actions, agent logs | None | 200 with thread object |
| POST | `/respond/{email_id}` | Send reply, update status, append to thread | None | 200 with reply confirmation |
| PATCH | `/drafts/{id}` | Edit proposed auto-reply before sending | None | 200 with updated draft |
| POST | `/drafts/{id}/approve` | Approve and send; triggers audit log | None | 200 with send confirmation |
| GET | `/analytics/sentiment-trend` | Time-series sentiment per sender or global | None | 200 with data points |
| GET | `/analytics/category-breakdown` | Category distribution over configurable date range | None | 200 with breakdown |
| GET | `/rag/search` | Debug: query KB, return chunks + scores | None | 200 with chunks |
| GET | `/intelligence/reputation` | Latest scraped public sentiment | None | 200 with reputation data |
| POST | `/agent/dry-run/{email_id}` | Agent planning mode; return trace without executing | None | 200 with planned steps |
| GET | `/audit/{entity_type}/{entity_id}` | Full audit history for any entity | None | 200 with audit entries |
| GET | `/contacts/{email}` | Contact profile with churn risk, account value, threads | None | 200 with contact |
| PATCH | `/contacts/{email}/status` | Update contact status (VIP, Blocked, etc.) | None | 200 with updated contact |

#### 3.6.2 Error Envelope (ALL Endpoints)

Every error response MUST follow this format:

```json
{
  "error_code": "VALIDATION_ERROR",
  "message": "Human-readable description",
  "details": { }
}
```

Standard error codes: `VALIDATION_ERROR`, `NOT_FOUND`, `DUPLICATE`, `PROCESSING_ERROR`, `RATE_LIMITED`, `INTERNAL_ERROR`

#### 3.6.3 OpenAPI Spec

Generate a `swagger.yaml` or `openapi.json` file covering ALL endpoints with request/response schemas. Include in repo root.

---

### 3.7 Component 7: Frontend Dashboard [REQUIRED]

#### 3.7.1 View 1 — Mission Control Inbox

**Layout:** Full-width table/list view

**Features:**
- Filterable/sortable email list
- Visual badges per row: Sentiment (color: green/yellow/red), Category (pill), Urgency (icon)
- Tab system: `All` | `Needs Human` | `Auto-Replied` | `Escalated` | `Spam`
- Thread grouping: collapse emails from same thread into single row, show last activity timestamp
- Bulk actions bar: Mark as Spam, Assign, Archive (appears when rows selected)
- Search bar: full-text search across subject and body
- Real-time updates: WebSocket or polling (configurable interval, default 5s)

**Sentiment Color Mapping:**
- Score > 0.3 → Green
- Score -0.3 to 0.3 → Yellow/Amber
- Score < -0.3 → Red

#### 3.7.2 View 2 — Thread Workspace (Detail View)

**Layout:** Three-pane layout

**Left Pane — Email Content:**
- Email body with entity highlights (monetary amounts in blue underline, ticket IDs clickable, deadlines in bold)
- Sender info header

**Center Pane — Thread Timeline:**
- Chronological list of all emails in thread
- Each email shows: timestamp, sender, subject snippet, sentiment indicator dot
- Visual connector line between emails

**Right Pane — Contact Profile Card:**
- Name, company, email
- VIP status badge
- Account value
- Churn risk score (progress bar, color-coded)
- Open threads count
- Last contact date

**Agent Reasoning Panel (Collapsible):**
- Expandable section below email content
- Shows: Thought → Action → Observation for each step
- Numbered steps, color-coded actions

**RAG Context Panel (Collapsible):**
- Shows retrieved knowledge chunks
- Each chunk: source document name, chunk text preview, similarity score bar

**Action Bar:**
- Buttons: `Approve & Send` | `Edit Draft` | `Escalate` | `Mark Spam`
- Edit Draft opens inline editor for `proposed_content`

**Web Intelligence Panel (Conditional):**
- Only shown if web intelligence was fetched for this email
- Shows: G2 rating, Trustpilot rating, recent complaint themes

#### 3.7.3 View 3 — Analytics Dashboard

**Charts:**
- Sentiment trend line chart: X = date, Y = sentiment score, filterable by sender or global
- Category distribution: pie chart or horizontal bar chart
- Response time heatmap: X = hour of day, Y = day of week, color = average response time

**Panels:**
- At-risk accounts: table of senders with deteriorating sentiment OR unresolved threads > 48h
- Agent performance metrics: auto-reply rate %, escalation rate %, average confidence score

---

## 4. SPECIAL SCENARIO HANDLING — AUTOMATIC DISQUALIFIERS

These scenarios WILL be specifically tested. Failing any of these is an automatic disqualifier.

### 4.1 GDPR Data Request (msg_052)

**Sender:** `marcus.del@fintech-startup.co`
**Type:** Formal GDPR Article 20 data portability request

**Required System Behavior:**
1. Heuristic layer detects "GDPR" keyword → urgency = "High"
2. LLM classifies as category = "Legal" or "Compliance" (NOT "Inquiry")
3. Agent calls `flag_for_legal("msg_052", "GDPR Article 20 data portability")`
4. Agent generates auto-acknowledgement citing 30-day statutory window
5. Agent calls `create_internal_ticket("GDPR Data Portability Request", "...", "compliance-team")`
6. Agent DOES NOT send a generic auto-reply

**DISQUALIFIER:** Classifying this as a generic "Inquiry" without legal flag.

### 4.2 Ransomware Threat (msg_038)

**Content:** "Send 2 BTC or we publish data"

**Required System Behavior:**
1. Heuristic layer detects "BTC" + threat language → urgency = "Critical", security flag
2. LLM confirms category = "Legal" (extortion)
3. Agent IMMEDIATELY escalates: `escalate_to_human()` + `flag_for_legal()`
4. Route to security queue per escalation matrix
5. NEVER auto-reply to the attacker

**DISQUALIFIER:** Auto-replying to ransomware threats.

### 4.3 Chatbot Misinformation (msg_056)

**Context:** Customer reports your own AI chatbot gave wrong refund information

**Required System Behavior:**
1. Agent retrieves actual refund policy via RAG (`search_knowledge_base("refund policy")`)
2. Agent compares what chatbot said vs. actual policy
3. Agent drafts empathetic reply acknowledging the discrepancy
4. Reply MUST NOT admit legal liability (no "we were wrong and owe you")
5. Agent escalates with summary: "Chatbot stated X, actual policy is Y"
6. Route to Product team per escalation matrix

### 4.4 Reputation Crisis — Karen (msg_033)

**Context:** `karen.w@retail-co.com` has sent 3 emails with ZERO replies, threatening public reviews

**Required System Behavior:**
1. Sentiment trend detection: 3 consecutive negative emails
2. Agent triggers web scraping (G2/Trustpilot current score)
3. Agent generates high-priority escalation brief
4. RAG retrieves: refund policy (retention playbook) + escalation matrix (PR crisis)
5. Agent suggests retention offer from KB

### 4.5 Conflicting Thread — Alice (msg_041)

**Context:** 5-email thread: pricing inquiry → discount → close → upgrade → pro-rata billing question

**Required System Behavior:**
1. Agent reads FULL 5-email thread history before classifying msg_041
2. Agent recognizes msg_041 is a pro-rata billing question (not a new pricing inquiry)
3. RAG retrieves pricing_policy.md with correct tier info (non-profit 30% discount on Standard)
4. Agent drafts reply referencing the correct pricing tier and pro-rata rules

---

## 5. AUTOMATIC DISQUALIFIERS CHECKLIST

Before submission, verify NONE of these apply:

- [ ] System auto-replies to spam emails
- [ ] System auto-replies to ransomware threat (msg_038)
- [ ] System auto-replies to legal cease-and-desist emails
- [ ] GDPR request (msg_052) classified as generic "Inquiry" without legal flag
- [ ] Duplicate message_id creates duplicate records (no idempotency)
- [ ] Agent produces no reasoning trace (black-box decisions)
- [ ] Malformed email payloads cause unhandled crashes (no error handling)

---

## 6. DELIVERABLES CHECKLIST

| # | Deliverable | Format | Location |
|---|---|---|---|
| 1 | GitHub Repository | Public repo | github.com/... |
| 2 | README.md | Markdown | repo root |
| 3 | Architecture Diagram | Image (Mermaid/Excalidraw/Lucidchart) | repo root or `/docs` |
| 4 | Knowledge Base Files | 6 × `.md` files | `/knowledge_base/` |
| 5 | ER Diagram + SQL Schema | SQL + image | `/database/` |
| 6 | Screen Recording | 5–10 min video | linked in README |
| 7 | OpenAPI Spec | `swagger.yaml` or `openapi.json` | repo root |
| 8 | Docker Compose (Bonus) | `docker-compose.yml` | repo root |

### 6.1 README.md Must Include

- Setup guide (dependencies, env vars, install steps)
- How to seed the knowledge base
- How to run the email simulation
- Architecture decisions with trade-off analysis
- Known limitations
- Environment variables list

### 6.2 Screen Recording Must Demonstrate

1. Email stream ingestion (streaming simulation running)
2. Agent reasoning trace for `thread_bob_outage` escalation
3. RAG retrieval debug view (`/rag/search`)
4. Karen churn scenario with web intelligence
5. Analytics dashboard with sentiment trends

---

## 7. EVALUATION WEIGHTS

| Criterion | Weight | Focus Areas |
|---|---|---|
| AI System Design | 25% | LLM prompt quality, structured output reliability, RAG retrieval accuracy, agent reasoning quality, low-confidence handling |
| Agent Architecture | 20% | ReAct/CoT trace, tool selection logic, max-steps enforcement, dry-run mode, bob/karen/GDPR scenario correctness |
| Backend Engineering | 20% | API design, DB normalization, query performance benchmarks, error handling, idempotency, audit log completeness |
| RAG Pipeline | 15% | Chunking strategy, embedding model justification, retrieval relevance, policy citation in replies, vector DB performance |
| Web Intelligence | 10% | Scraper reliability, caching, robots.txt, graceful degradation, trigger logic accuracy |
| Frontend & UX | 5% | Inbox usability, thread workspace clarity, agent reasoning visibility, analytics dashboard |
| Problem Solving & Docs | 5% | README quality, architecture diagram, trade-off analysis, edge case handling |

---

## 8. IMPLEMENTATION ORDER (Recommended)

This is the suggested build sequence for an AI agent or developer:

```
Phase 1 — Foundation (Day 1, Morning)
  ├── Set up project structure (backend + frontend + DB)
  ├── Implement database schema + migrations
  ├── Create knowledge base .md files
  └── Implement POST /api/ingest with validation + deduplication

Phase 2 — Intelligence (Day 1, Afternoon)
  ├── Implement Layer 1 heuristic pre-filter
  ├── Implement RAG pipeline (chunk, embed, store, retrieve)
  ├── Implement Layer 2 LLM classification with RAG context
  └── Implement Layer 3 sentiment trend tracking

Phase 3 — Agent (Day 2, Morning)
  ├── Implement agent tools (at least 4)
  ├── Implement ReAct agent loop with reasoning trace
  ├── Implement dry-run mode
  └── Test mandatory scenarios (Bob, Karen, GDPR, Ransomware)

Phase 4 — Web Intelligence + API (Day 2, Afternoon)
  ├── Implement web scraping with cache
  ├── Complete all remaining API endpoints
  ├── Implement error envelopes
  └── Generate OpenAPI spec

Phase 5 — Frontend (Day 3, Morning)
  ├── Build Mission Control Inbox view
  ├── Build Thread Workspace view
  ├── Build Analytics Dashboard view
  └── Implement WebSocket/polling for real-time updates

Phase 6 — Polish (Day 3, Afternoon)
  ├── Run all mandatory test scenarios end-to-end
  ├── Write README with trade-offs and setup guide
  ├── Create architecture diagram
  ├── Record screen demo (5–10 min)
  └── Create Docker Compose (bonus)
```

---

## 9. ARCHITECTURE DIAGRAM (Mermaid)

```mermaid
graph TB
    subgraph Ingestion
        A[Email JSON Payload] -->|POST /api/ingest| B[Schema Validator]
        B -->|Invalid| C[400/422 Error Response]
        B -->|Valid| D[Deduplication Check]
        D -->|Duplicate| E[409 Conflict]
        D -->|New| F[Thread Linker]
        F --> G[Priority Queue / Heuristic Pre-filter]
    end

    subgraph Intelligence Engine
        G -->|Spam| H[Spam Bin — No Reply]
        G -->|Internal| I[Internal Inbox]
        G -->|Security| J[Security Queue — Immediate Escalation]
        G -->|Normal| K[RAG Retrieval]
        K --> L[LLM Classification Engine]
        L --> M{Confidence >= 0.70?}
        M -->|No| N[Flag for Human Review]
        M -->|Yes| O[Autonomous Agent]
    end

    subgraph RAG Pipeline
        K --> P[(Vector DB)]
        P --> Q[Top-3 Chunks]
        Q --> L
    end

    subgraph Agent Loop
        O --> R{ReAct Loop — Max 6 Steps}
        R --> S[search_knowledge_base]
        R --> T[get_thread_history]
        R --> U[get_contact_profile]
        R --> V[check_account_status]
        R --> W[draft_reply]
        R --> X[escalate_to_human]
        R --> Y[flag_for_legal]
        R --> Z[create_internal_ticket]
        R --> AA[scrape_public_sentiment]
    end

    subgraph Web Intelligence
        AA --> AB{Cache Valid?}
        AB -->|Yes| AC[Return Cached]
        AB -->|No| AD[Async Scrape]
        AD --> AE[G2 / Trustpilot / Competitor]
        AE --> AF[Store in Cache — 6hr TTL]
    end

    subgraph Storage
        AG[(PostgreSQL)]
        AH[(Vector DB — pgvector/Chroma)]
    end

    subgraph Frontend
        AI[Mission Control Inbox]
        AJ[Thread Workspace]
        AK[Analytics Dashboard]
        AL[WebSocket / SSE Real-time Updates]
    end

    R -->|Reasoning Log| AG
    L -->|Classification| AG
    AI --> AG
    AJ --> AG
    AK --> AG
```

---

## 10. ENVIRONMENT VARIABLES

```env
# Database
DATABASE_URL=postgresql://user:pass@localhost:5432/senai_crm
VECTOR_DB_TYPE=pgvector  # or chroma, faiss

# LLM
LLM_PROVIDER=openai  # or anthropic
LLM_API_KEY=sk-...
LLM_MODEL=gpt-4o  # or claude-sonnet-4-20250514

# Embeddings
EMBEDDING_MODEL=text-embedding-3-small
EMBEDDING_DIMENSION=1536

# Web Intelligence
SCRAPE_CACHE_TTL_HOURS=6
SCRAPE_TIMEOUT_SECONDS=10

# Server
PORT=8000
FRONTEND_URL=http://localhost:3000
WEBSOCKET_ENABLED=true
POLLING_INTERVAL_MS=5000

# Email Simulation
SIMULATION_SPEED=1  # emails per second
```

---

## 11. BONUS TRACKS (Optional Enhancements)

| Bonus | Description | Implementation Hint |
|---|---|---|
| WebSocket Streaming | Push email events and agent decisions to frontend in real-time | Socket.IO or native WebSocket on backend; useEffect listener on frontend |
| Multi-Agent Architecture | Split into Classifier Agent, Research Agent, Reply Agent with a Coordinator | Each sub-agent has distinct tool access; coordinator orchestrates sequence |
| Human-in-the-Loop Fine-tuning | Log deltas when humans edit agent drafts as training pairs | Store `{ original_draft, edited_draft, email_context }` for future fine-tuning |
| Thread Summarization | Auto-generate 3-sentence executive summary for threads with 5+ emails | LLM call with thread history, display summary at top of Thread Workspace |
| Churn Prediction Score | Score churn risk using sentiment trend + response time + category history | Weighted formula or LLM prompt-engineered scoring per sender |
| Docker Compose | One-command startup: app + DB + vector DB + scraper + frontend | `docker-compose.yml` with services: api, db, vectordb, frontend, scraper |
