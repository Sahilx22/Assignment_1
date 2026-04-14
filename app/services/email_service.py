"""
Email Gateway Integration using SendGrid.

Provides templated transactional emails:
  - Welcome email after registration
  - Password reset link
  - Security alert (new login from unknown device)

Falls back to a no-op logger when SendGrid is not configured.
"""
from typing import Optional

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


# Email templates
def _welcome_html(name: str, app_name: str) -> str:
    return f"""
    <html><body style="font-family:Arial,sans-serif;max-width:600px;margin:auto">
      <h2 style="color:#2563EB">Welcome to {app_name}!</h2>
      <p>Hi {name},</p>
      <p>Your account has been created successfully. We're glad to have you on board.</p>
      <p style="color:#6B7280;font-size:12px">If you didn't create this account, please ignore this email.</p>
    </body></html>
    """


def _password_reset_html(name: str, reset_link: str, app_name: str) -> str:
    return f"""
    <html><body style="font-family:Arial,sans-serif;max-width:600px;margin:auto">
      <h2 style="color:#2563EB">Password Reset Request</h2>
      <p>Hi {name},</p>
      <p>Click the button below to reset your password. This link expires in 1 hour.</p>
      <a href="{reset_link}"
         style="display:inline-block;padding:12px 24px;background:#2563EB;color:#fff;
                text-decoration:none;border-radius:6px;font-weight:bold">
        Reset Password
      </a>
      <p style="color:#6B7280;font-size:12px">
        If you didn't request a password reset, you can safely ignore this email.
      </p>
    </body></html>
    """


def _login_alert_html(name: str, ip: str, user_agent: str, app_name: str) -> str:
    return f"""
    <html><body style="font-family:Arial,sans-serif;max-width:600px;margin:auto">
      <h2 style="color:#DC2626">New Login Detected</h2>
      <p>Hi {name},</p>
      <p>A new login was detected on your {app_name} account:</p>
      <ul>
        <li><b>IP Address:</b> {ip}</li>
        <li><b>Device:</b> {user_agent[:100]}</li>
      </ul>
      <p>If this wasn't you, please reset your password immediately.</p>
    </body></html>
    """


# Email service
class EmailService:
    """Thin wrapper around the SendGrid Python SDK."""

    def __init__(self) -> None:
        self._client = None
        self._configured = bool(settings.SENDGRID_API_KEY)

        if self._configured:
            try:
                import sendgrid  # type: ignore
                from sendgrid.helpers.mail import Mail  # type: ignore  # noqa: F401

                self._sg = sendgrid.SendGridAPIClient(api_key=settings.SENDGRID_API_KEY)
                logger.info("email_service_initialized")
            except ImportError:
                logger.warning("sendgrid_not_installed", hint="pip install sendgrid")
                self._configured = False

    def _send(self, to: str, subject: str, html_content: str) -> bool:
        """Low-level send helper."""
        if not self._configured:
            logger.warning(
                "email_not_configured_dev_mode",
                to=to,
                subject=subject,
            )
            return False

        try:
            from sendgrid.helpers.mail import Mail  # type: ignore

            message = Mail(
                from_email=(settings.SENDGRID_FROM_EMAIL, settings.SENDGRID_FROM_NAME),
                to_emails=to,
                subject=subject,
                html_content=html_content,
            )
            response = self._sg.send(message)
            logger.info("email_sent", to=to, subject=subject, status=response.status_code)
            return 200 <= response.status_code < 300
        except Exception as exc:
            logger.error("email_send_failed", error=str(exc), to=to)
            return False

    def send_welcome_email(self, to: str, name: Optional[str] = None) -> bool:
        """Send a welcome email after successful registration."""
        display_name = name or "there"
        return self._send(
            to=to,
            subject=f"Welcome to {settings.APP_NAME}!",
            html_content=_welcome_html(display_name, settings.APP_NAME),
        )

    def send_password_reset(self, to: str, reset_link: str, name: Optional[str] = None) -> bool:
        """Send a password-reset email with a time-limited link."""
        display_name = name or "there"
        return self._send(
            to=to,
            subject=f"{settings.APP_NAME} – Password Reset",
            html_content=_password_reset_html(display_name, reset_link, settings.APP_NAME),
        )

    def send_login_alert(
        self,
        to: str,
        ip: str,
        user_agent: str,
        name: Optional[str] = None,
    ) -> bool:
        """Send a security alert when a new login is detected."""
        display_name = name or "there"
        return self._send(
            to=to,
            subject=f"{settings.APP_NAME} – New Login Detected",
            html_content=_login_alert_html(display_name, ip, user_agent, settings.APP_NAME),
        )

    def send_email(self, to: str, subject: str, html: str) -> bool:
        """Generic email sending method for custom emails."""
        return self._send(to=to, subject=subject, html_content=html)


# Singleton
email_service = EmailService()
