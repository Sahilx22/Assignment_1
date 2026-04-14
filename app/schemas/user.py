"""
Pydantic schemas for request/response validation.

Naming convention:
  <Entity>Create   — input for creating a resource
  <Entity>Update   — input for partial updates
  <Entity>Response — output returned to the client (never exposes secrets)
"""
import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field, validator

from app.models.user import UserRole


# Base schemas
class BaseResponse(BaseModel):
    """Standard envelope for single-resource responses."""
    class Config:
        from_attributes = True


# User schemas
class UserCreate(BaseModel):
    """Payload for POST /auth/register."""
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
    full_name: Optional[str] = Field(None, max_length=255)
    phone_number: Optional[str] = Field(None, max_length=20)

    @validator("password")
    def password_strength(cls, v: str) -> str:
        """Enforce minimal password complexity."""
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit.")
        if not any(c.isalpha() for c in v):
            raise ValueError("Password must contain at least one letter.")
        return v


class UserUpdate(BaseModel):
    """Payload for PATCH /users/me — all fields optional."""
    full_name: Optional[str] = Field(None, max_length=255)
    phone_number: Optional[str] = Field(None, max_length=20)


class UserResponse(BaseResponse):
    """Safe user representation — no password hash, no internal flags."""
    id: uuid.UUID
    email: EmailStr
    full_name: Optional[str]
    phone_number: Optional[str]
    role: UserRole
    is_active: bool
    is_verified: bool
    is_oauth_user: bool
    created_at: datetime
    last_login_at: Optional[datetime]


class AdminUserResponse(UserResponse):
    """Extended view for admins — includes timestamps and Google ID flag."""
    google_id: Optional[str]  # Show presence, not value
    updated_at: datetime


# Auth schemas
class LoginRequest(BaseModel):
    """Payload for POST /auth/login."""
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    """Token pair returned on successful login or refresh."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # Access token TTL in seconds


class RefreshRequest(BaseModel):
    """Payload for POST /auth/refresh."""
    refresh_token: str


class LogoutRequest(BaseModel):
    """Payload for POST /auth/logout — client sends back the refresh token to revoke."""
    refresh_token: str


class GoogleCallbackResponse(BaseModel):
    """Response after successful Google OAuth2 flow."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    is_new_user: bool  # True if account was created during this flow


# Verification schemas
class VerificationCodeRequest(BaseModel):
    """Request to send a verification code."""
    verification_type: str = Field(..., pattern="^(email|sms)$")  # "email" or "sms"


class VerifyCodeRequest(BaseModel):
    """Request to verify a code."""
    code: str = Field(..., min_length=6, max_length=6, pattern="^\\d+$")


class VerificationResponse(BaseModel):
    """Response after successful verification."""
    message: str
    is_verified: bool
    verification_type: str


# Response helpers
class MessageResponse(BaseModel):
    """Simple acknowledgement response."""
    message: str


class ErrorDetail(BaseModel):
    """Structured error detail."""
    field: Optional[str] = None
    message: str


class ErrorResponse(BaseModel):
    """Standard error envelope."""
    error: str
    details: Optional[list[ErrorDetail]] = None
