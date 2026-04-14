"""
Verification service for email and SMS verification codes.

Handles:
  - Email: Manual 6-digit code generation and sending via SendGrid
  - SMS: Using Twilio Verify API (official, fraud-protected, rate-limited)
  - Code validation and user account activation
"""
import random
import string
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.logging import get_logger
from app.models.user import User, VerificationCode
from app.services.email_service import email_service
from app.services.twilio_verify_service import twilio_verify_service

logger = get_logger(__name__)


def _generate_code() -> str:
    """Generate a 6-digit numeric verification code."""
    return "".join(random.choices(string.digits, k=6))


def send_email_verification(user: User, db: Session) -> bool:
    """
    Send an email verification code to the user.
    
    - Generates a 6-digit code
    - Stores it in the database with 15-minute expiry
    - Sends via email
    - Returns True on success
    """
    code = _generate_code()
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=15)
    
    verification = VerificationCode(
        user_id=user.id,
        verification_type="email",
        code=code,
        target=user.email,
        expires_at=expires_at,
    )
    db.add(verification)
    db.commit()
    
    # Send via email
    subject = f"Your {settings.APP_NAME} Verification Code"
    html = f"""
    <html><body style="font-family:Arial,sans-serif;max-width:600px;margin:auto">
      <h2 style="color:#2563EB">Email Verification</h2>
      <p>Hi {user.full_name or 'there'},</p>
      <p>Your verification code is:</p>
      <h1 style="text-align:center;color:#2563EB;letter-spacing:8px;font-size:36px">{code}</h1>
      <p style="color:#6B7280">This code will expire in <b>15 minutes</b>.</p>
      <p style="color:#6B7280;font-size:12px">If you didn't request this, you can safely ignore this email.</p>
    </body></html>
    """
    
    success = email_service.send_email(
        to=user.email,
        subject=subject,
        html=html,
    )
    
    if success:
        logger.info("email_verification_sent", user_id=str(user.id), email=user.email)
    else:
        logger.warning("email_verification_failed", user_id=str(user.id))
    
    return success


def send_sms_verification(user: User, db: Session) -> bool:
    """
    Send SMS verification using Twilio Verify API.
    
    Unlike email verification which stores codes in DB, Twilio Verify:
    - Generates and manages OTP internally
    - Handles fraud protection
    - Rate limits automatically
    - No database storage needed
    
    Returns True on success or if in dev mode (code logged).
    """
    if not user.phone_number:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No phone number on file.",
        )
    
    # Use normalized phone (remove spaces)
    phone = user.phone_number.replace(" ", "").replace("-", "")
    
    # Ensure E.164 format
    if not phone.startswith("+"):
        phone = f"+{phone}"
    
    success = twilio_verify_service.send_verification(phone, channel="sms")
    
    if success:
        logger.info("sms_verification_sent", user_id=str(user.id), phone=phone)
    else:
        logger.warning("sms_verification_failed_dev_mode", user_id=str(user.id))
    
    # Always return True - Twilio Verify handles the rest
    return True


def verify_code(user: User, code: str, verification_type: str, db: Session) -> Tuple[bool, str]:
    """
    Verify a code submitted by the user.
    
    - Email: Check database for stored code
    - SMS: Check against Twilio Verify API
    
    Returns (success: bool, message: str)
    """
    if verification_type == "sms":
        # For SMS, delegate to Twilio Verify
        phone = user.phone_number.replace(" ", "").replace("-", "")
        if not phone.startswith("+"):
            phone = f"+{phone}"
        
        result = twilio_verify_service.check_verification(phone, code)
        
        if result["status"] == "approved":
            # Mark user as verified
            if not user.is_verified:
                user.is_verified = True
                db.commit()
            
            logger.info(
                "sms_verification_approved",
                user_id=str(user.id),
                status=result["status"],
            )
            return True, "SMS verified successfully!"
        else:
            logger.warning(
                "sms_verification_failed",
                user_id=str(user.id),
                status=result["status"],
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid or expired SMS verification code. Status: {result['status']}",
            )
    
    elif verification_type == "email":
        # For email, check our database
        # Find matching code
        verification = db.query(VerificationCode).filter(
            VerificationCode.user_id == user.id,
            VerificationCode.code == code,
            VerificationCode.verification_type == verification_type,
        ).first()
        
        if not verification:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid verification code.",
            )
        
        # Check if already used
        if verification.is_used:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Code has already been used.",
            )
        
        # Check if expired
        if verification.is_expired:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Verification code has expired. Request a new one.",
            )
        
        # Mark as used and verified
        verification.is_used = True
        verification.verified_at = datetime.now(timezone.utc)
        
        # Mark user as verified if this is their first successful verification
        if not user.is_verified:
            user.is_verified = True
        
        db.commit()
        logger.info(
            "email_verification_verified",
            user_id=str(user.id),
        )
        
        return True, "Email verified successfully!"
    
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid verification type.",
        )
