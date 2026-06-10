# SenAI Solutions — API Documentation

## Document Metadata

| Field            | Value                                    |
|------------------|------------------------------------------|
| Version          | 2.5 (API v2)                             |
| Last Updated     | 2024-10-20                               |
| Owner            | Platform Engineering — Alex Drummond     |
| Classification   | Internal                                 |
| Approved By      | CTO — James Whitfield                    |
| Next Review Date | 2025-04-20                               |

---

## 1. API Overview

The SenAI API provides programmatic access to the SenAI CRM Intelligence Platform. It enables customers to integrate email ingestion, classification, analytics, and agent workflows into their existing systems. The API follows RESTful conventions and returns JSON responses.

**Base URLs:**
- **Production:** `https://api.senai.io/v2`
- **Sandbox:** `https://sandbox-api.senai.io/v2`
- **Legacy (v1 — deprecated):** `https://api.senai.io/v1`

---

## 2. Rate Limits by Tier

Each subscription tier has a defined API rate limit. Rate limits are enforced on a **per-minute, per-API-key** basis. When the rate limit is exceeded, the API returns an HTTP **429 Too Many Requests** response.

### 2.1 Rate Limit Table

| Tier          | Rate Limit          | Burst Allowance     | Daily Request Cap    |
|---------------|---------------------|---------------------|----------------------|
| **Starter**   | 100 requests/minute | 120 requests/minute | 50,000 requests/day  |
| **Standard**  | 500 requests/minute | 600 requests/minute | 250,000 requests/day |
| **Professional** | 2,000 requests/minute | 2,400 requests/minute | 1,000,000 requests/day |
| **Enterprise** | Unlimited / Custom | Custom              | Custom               |

### 2.2 Rate Limit Headers

Every API response includes the following rate limit headers:

| Header                    | Description                                      |
|---------------------------|--------------------------------------------------|
| `X-RateLimit-Limit`       | Maximum requests allowed per minute              |
| `X-RateLimit-Remaining`   | Requests remaining in the current window         |
| `X-RateLimit-Reset`       | Unix timestamp when the rate limit window resets |
| `X-RateLimit-Retry-After` | Seconds until the client can retry (only on 429) |

### 2.3 Rate Limit Exceeded Handling and Retry Logic

When a client exceeds the rate limit, the API returns:

```json
{
  "error_code": "RATE_LIMITED",
  "message": "Rate limit exceeded. Please retry after the specified window.",
  "details": {
    "limit": 500,
    "remaining": 0,
    "reset_at": "2024-11-01T14:32:00Z",
    "retry_after_seconds": 12
  }
}
```

**Recommended client-side retry strategy:**

1. **Respect the `Retry-After` header.** Wait the specified number of seconds before retrying.
2. **Implement exponential backoff** with jitter for sustained rate limit scenarios:
   - 1st retry: wait 1 second + random jitter (0–500ms)
   - 2nd retry: wait 2 seconds + random jitter
   - 3rd retry: wait 4 seconds + random jitter
   - Maximum retry delay: 30 seconds
   - Maximum retry attempts: 5
3. **Do NOT implement tight retry loops.** Clients that repeatedly hit rate limits without backoff may be temporarily blocked (HTTP 403) for up to 15 minutes.
4. **Monitor usage** via the `/v2/usage/rate-limits` endpoint to track current consumption against limits.
5. **Request a rate limit increase** by contacting support@senai.io if sustained overages indicate a need to upgrade tiers.

---

## 3. API v1 Deprecation Timeline

### 3.1 Deprecation Notice

**API v1 was officially deprecated on March 1, 2024.** API v1 will reach its **sunset date on June 30, 2025**, after which all v1 endpoints will return HTTP **410 Gone** responses.

### 3.2 Key Dates

| Milestone                    | Date               | Status     |
|------------------------------|---------------------|------------|
| API v2 general availability  | January 15, 2024    | ✅ Complete |
| API v1 deprecation announced | March 1, 2024       | ✅ Complete |
| API v1 deprecation warnings  | June 1, 2024        | ✅ Active   |
| API v1 read-only mode        | March 31, 2025      | Upcoming   |
| **API v1 sunset (shutdown)** | **June 30, 2025**   | Upcoming   |

### 3.3 Migration Support

- A comprehensive **v1-to-v2 migration guide** is available at `https://docs.senai.io/migration/v1-to-v2`.
- All SenAI SDKs (Python, Node.js, Ruby, Go) have been updated to support v2. Customers using SDKs should upgrade to the latest SDK version.
- SenAI Support offers **free migration assistance sessions** for Professional and Enterprise customers. Contact support@senai.io to schedule.
- Starting June 1, 2024, all API v1 requests include a deprecation warning header: `X-API-Deprecation: v1 is deprecated. Migrate to v2 by June 30, 2025.`

---

