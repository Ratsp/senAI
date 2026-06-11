from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api import (
    ingest_router,
    dashboard_router,
    threads_router,
    respond_router,
    drafts_router,
    analytics_router,
    rag_router,
    intelligence_router,
    agent_router,
    audit_router,
    contacts_router,
)
from app.config import settings
from app.websocket import ConnectionManager
from fastapi.exceptions import RequestValidationError


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        from sentence_transformers import SentenceTransformer
        app.state.embedder = SentenceTransformer(settings.embedding_model)
    except Exception as exc:
        print(f"Warning: Failed to load SentenceTransformer during startup: {exc}. Using DummyEmbedder fallback.")
        class DummyEmbedder:
            def encode(self, text: str):
                return [0.0] * 384
        app.state.embedder = DummyEmbedder()
    app.state.jobs = {}
    app.state.ws_manager = ConnectionManager()
    yield


app = FastAPI(title="SenAI Agentic CRM Intelligence API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url, "http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(ingest_router)
app.include_router(dashboard_router)
app.include_router(threads_router)
app.include_router(respond_router)
app.include_router(drafts_router)
app.include_router(analytics_router)
app.include_router(rag_router)
app.include_router(intelligence_router)
app.include_router(agent_router)
app.include_router(audit_router)
app.include_router(contacts_router)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    manager: ConnectionManager = websocket.app.state.ws_manager
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    if isinstance(exc.detail, dict):
        error_code = exc.detail.get("error_code", f"HTTP_{exc.status_code}")
        message = exc.detail.get("message", str(exc.detail))
        details = exc.detail.get("details", {})
    else:
        error_code = f"HTTP_{exc.status_code}"
        message = str(exc.detail)
        details = {}
    payload = {"error_code": error_code, "message": message, "details": details}
    return JSONResponse(status_code=exc.status_code, content=payload)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content={
            "error_code": "VALIDATION_ERROR",
            "message": "Request validation failed",
            "details": {"errors": exc.errors()},
        },
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(
        status_code=500,
        content={
            "error_code": "INTERNAL_SERVER_ERROR",
            "message": "Unexpected server error",
            "details": {"error": str(exc)},
        },
    )
