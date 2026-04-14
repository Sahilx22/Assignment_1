"""
Authentication endpoints:
  POST /auth/register      — Create a new account
  POST /auth/login         — Email/password login
  POST /auth/logout        — Revoke refresh token
  POST /auth/refresh       — Rotate tokens
  GET  /auth/google/login  — Begin Google OAuth2 flow
  GET  /auth/google/callback — Handle Google OAuth2 callback
  POST /auth/verify/send   — Request verification code (email/SMS)
  POST /auth/verify/code   — Verify code and activate account
"""
import secrets

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.user import (
    GoogleCallbackResponse,
    LoginRequest,
    LogoutRequest,
    MessageResponse,
    RefreshRequest,
    TokenResponse,
    UserCreate,
    UserResponse,
    VerificationCodeRequest,
    VerifyCodeRequest,
    VerificationResponse,
)
from app.services import auth_service
from app.services.email_service import email_service
from app.services.verification_service import (
    send_email_verification,
    send_sms_verification,
    verify_code,
)
from app.services.google_oauth import get_google_auth_url, get_google_user_profile
from app.services.sms_service import sms_service

router = APIRouter(prefix="/auth", tags=["Authentication"])


# Registration
@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user account",
)
def register(payload: UserCreate, db: Session = Depends(get_db)) -> User:
    """
    Create a new user account with email and password.

    - Validates password complexity (min 8 chars, letter + digit).
    - Sends a welcome email and SMS (if phone provided).
    - Returns the created user profile (no tokens — user must log in).
    """
    user = auth_service.register_user(payload, db)

    # Fire-and-forget notifications (errors are logged, not raised)
    email_service.send_welcome_email(to=user.email, name=user.full_name)
    if user.phone_number:
        sms_service.send_welcome(to=user.phone_number, name=user.full_name)

    return user


# Login
@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Login with email and password",
)
def login(
    payload: LoginRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> TokenResponse:
    """
    Authenticate with email and password.

    Returns a short-lived **access token** and a long-lived **refresh token**.
    Store the refresh token securely (httpOnly cookie or secure storage).
    """
    user = auth_service.authenticate_user(payload.email, payload.password, db)
    return auth_service.create_user_tokens(user, db, request)


# Logout
@router.post(
    "/logout",
    response_model=MessageResponse,
    summary="Logout and revoke refresh token",
)
def logout(
    payload: LogoutRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MessageResponse:
    """
    Revoke the provided refresh token, effectively logging the user out
    from that session. The access token remains valid until it expires
    (mitigated by its short TTL).
    """
    auth_service.revoke_refresh_token(payload.refresh_token, db)
    return MessageResponse(message="Logged out successfully.")


# Token refresh
@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Rotate tokens using a refresh token",
)
def refresh_tokens(
    payload: RefreshRequest,
    db: Session = Depends(get_db),
) -> TokenResponse:
    """
    Exchange a valid refresh token for a new access + refresh token pair.

    Uses **token rotation** — the old refresh token is immediately revoked
    and a new one is issued. This detects token theft (if a stolen token
    is replayed, both the attacker and legitimate user will see an error).
    """
    return auth_service.refresh_user_tokens(payload.refresh_token, db)


# OAuth2
@router.get(
    "/google/login",
    summary="Redirect to Google OAuth2 consent screen",
    response_class=RedirectResponse,
)
def google_login() -> RedirectResponse:
    """
    Initiate the Google OAuth2 flow.

    Generates a CSRF `state` token and redirects the browser to Google's
    consent screen. The state is included in the redirect URI for verification.
    """
    state = secrets.token_urlsafe(32)
    # NOTE: In production, persist `state` in a short-lived server-side session
    #       or signed cookie and verify it in the callback to prevent CSRF.
    url = get_google_auth_url(state=state)
    return RedirectResponse(url=url)


@router.get(
    "/google/callback",
    response_model=GoogleCallbackResponse,
    summary="Handle Google OAuth2 callback",
)
async def google_callback(
    code: str,
    db: Session = Depends(get_db),
    state: str | None = None,
) -> GoogleCallbackResponse:
    """
    Exchange the authorization code from Google for a token pair.

    - Looks up or creates a local user from the Google profile.
    - Returns our own JWT pair (not Google's tokens).
    """
    if not code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing authorization code from Google.",
        )

    try:
        google_id, email, full_name = await get_google_user_profile(code)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to authenticate with Google. Please try again.",
        )

    user, is_new_user = auth_service.get_or_create_google_user(google_id, email, full_name, db)
    token_response = auth_service.create_user_tokens(user, db)

    if is_new_user:
        email_service.send_welcome_email(to=user.email, name=user.full_name)

    return GoogleCallbackResponse(
        access_token=token_response.access_token,
        refresh_token=token_response.refresh_token,
        token_type="bearer",
        is_new_user=is_new_user,
    )


# Verification
@router.post(
    "/verify/send",
    response_model=MessageResponse,
    summary="Request a verification code via email or SMS",
)
def request_verification(
    payload: VerificationCodeRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MessageResponse:
    """
    Send a verification code to the user's email or phone number.
    
    - **email**: Sends a 6-digit code to the user's registered email (stored in DB)
    - **sms**: Sends OTP via Twilio Verify API (fraud-protected, rate-limited)
    
    Requires authentication. User must have valid access token.
    """
    if payload.verification_type == "email":
        success = send_email_verification(user, db)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to send verification email. Please try again.",
            )
        return MessageResponse(
            message=f"Verification code sent to {user.email}. Valid for 15 minutes."
        )
    
    elif payload.verification_type == "sms":
        if not user.phone_number:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No phone number on file. Please add one first.",
            )
        send_sms_verification(user, db)
        # Note: SMS uses Twilio Verify API which handles delivery internally
        return MessageResponse(
            message=f"Verification code sent to {user.phone_number} via SMS."
        )
    
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid verification type. Use 'email' or 'sms'.",
        )


@router.post(
    "/verify/code",
    response_model=VerificationResponse,
    summary="Verify code and activate user account",
)
def verify_code_endpoint(
    payload: VerifyCodeRequest,
    verification_type: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> VerificationResponse:
    """
    Verify a code submitted by the user.
    
    Query parameters:
    - **verification_type**: 'email' or 'sms'
    
    If the code is valid and not expired:
    - The code is marked as used
    - The user is marked as verified (is_verified=true)
    
    Requires authentication.
    """
    if verification_type not in ["email", "sms"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="verification_type must be 'email' or 'sms'.",
        )
    
    success, message = verify_code(user, payload.code, verification_type, db)
    
    return VerificationResponse(
        message=message,
        is_verified=True,
        verification_type=verification_type,
    )
