import json
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, status
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app.database import get_db
from app.schemas import EmailIngestPayload, IngestAcceptedResponse, JobStatusResponse
from app.services.email_processor import process_email_job
from app.services.heuristic_filter import run_heuristic_filter
from app.auth import verify_api_key

router = APIRouter(prefix="/api", tags=["ingest"], dependencies=[Depends(verify_api_key)])


class SimpleContact:
    def __init__(self, id: uuid.UUID, email: str):
        self.id = id
        self.email = email


class SimpleThread:
    def __init__(self, id: uuid.UUID, thread_id: str):
        self.id = id
        self.thread_id = thread_id


@router.post("/ingest", response_model=IngestAcceptedResponse, status_code=status.HTTP_202_ACCEPTED)
async def ingest_email(
    payload: EmailIngestPayload,
    background_tasks: BackgroundTasks,
    request: Request,
    db=Depends(get_db),
) -> IngestAcceptedResponse:
    existing = await db.scalar(
        text("SELECT id FROM emails WHERE message_id = :message_id"),
        {"message_id": payload.message_id}
    )
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"error_code": "DUPLICATE_MESSAGE", "message": "message_id already exists"},
        )

    import html

    raw_entities: dict = {}
    body = payload.body
    if body is not None:
        body = html.unescape(body)
    
    subject = payload.subject
    if subject is not None:
        subject = html.unescape(subject)

    if body is None or body.strip() == "":
        raw_entities["body_empty"] = True
        body = ""
    elif len(body) > 10000:
        raw_entities["truncated"] = True
        raw_entities["original_length"] = len(body)
        body = body[:10000]

    if subject is None or subject.strip() == "":
        subject = ""

    heuristic = run_heuristic_filter(payload.sender, subject, body)
    contact = await _upsert_contact(db, payload.sender, payload.timestamp)
    thread = await _upsert_thread(db, payload.thread_id, subject, payload.timestamp, contact.email)

    email_id = uuid.uuid4()
    await db.execute(
        text("""
            INSERT INTO emails (
                id, thread_id, message_id, sender, subject, body, timestamp, 
                sentiment_score, category, urgency, requires_human, confidence, raw_entities, status
            ) VALUES (
                :id, :thread_id, :message_id, :sender, :subject, :body, :timestamp, 
                :sentiment_score, :category, :urgency, :requires_human, :confidence, :raw_entities, :status
            )
        """),
        {
            "id": email_id,
            "thread_id": thread.id,
            "message_id": payload.message_id,
            "sender": payload.sender,
            "subject": subject,
            "body": body,
            "timestamp": payload.timestamp,
            "sentiment_score": None,
            "category": heuristic.initial_category,
            "urgency": heuristic.urgency,
            "requires_human": heuristic.requires_human,
            "confidence": None,
            "raw_entities": json.dumps(raw_entities) if raw_entities else None,
            "status": "Received",
        }
    )

    audit_diff = {
        "message_id": payload.message_id,
        "heuristic": heuristic.__dict__,
        "recipient": str(payload.recipient) if payload.recipient else None,
        "labels": payload.labels,
    }
    await db.execute(
        text("""
            INSERT INTO audit_log (id, entity_type, entity_id, action, performed_by, timestamp, diff)
            VALUES (:id, :entity_type, :entity_id, :action, :performed_by, :timestamp, :diff)
        """),
        {
            "id": uuid.uuid4(),
            "entity_type": "email",
            "entity_id": email_id,
            "action": "ingested",
            "performed_by": "api",
            "timestamp": datetime.now(timezone.utc),
            "diff": json.dumps(audit_diff),
        }
    )

    await db.commit()

    job_id = str(uuid.uuid4())
    request.app.state.jobs[job_id] = {"job_id": job_id, "status": "queued", "message_id": payload.message_id}
    background_tasks.add_task(
        process_email_job,
        job_id,
        email_id,
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


async def _upsert_contact(db, sender: str, timestamp: datetime) -> SimpleContact:
    try:
        async with db.begin_nested():
            res = await db.execute(
                text("SELECT id, email FROM contacts WHERE email = :email"),
                {"email": sender}
            )
            row = res.fetchone()
            if row is None:
                contact_id = uuid.uuid4()
                await db.execute(
                    text("""
                        INSERT INTO contacts (id, email, name, company, status, account_value, churn_risk_score, created_at, last_contact_at)
                        VALUES (:id, :email, NULL, NULL, 'Active', 0.0, 0.0, :now, :last_contact)
                    """),
                    {
                        "id": contact_id,
                        "email": sender,
                        "now": datetime.now(timezone.utc),
                        "last_contact": timestamp,
                    }
                )
                return SimpleContact(id=contact_id, email=sender)
    except IntegrityError:
        pass

    res = await db.execute(
        text("SELECT id, email FROM contacts WHERE email = :email"),
        {"email": sender}
    )
    row = res.fetchone()
    if row is not None:
        contact_id = row.id
        await db.execute(
            text("UPDATE contacts SET last_contact_at = :last_contact WHERE id = :id"),
            {"last_contact": timestamp, "id": contact_id}
        )
        return SimpleContact(id=contact_id, email=row.email)
    raise ValueError(f"Failed to upsert contact {sender}")


async def _upsert_thread(db, thread_id_val: str, subject: str, timestamp: datetime, sender_email: str) -> SimpleThread:
    try:
        async with db.begin_nested():
            res = await db.execute(
                text("SELECT id, thread_id, subject, last_updated_at FROM threads WHERE thread_id = :thread_id"),
                {"thread_id": thread_id_val}
            )
            row = res.fetchone()
            now = datetime.now(timezone.utc)
            if row is None:
                thread_uuid = uuid.uuid4()
                await db.execute(
                    text("""
                        INSERT INTO threads (id, thread_id, subject, sender_email, first_seen_at, last_updated_at, status, assigned_to)
                        VALUES (:id, :thread_id, :subject, :sender_email, :first_seen_at, :last_updated_at, 'Open', NULL)
                    """),
                    {
                        "id": thread_uuid,
                        "thread_id": thread_id_val,
                        "subject": subject,
                        "sender_email": sender_email,
                        "first_seen_at": timestamp,
                        "last_updated_at": timestamp,
                    }
                )
                return SimpleThread(id=thread_uuid, thread_id=thread_id_val)
    except IntegrityError:
        pass

    res = await db.execute(
        text("SELECT id, thread_id, subject, last_updated_at FROM threads WHERE thread_id = :thread_id"),
        {"thread_id": thread_id_val}
    )
    row = res.fetchone()
    if row is not None:
        thread_uuid = row.id
        new_subject = row.subject or subject
        new_last_updated = max(timestamp, row.last_updated_at or now)
        await db.execute(
            text("UPDATE threads SET subject = :subject, last_updated_at = :last_updated WHERE id = :id"),
            {"subject": new_subject, "last_updated": new_last_updated, "id": thread_uuid}
        )
        return SimpleThread(id=thread_uuid, thread_id=thread_id_val)
    raise ValueError(f"Failed to upsert thread {thread_id_val}")
