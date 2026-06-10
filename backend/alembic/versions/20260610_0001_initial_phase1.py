"""initial phase 1 schema

Revision ID: 20260610_0001
Revises:
Create Date: 2026-06-10
"""
from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql


revision = "20260610_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "contacts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=True),
        sa.Column("company", sa.String(), nullable=True),
        sa.Column("status", sa.String(), server_default="Active", nullable=False),
        sa.Column("account_value", sa.Numeric(12, 2), nullable=True),
        sa.Column("churn_risk_score", sa.Float(), server_default="0", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_contact_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("email"),
    )
    op.create_index(op.f("ix_contacts_email"), "contacts", ["email"])
    op.create_index(op.f("ix_contacts_status"), "contacts", ["status"])
    op.create_index("ix_contacts_status_email", "contacts", ["status", "email"])

    op.create_table(
        "threads",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("thread_id", sa.String(), nullable=False),
        sa.Column("subject", sa.String(), nullable=True),
        sa.Column("sender_email", sa.String(), nullable=False),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(), server_default="Open", nullable=False),
        sa.Column("assigned_to", sa.String(), nullable=True),
        sa.ForeignKeyConstraint(["sender_email"], ["contacts.email"]),
        sa.UniqueConstraint("thread_id"),
    )
    op.create_index(op.f("ix_threads_sender_email"), "threads", ["sender_email"])
    op.create_index(op.f("ix_threads_status"), "threads", ["status"])
    op.create_index(op.f("ix_threads_thread_id"), "threads", ["thread_id"])

    op.create_table(
        "emails",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("thread_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("message_id", sa.String(), nullable=False),
        sa.Column("sender", sa.String(), nullable=False),
        sa.Column("subject", sa.String(), nullable=True),
        sa.Column("body", sa.Text(), nullable=True),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("sentiment_score", sa.Float(), nullable=True),
        sa.Column("category", sa.String(), nullable=True),
        sa.Column("urgency", sa.String(), nullable=True),
        sa.Column("requires_human", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("raw_entities", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("status", sa.String(), server_default="Received", nullable=False),
        sa.ForeignKeyConstraint(["thread_id"], ["threads.id"]),
        sa.UniqueConstraint("message_id"),
    )
    op.create_index(op.f("ix_emails_message_id"), "emails", ["message_id"])
    op.create_index(op.f("ix_emails_sender"), "emails", ["sender"])
    op.create_index(op.f("ix_emails_thread_id"), "emails", ["thread_id"])
    op.create_index(op.f("ix_emails_timestamp"), "emails", ["timestamp"])
    op.create_index("ix_emails_sender_timestamp_sentiment", "emails", ["sender", "timestamp", "sentiment_score"])

    op.create_table(
        "actions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("email_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("agent_reasoning_log", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("action_type", sa.String(), nullable=False),
        sa.Column("proposed_content", sa.Text(), nullable=True),
        sa.Column("is_approved", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("approved_by", sa.String(), nullable=True),
        sa.Column("executed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["email_id"], ["emails.id"]),
    )
    op.create_index(op.f("ix_actions_email_id"), "actions", ["email_id"])

    op.create_table(
        "knowledge_chunks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("source_doc", sa.String(), nullable=False),
        sa.Column("chunk_text", sa.Text(), nullable=False),
        sa.Column("embedding", Vector(384), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.execute(
        "CREATE INDEX ix_knowledge_chunks_embedding_ivfflat "
        "ON knowledge_chunks USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100)"
    )

    op.create_table(
        "web_intelligence_cache",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("source_url", sa.String(), nullable=True),
        sa.Column("target_entity", sa.String(), nullable=False),
        sa.Column("scraped_data", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("scraped_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(op.f("ix_web_intelligence_cache_expires_at"), "web_intelligence_cache", ["expires_at"])
    op.create_index(op.f("ix_web_intelligence_cache_target_entity"), "web_intelligence_cache", ["target_entity"])

    op.create_table(
        "audit_log",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("entity_type", sa.String(), nullable=False),
        sa.Column("entity_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("action", sa.String(), nullable=False),
        sa.Column("performed_by", sa.String(), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("diff", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("audit_log")
    op.drop_index(op.f("ix_web_intelligence_cache_target_entity"), table_name="web_intelligence_cache")
    op.drop_index(op.f("ix_web_intelligence_cache_expires_at"), table_name="web_intelligence_cache")
    op.drop_table("web_intelligence_cache")
    op.execute("DROP INDEX IF EXISTS ix_knowledge_chunks_embedding_ivfflat")
    op.drop_table("knowledge_chunks")
    op.drop_index(op.f("ix_actions_email_id"), table_name="actions")
    op.drop_table("actions")
    op.drop_index("ix_emails_sender_timestamp_sentiment", table_name="emails")
    op.drop_index(op.f("ix_emails_timestamp"), table_name="emails")
    op.drop_index(op.f("ix_emails_thread_id"), table_name="emails")
    op.drop_index(op.f("ix_emails_sender"), table_name="emails")
    op.drop_index(op.f("ix_emails_message_id"), table_name="emails")
    op.drop_table("emails")
    op.drop_index(op.f("ix_threads_thread_id"), table_name="threads")
    op.drop_index(op.f("ix_threads_status"), table_name="threads")
    op.drop_index(op.f("ix_threads_sender_email"), table_name="threads")
    op.drop_table("threads")
    op.drop_index("ix_contacts_status_email", table_name="contacts")
    op.drop_index(op.f("ix_contacts_status"), table_name="contacts")
    op.drop_index(op.f("ix_contacts_email"), table_name="contacts")
    op.drop_table("contacts")
