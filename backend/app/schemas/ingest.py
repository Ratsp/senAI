from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class EmailIngestPayload(BaseModel):
    message_id: str = Field(min_length=1)
    thread_id: str = Field(min_length=1)
    sender: EmailStr
    subject: str | None = None
    body: str | None = None
    timestamp: datetime
    recipient: EmailStr | None = None
    labels: list[str] | None = None


class IngestAcceptedResponse(BaseModel):
    job_id: str
    status: str
    message_id: str


class JobStatusResponse(BaseModel):
    job_id: str
    status: str
    message_id: str | None = None
    detail: str | None = None
    result: dict | None = None

    model_config = ConfigDict(from_attributes=True)
