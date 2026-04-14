"""
Google OAuth2 service.

Flow:
  1. Client calls GET /auth/google/login  → redirect to Google consent screen
  2. Google calls GET /auth/google/callback?code=...
  3. We exchange the code for tokens, fetch the user profile, then
     create/update the local user and issue our own JWT pair.
"""
from typing import Optional, Tuple
from urllib.parse import urlencode

import httpx

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

# Google OAuth2 endpoints
GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"


def get_google_auth_url(state: Optional[str] = None) -> str:
    """
    Build the Google OAuth2 authorization URL.

    The client is redirected here to begin the OAuth2 flow.
    :param state: CSRF token to validate in the callback.
    """
    params = {
        "client_id": settings.GOOGLE_CLIENT_ID,
        "redirect_uri": settings.GOOGLE_REDIRECT_URI,
        "response_type": "code",
        "scope": "openid email profile",
        "access_type": "offline",
        "prompt": "select_account",
    }
    if state:
        params["state"] = state

    return f"{GOOGLE_AUTH_URL}?{urlencode(params)}"


async def exchange_code_for_tokens(code: str) -> dict:
    """
    Exchange an authorization code for Google access/ID tokens.

    :raises HTTPException: on network error or invalid code.
    """
    payload = {
        "code": code,
        "client_id": settings.GOOGLE_CLIENT_ID,
        "client_secret": settings.GOOGLE_CLIENT_SECRET,
        "redirect_uri": settings.GOOGLE_REDIRECT_URI,
        "grant_type": "authorization_code",
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(GOOGLE_TOKEN_URL, data=payload)
        response.raise_for_status()
        return response.json()


async def get_google_user_info(access_token: str) -> dict:
    """
    Fetch the authenticated user's profile from the Google userinfo endpoint.
    """
    async with httpx.AsyncClient() as client:
        response = await client.get(
            GOOGLE_USERINFO_URL,
            headers={"Authorization": f"Bearer {access_token}"},
        )
        response.raise_for_status()
        return response.json()


async def get_google_user_profile(code: str) -> Tuple[str, str, Optional[str]]:
    """
    High-level helper: given an OAuth2 code, return (google_id, email, full_name).

    :raises Exception: on Google API errors.
    """
    try:
        tokens = await exchange_code_for_tokens(code)
        user_info = await get_google_user_info(tokens["access_token"])

        google_id: str = user_info["sub"]
        email: str = user_info["email"]
        full_name: Optional[str] = user_info.get("name")

        logger.info("google_profile_fetched", google_id=google_id, email=email)
        return google_id, email, full_name

    except httpx.HTTPStatusError as exc:
        logger.error("google_api_error", status=exc.response.status_code, detail=exc.response.text)
        raise
    except Exception as exc:
        logger.error("google_auth_unexpected_error", error=str(exc))
        raise
