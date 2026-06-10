import asyncio
from pathlib import Path

from sentence_transformers import SentenceTransformer

from app.config import settings
from app.database import get_db_session
from app.services.rag_pipeline import seed_knowledge_base


async def main() -> None:
    backend_app_dir = Path(__file__).resolve().parents[1] / "app"
    kb_dir = (backend_app_dir / settings.knowledge_base_dir).resolve()
    embedder = SentenceTransformer(settings.embedding_model)
    async with get_db_session() as db:
        chunk_count = await seed_knowledge_base(kb_dir, embedder, db)
    print(f"Seeded {chunk_count} knowledge chunks from {kb_dir}")


if __name__ == "__main__":
    asyncio.run(main())
