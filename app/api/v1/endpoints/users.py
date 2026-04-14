"""
User management endpoints:
  GET    /users/me          — Get current user's profile (authenticated)
  PATCH  /users/me          — Update current user's profile
  GET    /users/            — List all users (admin only)
  GET    /users/{user_id}   — Get any user by ID (admin only)
  PATCH  /users/{user_id}/role — Change a user's role (admin only)
  DELETE /users/{user_id}   — Deactivate a user (admin only)
"""
import uuid
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user, require_admin
from app.db.session import get_db
from app.models.user import User, UserRole
from app.schemas.user import (
    AdminUserResponse,
    MessageResponse,
    UserResponse,
    UserUpdate,
)

router = APIRouter(prefix="/users", tags=["Users"])


# Current user
@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get current user profile",
)
def get_my_profile(current_user: User = Depends(get_current_user)) -> User:
    """
    Return the authenticated user's profile.
    Requires a valid access token in the Authorization header.
    """
    return current_user


@router.patch(
    "/me",
    response_model=UserResponse,
    summary="Update current user profile",
)
def update_my_profile(
    payload: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> User:
    """
    Update mutable profile fields (full_name, phone_number).
    Email and role changes are not permitted via this endpoint.
    """
    if payload.full_name is not None:
        current_user.full_name = payload.full_name
    if payload.phone_number is not None:
        current_user.phone_number = payload.phone_number

    db.commit()
    db.refresh(current_user)
    return current_user


# Admin endpoints
@router.get(
    "/",
    response_model=List[AdminUserResponse],
    summary="List all users [Admin only]",
    dependencies=[Depends(require_admin)],
)
def list_users(
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
) -> List[User]:
    """
    Paginated list of all users.
    Accessible only by users with the **admin** role.
    """
    return db.query(User).offset(skip).limit(min(limit, 200)).all()


@router.get(
    "/{user_id}",
    response_model=AdminUserResponse,
    summary="Get user by ID [Admin only]",
    dependencies=[Depends(require_admin)],
)
def get_user(user_id: uuid.UUID, db: Session = Depends(get_db)) -> User:
    """Fetch a specific user by UUID. Admin access required."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
    return user


@router.patch(
    "/{user_id}/role",
    response_model=UserResponse,
    summary="Change a user's role [Admin only]",
)
def change_user_role(
    user_id: uuid.UUID,
    role: UserRole,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> User:
    """
    Promote or demote a user's role.
    Admins cannot demote their own account to prevent lockout.
    """
    if user_id == admin.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Admins cannot change their own role.",
        )

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

    user.role = role
    db.commit()
    db.refresh(user)
    return user


@router.delete(
    "/{user_id}",
    response_model=MessageResponse,
    summary="Deactivate a user [Admin only]",
)
def deactivate_user(
    user_id: uuid.UUID,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> MessageResponse:
    """
    Soft-delete: marks the user as inactive instead of removing the record.
    Active sessions will be rejected because `is_active` is checked on every request.
    """
    if user_id == admin.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Admins cannot deactivate their own account.",
        )

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

    user.is_active = False
    db.commit()
    return MessageResponse(message=f"User {user_id} has been deactivated.")
