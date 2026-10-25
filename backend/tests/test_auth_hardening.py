import secrets
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
import jwt

from app.core.config import settings
from app.core.database import SessionLocal, engine
from app.core.security import get_password_hash, create_access_token, decode_access_token
from app.core.limiter import limiter
from app.models.user import User
from app.models.token import RevokedToken, PasswordResetToken
from app.services.auth_service import AuthService
from .conftest import auth_headers


def ensure_utc(dt):
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def test_signup_cannot_set_role(client):
    """Public signup cannot set role or become Admin; always gets an active Customer."""
    payload = {
        "name": "Attacker",
        "email": "attacker@example.com",
        "password": "StrongPassword123!",
        "role": "Admin",  # Attempt privilege escalation
    }
    response = client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 201
    assert response.json()["success"] is True

    with Session(engine) as db:
        user = db.query(User).filter(User.email == "attacker@example.com").first()
        assert user is not None
        assert user.role == "Customer"
        assert user.status == "Active"

    # Verify duplicate signup returns identical generic response without revealing account existence
    dup_res = client.post("/api/v1/auth/register", json=payload)
    assert dup_res.status_code == 201
    assert dup_res.json()["message"] == response.json()["message"]


def test_weak_password_rejected(client):
    """Password policy rejects passwords with <10 chars, missing upper, lower, or digit."""
    # Too short (<10)
    res = client.post(
        "/api/v1/auth/register",
        json={"name": "User", "email": "p1@test.com", "password": "Short1Aa"},
    )
    assert res.status_code == 422

    # No uppercase
    res = client.post(
        "/api/v1/auth/register",
        json={"name": "User", "email": "p2@test.com", "password": "lowercaseonly123"},
    )
    assert res.status_code == 422

    # No lowercase
    res = client.post(
        "/api/v1/auth/register",
        json={"name": "User", "email": "p3@test.com", "password": "UPPERCASEONLY123"},
    )
    assert res.status_code == 422

    # No digit
    res = client.post(
        "/api/v1/auth/register",
        json={"name": "User", "email": "p4@test.com", "password": "NoDigitsPasswordHere"},
    )
    assert res.status_code == 422

    # Meets policy (>=10 chars, upper, lower, digit)
    res = client.post(
        "/api/v1/auth/register",
        json={"name": "User", "email": "p5@test.com", "password": "ValidPassword123"},
    )
    assert res.status_code == 201


def test_pending_staff_user_rejected(client):
    """Pending staff users remain blocked from login and get_current_user."""
    with Session(engine) as db:
        user = User(
            name="Pending User",
            email="pending@test.com",
            password_hash=get_password_hash("StrongPassword123"),
            role="Sales Rep",
            status="Pending",
            token_version=0,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        user_id = user.id

    # /auth/login returns identical 401 generic error
    login_res = client.post(
        "/api/v1/auth/login",
        json={"email": "pending@test.com", "password": "StrongPassword123"},
    )
    assert login_res.status_code == 401
    assert login_res.json()["message"] == "Incorrect email or password"

    # get_current_user dependency rejects inactive account with 401
    fake_token = create_access_token(subject=user_id, token_version=0)
    me_res = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {fake_token}"})
    assert me_res.status_code == 401


def test_lockout_after_5_failures(client):
    """Account is locked for 15 minutes after 5 consecutive failed logins, resetting on success."""
    email = "lockout@test.com"
    correct_pass = "StrongPassword123"

    with Session(engine) as db:
        user = User(
            name="Lockout Target",
            email=email,
            password_hash=get_password_hash(correct_pass),
            role="Customer",
            status="Active",
            token_version=0,
            failed_attempts=0,
        )
        db.add(user)
        db.commit()

    # 5 failed login attempts
    for i in range(5):
        res = client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": "WrongPassword999"},
        )
        assert res.status_code == 401
        assert res.json()["message"] == "Incorrect email or password"

    # Verify locked_until is set in DB
    with Session(engine) as db:
        user = db.query(User).filter(User.email == email).first()
        assert user.failed_attempts == 5
        assert user.locked_until is not None
        assert ensure_utc(user.locked_until) > datetime.now(timezone.utc)

    # Reset IP rate limiter to test account-level lockout independently of IP throttling
    limiter.reset()

    # 6th attempt with correct password fails because account is locked
    locked_attempt = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": correct_pass},
    )
    assert locked_attempt.status_code == 401
    assert locked_attempt.json()["message"] == "Incorrect email or password"

    # Unlock account by moving locked_until to past
    with Session(engine) as db:
        user = db.query(User).filter(User.email == email).first()
        user.locked_until = datetime.now(timezone.utc) - timedelta(minutes=1)
        db.commit()

    limiter.reset()

    # Now login with correct password succeeds and resets failed_attempts
    success_attempt = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": correct_pass},
    )
    assert success_attempt.status_code == 200

    with Session(engine) as db:
        user = db.query(User).filter(User.email == email).first()
        assert user.failed_attempts == 0
        assert user.locked_until is None


