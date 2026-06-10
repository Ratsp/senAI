import asyncio
import time
from pathlib import Path

from sentence_transformers import SentenceTransformer

from app.database import get_db_session
from app.services.rag_pipeline import chunk_document, store_chunks


async def main() -> None:
    # Resolve knowledge_base path relative to scripts directory
    kb_dir = (Path(__file__).resolve().parents[2] / "knowledge_base").resolve()
    if not kb_dir.exists():
        raise FileNotFoundError(f"Knowledge base directory not found at: {kb_dir}")

    print(f"Loading embedding model for RAG...")
    from app.config import settings
    embedder = SentenceTransformer(settings.embedding_model)

    async with get_db_session() as db:
        md_files = sorted(kb_dir.glob("*.md"))
        print(f"Seeding {len(md_files)} markdown files from {kb_dir}...\n")
        
        for doc_path in md_files:
            start_time = time.time()
            text_content = doc_path.read_text(encoding="utf-8")
            
            # Chunk document
            chunks = chunk_document(text_content, doc_path.name)
            
            # Embed and store chunks (deletes old chunks for this file first)
            await store_chunks(chunks, embedder, db)
            
            duration = time.time() - start_time
            print(f"File: {doc_path.name:22} | Chunks: {len(chunks):2} | Time: {duration:.2f}s")

    print("\nKnowledge base seeding completed successfully!")


if __name__ == "__main__":
    asyncio.run(main())
