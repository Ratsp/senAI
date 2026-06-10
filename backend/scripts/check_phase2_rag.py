import asyncio

from sentence_transformers import SentenceTransformer
from sqlalchemy import func, select

from app.config import settings
from app.database import get_db_session
from app.models import KnowledgeChunk
from app.services.rag_pipeline import retrieve_relevant_chunks


async def main() -> None:
    embedder = SentenceTransformer(settings.embedding_model)
    async with get_db_session() as db:
        chunk_count = await db.scalar(select(func.count(KnowledgeChunk.id)))
        chunks = await retrieve_relevant_chunks("refund SLA escalation policy", embedder, db, top_k=3)
    print({"knowledge_chunks": chunk_count, "top_sources": [chunk["source_doc"] for chunk in chunks]})
    if not chunk_count or not chunks:
        raise SystemExit(1)


if __name__ == "__main__":
    asyncio.run(main())