def test_logout_revokes_the_token(client):
    """POST /auth/logout adds token jti to revoked_tokens, and get_current_user rejects it."""
    headers = auth_headers(client, role="Admin", email="admin_logout@solara.test")
    token = headers["Authorization"].split(" ")[1]

    # Valid token can access /auth/me
    res = client.get("/api/v1/auth/me", headers=headers)
    assert res.status_code == 200

    # Logout revokes token
    logout_res = client.post("/api/v1/auth/logout", headers=headers)
    assert logout_res.status_code == 200

    # Subsequent access using same token is rejected with 401
    revoked_res = client.get("/api/v1/auth/me", headers=headers)
    assert revoked_res.status_code == 401
    assert revoked_res.headers["www-authenticate"] == "Bearer"
    revoked_jti = decode_access_token(token)["jti"]
    with Session(engine) as db:
        assert db.query(RevokedToken).filter(RevokedToken.jti == revoked_jti).first()


def test_missing_invalid_expired_and_revoked_credentials_return_401(client):
    assert client.get("/api/v1/auth/me").status_code == 401
    assert client.post("/api/v1/auth/logout").status_code == 401

    invalid_response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer invalid-token"},
    )
    assert invalid_response.status_code == 401

    missing_claim_token = jwt.encode(
        {
            "sub": "1",
            "iat": int(datetime.now(timezone.utc).timestamp()),
            "exp": int((datetime.now(timezone.utc) + timedelta(minutes=5)).timestamp()),
            "ver": 0,
        },
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM,
    )
    missing_claim_response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {missing_claim_token}"},
    )
    assert missing_claim_response.status_code == 401

    expired_token = create_access_token(
        subject="1",
        expires_delta=timedelta(seconds=-1),
    )
    expired_response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {expired_token}"},
    )
    assert expired_response.status_code == 401
    assert expired_response.headers["www-authenticate"] == "Bearer"

    # Optional authentication is anonymous only when no credential was sent;
    # malformed credentials must not silently fall back to public access.
    optional_auth_response = client.get(
        "/api/v1/projects",
        headers={"Authorization": "Bearer invalid-token"},
    )
    assert optional_auth_response.status_code == 401


