import asyncio
import json
from sqlalchemy import text
from app.database import get_db_session

async def main():
    async with get_db_session() as db:
        # Fetch all threads
        res = await db.execute(text("SELECT id, thread_id, subject, sender_email, status FROM threads WHERE status != 'Resolved'"))
        threads = [dict(r._mapping) for r in res.fetchall()]
        
        print(f"Total active threads: {len(threads)}")
        for idx, t in enumerate(threads):
            # Fetch emails for this thread
            eres = await db.execute(text("SELECT id, subject, sender, status, category, urgency, requires_human, confidence FROM emails WHERE thread_id = :tid"), {"tid": t["id"]})
            emails = [dict(r._mapping) for r in eres.fetchall()]
            print(f"{idx+1}. Thread ID: {t['thread_id']} | Subject: {t['subject']} | Sender: {t['sender_email']} | Status: {t['status']}")
            for e in emails:
                # Check if agent was executed
                ares = await db.execute(text("SELECT COUNT(id) FROM audit_log WHERE entity_id = :eid AND action = 'react_agent_completed'"), {"eid": e["id"]})
                agent_executed = ares.scalar() > 0
                print(f"   - Email ID: {e['id']} | Subject: {e['subject']} | Category: {e['category']} | Requires Human: {e['requires_human']} | Confidence: {e['confidence']} | Agent Run: {agent_executed}")

if __name__ == "__main__":
    asyncio.run(main())
