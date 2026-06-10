import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import AuditLog, Contact, Email, Thread
from app.schemas import EmailIngestPayload, IngestAcceptedResponse, JobStatusResponse
from app.services.email_processor import process_email_job
from app.services.heuristic_filter import run_heuristic_filter

router = APIRouter(prefix="/api", tags=["ingest"])


@router.post("/ingest", response_model=IngestAcceptedResponse, status_code=status.HTTP_202_ACCEPTED)
async def ingest_email(
    payload: EmailIngestPayload,
    background_tasks: BackgroundTasks,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> IngestAcceptedResponse:
    existing = await db.scalar(select(Email).where(Email.message_id == payload.message_id))
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"error_code": "DUPLICATE_MESSAGE", "message": "message_id already exists"},
        )

    raw_entities: dict = {}
    body = payload.body
    if body is None or body.strip() == "":
        raw_entities["body_empty"] = True
        body = ""
    elif len(body) > 10000:
        raw_entities["truncated"] = True
        raw_entities["original_length"] = len(body)
        body = body[:10000]

    heuristic = run_heuristic_filter(payload.sender, payload.subject, body)
    contact = await _upsert_contact(db, payload.sender, payload.timestamp)
    thread = await _upsert_thread(db, payload, contact.email)

    email = Email(
        thread_id=thread.id,
        message_id=payload.message_id,
        sender=payload.sender,
        subject=payload.subject,
        body=body,
        timestamp=payload.timestamp,
        category=heuristic.initial_category,
        urgency=heuristic.urgency,
        requires_human=heuristic.requires_human,
        raw_entities=raw_entities or None,
        status="Received",
    )
    db.add(email)
    await db.flush()

    audit = AuditLog(
        entity_type="email",
        entity_id=email.id,
        action="ingested",
        performed_by="api",
        diff={
            "message_id": payload.message_id,
            "heuristic": heuristic.__dict__,
            "recipient": str(payload.recipient) if payload.recipient else None,
            "labels": payload.labels,
        },
    )
    db.add(audit)
    await db.commit()

    job_id = str(uuid.uuid4())
    request.app.state.jobs[job_id] = {"job_id": job_id, "status": "queued", "message_id": payload.message_id}
    background_tasks.add_task(
        process_email_job,
        job_id,
        email.id,
        request.app.state.jobs,
        request.app.state.ws_manager,
        request.app.state.embedder,
    )

    return IngestAcceptedResponse(job_id=job_id, status="queued", message_id=payload.message_id)


@router.get("/status/{job_id}", response_model=JobStatusResponse)
async def get_job_status(job_id: str, request: Request) -> JobStatusResponse:
    job = request.app.state.jobs.get(job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    return JobStatusResponse(**job)


async def _upsert_contact(db: AsyncSession, sender: str, timestamp: datetime) -> Contact:
    contact = await db.scalar(select(Contact).where(Contact.email == sender))
    if contact is None:
        contact = Contact(email=sender, last_contact_at=timestamp)
        db.add(contact)
        await db.flush()
    else:
        contact.last_contact_at = timestamp
    return contact


async def _upsert_thread(db: AsyncSession, payload: EmailIngestPayload, sender_email: str) -> Thread:
    thread = await db.scalar(select(Thread).where(Thread.thread_id == payload.thread_id))
    now = datetime.now(timezone.utc)
    if thread is None:
        thread = Thread(
            thread_id=payload.thread_id,
            subject=payload.subject,
            sender_email=sender_email,
            first_seen_at=payload.timestamp,
            last_updated_at=payload.timestamp,
        )
        db.add(thread)
        await db.flush()
    else:
        thread.subject = thread.subject or payload.subject
        thread.last_updated_at = max(payload.timestamp, thread.last_updated_at or now)
    return thread
