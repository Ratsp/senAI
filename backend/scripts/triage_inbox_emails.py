import asyncio
import json
from sqlalchemy import text
from app.database import get_db_session

async def main():
    async with get_db_session() as db:
        # Fetch all emails that are in the active inbox (Status is not 'Resolved' and status != 'Replied')
        # Let's fetch all emails where status in ('Received', 'Escalated', 'Processing')
        res = await db.execute(text("""
            SELECT id, subject, sender, status, category, urgency, requires_human, confidence, raw_entities
            FROM emails
            WHERE status IN ('Received', 'Escalated', 'Processing')
            ORDER BY timestamp DESC
        """))
        emails = [dict(r._mapping) for r in res.fetchall()]
        
        # Check audit log for react_agent_completed
        audit_res = await db.execute(text("SELECT entity_id, action FROM audit_log WHERE action = 'react_agent_completed'"))
        agent_runs = {str(r.entity_id) for r in audit_res.fetchall()}
        
        print(f"Total active emails in inbox queue: {len(emails)}")
        print(json.dumps(emails, indent=2, default=str))
        print("Agent runs on these emails:", agent_runs)

if __name__ == "__main__":
    asyncio.run(main())
