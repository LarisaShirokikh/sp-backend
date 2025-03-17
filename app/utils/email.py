# app/utils/email.py
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from app.core.config import settings

from app.utils.code import generate_verification_code  # если нужно сгенерировать прямо здесь

def send_email(subject: str, recipient: str, html_content: str, text_content: str = "") -> None:
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = settings.EMAIL_SENDER
    msg["To"] = recipient

    part1 = MIMEText(text_content, "plain")
    part2 = MIMEText(html_content, "html")
    msg.attach(part1)
    msg.attach(part2)

    try:
        with smtplib.SMTP(settings.SMTP_SERVER, settings.SMTP_PORT) as server:
            server.starttls()
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.sendmail(settings.EMAIL_SENDER, recipient, msg.as_string())
    except Exception as e:
        print(f"Ошибка отправки email: {e}")

def send_verification_email_code(recipient: str, code: str) -> None:
    """Отправляет email с 6-значным кодом подтверждения."""
    subject = "Ваш код подтверждения email"
    html_content = f"""
    <html>
      <body>
        <p>Ваш код подтверждения email: <strong>{code}</strong></p>
      </body>
    </html>
    """
    text_content = f"Ваш код подтверждения email: {code}"
    send_email(subject, recipient, html_content, text_content)