from app.api.ingest import router as ingest_router
from app.api.dashboard import router as dashboard_router
from app.api.threads import router as threads_router
from app.api.respond import router as respond_router
from app.api.drafts import router as drafts_router
from app.api.analytics import router as analytics_router
from app.api.rag import router as rag_router
from app.api.intelligence import router as intelligence_router
from app.api.agent import router as agent_router
from app.api.audit import router as audit_router
from app.api.contacts import router as contacts_router

__all__ = [
    "ingest_router",
    "dashboard_router",
    "threads_router",
    "respond_router",
    "drafts_router",
    "analytics_router",
    "rag_router",
    "intelligence_router",
    "agent_router",
    "audit_router",
    "contacts_router",
]
