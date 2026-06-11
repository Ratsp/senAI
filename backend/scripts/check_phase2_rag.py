import asyncio

from sentence_transformers import SentenceTransformer
from sqlalchemy import text

from app.config import settings
from app.database import get_db_session
from app.services.rag_pipeline import retrieve_relevant_chunks


async def main() -> None:
    embedder = SentenceTransformer(settings.embedding_model)
    async with get_db_session() as db:
        chunk_count = await db.scalar(text("SELECT COUNT(id) FROM knowledge_chunks"))
        chunks = await retrieve_relevant_chunks("refund SLA escalation policy", embedder, db, top_k=3)
    print({"knowledge_chunks": chunk_count, "top_sources": [chunk["source_doc"] for chunk in chunks]})
    if not chunk_count or not chunks:
        raise SystemExit(1)


if __name__ == "__main__":
    asyncio.run(main())