## 4. API v2 Breaking Changes

Customers migrating from API v1 to API v2 must be aware of the following **breaking changes**. These changes are not backward-compatible and require code updates.

### 4.1 List of Breaking Changes

#### Breaking Change 1: Authentication Header Format

**v1 (deprecated):** `X-API-Key: sk_live_abc123`

**v2 (current):** `Authorization: Bearer sk_live_abc123`

The custom `X-API-Key` header is no longer accepted. All requests must use the standard `Authorization: Bearer` header format. Requests using the old header format will receive an HTTP **401 Unauthorized** response with error code `AUTH_HEADER_INVALID`.

#### Breaking Change 2: Endpoint Path Renames

Several endpoint paths have been restructured for consistency:

| v1 Endpoint                    | v2 Endpoint                         | Notes                          |
|--------------------------------|-------------------------------------|--------------------------------|
| `POST /emails/submit`          | `POST /api/ingest`                  | Request body unchanged         |
| `GET /emails/status/{id}`      | `GET /api/status/{job_id}`          | Parameter renamed to job_id    |
| `GET /emails/thread/{email}`   | `GET /threads/{contact_email}`      | Response format changed        |
| `GET /stats/dashboard`         | `GET /dashboard/stats`              | Response structure updated     |
| `POST /emails/reply/{id}`      | `POST /respond/{email_id}`          | Request body format changed    |
| `GET /analytics/sentiment`     | `GET /analytics/sentiment-trend`    | Added query parameters         |

#### Breaking Change 3: Response Envelope Format

**v1 response format:**
```json
{
  "success": true,
  "data": { ... },
  "error": null
}
```

**v2 response format (success):**
```json
{
  "status": "ok",
  "data": { ... },
  "meta": {
    "request_id": "req_abc123",
    "timestamp": "2024-11-01T14:30:00Z"
  }
}
```

**v2 response format (error):**
```json
{
  "error_code": "VALIDATION_ERROR",
  "message": "Human-readable description",
  "details": { ... }
}
```

The `success` boolean field has been removed. Clients must check the HTTP status code (2xx for success, 4xx/5xx for errors) instead of parsing a `success` field.

#### Breaking Change 4: Pagination Format

**v1:** Offset-based pagination with `?page=1&per_page=20`

**v2:** Cursor-based pagination with `?cursor=eyJ...&limit=20`

The response now includes a `next_cursor` field instead of `total_pages`:
```json
{
  "data": [...],
  "meta": {
    "next_cursor": "eyJpZCI6MTAwfQ==",
    "has_more": true,
    "limit": 20
  }
}
```

#### Breaking Change 5: Date/Time Format Standardization

**v1:** Mixed date formats (some endpoints returned Unix timestamps, others returned ISO 8601 strings).

**v2:** All date/time fields use **ISO 8601 format with UTC timezone** (`YYYY-MM-DDTHH:MM:SSZ`). No Unix timestamps are returned by any endpoint.

#### Breaking Change 6: Webhook Payload Structure

**v1 webhook payload:**
```json
{
  "event": "email.classified",
  "data": { ... }
}
```

**v2 webhook payload:**
```json
{
  "event_type": "email.classified",
  "event_id": "evt_abc123",
  "timestamp": "2024-11-01T14:30:00Z",
  "data": { ... },
  "webhook_id": "wh_def456"
}
```

The `event` field has been renamed to `event_type`. New required fields `event_id`, `timestamp`, and `webhook_id` have been added for idempotency and debugging.

---

## 5. Required Headers for API v2

All API v2 requests **must** include the following headers:

| Header            | Value                          | Required | Description                                    |
|-------------------|--------------------------------|----------|------------------------------------------------|
| `Authorization`   | `Bearer sk_live_abc123`        | **Yes**  | API key prefixed with "Bearer"                 |
| `Content-Type`    | `application/json`             | **Yes**  | Required for all POST/PATCH/PUT requests       |
| `Accept`          | `application/json`             | Recommended | Ensures JSON responses                      |
| `API-Version`     | `2024-10-01`                   | **Yes**  | Date-based API version identifier              |
| `X-Request-ID`    | `req_abc123`                   | Recommended | Client-generated request ID for tracing     |

**API-Version Header:** The `API-Version` header is mandatory and must specify a valid API version date. The current version is `2024-10-01`. If the header is omitted, the API returns an HTTP **400 Bad Request** with error code `MISSING_API_VERSION`. SenAI supports a rolling window of 3 API versions. Older versions are retired with 6 months' notice.

---

## 6. Authentication

### 6.1 API Key Authentication

API keys are the primary authentication method for server-to-server integrations. Each SenAI account can generate up to 5 API keys.

**API key types:**
- `sk_live_*` — Production keys. Full read/write access.
- `sk_test_*` — Sandbox keys. Only work against the sandbox environment. No production data access.

