from pathlib import Path
from typing import Any

import tiktoken
from sqlalchemy import delete, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import KnowledgeChunk


CHUNK_SIZE = 400
CHUNK_OVERLAP = 50
EMBEDDING_DIMENSION = 384


def chunk_document(text_content: str, source_doc: str) -> list[dict[str, str]]:
    encoding = tiktoken.get_encoding("cl100k_base")
    tokens = encoding.encode(text_content)
    chunks: list[dict[str, str]] = []

    start = 0
    while start < len(tokens):
        end = min(start + CHUNK_SIZE, len(tokens))
        chunk_tokens = tokens[start:end]
        chunk_text = encoding.decode(chunk_tokens).strip()
        if chunk_text:
            chunks.append({"source_doc": source_doc, "chunk_text": chunk_text})
        if end == len(tokens):
            break
        start = max(end - CHUNK_OVERLAP, start + 1)

    return chunks


def embed_text(text_content: str, embedder: Any) -> list[float]:
    vector = embedder.encode(text_content)
    if hasattr(vector, "tolist"):
        vector = vector.tolist()
    embedding = [float(value) for value in vector]
    if len(embedding) != EMBEDDING_DIMENSION:
        raise ValueError(f"Expected {EMBEDDING_DIMENSION}-dimension embedding, got {len(embedding)}")
    return embedding


async def store_chunks(chunks: list[dict[str, str]], embedder: Any, db: AsyncSession) -> None:
    source_docs = {chunk["source_doc"] for chunk in chunks}
    for source_doc in source_docs:
        await db.execute(delete(KnowledgeChunk).where(KnowledgeChunk.source_doc == source_doc))

    for chunk in chunks:
        db.add(
            KnowledgeChunk(
                source_doc=chunk["source_doc"],
                chunk_text=chunk["chunk_text"],
                embedding=embed_text(chunk["chunk_text"], embedder),
            )
        )
    await db.commit()


async def retrieve_relevant_chunks(
    query: str,
    embedder: Any,
    db: AsyncSession,
    top_k: int = 3,
) -> list[dict[str, Any]]:
    query_embedding = embed_text(query, embedder)
    result = await db.execute(
        text(
            """
            select source_doc,
                   chunk_text,
                   1 - (embedding <=> cast(:embedding as vector)) as similarity_score
            from knowledge_chunks
            order by embedding <=> cast(:embedding as vector)
            limit :top_k
            """
        ),
        {"embedding": _to_pgvector_literal(query_embedding), "top_k": top_k},
    )
    return [
        {
            "source_doc": row.source_doc,
            "chunk_text": row.chunk_text,
            "similarity_score": float(row.similarity_score),
        }
        for row in result
    ]


async def seed_knowledge_base(kb_dir: str | Path, embedder: Any, db: AsyncSession) -> int:
    root = Path(kb_dir).resolve()
    all_chunks: list[dict[str, str]] = []
    for doc_path in sorted(root.glob("*.md")):
        text_content = doc_path.read_text(encoding="utf-8")
        all_chunks.extend(chunk_document(text_content, doc_path.name))

    if all_chunks:
        await store_chunks(all_chunks, embedder, db)
    return len(all_chunks)


def _to_pgvector_literal(embedding: list[float]) -> str:
    return "[" + ",".join(str(value) for value in embedding) + "]"
