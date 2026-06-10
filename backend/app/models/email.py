import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Email(Base):
    __tablename__ = "emails"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    thread_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("threads.id"), index=True, nullable=False)
    message_id: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    sender: Mapped[str] = mapped_column(String, index=True, nullable=False)
    subject: Mapped[str | None] = mapped_column(String, nullable=True)
    body: Mapped[str | None] = mapped_column(Text, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True, nullable=False)
    sentiment_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    category: Mapped[str | None] = mapped_column(String, nullable=True)
    urgency: Mapped[str | None] = mapped_column(String, nullable=True)
    requires_human: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false", nullable=False)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    raw_entities: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    status: Mapped[str] = mapped_column(String, default="Received", server_default="Received", nullable=False)

    thread = relationship("Thread", back_populates="emails")
    actions = relationship("Action", back_populates="email")


Index("ix_emails_sender_timestamp_sentiment", Email.sender, Email.timestamp, Email.sentiment_score)
