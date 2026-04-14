"""
SQLAlchemy ORM models for the auth service.

Tables:
  - users         Core user account data
  - refresh_tokens  Persisted refresh tokens (allows server-side revocation)
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base, GUID


def _now() -> datetime:
    return datetime.now(timezone.utc)


# User roles enum
import enum


class UserRole(str, enum.Enum):
    ADMIN = "admin"
    USER = "user"


# User model
class User(Base):
    __tablename__ = "users"

    # Primary key — UUID avoids enumeration attacks
    id: Mapped[uuid.UUID] = mapped_column(
        GUID(), primary_key=True, default=uuid.uuid4, index=True
    )

    # Credentials
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str | None] = mapped_column(
        String(255), nullable=True
    )  # Null for social-auth users

    # Profile
    full_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    phone_number: Mapped[str | None] = mapped_column(String(20), nullable=True, unique=True)

    # RBAC
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole), default=UserRole.USER, nullable=False
    )

    # Account state
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # OAuth flags
    google_id: Mapped[str | None] = mapped_column(String(255), nullable=True, unique=True)
    is_oauth_user: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, onupdate=_now, nullable=False
    )
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    refresh_tokens: Mapped[list["RefreshToken"]] = relationship(
        "RefreshToken", back_populates="user", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email} role={self.role}>"


# Refresh tokens
class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id: Mapped[uuid.UUID] = mapped_column(
        GUID(), primary_key=True, default=uuid.uuid4
    )

    # The actual token string stored hashed for security
    token_hash: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)

    # Owner
    user_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    user: Mapped["User"] = relationship("User", back_populates="refresh_tokens")

    # Lifecycle
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Metadata (useful for security auditing)
    user_agent: Mapped[str | None] = mapped_column(Text, nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)  # IPv6 max length

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, nullable=False
    )

    @property
    def is_expired(self) -> bool:
        # Handle both timezone-aware (PostgreSQL) and naive (SQLite) datetimes
        now = datetime.now(timezone.utc)
        expires = self.expires_at
        if expires.tzinfo is None:
            now = now.replace(tzinfo=None)
        return now > expires

    @property
    def is_valid(self) -> bool:
        return not self.revoked and not self.is_expired

    def __repr__(self) -> str:
        return f"<RefreshToken id={self.id} user_id={self.user_id} revoked={self.revoked}>"


# Verification codes
class VerificationCode(Base):
    __tablename__ = "verification_codes"

    id: Mapped[uuid.UUID] = mapped_column(
        GUID(), primary_key=True, default=uuid.uuid4
    )

    # Reference to user
    user_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    user: Mapped["User"] = relationship("User")

    # Verification type: 'email' or 'sms'
    verification_type: Mapped[str] = mapped_column(String(50), nullable=False)  # email, sms

    # The actual code (6-digit numeric)
    code: Mapped[str] = mapped_column(String(10), nullable=False, index=True)

    # Target (email or phone number being verified)
    target: Mapped[str] = mapped_column(String(255), nullable=False)  # email or phone

    # Is this code already used/verified?
    is_used: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Expiry
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, nullable=False
    )

    @property
    def is_expired(self) -> bool:
        # Handle both timezone-aware (PostgreSQL) and naive (SQLite) datetimes
        now = datetime.now(timezone.utc)
        expires = self.expires_at
        if expires.tzinfo is None:
            now = now.replace(tzinfo=None)
        return now > expires

    @property
    def is_valid(self) -> bool:
        return not self.is_used and not self.is_expired

    def __repr__(self) -> str:
        return f"<VerificationCode id={self.id} type={self.verification_type} target={self.target}>"
