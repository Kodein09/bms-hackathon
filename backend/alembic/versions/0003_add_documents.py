"""add documents

Revision ID: 0003_add_documents
Revises: 0002_add_notifications
Create Date: 2026-08-21
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0003_add_documents"
down_revision: Union[str, Sequence[str], None] = "0002_add_notifications"
branch_labels = None
depends_on = None


def upgrade() -> None:
    status_type = sa.Enum(
        "pending", "completed", "incoming", "outgoing",
        name="documentstatus", native_enum=False, length=20,
    )
    direction_type = sa.Enum(
        "incoming", "outgoing",
        name="documentdirection", native_enum=False, length=20,
    )
    op.create_table(
        "documents",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("original_name", sa.String(length=255), nullable=False),
        sa.Column("stored_name", sa.String(length=255), nullable=False),
        sa.Column("file_path", sa.String(length=500), nullable=False),
        sa.Column("file_size", sa.Integer(), nullable=False),
        sa.Column("mime_type", sa.String(length=150), nullable=False),
        sa.Column("extension", sa.String(length=20), nullable=False),
        sa.Column("status", status_type, nullable=False),
        sa.Column("direction", direction_type, nullable=False),
        sa.Column("is_deleted", sa.Boolean(), nullable=False),
        sa.Column("preview_path", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("stored_name"),
    )
    op.create_index(op.f("ix_documents_user_id"), "documents", ["user_id"], unique=False)
    op.create_index(op.f("ix_documents_is_deleted"), "documents", ["is_deleted"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_documents_is_deleted"), table_name="documents")
    op.drop_index(op.f("ix_documents_user_id"), table_name="documents")
    op.drop_table("documents")