**API key management:**
- Generate and revoke keys at `https://app.senai.io/settings/api-keys`.
- Keys are scoped to the account level (not individual users).
- Revoked keys immediately stop working. There is no grace period.

### 6.2 OAuth 2.0 Authentication

OAuth 2.0 is available for customers building user-facing integrations (e.g., connecting SenAI to their own product). OAuth uses the **Authorization Code Grant** flow.

**OAuth configuration:**
- **Authorization endpoint:** `https://auth.senai.io/oauth/authorize`
- **Token endpoint:** `https://auth.senai.io/oauth/token`
- **Scopes:** `read:emails`, `write:emails`, `read:analytics`, `read:contacts`, `write:contacts`, `admin`
- **Token expiry:** Access tokens expire after **1 hour**. Refresh tokens expire after **30 days**.

OAuth is available on **Professional and Enterprise tiers** only.

---

## 7. Webhook Configuration

### 7.1 Supported Webhook Events

| Event Type               | Description                                          | Tier Required    |
|--------------------------|------------------------------------------------------|------------------|
| `email.ingested`         | Fired when a new email is ingested                   | Standard+        |
| `email.classified`       | Fired when classification is complete                | Standard+        |
| `email.escalated`        | Fired when an email is escalated to a human          | Standard+        |
| `email.replied`          | Fired when a reply is sent (auto or manual)          | Standard+        |
| `agent.action_completed` | Fired when the agent completes a workflow step       | Professional+    |
| `contact.churn_risk`     | Fired when a contact's churn risk exceeds threshold  | Professional+    |
| `incident.created`       | Fired when a new incident is detected                | Professional+    |
| `sla.breach`             | Fired when an SLA target is missed                   | Enterprise       |

### 7.2 Webhook Configuration

Configure webhooks at `https://app.senai.io/settings/webhooks` or via the API:

```bash
POST /v2/webhooks
{
  "url": "https://your-server.com/webhook",
  "events": ["email.classified", "email.escalated"],
  "secret": "whsec_your_signing_secret"
}
```

**Webhook limits by tier:**
- Standard: 5 webhooks
- Professional: 25 webhooks
- Enterprise: Unlimited

### 7.3 Webhook Security

All webhook payloads are signed with an HMAC-SHA256 signature using the webhook secret. The signature is included in the `X-SenAI-Signature` header. Clients should validate this signature before processing the payload.

### 7.4 Webhook Retry Policy

If a webhook delivery fails (non-2xx response or timeout after 10 seconds), SenAI retries with exponential backoff:
- 1st retry: 1 minute
- 2nd retry: 5 minutes
- 3rd retry: 30 minutes
- 4th retry: 2 hours
- 5th retry: 12 hours

After 5 failed retries, the webhook is marked as "failing" and the account owner is notified via email. The webhook is disabled after **3 consecutive days** of failures.

---

## 8. Error Codes

All API errors follow the standard error envelope format. Below is a complete list of error codes:

| Error Code                | HTTP Status | Description                                              | Recommended Action                          |
|---------------------------|-------------|----------------------------------------------------------|----------------------------------------------|
| `VALIDATION_ERROR`        | 400         | Request body or query parameters are invalid             | Check request format against documentation   |
| `MISSING_API_VERSION`     | 400         | The `API-Version` header is missing                      | Add `API-Version: 2024-10-01` header         |
| `AUTH_HEADER_INVALID`     | 401         | Authorization header is missing or malformed             | Use `Authorization: Bearer <api_key>` format |
| `AUTH_KEY_EXPIRED`        | 401         | API key has been revoked or expired                      | Generate a new API key in settings           |
| `AUTH_INSUFFICIENT_SCOPE` | 403         | API key does not have permission for this operation      | Check key scopes and tier permissions        |
| `TEMPORARILY_BLOCKED`     | 403         | Client temporarily blocked due to abuse (rate limiting)  | Wait 15 minutes, implement proper backoff    |
| `NOT_FOUND`               | 404         | The requested resource does not exist                    | Verify the resource ID or endpoint path      |
| `DUPLICATE`               | 409         | A resource with this identifier already exists           | Use the existing resource or choose a new ID |
| `RATE_LIMITED`             | 429         | API rate limit exceeded                                  | Wait and retry with exponential backoff      |
| `PAYLOAD_TOO_LARGE`       | 413         | Request body exceeds the 1 MB size limit                 | Reduce payload size or use chunked uploads   |
| `PROCESSING_ERROR`        | 500         | An internal error occurred during processing             | Retry the request; if persistent, contact support |
| `SERVICE_UNAVAILABLE`     | 503         | The service is temporarily unavailable (maintenance)     | Check status.senai.io for incident updates   |
| `DEPRECATED_ENDPOINT`     | 410         | This endpoint has been sunset (v1 after June 30, 2025)   | Migrate to API v2                            |

