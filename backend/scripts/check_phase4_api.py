import asyncio
from datetime import datetime, timezone
from httpx import AsyncClient
from sqlalchemy import func, select

from app.main import app
from app.database import get_db_session
from app.models import Action, Contact, Email, Thread


async def main() -> None:
    print("Starting Phase 4 API Validation...")

    async with get_db_session() as db:
        # 0. Set up database context for testing
        contact = await db.scalar(select(Contact).where(Contact.email == "bob.jones@enterprise.net"))
        if not contact:
            contact = Contact(
                email="bob.jones@enterprise.net",
                name="Bob Jones",
                company="Enterprise Net",
                status="VIP",
                account_value=150000.0,
                churn_risk_score=0.85,
            )
            db.add(contact)
            await db.flush()

        thread = await db.scalar(select(Thread).where(Thread.thread_id == "thread_test_api"))
        if not thread:
            thread = Thread(
                thread_id="thread_test_api",
                subject="API testing thread",
                sender_email=contact.email,
            )
            db.add(thread)
            await db.flush()

        email = await db.scalar(select(Email).where(Email.message_id == "msg_test_api"))
        if not email:
            email = Email(
                thread_id=thread.id,
                message_id="msg_test_api",
                sender=contact.email,
                subject="API testing thread",
                body="Hello, I need assistance with SLA breach and custom billing options.",
                timestamp=datetime.now(timezone.utc),
                category="Inquiry",
                urgency="Medium",
                status="Received",
            )
            db.add(email)
            await db.flush()

        action = await db.scalar(select(Action).where(Action.email_id == email.id))
        if not action:
            action = Action(
                email_id=email.id,
                action_type="Auto-Reply",
                proposed_content="Draft reply content for testing.",
                is_approved=False,
            )
            db.add(action)
            await db.flush()

        await db.commit()

        email_id = str(email.id)
        action_id = str(action.id)
        contact_email = contact.email

    # We must mock the lifespan or app state values that would normally be initialized
    # e.g., app.state.embedder and app.state.ws_manager
    from sentence_transformers import SentenceTransformer
    from app.config import settings
    from app.websocket import ConnectionManager
    app.state.embedder = SentenceTransformer(settings.embedding_model)
    app.state.ws_manager = ConnectionManager()
    app.state.jobs = {}

    import httpx
    async with AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        # 1. Health
        print("\nTesting GET /health...")
        res = await client.get("/health")
        assert res.status_code == 200, f"Failed health: {res.text}"
        print("GET /health Success:", res.json())

        # 2. Stats Dashboard
        print("\nTesting GET /dashboard/stats...")
        res = await client.get("/dashboard/stats")
        assert res.status_code == 200, f"Failed stats: {res.text}"
        data = res.json()
        assert "pending" in data and "total" in data, "Stats missing expected fields"
        print("GET /dashboard/stats Success:", data)

        # 3. Threads list
        print(f"\nTesting GET /threads/{contact_email}...")
        res = await client.get(f"/threads/{contact_email}")
        assert res.status_code == 200, f"Failed threads: {res.text}"
        data = res.json()
        assert len(data) > 0, "No threads returned"
        assert "emails" in data[0], "Emails missing in thread structure"
        assert "actions" in data[0]["emails"][0], "Actions missing in email structure"
        print("GET /threads Success: Retrieved nested threads correctly.")

        # 4. Respond to email
        print(f"\nTesting POST /respond/{email_id}...")
        res = await client.post(f"/respond/{email_id}", json={"reply_text": "Manual reply text", "escalate": False})
        assert res.status_code == 200, f"Failed respond: {res.text}"
        assert res.json()["status"] == "Replied"
        print("POST /respond Success:", res.json())

        # 5. Patch Action Draft
        print(f"\nTesting PATCH /drafts/{action_id}...")
        res = await client.patch(f"/drafts/{action_id}", json={"proposed_content": "Updated draft content."})
        assert res.status_code == 200, f"Failed update draft: {res.text}"
        assert res.json()["proposed_content"] == "Updated draft content."
        print("PATCH /drafts Success:", res.json())

        # 6. Approve Action Draft
        print(f"\nTesting POST /drafts/{action_id}/approve...")
        res = await client.post(f"/drafts/{action_id}/approve")
        assert res.status_code == 200, f"Failed approve draft: {res.text}"
        assert res.json()["status"] == "Replied"
        print("POST /drafts/approve Success:", res.json())

        # 7. Sentiment Trend (filtered and global)
        print("\nTesting GET /analytics/sentiment-trend...")
        res = await client.get(f"/analytics/sentiment-trend?sender={contact_email}&days=30")
        assert res.status_code == 200, f"Failed filtered trend: {res.text}"
        print("GET /analytics/sentiment-trend (Filtered) Success:", res.json())

        res = await client.get("/analytics/sentiment-trend?days=30")
        assert res.status_code == 200, f"Failed global trend: {res.text}"
        print("GET /analytics/sentiment-trend (Global) Success:", res.json())

        # 8. Category Breakdown
        print("\nTesting GET /analytics/category-breakdown...")
        res = await client.get("/analytics/category-breakdown")
        assert res.status_code == 200, f"Failed breakdown: {res.text}"
        print("GET /analytics/category-breakdown Success:", res.json())

        # 9. RAG Search
        print("\nTesting GET /rag/search...")
        res = await client.get("/rag/search?q=SLA credit policy downtime")
        assert res.status_code == 200, f"Failed RAG search: {res.text}"
        assert "results" in res.json()
        print("GET /rag/search Success: Retrieved chunks.")

        # 10. Web Reputation
        print("\nTesting GET /intelligence/reputation...")
        res = await client.get("/intelligence/reputation")
        assert res.status_code == 200, f"Failed reputation: {res.text}"
        print("GET /intelligence/reputation Success:", res.json())

        # 11. Agent Dry-Run (Verification of no database persistence)
        print(f"\nTesting POST /agent/dry-run/{email_id}...")
        # Check initial action count for this email
        async with get_db_session() as db2:
            initial_count = await db2.scalar(
                select(func.count(Action.id)).where(Action.email_id == email.id)
            )

        res = await client.post(f"/agent/dry-run/{email_id}")
        assert res.status_code == 200, f"Failed dry-run: {res.text}"
        assert "reasoning_log" in res.json()

        # Check action count after dry run (should be unchanged)
        async with get_db_session() as db2:
            final_count = await db2.scalar(
                select(func.count(Action.id)).where(Action.email_id == email.id)
            )
        assert initial_count == final_count, f"Dry-run persisted writes! Count before: {initial_count}, count after: {final_count}"
        print("POST /agent/dry-run Success: Executed ReAct trace and rolled back cleanly.")

        # 12. Audit Logs
        print(f"\nTesting GET /audit/email/{email_id}...")
        res = await client.get(f"/audit/email/{email_id}")
        assert res.status_code == 200, f"Failed audit: {res.text}"
        print("GET /audit Success: Retrieved log list.")

        # 13. Contacts Detail
        print(f"\nTesting GET /contacts/{contact_email}...")
        res = await client.get(f"/contacts/{contact_email}")
        assert res.status_code == 200, f"Failed contact profile: {res.text}"
        assert "open_thread_count" in res.json()
        print("GET /contacts Success:", res.json())

        # 14. Update Contact Status
        print(f"\nTesting PATCH /contacts/{contact_email}/status...")
        res = await client.patch(f"/contacts/{contact_email}/status", json={"status": "VIP"})
        assert res.status_code == 200, f"Failed status patch: {res.text}"
        assert res.json()["status"] == "VIP"
        print("PATCH /contacts/status Success:", res.json())

        # 15. Check Error Envelope validation
        print("\nTesting Error Envelope validation...")
        res = await client.get("/contacts/non_existent_email@test.com")
        assert res.status_code == 404, "Expected 404"
        err_data = res.json()
        assert "error_code" in err_data and "message" in err_data and "details" in err_data, "Error response does not match the envelope specifications"
        print("Error Envelope verification Success:", err_data)

    print("\nPhase 4 API Validation PASSED successfully!")


if __name__ == "__main__":
    asyncio.run(main())
