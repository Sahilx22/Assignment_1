"""Initial migration: create users and refresh_tokens tables

Revision ID: 0001_initial
Revises:
Create Date: 2025-01-01 00:00:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers
revision: str = "0001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ------------------------------------------------------------------
    # Enum type for user roles (using raw SQL to avoid SQLAlchemy conflicts)
    # ------------------------------------------------------------------
    conn = op.get_bind()
    
    # Create ENUM type if it doesn't exist
    try:
        op.execute("CREATE TYPE userrole AS ENUM ('admin', 'user')")
    except Exception:
        # Type already exists, continue
        pass

    # ------------------------------------------------------------------
    # users table
    # ------------------------------------------------------------------
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("hashed_password", sa.String(255), nullable=True),
        sa.Column("full_name", sa.String(255), nullable=True),
        sa.Column("phone_number", sa.String(20), nullable=True),
        sa.Column(
            "role",
            sa.Enum("admin", "user", name="userrole", native_enum=False),
            nullable=False,
            server_default="user",
        ),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("is_verified", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("google_id", sa.String(255), nullable=True),
        sa.Column("is_oauth_user", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_users_id", "users", ["id"])
    op.create_index("ix_users_email", "users", ["email"], unique=True)
    op.create_unique_constraint("uq_users_phone_number", "users", ["phone_number"])
    op.create_unique_constraint("uq_users_google_id", "users", ["google_id"])

    # ------------------------------------------------------------------
    # refresh_tokens table
    # ------------------------------------------------------------------
    op.create_table(
        "refresh_tokens",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("token_hash", sa.String(255), nullable=False),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("user_agent", sa.Text(), nullable=True),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_refresh_tokens_token_hash", "refresh_tokens", ["token_hash"], unique=True)


def downgrade() -> None:
    op.drop_table("refresh_tokens")
    op.drop_table("users")
    op.execute("DROP TYPE IF EXISTS userrole")