---

## 9. SDKs

SenAI provides official SDKs for the following languages. All SDKs are open source and available on GitHub at `https://github.com/senai-io`.

### 9.1 Available SDKs

| Language    | Package Name        | Version | GitHub Repository                     | Install Command               |
|-------------|---------------------|---------|---------------------------------------|-------------------------------|
| **Python**  | `senai-python`      | 2.4.1   | `github.com/senai-io/senai-python`    | `pip install senai-python`    |
| **Node.js** | `@senai/node-sdk`   | 2.3.0   | `github.com/senai-io/senai-node`      | `npm install @senai/node-sdk` |
| **Ruby**    | `senai-ruby`        | 2.1.0   | `github.com/senai-io/senai-ruby`      | `gem install senai-ruby`      |
| **Go**      | `senai-go`          | 2.2.0   | `github.com/senai-io/senai-go`        | `go get github.com/senai-io/senai-go` |

### 9.2 SDK Quickstart (Python)

```python
from senai import SenAIClient

client = SenAIClient(api_key="sk_live_abc123", api_version="2024-10-01")

# Ingest an email
result = client.emails.ingest(
    message_id="msg_001",
    thread_id="thread_alice_pricing",
    sender="alice.smith@greenlight-npo.org",
    recipient="support@senai.io",
    subject="Pricing for Non-Profit",
    body="Hello, I'd like to inquire about pricing...",
    timestamp="2024-11-01T09:15:00Z"
)

print(result.job_id)  # "job_abc123"
print(result.initial_priority)  # "Medium"
```

### 9.3 SDK Quickstart (Node.js)

```javascript
const { SenAIClient } = require("@senai/node-sdk");

const client = new SenAIClient({
  apiKey: "sk_live_abc123",
  apiVersion: "2024-10-01",
});

const result = await client.emails.ingest({
  message_id: "msg_001",
  thread_id: "thread_alice_pricing",
  sender: "alice.smith@greenlight-npo.org",
  recipient: "support@senai.io",
  subject: "Pricing for Non-Profit",
  body: "Hello, I'd like to inquire about pricing...",
  timestamp: "2024-11-01T09:15:00Z",
});

console.log(result.jobId); // "job_abc123"
```

---

## 10. Sandbox / Testing Environment

### 10.1 Sandbox Overview

The SenAI Sandbox provides a fully isolated testing environment that mirrors the production API. Sandbox data is completely separate from production data and is automatically purged every **7 days**.

**Sandbox base URL:** `https://sandbox-api.senai.io/v2`

### 10.2 Sandbox Features

- All API endpoints are available in the sandbox with identical behavior to production.
- Sandbox rate limits are set to **Standard tier levels** (500 req/min) regardless of the customer's actual subscription tier.
- Sandbox API keys use the `sk_test_*` prefix and cannot access production data.
- Sandbox webhooks are delivered to the configured URLs but include a `X-SenAI-Environment: sandbox` header.
- LLM classification in sandbox uses a lighter model to reduce costs; results may differ slightly from production.

### 10.3 Sandbox Access

Sandbox access is available on **Professional and Enterprise tiers**. Starter and Standard tier customers can request sandbox access for evaluation purposes by contacting support@senai.io.

### 10.4 Sandbox Limitations

- Data is purged every 7 days. Do not rely on sandbox data for persistent testing.
- Email sending (auto-reply) is simulated — no actual emails are sent from sandbox.
- Web intelligence scraping is mocked in sandbox — returns static fixture data.
- Maximum 10,000 API requests per day in sandbox (regardless of tier).

---

## 11. API Changelog

### v2.5 (2024-10-20) — Current
- Added `API-Version` header requirement
- Added `/v2/usage/rate-limits` endpoint for monitoring
- Improved error messages for authentication failures

### v2.4 (2024-08-15)
- Added cursor-based pagination to all list endpoints
- Added `X-Request-ID` header support for request tracing
- Fixed webhook retry timing to match documented intervals

### v2.3 (2024-06-01)
- Added `contact.churn_risk` webhook event
- Added `/v2/contacts/{email}/status` PATCH endpoint
- Improved rate limit headers with `X-RateLimit-Retry-After`

### v2.2 (2024-04-01)
- Added Go SDK
- Added OAuth 2.0 authentication support
- Added bulk email ingestion endpoint (up to 50 emails per request)

### v2.1 (2024-02-15)
- Added `/v2/agent/dry-run/{email_id}` endpoint
- Added structured reasoning log to agent actions
- Fixed inconsistent date formats in analytics endpoints

### v2.0 (2024-01-15)
- Initial v2 release with all breaking changes documented in Section 4
- New authentication format (Bearer token)
- New response envelope format
- Cursor-based pagination
- Standardized ISO 8601 date formats
