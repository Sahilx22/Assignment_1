"""
Twilio Verify API integration for SMS/Email OTP verification.

Uses the official Twilio Verify service which handles:
  - OTP generation and delivery
  - Fraud protection
  - Rate limiting
  - Built-in phone number validation
"""
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class TwilioVerifyService:
    """Thin wrapper around Twilio Verify REST API."""

    def __init__(self) -> None:
        self._client = None
        self._configured = bool(
            settings.TWILIO_ACCOUNT_SID
            and settings.TWILIO_AUTH_TOKEN
            and settings.TWILIO_VERIFY_SERVICE_SID
        )

        if self._configured:
            try:
                from twilio.rest import Client  # type: ignore

                self._client = Client(
                    settings.TWILIO_ACCOUNT_SID,
                    settings.TWILIO_AUTH_TOKEN,
                )
                logger.info("twilio_verify_service_initialized")
            except ImportError:
                logger.warning("twilio_not_installed", hint="pip install twilio")
                self._configured = False

    def send_verification(self, phone_number: str, channel: str = "sms") -> bool:
        """
        Send a verification code via Twilio Verify.

        :param phone_number: E.164-formatted phone number, e.g. "+919876543210"
        :param channel: "sms", "call", or "email"
        :returns: True on success, False on failure.
        """
        if not self._configured or not self._client:
            logger.warning(
                "twilio_verify_not_configured_dev_mode",
                phone=phone_number,
                channel=channel,
            )
            return False

        try:
            verification = self._client.verify.v2.services(
                settings.TWILIO_VERIFY_SERVICE_SID
            ).verifications.create(to=phone_number, channel=channel)

            logger.info(
                "verification_sent",
                phone=phone_number,
                channel=channel,
                sid=verification.sid,
            )
            return True
        except Exception as exc:
            logger.error(
                "verification_send_failed",
                error=str(exc),
                phone=phone_number,
                channel=channel,
            )
            return False

    def check_verification(self, phone_number: str, code: str) -> dict:
        """
        Check a verification code submitted by the user.

        :param phone_number: E.164-formatted phone number
        :param code: The code user entered
        :returns: {'success': bool, 'status': str}
                  status can be 'approved', 'pending', or 'denied'
        """
        if not self._configured or not self._client:
            logger.warning(
                "twilio_verify_not_configured_dev_mode",
                phone=phone_number,
                action="check",
            )
            return {"success": False, "status": "pending"}

        try:
            verification_check = self._client.verify.v2.services(
                settings.TWILIO_VERIFY_SERVICE_SID
            ).verification_checks.create(to=phone_number, code=code)

            status = verification_check.status
            success = status == "approved"

            logger.info(
                "verification_checked",
                phone=phone_number,
                status=status,
                success=success,
            )

            return {"success": success, "status": status}

        except Exception as exc:
            logger.error(
                "verification_check_failed",
                error=str(exc),
                phone=phone_number,
            )
            return {"success": False, "status": "denied"}


# Singleton
twilio_verify_service = TwilioVerifyService()
