import logging
import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from app.core.config import settings

logger = logging.getLogger("solara_email")


class EmailService:
    @staticmethod
    def send_password_reset_email(to_email: str, reset_token: str) -> bool:
        reset_url = f"{settings.FRONTEND_URL}/reset-password?token={reset_token}"
        backend = settings.EMAIL_BACKEND.strip().lower()
        if backend == "console":
            # Developer console backend: explicitly permitted to display link for local testing
            print(f"\n[DEV CONSOLE EMAIL] Password reset link for {to_email}: {reset_url}\n")
            logger.info("Dev console password reset email emitted.")
            return True

        if backend == "smtp":
            subject = f"Password Reset Request - {settings.PROJECT_NAME}"
            body = (
                f"Hello,\n\n"
                f"A password reset was requested for your account ({to_email}).\n"
                f"Please use the following link to reset your password within {settings.PASSWORD_RESET_TOKEN_EXPIRE_MINUTES} minutes:\n\n"
                f"{reset_url}\n\n"
                f"If you did not request this, please ignore this email.\n"
            )
            return EmailService._send_smtp_email(to_email, subject, body)

        logger.error("Unsupported EMAIL_BACKEND configured; email not sent.")
        return False

    @staticmethod
    def send_account_invitation_email(to_email: str, activation_token: str) -> bool:
        activate_url = f"{settings.FRONTEND_URL}/activate?token={activation_token}"
        backend = settings.EMAIL_BACKEND.strip().lower()
        if backend == "console":
            # Developer console backend: explicitly permitted to display link for local testing
            print(f"\n[DEV CONSOLE EMAIL] Account activation link for {to_email}: {activate_url}\n")
            logger.info("Dev console account invitation email emitted.")
            return True

        if backend == "smtp":
            subject = f"Activate your {settings.PROJECT_NAME} account"
            body = (
                f"Hello,\n\n"
                f"Please use the following link to activate your {settings.PROJECT_NAME} account:\n\n"
                f"{activate_url}\n\n"
                f"If you did not create this account, you can ignore this email.\n"
            )
            return EmailService._send_smtp_email(to_email, subject, body)

        logger.error("Unsupported EMAIL_BACKEND configured; email not sent.")
        return False

    @staticmethod
    def _close_smtp_server(server) -> None:
        try:
            server.close()
        except (OSError, smtplib.SMTPException) as exc:
            logger.warning(
                "SMTP connection cleanup failed (%s).",
                type(exc).__name__,
            )

    @staticmethod
    def _send_smtp_email(to_email: str, subject: str, text_body: str) -> bool:
        if not settings.SMTP_HOST or not settings.EMAILS_FROM_EMAIL:
            logger.error("SMTP_HOST and EMAILS_FROM_EMAIL must be configured. Email not sent.")
            return False

        if settings.SMTP_HOST.lower() == "smtp.gmail.com" and not (
            settings.SMTP_USER and settings.SMTP_PASSWORD
        ):
            logger.error("Gmail SMTP requires SMTP_USER and SMTP_PASSWORD. Email not sent.")
            return False

        msg = MIMEMultipart()
        msg["From"] = settings.EMAILS_FROM_EMAIL
        msg["To"] = to_email
        msg["Subject"] = subject
        msg.attach(MIMEText(text_body, "plain"))

        for attempt in range(2):
            server = None
            try:
                server = smtplib.SMTP(
                    settings.SMTP_HOST,
                    settings.SMTP_PORT,
                    timeout=10,
                )
                server.ehlo()
                if settings.SMTP_TLS:
                    server.starttls(context=ssl.create_default_context())
                    server.ehlo()
                if settings.SMTP_USER and settings.SMTP_PASSWORD:
                    server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            except (OSError, smtplib.SMTPServerDisconnected) as exc:
                if server is not None:
                    EmailService._close_smtp_server(server)
                if attempt == 0:
                    logger.warning(
                        "SMTP connection failed before message submission "
                        "(%s); retrying once.",
                        type(exc).__name__,
                    )
                    continue
                logger.error(
                    "SMTP connection failed before message submission (%s).",
                    type(exc).__name__,
                )
                return False
            except smtplib.SMTPException as exc:
                if server is not None:
                    EmailService._close_smtp_server(server)
                logger.error(
                    "SMTP setup failed before message submission (%s).",
                    type(exc).__name__,
                )
                return False

            try:
                refused = server.send_message(
                    msg,
                    from_addr=settings.EMAILS_FROM_EMAIL,
                    to_addrs=[to_email],
                )
            except (OSError, smtplib.SMTPException) as exc:
                logger.error(
                    "SMTP delivery failed after submission began (%s); "
                    "delivery outcome may be unknown.",
                    type(exc).__name__,
                )
                return False
            finally:
                EmailService._close_smtp_server(server)

            if refused:
                logger.error("SMTP server refused one or more recipients.")
                return False
            return True

        return False
