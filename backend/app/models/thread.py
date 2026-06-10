import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Thread(Base):
    __tablename__ = "threads"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    thread_id: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    subject: Mapped[str | None] = mapped_column(String, nullable=True)
    sender_email: Mapped[str] = mapped_column(ForeignKey("contacts.email"), index=True, nullable=False)
    first_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    last_updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    status: Mapped[str] = mapped_column(String, default="Open", server_default="Open", index=True, nullable=False)
    assigned_to: Mapped[str | None] = mapped_column(String, nullable=True)

    contact = relationship("Contact")
    emails = relationship("Email", back_populates="thread")
