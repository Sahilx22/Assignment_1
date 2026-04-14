"""
SMS Gateway Integration using Twilio.

Provides a simple interface for sending SMS messages.
Falls back gracefully when Twilio credentials are not configured
(useful in development/testing environments).
"""
from typing import Optional

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class SMSService:
    """Thin wrapper around the Twilio REST client."""

    def __init__(self) -> None:
        self._client = None
        self._configured = bool(
            settings.TWILIO_ACCOUNT_SID
            and settings.TWILIO_AUTH_TOKEN
            and settings.TWILIO_PHONE_NUMBER
        )

        if self._configured:
            try:
                from twilio.rest import Client  # type: ignore
                self._client = Client(
                    settings.TWILIO_ACCOUNT_SID,
                    settings.TWILIO_AUTH_TOKEN,
                )
                logger.info("sms_service_initialized")
            except ImportError:
                logger.warning("twilio_not_installed", hint="pip install twilio")
                self._configured = False

    def send_sms(self, to: str, body: str) -> bool:
        """
        Send an SMS to the given phone number.

        :param to:   E.164-formatted phone number, e.g. "+919876543210"
        :param body: Message text (max 1600 chars for concatenated SMS).
        :returns:    True on success, False on failure.
        """
        if not self._configured or not self._client:
            # Log the message in development so we can verify flow without billing
            logger.warning(
                "sms_not_configured_dev_mode",
                to=to,
                body=body[:80],
            )
            return False

        try:
            message = self._client.messages.create(
                body=body,
                from_=settings.TWILIO_PHONE_NUMBER,
                to=to,
            )
            logger.info("sms_sent", sid=message.sid, to=to)
            return True
        except Exception as exc:
            logger.error("sms_send_failed", error=str(exc), to=to)
            return False

    def send_otp(self, to: str, otp: str) -> bool:
        """Send a one-time password via SMS."""
        body = f"Your {settings.APP_NAME} verification code is: {otp}. Valid for 10 minutes."
        return self.send_sms(to, body)

    def send_welcome(self, to: str, name: Optional[str] = None) -> bool:
        """Send a welcome SMS after successful registration."""
        greeting = f"Hi {name}! " if name else "Hi! "
        body = f"{greeting}Welcome to {settings.APP_NAME}. Your account has been created."
        return self.send_sms(to, body)


# Singleton — import and use directly: `from app.services.sms_service import sms_service`
sms_service = SMSService()
