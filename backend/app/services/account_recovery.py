import hashlib
import logging
import smtplib
import ssl
from datetime import UTC, datetime, timedelta
from email.message import EmailMessage

from fastapi import HTTPException, Request
from sqlalchemy import case, delete, func
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.models.account_recovery import AuthThrottle

logger = logging.getLogger(__name__)


async def throttle(request: Request, email: str, purpose: str, db: AsyncSession) -> None:
    now = datetime.now(UTC)
    expiry = now + timedelta(minutes=15)
    # Use the direct peer, never untrusted forwarding headers. Account limits
    # still protect deployments whose reverse proxy shares a single address.
    peer = request.client.host if request.client else "unknown"
    counts = []
    for identity, limit in [
        (f"{purpose}:email:{email.casefold()}", 10),
        (f"{purpose}:ip:{peer}", 200),
    ]:
        key = hashlib.sha256(identity.encode()).hexdigest()
        expired = AuthThrottle.expires_at <= now
        statement = insert(AuthThrottle).values(key=key, attempts=1, expires_at=expiry)
        count = await db.scalar(
            statement.on_conflict_do_update(
                index_elements=[AuthThrottle.key],
                set_={
                    "attempts": case((expired, 1), else_=AuthThrottle.attempts + 1),
                    "expires_at": case((expired, expiry), else_=AuthThrottle.expires_at),
                },
            ).returning(AuthThrottle.attempts)
        )
        counts.append((count or 0) > limit)
    await db.execute(delete(AuthThrottle).where(AuthThrottle.expires_at < func.now()))
    await db.commit()
    if any(counts):
        raise HTTPException(
            status_code=429,
            detail="Too many attempts. Try again later.",
            headers={"Retry-After": "900"},
        )


def send_password_reset(settings: Settings, email: str, token: str, locale: str) -> None:
    message = EmailMessage()
    message["From"] = settings.smtp_from
    message["To"] = email
    url = f"{settings.public_frontend_url.rstrip('/')}/reset-password#token={token}"
    if locale == "en":
        message["Subject"] = "Rodiva — reset your password"
        message.set_content(
            "Use this link within 30 minutes to reset your password:\n\n"
            f"{url}\n\nIf you did not request this, ignore this email."
        )
    else:
        message["Subject"] = "Rodiva — recuperar palavra-passe"
        message.set_content(
            "Use esta ligação nos próximos 30 minutos para alterar a palavra-passe:\n\n"
            f"{url}\n\nSe não fez este pedido, ignore esta mensagem."
        )
    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=15) as server:
            if settings.smtp_starttls:
                server.starttls(context=ssl.create_default_context())
            if settings.smtp_username:
                server.login(settings.smtp_username, settings.smtp_password)
            server.send_message(message)
    except (OSError, smtplib.SMTPException):
        # Do not log the email address or bearer token.
        logger.error("Password recovery email could not be delivered")
