"""Add verification_codes table for email/SMS verification

Revision ID: 0002_verification_codes
Revises: 0001_initial
Create Date: 2026-04-14 00:00:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers
revision: str = "0002_verification_codes"
down_revision: Union[str, None] = "0001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create verification_codes table
    op.create_table(
        "verification_codes",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("verification_type", sa.String(50), nullable=False),
        sa.Column("code", sa.String(10), nullable=False),
        sa.Column("target", sa.String(255), nullable=False),
        sa.Column("is_used", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_verification_codes_code", "verification_codes", ["code"], unique=False)
    op.create_index(
        "ix_verification_codes_user_id", "verification_codes", ["user_id"], unique=False
    )


def downgrade() -> None:
    op.drop_table("verification_codes")
