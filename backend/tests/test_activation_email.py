from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.core.database import engine
from app.models.token import PasswordResetToken
from app.models.user import User
from tests.conftest import auth_headers


def test_signup_sends_activation_email_and_activates_account(client, monkeypatch):
    sent_emails = []

    def capture_activation_email(to_email, token):
        sent_emails.append((to_email, token))
        return True

    monkeypatch.setattr(
        "app.routers.auth.EmailService.send_account_invitation_email",
        capture_activation_email,
    )
    signup = client.post(
        "/api/v1/auth/register",
        json={
            "name": "Activation Customer",
            "email": "activation@example.com",
            "password": "StrongPassword123",
        },
    )

    assert signup.status_code == 201
    assert "activation link" in signup.json()["message"].lower()
    assert len(sent_emails) == 1
    assert sent_emails[0][0] == "activation@example.com"

    with Session(engine) as db:
        user = db.query(User).filter_by(email="activation@example.com").one()
        activation = (
            db.query(PasswordResetToken)
            .filter_by(user_id=user.id, token_type="activate")
            .one()
        )
        assert user.status == "Pending"
        assert activation.token_hash != sent_emails[0][1]

    activated = client.post(
        "/api/v1/auth/activate",
        json={
            "token": sent_emails[0][1],
            "password": "NewStrongPassword123",
            "confirm_password": "NewStrongPassword123",
        },
    )

    assert activated.status_code == 200
    with Session(engine) as db:
        user = db.query(User).filter_by(email="activation@example.com").one()
        assert user.status == "Active"


def test_repeated_pending_signup_does_not_replace_or_resend_valid_token(
    client,
    monkeypatch,
):
    sent_tokens = []

    def capture_activation_email(to_email, token):
        sent_tokens.append(token)
        return True

    monkeypatch.setattr(
        "app.routers.auth.EmailService.send_account_invitation_email",
        capture_activation_email,
    )
    payload = {
        "name": "Single Invitation Customer",
        "email": "single-invitation@example.com",
        "password": "StrongPassword123",
    }

    first_signup = client.post("/api/v1/auth/register", json=payload)
    repeated_signup = client.post("/api/v1/auth/register", json=payload)

    assert first_signup.status_code == repeated_signup.status_code == 201
    assert len(sent_tokens) == 1
    activated = client.post(
        "/api/v1/auth/activate",
        json={"token": sent_tokens[0], "password": "NewStrongPassword123"},
    )
    assert activated.status_code == 200


def test_signup_only_reissues_activation_after_existing_token_expires(
    client,
    monkeypatch,
):
    payload = {
        "name": "Retry Customer",
        "email": "retry-activation@example.com",
        "password": "StrongPassword123",
    }
    sent_tokens = []

    def fail_delivery(to_email, token):
        sent_tokens.append(token)
        return False

    monkeypatch.setattr(
        "app.routers.auth.EmailService.send_account_invitation_email",
        fail_delivery,
    )
    failed_signup = client.post("/api/v1/auth/register", json=payload)
    assert failed_signup.status_code == 503
    assert failed_signup.json()["success"] is False

    def capture_retry(to_email, token):
        sent_tokens.append(token)
        return True

    monkeypatch.setattr(
        "app.routers.auth.EmailService.send_account_invitation_email",
        capture_retry,
    )
    duplicate_signup = client.post("/api/v1/auth/register", json=payload)
    assert duplicate_signup.status_code == 201
    assert len(sent_tokens) == 1

    with Session(engine) as db:
        user = db.query(User).filter_by(email=payload["email"]).one()
        activation = (
            db.query(PasswordResetToken)
            .filter_by(user_id=user.id, token_type="activate")
            .one()
        )
        activation.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
        db.commit()

    retried_signup = client.post("/api/v1/auth/register", json=payload)

    assert retried_signup.status_code == 201
    assert len(sent_tokens) == 2
    assert sent_tokens[0] != sent_tokens[1]

    expired_link = client.post(
        "/api/v1/auth/activate",
        json={"token": sent_tokens[0], "password": "NewStrongPassword123"},
    )
    assert expired_link.status_code == 400

    valid_link = client.post(
        "/api/v1/auth/activate",
        json={"token": sent_tokens[1], "password": "NewStrongPassword123"},
    )
    assert valid_link.status_code == 200


def test_admin_invitation_sends_activation_email(client, monkeypatch):
    sent_emails = []
    admin_headers = auth_headers(
        client,
        role="Admin",
        email="activation-admin@solara.test",
    )

    def capture_activation_email(to_email, token):
        sent_emails.append((to_email, token))
        return True

    monkeypatch.setattr(
        "app.routers.users.EmailService.send_account_invitation_email",
        capture_activation_email,
    )
    invitation = client.post(
        "/api/v1/users/invite",
        headers=admin_headers,
        json={
            "name": "Invited Staff",
            "email": "invited-staff@example.com",
            "role": "Sales Rep",
        },
    )

    assert invitation.status_code == 201
    assert invitation.json()["message"] == (
        "User invitation created and activation email sent successfully."
    )
    assert sent_emails[0][0] == "invited-staff@example.com"
    activated = client.post(
        "/api/v1/auth/activate",
        json={
            "token": sent_emails[0][1],
            "password": "NewStrongPassword123",
        },
    )
    assert activated.status_code == 200


