# app/email.py
import smtplib
import ssl
from email.message import EmailMessage
from app.config import settings


def send_reset_email(to_email: str, reset_link: str) -> None:
    msg = EmailMessage()
    msg["Subject"] = "Reset hasła"
    msg["From"] = f"{settings.smtp_from_name} <{settings.smtp_from_address}>"
    msg["To"] = to_email
    msg.set_content(
        f"Cześć,\n\n"
        f"Aby ustawić nowe hasło, kliknij w link:\n{reset_link}\n\n"
        f"Jeśli to nie Ty inicjowałeś tę operację, zignoruj tę wiadomość."
    )

    context = ssl.create_default_context()
    with smtplib.SMTP_SSL(settings.smtp_host, settings.smtp_port, context=context) as smtp:
        smtp.login(settings.smtp_username, settings.smtp_password)
        smtp.send_message(msg)