import asyncio

from sqlalchemy import text

from app.database import engine


EXPECTED_TABLES = {
    "actions",
    "audit_log",
    "contacts",
    "emails",
    "knowledge_chunks",
    "threads",
    "web_intelligence_cache",
}


async def main() -> None:
    async with engine.connect() as conn:
        rows = (
            await conn.execute(
                text(
                    """
                    select tablename
                    from pg_tables
                    where schemaname = 'public'
                      and tablename = any(:table_names)
                    order by tablename
                    """
                ),
                {"table_names": sorted(EXPECTED_TABLES)},
            )
        ).scalars().all()

    await engine.dispose()
    found = set(rows)
    missing = sorted(EXPECTED_TABLES - found)
    print({"found": rows, "missing": missing})
    if missing:
        raise SystemExit(1)


if __name__ == "__main__":
    asyncio.run(main())
