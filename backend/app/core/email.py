import asyncio
import smtplib
import logging
import secrets
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from app.core.config import settings

logger = logging.getLogger(__name__)


def _send_smtp_sync(to_email: str, code: str) -> bool:
    """Synchronous SMTP call — MUST be run via asyncio.to_thread()."""
    subject = "PRLens — Your verification code"
    body = f"""Your verification code is:

{code}

This code expires in 10 minutes. If you didn't request this, please ignore this email.

— PRLens
"""

    msg = MIMEMultipart()
    msg["From"] = settings.smtp_from
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))

    try:
        if settings.smtp_port == 465:
            server = smtplib.SMTP_SSL(settings.smtp_host, settings.smtp_port, timeout=10)
        else:
            server = smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10)
            if settings.smtp_port == 587 or settings.smtp_use_tls:
                server.starttls()
        server.login(settings.smtp_username, settings.smtp_password)
        server.sendmail(settings.smtp_from, to_email, msg.as_string())
        server.quit()
        return True
    except Exception as e:
        logger.warning("Failed to send OTP via SMTP, logging to console: %s", e)
        logger.info("OTP for %s: %s", to_email, code)
        return False


async def send_otp(to_email: str, code: str) -> bool:
    if settings.smtp_host == "console":
        logger.info("OTP for %s: %s", to_email, code)
        return True
    return await asyncio.to_thread(_send_smtp_sync, to_email, code)


def generate_otp() -> str:
    return str(secrets.randbelow(1_000_000)).zfill(6)
