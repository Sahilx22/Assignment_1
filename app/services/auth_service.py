"""
Authentication service layer.

Encapsulates all business logic for:
  - User registration
  - Email/password login
  - Token issuance, refresh, and revocation
  - Google OAuth2 user creation/lookup
"""
import hashlib
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple

from fastapi import HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.logging import get_logger
from app.core.security import (
    create_access_token,
    create_refresh_token,
    hash_password,
    verify_password,
    verify_refresh_token,
)
from app.models.user import RefreshToken, User, UserRole
from app.schemas.user import TokenResponse, UserCreate

logger = get_logger(__name__)


# Helper functions
def _hash_token(raw_token: str) -> str:
    """Store only a SHA-256 hash of the refresh token for security."""
    return hashlib.sha256(raw_token.encode()).hexdigest()


def _build_token_response(user: User, raw_refresh: str) -> TokenResponse:
    access = create_access_token(
        subject=str(user.id),
        extra_claims={"role": user.role.value, "email": user.email},
    )
    return TokenResponse(
        access_token=access,
        refresh_token=raw_refresh,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


# Service functions
def register_user(payload: UserCreate, db: Session) -> User:
    """
    Create a new local (email/password) user account.

    Raises 409 if email already registered.
    """
    existing = db.query(User).filter(User.email == payload.email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists.",
        )

    user = User(
        email=payload.email,
        hashed_password=hash_password(payload.password),
        full_name=payload.full_name,
        phone_number=payload.phone_number,
        role=UserRole.USER,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    logger.info("user_registered", user_id=str(user.id), email=user.email)
    return user


def authenticate_user(email: str, password: str, db: Session) -> User:
    """
    Verify credentials and return the matching User.

    Raises 401 on invalid credentials (deliberately vague to prevent enumeration).
    """
    user: Optional[User] = db.query(User).filter(User.email == email).first()

    # Always run verify_password even on missing user to resist timing attacks
    # Dummy hash is a valid bcrypt hash format with wrong checksum to maintain constant time
    dummy_hash = "$2b$12$R9h7cIPz0gi.URNNC3kh2OPST9/PgBkqquzi.Ss7KIUgO2t0jKMUm"
    stored_hash = user.hashed_password if (user and user.hashed_password) else dummy_hash

    if not verify_password(password, stored_hash) or not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is inactive.",
        )

    return user


def create_user_tokens(
    user: User,
    db: Session,
    request: Optional[Request] = None,
) -> TokenResponse:
    """
    Issue an access + refresh token pair, persist the refresh token hash.
    """
    raw_refresh = create_refresh_token(str(user.id))
    token_hash = _hash_token(raw_refresh)

    expires_at = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

    db_token = RefreshToken(
        token_hash=token_hash,
        user_id=user.id,
        expires_at=expires_at,
        user_agent=request.headers.get("user-agent") if request else None,
        ip_address=request.client.host if (request and request.client) else None,
    )
    db.add(db_token)

    # Update last login timestamp
    user.last_login_at = datetime.now(timezone.utc)
    db.commit()

    logger.info("tokens_issued", user_id=str(user.id))
    return _build_token_response(user, raw_refresh)


def refresh_user_tokens(raw_refresh: str, db: Session) -> TokenResponse:
    """
    Validate a refresh token, revoke it, and issue a fresh pair (token rotation).

    Raises 401 on any invalid/expired/revoked token.
    """
    user_id = verify_refresh_token(raw_refresh)
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token.",
        )

    token_hash = _hash_token(raw_refresh)
    db_token: Optional[RefreshToken] = (
        db.query(RefreshToken).filter(RefreshToken.token_hash == token_hash).first()
    )

    if not db_token or not db_token.is_valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token has been revoked or expired.",
        )

    # Revoke the used token (rotation prevents replay)
    db_token.revoked = True
    db_token.revoked_at = datetime.now(timezone.utc)
    db.commit()

    user: Optional[User] = db.query(User).filter(User.id == user_id).first()
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive.",
        )

    return create_user_tokens(user, db)


def revoke_refresh_token(raw_refresh: str, db: Session) -> None:
    """Revoke a specific refresh token on logout."""
    token_hash = _hash_token(raw_refresh)
    db_token: Optional[RefreshToken] = (
        db.query(RefreshToken).filter(RefreshToken.token_hash == token_hash).first()
    )
    if db_token and not db_token.revoked:
        db_token.revoked = True
        db_token.revoked_at = datetime.now(timezone.utc)
        db.commit()
        logger.info("token_revoked", token_id=str(db_token.id))


def get_or_create_google_user(
    google_id: str,
    email: str,
    full_name: Optional[str],
    db: Session,
) -> Tuple[User, bool]:
    """
    Find or create a user from a verified Google profile.

    Returns (user, is_new_user).
    """
    # 1. Match by google_id (returning user)
    user = db.query(User).filter(User.google_id == google_id).first()
    if user:
        return user, False

    # 2. Match by email (user may have registered normally before OAuth)
    user = db.query(User).filter(User.email == email).first()
    if user:
        user.google_id = google_id
        user.is_oauth_user = True
        db.commit()
        db.refresh(user)
        return user, False

    # 3. Create a brand-new OAuth user
    user = User(
        email=email,
        google_id=google_id,
        full_name=full_name,
        hashed_password=None,   # OAuth users have no local password
        is_oauth_user=True,
        is_verified=True,       # Email verified by Google
        role=UserRole.USER,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    logger.info("google_user_created", user_id=str(user.id), email=user.email)
    return user, True