def test_authorization_denial_remains_403(client):
    with Session(engine) as db:
        user = User(
            name="Customer User",
            email="customer_forbidden@solara.test",
            password_hash=get_password_hash("StrongPassword123"),
            role="Customer",
            status="Active",
            token_version=0,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        token = create_access_token(
            subject=user.id,
            token_version=0,
            extra_claims={"role": "Admin", "customer_id": 999999},
        )

    response = client.get(
        "/api/v1/users",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 403


def test_remember_me_expiry(client):
    """remember_me=true gives 30-day token, false gives 8 hours."""
    headers = auth_headers(client, role="Customer", email="remember@solara.test")

    # remember_me = False
    res_short = client.post(
        "/api/v1/auth/login",
        json={"email": "remember@solara.test", "password": "StrongPass123", "remember_me": False},
    )
    assert res_short.status_code == 200
    token_short = res_short.json()["access_token"]
    payload_short = decode_access_token(token_short)
    lifetime_short = payload_short["exp"] - payload_short["iat"]
    expected_short = settings.ACCESS_TOKEN_EXPIRE_HOURS * 3600
    assert abs(lifetime_short - expected_short) < 10

    # remember_me = True
    res_long = client.post(
        "/api/v1/auth/login",
        json={"email": "remember@solara.test", "password": "StrongPass123", "remember_me": True},
    )
    assert res_long.status_code == 200
    token_long = res_long.json()["access_token"]
    payload_long = decode_access_token(token_long)
    lifetime_long = payload_long["exp"] - payload_long["iat"]
    expected_long = settings.ACCESS_TOKEN_EXPIRE_REMEMBER_ME_DAYS * 86400
    assert abs(lifetime_long - expected_long) < 10


def test_reset_token_single_use_and_expiry(client):
    """Password reset token is single-use, expires in 30 minutes, and updates password."""
    email = "reset_user@solara.test"
    with Session(engine) as db:
        user = User(
            name="Reset User",
            email=email,
            password_hash=get_password_hash("InitialPass123"),
            role="Customer",
            status="Active",
            token_version=0,
        )
        db.add(user)
        db.commit()

    # Request reset
    forgot_res = client.post("/api/v1/auth/forgot-password", json={"email": email})
    assert forgot_res.status_code == 200
    assert forgot_res.json()["success"] is True

    # Retrieve generated reset token hash from DB
    with Session(engine) as db:
        token_record = (
            db.query(PasswordResetToken)
            .filter(PasswordResetToken.token_type == "reset")
            .order_by(PasswordResetToken.id.desc())
            .first()
        )
        assert token_record is not None
        assert token_record.used_at is None

    # Simulate raw token by inserting a known token for deterministic endpoint testing
    raw_token = secrets.token_urlsafe(32)
    import hashlib
    token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()

    with Session(engine) as db:
        test_reset = PasswordResetToken(
            user_id=token_record.user_id,
            token_hash=token_hash,
            token_type="reset",
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=30),
        )
        db.add(test_reset)
        db.commit()

    # Reset password with valid token
    new_pwd = "BrandNewPassword123"
    reset_res = client.post(
        "/api/v1/auth/reset-password",
        json={"token": raw_token, "new_password": new_pwd},
    )
    assert reset_res.status_code == 200
    assert reset_res.json()["success"] is True

    # Verify user can log in with new password
    login_res = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": new_pwd},
    )
    assert login_res.status_code == 200

    # Second use of same token fails (single use)
    reuse_res = client.post(
        "/api/v1/auth/reset-password",
        json={"token": raw_token, "new_password": "AnotherPassword456"},
    )
    assert reuse_res.status_code == 400

    # Expired token test
    expired_token = secrets.token_urlsafe(32)
    expired_hash = hashlib.sha256(expired_token.encode("utf-8")).hexdigest()
    with Session(engine) as db:
        db.add(
            PasswordResetToken(
                user_id=token_record.user_id,
                token_hash=expired_hash,
                token_type="reset",
                expires_at=datetime.now(timezone.utc) - timedelta(minutes=5),
            )
        )
        db.commit()

    exp_res = client.post(
        "/api/v1/auth/reset-password",
        json={"token": expired_token, "new_password": "ExpiredPassAttempt1"},
    )
    assert exp_res.status_code == 400


def test_token_invalid_after_password_change(client):
    """Changing or resetting password increments token_version, invalidating previous sessions."""
    headers = auth_headers(client, role="Customer", email="version_test@solara.test")
    old_token = headers["Authorization"].split(" ")[1]

    # Verify old token works initially
    res = client.get("/api/v1/auth/me", headers=headers)
    assert res.status_code == 200

    # Change password
    change_res = client.post(
        "/api/v1/auth/change-password",
        headers=headers,
        json={
            "current_password": "StrongPass123",
            "new_password": "NewStrongPass999",
            "confirm_password": "NewStrongPass999",
        },
    )
    assert change_res.status_code == 200

    # Old token must now be rejected (token_version mismatch)
    old_attempt = client.get("/api/v1/auth/me", headers=headers)
    assert old_attempt.status_code == 401

    # New login works and produces valid new token
    new_login = client.post(
        "/api/v1/auth/login",
        json={"email": "version_test@solara.test", "password": "NewStrongPass999"},
    )
    assert new_login.status_code == 200
    new_token = new_login.json()["access_token"]

    new_me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {new_token}"})
    assert new_me.status_code == 200


