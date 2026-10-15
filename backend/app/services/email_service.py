import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from app.core.config import settings

logger = logging.getLogger("solara_email")


class EmailService:
    @staticmethod
    def send_password_reset_email(to_email: str, reset_token: str) -> bool:
        reset_url = f"{settings.FRONTEND_URL}/reset-password?token={reset_token}"
        if settings.EMAIL_BACKEND == "console":
            # Developer console backend: explicitly permitted to display link for local testing
            print(f"\n[DEV CONSOLE EMAIL] Password reset link for {to_email}: {reset_url}\n")
            logger.info("Dev console password reset email emitted.")
            return True

        if settings.EMAIL_BACKEND == "smtp":
            subject = f"Password Reset Request - {settings.PROJECT_NAME}"
            body = (
                f"Hello,\n\n"
                f"A password reset was requested for your account ({to_email}).\n"
                f"Please use the following link to reset your password within {settings.PASSWORD_RESET_TOKEN_EXPIRE_MINUTES} minutes:\n\n"
                f"{reset_url}\n\n"
                f"If you did not request this, please ignore this email.\n"
            )
            return EmailService._send_smtp_email(to_email, subject, body)

        return False

    @staticmethod
    def send_account_invitation_email(to_email: str, activation_token: str) -> bool:
        activate_url = f"{settings.FRONTEND_URL}/activate?token={activation_token}"
        if settings.EMAIL_BACKEND == "console":
            # Developer console backend: explicitly permitted to display link for local testing
            print(f"\n[DEV CONSOLE EMAIL] Account activation link for {to_email}: {activate_url}\n")
            logger.info("Dev console account invitation email emitted.")
            return True

        if settings.EMAIL_BACKEND == "smtp":
            subject = f"Welcome to {settings.PROJECT_NAME} - Activate Your Account"
            body = (
                f"Hello,\n\n"
                f"An administrator has invited you to {settings.PROJECT_NAME}.\n"
                f"Please use the following link to set your password and activate your account:\n\n"
                f"{activate_url}\n\n"
            )
            return EmailService._send_smtp_email(to_email, subject, body)

        return False

    @staticmethod
    def _send_smtp_email(to_email: str, subject: str, text_body: str) -> bool:
        if not settings.SMTP_HOST:
            logger.warning("SMTP_HOST not configured. Email not sent.")
            return False

        try:
            msg = MIMEMultipart()
            msg["From"] = settings.EMAILS_FROM_EMAIL
            msg["To"] = to_email
            msg["Subject"] = subject
            msg.attach(MIMEText(text_body, "plain"))

            server = smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=10)
            if settings.SMTP_TLS:
                server.starttls()
            if settings.SMTP_USER and settings.SMTP_PASSWORD:
                server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.sendmail(settings.EMAILS_FROM_EMAIL, [to_email], msg.as_string())
            server.quit()
            return True
        except Exception as e:
            logger.error(f"Failed to send email via SMTP: {e}")
            return False
