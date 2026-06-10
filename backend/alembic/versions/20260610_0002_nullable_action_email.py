"""allow internal ticket actions without email link

Revision ID: 20260610_0002
Revises: 20260610_0001
Create Date: 2026-06-10
"""
from alembic import op


revision = "20260610_0002"
down_revision = "20260610_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column("actions", "email_id", nullable=True)


def downgrade() -> None:
    op.alter_column("actions", "email_id", nullable=False)