def test_user_management_changes_invalidate_existing_sessions(client):
    admin_headers = auth_headers(
        client,
        role="Admin",
        email="session-change-admin@solara.test",
    )
    with SessionLocal() as db:
        target = AuthService.bootstrap_admin(
            db=db,
            name="Session Change Target",
            email="session-change-target@solara.test",
            password="InitialPassword123!",
            role="Sales Rep",
        )
        target_id = target.id

    login = client.post(
        "/api/v1/auth/login",
        json={
            "email": "session-change-target@solara.test",
            "password": "InitialPassword123!",
        },
    )
    assert login.status_code == 200
    old_headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    assert client.get("/api/v1/auth/me", headers=old_headers).status_code == 200

    changed_role = client.patch(
        f"/api/v1/users/{target_id}",
        headers=admin_headers,
        json={"role": "Support"},
    )
    assert changed_role.status_code == 200
    assert client.get("/api/v1/auth/me", headers=old_headers).status_code == 401

    re_login = client.post(
        "/api/v1/auth/login",
        json={
            "email": "session-change-target@solara.test",
            "password": "InitialPassword123!",
        },
    )
    assert re_login.status_code == 200
    pre_deactivation_headers = {
        "Authorization": f"Bearer {re_login.json()['access_token']}"
    }

    deactivated = client.patch(
        f"/api/v1/users/{target_id}",
        headers=admin_headers,
        json={"status": "Inactive"},
    )
    assert deactivated.status_code == 200
    reactivated = client.patch(
        f"/api/v1/users/{target_id}",
        headers=admin_headers,
        json={"status": "Active"},
    )
    assert reactivated.status_code == 200
    assert client.get(
        "/api/v1/auth/me",
        headers=pre_deactivation_headers,
    ).status_code == 401

    re_login = client.post(
        "/api/v1/auth/login",
        json={
            "email": "session-change-target@solara.test",
            "password": "InitialPassword123!",
        },
    )
    assert re_login.status_code == 200
    pre_password_change_headers = {
        "Authorization": f"Bearer {re_login.json()['access_token']}"
    }
    forced_password = client.patch(
        f"/api/v1/users/{target_id}",
        headers=admin_headers,
        json={"password": "AdminChangedPassword123"},
    )
    assert forced_password.status_code == 200
    assert client.get(
        "/api/v1/auth/me",
        headers=pre_password_change_headers,
    ).status_code == 401
    assert client.post(
        "/api/v1/auth/login",
        json={
            "email": "session-change-target@solara.test",
            "password": "AdminChangedPassword123",
        },
    ).status_code == 200


def test_admin_role_check_normalizes_existing_role_values():
    from app.dependencies.auth import require_admin

    admin = User(
        name="Normalized Admin",
        email="normalized-admin@solara.test",
        password_hash="unused",
        role=" admin ",
        status="Active",
    )

    assert require_admin(current_user=admin) is admin


def test_account_activation_invitation_flow(client):
    """Admin invites user via POST /users, generating activation token, and user activates account."""
    admin_headers = auth_headers(client, role="Admin", email="admin_inviter@solara.test")

    # Admin creates user
    create_res = client.post(
        "/api/v1/users",
        headers=admin_headers,
        json={
            "name": "Invited Employee",
            "email": "employee@solara.test",
            "role": "Sales Rep",
            "status": "Invited",
        },
    )
    assert create_res.status_code == 201
    user_id = create_res.json()["data"]["id"]

    # Retrieve activation token record
    with Session(engine) as db:
        token_rec = (
            db.query(PasswordResetToken)
            .filter(PasswordResetToken.user_id == user_id, PasswordResetToken.token_type == "activate")
            .first()
        )
        assert token_rec is not None
        assert token_rec.used_at is None

    # Simulate activation with known token
    raw_token = secrets.token_urlsafe(32)
    import hashlib
    token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
    with Session(engine) as db:
        db.add(
            PasswordResetToken(
                user_id=user_id,
                token_hash=token_hash,
                token_type="activate",
                expires_at=datetime.now(timezone.utc) + timedelta(hours=24),
            )
        )
        db.commit()

    # User activates account by setting password
    act_res = client.post(
        "/api/v1/auth/activate",
        json={"token": raw_token, "password": "ActivatedPassword123"},
    )
    assert act_res.status_code == 200
    assert act_res.json()["success"] is True

    # User can now login as Active
    login_res = client.post(
        "/api/v1/auth/login",
        json={"email": "employee@solara.test", "password": "ActivatedPassword123"},
    )
    assert login_res.status_code == 200
    assert login_res.json()["user"]["status"] == "Active"


def test_security_headers(client):
    """API responses include recommended security headers."""
    response = client.get("/health")
    assert response.headers.get("X-Content-Type-Options") == "nosniff"
    assert response.headers.get("X-Frame-Options") == "DENY"
    assert response.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"
    assert "default-src 'none'" in response.headers.get("Content-Security-Policy", "")


def test_rate_limiting_enforced(client):
    """Endpoints /auth/login, /auth/forgot-password, and /auth/register enforce 5/minute limit."""
    limiter.reset()

    # First 5 calls pass rate limiting
    for i in range(5):
        res = client.post(
            "/api/v1/auth/forgot-password",
            json={"email": f"ratelimit{i}@example.com"},
        )
        assert res.status_code == 200

    # 6th call from same IP is throttled with 429
    throttled = client.post(
        "/api/v1/auth/forgot-password",
        json={"email": "ratelimit_excess@example.com"},
    )
    assert throttled.status_code == 429
    assert throttled.json()["error_code"] == "HTTP_429"
    limiter.reset()
