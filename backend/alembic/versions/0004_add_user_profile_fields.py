"""add user profile fields

Revision ID: 0004_add_user_profile_fields
Revises: 0003_add_documents
Create Date: 2026-08-21
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0004_add_user_profile_fields"
down_revision: Union[str, Sequence[str], None] = "0003_add_documents"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("full_name", sa.String(length=120), nullable=True))
    op.add_column("users", sa.Column("position", sa.String(length=120), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "position")
    op.drop_column("users", "full_name")