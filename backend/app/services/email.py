"""
services/email.py
=================
Gestione invio email e token di verifica.

Flusso:
1. Alla registrazione, si genera un token JWT con subject = user.uuid
2. Si costruisce un link: {FRONTEND_URL}/verify-email?token={token}
3. Si invia l'email via SMTP con il link
4. L'utente clicca il link → il frontend redirige al backend
   GET /users/verify/{token} → verifica il token → is_verified = True
"""

import logging
import smtplib
from datetime import datetime, timedelta, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from uuid import UUID

from jose import JWTError, jwt

from app.config.config import settings

logger = logging.getLogger(__name__)

VERIFY_TOKEN_EXPIRE_HOURS = 48
ALGORITHM = "HS256"


def create_verification_token(user_uuid: UUID) -> str:
    """Crea un JWT di verifica email con scadenza 48h."""
    expire = datetime.now(timezone.utc) + timedelta(hours=VERIFY_TOKEN_EXPIRE_HOURS)
    to_encode = {
        "exp": expire,
        "sub": str(user_uuid),
        "purpose": "email-verification",
    }
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)


def verify_email_token(token: str) -> UUID | None:
    """
    Decodifica e valida il token di verifica.
    Ritorna lo UUID dell'utente se valido, None altrimenti.
    """
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("purpose") != "email-verification":
            return None
        sub = payload.get("sub")
        if sub is None:
            return None
        return UUID(sub)
    except (JWTError, ValueError):
        return None


def send_verification_email(to_email: str, token: str) -> None:
    """
    Invia l'email di verifica.
    Se SMTP non e' configurato (development), logga il link e non invia.
    """
    verify_url = f"{settings.FRONTEND_URL}/verify-email?token={token}"

    if not settings.SMTP_HOST:
        logger.warning(
            "SMTP non configurato - email di verifica non inviata. Link di verifica: %s",
            verify_url,
        )
        return

    subject = "Polibench - Conferma il tuo indirizzo email"
    html_body = (
        '<div style="font-family: sans-serif; max-width: 480px; margin: 0 auto;">'
        '<h2 style="color: #564ab1;">Benvenuto su Polibench</h2>'
        "<p>Grazie per esserti registrato. Clicca il pulsante qui sotto per "
        "confermare il tuo indirizzo email:</p>"
        '<p style="text-align: center; margin: 2rem 0;">'
        f'<a href="{verify_url}" '
        'style="background: #564ab1; color: white; padding: 12px 24px; '
        "text-decoration: none; border-radius: 6px; "
        'display: inline-block;">'
        "Conferma email</a></p>"
        '<p style="color: #6c757d; font-size: 13px;">'
        "Se non hai creato un account su Polibench, ignora questa email. "
        f"Il link scade tra {VERIFY_TOKEN_EXPIRE_HOURS} ore.</p></div>"
    )

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = (
        settings.SMTP_FROM_EMAIL or settings.SMTP_USER or "noreply@polibench.com"
    )
    msg["To"] = to_email
    msg.attach(MIMEText(f"Conferma email: {verify_url}", "plain"))
    msg.attach(MIMEText(html_body, "html"))

    try:
        if settings.SMTP_SSL:
            # SSL diretto — porta 465 (Aruba, alcuni provider)
            server = smtplib.SMTP_SSL(settings.SMTP_HOST, settings.SMTP_PORT)
        elif settings.SMTP_TLS:
            # STARTTLS — porta 587 (Gmail, Outlook, la maggior parte)
            server = smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT)
            server.starttls()
        else:
            # Nessuna cifratura — solo per test interni
            server = smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT)

        if settings.SMTP_USER and settings.SMTP_PASSWORD:
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)

        server.sendmail(msg["From"], [to_email], msg.as_string())
        server.quit()
        logger.info("Email di verifica inviata a %s", to_email)
    except Exception:
        logger.exception("Errore nell'invio dell'email di verifica a %s", to_email)
