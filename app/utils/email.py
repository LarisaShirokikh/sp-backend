# app/utils/email.py
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from app.core.config import settings
from app.core.security import create_verification_token

def send_email(subject: str, recipient: str, html_content: str, text_content: str = "") -> None:
    """
    Отправляет электронное письмо.
    
    Args:
        subject: Тема письма
        recipient: Email получателя
        html_content: HTML-версия контента
        text_content: Текстовая версия контента
    """
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

def send_verification_email_link(recipient: str, user_id: int) -> None:
    """
    Отправляет email со ссылкой для подтверждения адреса.
    
    Args:
        recipient: Email получателя
        user_id: ID пользователя
    """
    # Создаем уникальный токен верификации
    token = create_verification_token(user_id, "email")
    
    # Формируем ссылку для подтверждения
    verification_url = f"{settings.FRONTEND_URL}/verify-email?token={token}"
    
    subject = "Подтверждение email адреса"
    html_content = f"""
    <html>
      <body>
        <h2>Подтверждение email адреса</h2>
        <p>Для подтверждения вашего email адреса, пожалуйста, перейдите по ссылке:</p>
        <p><a href="{verification_url}">Подтвердить email</a></p>
        <p>Если вы не регистрировались на нашем сайте, просто проигнорируйте это письмо.</p>
      </body>
    </html>
    """
    text_content = f"""
    Подтверждение email адреса
    
    Для подтверждения вашего email адреса, пожалуйста, перейдите по ссылке:
    {verification_url}
    
    Если вы не регистрировались на нашем сайте, просто проигнорируйте это письмо.
    """
    send_email(subject, recipient, html_content, text_content)

def send_password_reset_email(recipient: str, user_id: int) -> None:
    """
    Отправляет email со ссылкой для сброса пароля.
    
    Args:
        recipient: Email получателя
        user_id: ID пользователя
    """
    # Создаем уникальный токен для сброса пароля
    token = create_verification_token(user_id, "password")
    
    # Формируем ссылку для сброса пароля
    reset_url = f"{settings.FRONTEND_URL}/reset-password?token={token}"
    
    subject = "Сброс пароля"
    html_content = f"""
    <html>
      <body>
        <h2>Сброс пароля</h2>
        <p>Для сброса пароля, пожалуйста, перейдите по ссылке:</p>
        <p><a href="{reset_url}">Сбросить пароль</a></p>
        <p>Если вы не запрашивали сброс пароля на нашем сайте, просто проигнорируйте это письмо.</p>
        <p>Ссылка действительна в течение 24 часов.</p>
      </body>
    </html>
    """
    text_content = f"""
    Сброс пароля
    
    Для сброса пароля, пожалуйста, перейдите по ссылке:
    {reset_url}
    
    Если вы не запрашивали сброс пароля на нашем сайте, просто проигнорируйте это письмо.
    Ссылка действительна в течение 24 часов.
    """
    send_email(subject, recipient, html_content, text_content)