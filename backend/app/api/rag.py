from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.services.rag_pipeline import retrieve_relevant_chunks

router = APIRouter(prefix="/rag", tags=["rag"])


@router.get("/search")
async def search_rag_knowledge_base(
    q: str = Query(..., min_length=1, description="Query string to search in RAG KB"),
    request: Request = None,
    db: AsyncSession = Depends(get_db),
):
    embedder = request.app.state.embedder
    if embedder is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_code": "INTERNAL_ERROR",
                "message": "Sentence transformer model not loaded",
                "details": {},
            },
        )

    try:
        results = await retrieve_relevant_chunks(q, embedder, db, top_k=3)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_code": "PROCESSING_ERROR",
                "message": "Failed to run vector search",
                "details": {"error": str(exc)},
            },
        )

    return {
        "query": q,
        "results": results,
    }
