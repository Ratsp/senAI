from fastapi import APIRouter, Depends, HTTPException, Query, Request, status

from app.database import get_db
from app.services.rag_pipeline import retrieve_relevant_chunks
from app.auth import verify_api_key

router = APIRouter(prefix="/rag", tags=["rag"], dependencies=[Depends(verify_api_key)])


@router.get("/search")
async def search_rag_knowledge_base(
    q: str = Query(..., min_length=1, description="Query string to search in RAG KB"),
    request: Request = None,
    db=Depends(get_db),
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
