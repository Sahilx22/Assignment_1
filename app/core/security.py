"""
Security utilities:
- Password hashing with bcrypt
- JWT access & refresh token creation / verification
"""
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain_password: str) -> str:
    """Return a bcrypt hash of the given plaintext password."""
    return pwd_context.hash(plain_password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Return True if *plain_password* matches the stored *hashed_password*."""
    return pwd_context.verify(plain_password, hashed_password)


# JWT helpers
def _create_token(data: Dict[str, Any], expires_delta: timedelta) -> str:
    """Low-level helper that encodes a JWT with an expiry claim."""
    payload = data.copy()
    now = datetime.now(timezone.utc)
    expire = now + expires_delta
    # Add jti (JWT ID) for uniqueness to prevent token collision in fast operations
    payload.update({
        "exp": expire,
        "iat": now,
        "jti": f"{now.timestamp():.6f}"  # Unique per microsecond
    })
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_access_token(subject: str, extra_claims: Optional[Dict] = None) -> str:
    """
    Create a short-lived JWT access token.

    :param subject:      Usually the user's ID (str).
    :param extra_claims: Optional additional claims (e.g. {"role": "admin"}).
    """
    data: Dict[str, Any] = {"sub": subject, "type": "access"}
    if extra_claims:
        data.update(extra_claims)
    return _create_token(data, timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))


def create_refresh_token(subject: str) -> str:
    """
    Create a long-lived JWT refresh token.

    Refresh tokens carry minimal claims to reduce the blast radius of leakage.
    """
    data: Dict[str, Any] = {"sub": subject, "type": "refresh"}
    return _create_token(data, timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS))


def decode_token(token: str) -> Dict[str, Any]:
    """
    Decode and validate a JWT.

    :raises JWTError: if the token is expired, invalid, or tampered with.
    """
    return jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])


def verify_access_token(token: str) -> Optional[str]:
    """
    Verify an access token and return the subject (user ID) or None.

    Returns None instead of raising so callers can handle gracefully.
    """
    try:
        payload = decode_token(token)
        if payload.get("type") != "access":
            return None
        return payload.get("sub")
    except JWTError:
        return None


def verify_refresh_token(token: str) -> Optional[str]:
    """
    Verify a refresh token and return the subject (user ID) or None.
    """
    try:
        payload = decode_token(token)
        if payload.get("type") != "refresh":
            return None
        return payload.get("sub")
    except JWTError:
        return None
