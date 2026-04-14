"""
FastAPI dependency functions for authentication and role-based access control.

Usage:
    current_user: User = Depends(get_current_user)
    admin: User = Depends(require_admin)
"""
from typing import Optional

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.security import verify_access_token
from app.db.session import get_db
from app.models.user import User, UserRole

# Bearer tokens
bearer_scheme = HTTPBearer(auto_error=False)


def _extract_token(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
) -> Optional[str]:
    """Extract the raw JWT string from the Authorization header."""
    if credentials and credentials.scheme.lower() == "bearer":
        return credentials.credentials
    return None


# Authenticated user
def get_current_user(
    token: Optional[str] = Depends(_extract_token),
    db: Session = Depends(get_db),
) -> User:
    """
    Resolve the JWT bearer token to a User instance.

    Raises 401 if:
      - No token provided
      - Token is invalid / expired
      - User does not exist or is inactive
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials.",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if not token:
        raise credentials_exception

    user_id = verify_access_token(token)
    if not user_id:
        raise credentials_exception

    user: Optional[User] = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise credentials_exception

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is inactive. Please contact support.",
        )

    return user


# Optional auth
def get_current_user_optional(
    token: Optional[str] = Depends(_extract_token),
    db: Session = Depends(get_db),
) -> Optional[User]:
    """
    Like `get_current_user` but returns None instead of raising when
    no/invalid token is provided. Useful for endpoints that behave
    differently for authenticated vs anonymous users.
    """
    if not token:
        return None
    try:
        return get_current_user(token=token, db=db)
    except HTTPException:
        return None


# RBAC dependencies
def require_role(*roles: UserRole):
    """
    Factory that returns a dependency enforcing one of the given roles.

    Example:
        @router.get("/admin-only", dependencies=[Depends(require_role(UserRole.ADMIN))])
    """
    def _check(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required role(s): {[r.value for r in roles]}",
            )
        return current_user

    return _check


def require_admin(current_user: User = Depends(get_current_user)) -> User:
    """Shorthand dependency — allows only ADMIN role."""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required.",
        )
    return current_user