def test_admin_cannot_create_duplicate_unexpired_invitation(client, monkeypatch):
    sent_tokens = []
    admin_headers = auth_headers(
        client,
        role="Admin",
        email="duplicate-invitation-admin@solara.test",
    )
    monkeypatch.setattr(
        "app.routers.users.EmailService.send_account_invitation_email",
        lambda email, token: sent_tokens.append(token) or True,
    )
    payload = {
        "name": "Single Invitation Staff",
        "email": "single-invitation-staff@example.com",
        "role": "Sales Rep",
    }

    first_invitation = client.post(
        "/api/v1/users/invite",
        headers=admin_headers,
        json=payload,
    )
    duplicate_invitation = client.post(
        "/api/v1/users/invite",
        headers=admin_headers,
        json=payload,
    )

    assert first_invitation.status_code == 201
    assert duplicate_invitation.status_code == 409
    assert len(sent_tokens) == 1
    activated = client.post(
        "/api/v1/auth/activate",
        json={"token": sent_tokens[0], "password": "NewStrongPassword123"},
    )
    assert activated.status_code == 200


def test_gmail_smtp_delivery_uses_starttls_and_authentication(monkeypatch):
    from app.core.config import settings
    from app.services.email_service import EmailService

    calls = []

    class FakeSMTP:
        def __init__(self, host, port, timeout):
            calls.append(("connect", host, port, timeout))

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_value, traceback):
            return False

        def ehlo(self):
            calls.append(("ehlo",))

        def starttls(self, context):
            calls.append(("starttls", context))

        def login(self, username, password):
            calls.append(("login", username, password))

        def send_message(self, message, from_addr, to_addrs):
            calls.append(("send", message["To"], from_addr, to_addrs))

        def close(self):
            calls.append(("close",))

    monkeypatch.setattr("app.services.email_service.smtplib.SMTP", FakeSMTP)
    monkeypatch.setattr(settings, "SMTP_HOST", "smtp.gmail.com")
    monkeypatch.setattr(settings, "SMTP_PORT", 587)
    monkeypatch.setattr(settings, "SMTP_TLS", True)
    monkeypatch.setattr(settings, "SMTP_USER", "sender@gmail.com")
    monkeypatch.setattr(settings, "SMTP_PASSWORD", "app-password")
    monkeypatch.setattr(settings, "EMAILS_FROM_EMAIL", "sender@gmail.com")

    assert EmailService._send_smtp_email(
        "recipient@example.com",
        "Activate account",
        "Use the activation link.",
    )
    assert calls[0] == ("connect", "smtp.gmail.com", 587, 10)
    assert calls[1] == ("ehlo",)
    assert calls[2][0] == "starttls"
    assert ("login", "sender@gmail.com", "app-password") in calls
    assert (
        "send",
        "recipient@example.com",
        "sender@gmail.com",
        ["recipient@example.com"],
    ) in calls


def test_smtp_retries_connection_failure_before_submission(monkeypatch, caplog):
    from app.core.config import settings
    from app.services.email_service import EmailService

    attempts = []

    class FakeSMTP:
        def __init__(self, host, port, timeout):
            attempts.append(self)
            if len(attempts) == 1:
                raise TimeoutError("private host and credential details")

        def ehlo(self):
            pass

        def starttls(self, context):
            pass

        def send_message(self, message, from_addr, to_addrs):
            return {}

        def close(self):
            pass

    monkeypatch.setattr("app.services.email_service.smtplib.SMTP", FakeSMTP)
    monkeypatch.setattr(settings, "SMTP_HOST", "smtp.example.test")
    monkeypatch.setattr(settings, "SMTP_TLS", False)
    monkeypatch.setattr(settings, "SMTP_USER", None)
    monkeypatch.setattr(settings, "SMTP_PASSWORD", None)
    monkeypatch.setattr(settings, "EMAILS_FROM_EMAIL", "sender@example.test")

    assert EmailService._send_smtp_email(
        "recipient@example.test",
        "Subject",
        "Body",
    )
    assert len(attempts) == 2
    assert "private host" not in caplog.text
    assert "credential details" not in caplog.text
    assert "recipient@example.test" not in caplog.text


def test_smtp_does_not_retry_ambiguous_submission_failure(monkeypatch, caplog):
    from app.core.config import settings
    from app.services.email_service import EmailService

    attempts = []

    class FakeSMTP:
        def __init__(self, host, port, timeout):
            attempts.append(self)

        def ehlo(self):
            pass

        def starttls(self, context):
            pass

        def send_message(self, message, from_addr, to_addrs):
            raise TimeoutError("private message and token details")

        def close(self):
            pass

    monkeypatch.setattr("app.services.email_service.smtplib.SMTP", FakeSMTP)
    monkeypatch.setattr(settings, "SMTP_HOST", "smtp.example.test")
    monkeypatch.setattr(settings, "SMTP_TLS", False)
    monkeypatch.setattr(settings, "SMTP_USER", None)
    monkeypatch.setattr(settings, "SMTP_PASSWORD", None)
    monkeypatch.setattr(settings, "EMAILS_FROM_EMAIL", "sender@example.test")

    assert not EmailService._send_smtp_email(
        "private-recipient@example.test",
        "Subject",
        "private-token",
    )
    assert len(attempts) == 1
    assert "private message" not in caplog.text
    assert "private-token" not in caplog.text
    assert "private-recipient@example.test" not in caplog.text
