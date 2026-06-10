from app.schemas.common import ErrorEnvelope
from app.schemas.ingest import EmailIngestPayload, IngestAcceptedResponse, JobStatusResponse
from app.schemas.respond import RespondPayload
from app.schemas.draft import DraftUpdatePayload
from app.schemas.contact import ContactStatusPayload

__all__ = [
    "EmailIngestPayload",
    "ErrorEnvelope",
    "IngestAcceptedResponse",
    "JobStatusResponse",
    "RespondPayload",
    "DraftUpdatePayload",
    "ContactStatusPayload",
]
