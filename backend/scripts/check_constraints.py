import asyncio
from sqlalchemy import text
from app.database import engine

async def main():
    async with engine.connect() as conn:
        res = await conn.execute(text("""
            SELECT conname, pg_get_constraintdef(c.oid)
            FROM pg_constraint c
            JOIN pg_namespace n ON n.oid = c.connamespace
            WHERE n.nspname = 'public' AND c.conrelid = 'contacts'::regclass;
        """))
        for row in res.fetchall():
            print(row)
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(main())
