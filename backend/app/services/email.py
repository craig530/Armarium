import asyncio
import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional

from ..config import settings

logger = logging.getLogger("armarium.email")


def is_configured() -> bool:
    return bool(settings.smtp_host)


def resolve_base_url(request_base_url: str) -> str:
    """The host to build set-password/reset links against — `settings.
    public_base_url` if set, else the triggering request's own base URL."""
    return (settings.public_base_url or request_base_url).rstrip("/")


def _send_sync(to: str, subject: str, text_body: str, html_body: Optional[str]) -> None:
    from_address = settings.smtp_from_address or settings.smtp_username or "armarium@localhost"

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = from_address
    msg["To"] = to
    msg.attach(MIMEText(text_body, "plain"))
    if html_body:
        msg.attach(MIMEText(html_body, "html"))

    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10) as smtp:
        if settings.smtp_use_tls:
            smtp.starttls()
        if settings.smtp_username:
            smtp.login(settings.smtp_username, settings.smtp_password or "")
        smtp.sendmail(from_address, [to], msg.as_string())


async def send_email(to: str, subject: str, text_body: str, html_body: Optional[str] = None) -> None:
    """Send an email via the configured SMTP relay.

    Raises on failure — callers (always invoked from a FastAPI
    `BackgroundTasks` job, after the response has already been sent) should
    catch and log rather than let it propagate as an unhandled background
    task exception.
    """
    await asyncio.to_thread(_send_sync, to, subject, text_body, html_body)


async def send_email_logged(to: str, subject: str, text_body: str, html_body: Optional[str] = None) -> None:
    """Best-effort wrapper for `send_email`: logs and swallows failures
    instead of raising, since the caller has already responded to the
    request by the time this runs in the background."""
    try:
        await send_email(to, subject, text_body, html_body)
    except Exception:
        logger.warning("Failed to send email to %s (subject=%r)", to, subject, exc_info=True)


def build_invite_email(username: str, set_password_url: str) -> tuple[str, str, str]:
    subject = "You've been added to Armarium"
    text = (
        f"Hi {username},\n\n"
        "An administrator has created an Armarium account for you. "
        "Set your password to finish setting it up:\n\n"
        f"{set_password_url}\n\n"
        "This link expires in 24 hours."
    )
    html = (
        f"<p>Hi {username},</p>"
        "<p>An administrator has created an Armarium account for you. "
        f'Set your password to finish setting it up: <a href="{set_password_url}">{set_password_url}</a></p>'
        "<p>This link expires in 24 hours.</p>"
    )
    return subject, text, html


def build_reset_email(username: str, set_password_url: str) -> tuple[str, str, str]:
    subject = "Reset your Armarium password"
    text = (
        f"Hi {username},\n\n"
        "Use the link below to set a new password for your Armarium account:\n\n"
        f"{set_password_url}\n\n"
        "If you didn't request this, you can ignore this email. This link expires in 24 hours."
    )
    html = (
        f"<p>Hi {username},</p>"
        f'<p>Use the link below to set a new password for your Armarium account: <a href="{set_password_url}">{set_password_url}</a></p>'
        "<p>If you didn't request this, you can ignore this email. This link expires in 24 hours.</p>"
    )
    return subject, text, html
