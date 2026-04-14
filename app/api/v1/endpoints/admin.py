"""
Admin management endpoints for user verification and role assignment.
"""
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
from app.core.logging import get_logger
from app.db.session import get_db
from app.models.user import User, UserRole
from app.schemas.user import MessageResponse, UserResponse

logger = get_logger(__name__)

router = APIRouter(prefix="/admin", tags=["Admin"])


def check_admin(user: User = Depends(get_current_user)) -> User:
    """Dependency: verify current user is admin."""
    if user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can perform this action.",
        )
    return user


# User management
@router.post(
    "/users/{user_id}/verify",
    response_model=UserResponse,
    summary="Verify a user account",
)
def verify_user(
    user_id: uuid.UUID,
    db: Session = Depends(get_db),
    admin: User = Depends(check_admin),
) -> User:
    """
    Verify a user account (set is_verified=true).
    
    Admin-only endpoint. Activates the user for email/profile verification.
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found.",
        )
    
    user.is_verified = True
    db.commit()
    db.refresh(user)
    logger.info("user_verified", user_id=str(user.id), verified_by=str(admin.id))
    return user


@router.post(
    "/users/{user_id}/grant-admin",
    response_model=UserResponse,
    summary="Grant admin role to a user",
)
def grant_admin(
    user_id: uuid.UUID,
    db: Session = Depends(get_db),
    admin: User = Depends(check_admin),
) -> User:
    """
    Grant admin role to a user (set role=admin).
    
    Admin-only endpoint. User gets full administrative privileges.
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found.",
        )
    
    user.role = UserRole.ADMIN
    db.commit()
    db.refresh(user)
    logger.info("admin_role_granted", user_id=str(user.id), granted_by=str(admin.id))
    return user


@router.post(
    "/users/{user_id}/revoke-admin",
    response_model=UserResponse,
    summary="Revoke admin role from a user",
)
def revoke_admin(
    user_id: uuid.UUID,
    db: Session = Depends(get_db),
    admin: User = Depends(check_admin),
) -> User:
    """Revoke admin role and downgrade to regular user."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found.",
        )
    
    user.role = UserRole.USER
    db.commit()
    db.refresh(user)
    logger.info("admin_role_revoked", user_id=str(user.id), revoked_by=str(admin.id))
    return user


@router.post(
    "/users/{user_id}/deactivate",
    response_model=UserResponse,
    summary="Deactivate a user account",
)
def deactivate_user(
    user_id: uuid.UUID,
    db: Session = Depends(get_db),
    admin: User = Depends(check_admin),
) -> User:
    """Deactivate a user account (disable login)."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found.",
        )
    
    user.is_active = False
    db.commit()
    db.refresh(user)
    logger.info("user_deactivated", user_id=str(user.id), deactivated_by=str(admin.id))
    return user


@router.post(
    "/users/{user_id}/activate",
    response_model=UserResponse,
    summary="Reactivate a user account",
)
def activate_user(
    user_id: uuid.UUID,
    db: Session = Depends(get_db),
    admin: User = Depends(check_admin),
) -> User:
    """Reactivate a deactivated user account."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found.",
        )
    
    user.is_active = True
    db.commit()
    db.refresh(user)
    logger.info("user_activated", user_id=str(user.id), activated_by=str(admin.id))
    return user
