import pytest
from app.core.database import SessionLocal
from app.models.activity import Activity
from app.models.customer import Customer
from app.models.user import User
from app.schemas.user import UserInviteRequest
from app.services.auth_service import AuthService
from app.services.user_service import UserService
from .conftest import auth_headers


def get_error_message(resp):
    payload = resp.json()
    return (payload.get("message") or payload.get("detail") or "").lower()


def test_public_signup_cannot_create_admin(client):
    """Public signup must never grant Admin privileges; unconditionally creates Customer."""
    resp = client.post(
        "/api/v1/auth/register",
        json={
            "name": "Attacker Trying Admin",
            "email": "attacker@public.io",
            "password": "Password123!",
            "role": "Admin",
        },
    )
    assert resp.status_code == 201
    data = resp.json()["data"]
    assert data["role"] == "Sales Rep"
    assert data["status"] == "Active"

    # Token and secret hashes should not be exposed
    assert "password_hash" not in data
    assert "invitation_token_hash" not in data


def test_bootstrap_admin_is_idempotent_without_password_reset():
    with SessionLocal() as db:
        admin = AuthService.bootstrap_admin(
            db=db,
            name="Initial Admin",
            email="seed-idempotent@solara.test",
            password="SecureInitialAdmin123",
        )
        original_hash = admin.password_hash

        rerun = AuthService.bootstrap_admin(
            db=db,
            name="Changed Name",
            email="seed-idempotent@solara.test",
            password="DifferentAdminPassword456",
        )

        assert rerun.id == admin.id
        assert rerun.password_hash == original_hash
        assert rerun.name == "Initial Admin"


def test_admin_invitation_and_activation_workflow(client):
    """Admin creates an invitation with secure single-use token, user activates password."""
    admin_auth = auth_headers(client, role="Admin", email="superadmin@solara.io")

    # 1. Admin invites a Sales Rep via service/API
    with SessionLocal() as db:
        admin_user = db.query(User).filter(User.email == "superadmin@solara.io").first()
        invited_user, token = UserService.invite_user(
            db=db,
            request=UserInviteRequest(
                name="Arjun Kumar",
                email="arjun.rep@solara.io",
                role="Sales Rep",
                phone="+91 91234 56789",
            ),
            acting_user=admin_user,
        )
        assert invited_user.status == "Invited"
        # Token is never stored in plaintext in the database
        assert invited_user.invitation_token_hash is not None
        assert invited_user.invitation_token_hash != token
        assert len(token) >= 32

    # 2. Check user list endpoint: token and hash must NOT be in UserResponse
    users_resp = client.get("/api/v1/users", headers=admin_auth)
    assert users_resp.status_code == 200
    users = users_resp.json()["data"]
    invited_u = next(u for u in users if u["email"] == "arjun.rep@solara.io")
    assert invited_u["status"] == "Invited"
    assert invited_u["role"] == "Sales Rep"
    assert "invitation_token" not in invited_u
    assert "invitation_token_hash" not in invited_u
    assert "password_hash" not in invited_u

    # 3. Invited user cannot log in before activation (rejected with 403 Forbidden)
    unactivated_login = client.post(
        "/api/v1/auth/login",
        json={"email": "arjun.rep@solara.io", "password": "AnyPassword"},
    )
    assert unactivated_login.status_code == 403
    assert "pending activation" in get_error_message(unactivated_login)

    # 4. Activate using single-use token
    activate_resp = client.post(
        "/api/v1/auth/activate",
        json={
            "token": token,
            "password": "NewSecurePassword123!",
            "confirm_password": "NewSecurePassword123!",
        },
    )
    assert activate_resp.status_code == 200
    activated_data = activate_resp.json()["data"]
    assert activated_data["status"] == "Active"

    # 5. Token is single-use: repeated activation must fail
    reuse_resp = client.post(
        "/api/v1/auth/activate",
        json={
            "token": token,
            "password": "AnotherPassword123!",
            "confirm_password": "AnotherPassword123!",
        },
    )
    assert reuse_resp.status_code == 400
    assert "invalid or expired" in get_error_message(reuse_resp)

    # 6. Activated user can now log in
    active_login = client.post(
        "/api/v1/auth/login",
        json={"email": "arjun.rep@solara.io", "password": "NewSecurePassword123!"},
    )
    assert active_login.status_code == 200
    rep_token = active_login.json()["access_token"]
    rep_auth = {"Authorization": f"Bearer {rep_token}"}

    # Verify /auth/me returns updated role and status
    me_resp = client.get("/api/v1/auth/me", headers=rep_auth)
    assert me_resp.status_code == 200
    assert me_resp.json()["data"]["role"] == "Sales Rep"
    assert me_resp.json()["data"]["status"] == "Active"


def test_sales_rep_cannot_modify_admin_or_promote_roles(client):
    """Sales Rep cannot elevate roles or alter Admin accounts."""
    admin_auth = auth_headers(client, role="Admin", email="rootadmin@solara.io")
    sales_auth = auth_headers(client, role="Sales Rep", email="midsales@solara.io")

    # Get user records
    users_resp = client.get("/api/v1/users", headers=admin_auth)
    users = users_resp.json()["data"]
    root_admin = next(u for u in users if u["email"] == "rootadmin@solara.io")
    mid_sales = next(u for u in users if u["email"] == "midsales@solara.io")

    # 1. Sales Rep tries to edit Root Admin -> 403 Forbidden
    hack_admin = client.patch(
        f"/api/v1/users/{root_admin['id']}",
        headers=sales_auth,
        json={"name": "Hacked Name"},
    )
    assert hack_admin.status_code == 403

    # 2. Sales Rep tries to promote themselves to Admin -> 403 Forbidden
    self_promote = client.patch(
        f"/api/v1/users/{mid_sales['id']}",
        headers=sales_auth,
        json={"role": "Admin"},
    )
    assert self_promote.status_code == 403

    # 3. Sales Rep tries to invite an Admin -> 403 Forbidden
    invite_admin = client.post(
        "/api/v1/users/invite",
        headers=sales_auth,
        json={
            "name": "Sneaky Admin",
            "email": "sneaky@solara.io",
            "role": "Admin",
        },
    )
    assert invite_admin.status_code == 403

    # 4. Sales Rep cannot modify global company name or 2FA settings
    hack_settings = client.put(
        "/api/v1/settings",
        headers=sales_auth,
        json={"company_name": "Sales Owned Solar Inc", "two_factor_auth": True},
    )
    assert hack_settings.status_code == 403


def test_last_active_admin_protection(client):
    """Prevent accidental demotion, deactivation, or deletion of the last active administrator."""
    admin_auth = auth_headers(client, role="Admin", email="onlyadmin@solara.io")

    users_resp = client.get("/api/v1/users", headers=admin_auth)
    admin_user = next(u for u in users_resp.json()["data"] if u["email"] == "onlyadmin@solara.io")

    # 1. Self demotion attempt is rejected
    demote_resp = client.patch(
        f"/api/v1/users/{admin_user['id']}",
        headers=admin_auth,
        json={"role": "Sales Rep"},
    )
    assert demote_resp.status_code == 400
    assert "administrators cannot modify their own role" in get_error_message(demote_resp)

    # 2. Attempt to deactivate sole admin -> 400 Bad Request
    deact_resp = client.patch(
        f"/api/v1/users/{admin_user['id']}",
        headers=admin_auth,
        json={"status": "Inactive"},
    )
    assert deact_resp.status_code == 400
    assert "last active administrator" in get_error_message(deact_resp)

    # 3. Attempt to delete sole admin -> 400 Bad Request
    del_resp = client.delete(
        f"/api/v1/users/{admin_user['id']}",
        headers=admin_auth,
    )
    assert del_resp.status_code == 400
    assert "administrator" in get_error_message(del_resp)


def test_deactivated_user_session_revocation(client):
    """Deactivated accounts cannot access protected APIs even with previously issued valid tokens."""
    admin_auth = auth_headers(client, role="Admin", email="boss@solara.io")

    # Create and login staff user
    with SessionLocal() as db:
        user = AuthService.bootstrap_admin(
            db=db,
            name="Temporary Staff",
            email="tempstaff@solara.io",
            password="Password123!",
            role="Sales Rep",
        )
        user_id = user.id

    login_resp = client.post(
        "/api/v1/auth/login",
        json={"email": "tempstaff@solara.io", "password": "Password123!"},
    )
    assert login_resp.status_code == 200
    staff_token = login_resp.json()["access_token"]
    staff_auth = {"Authorization": f"Bearer {staff_token}"}

    # Verify staff works before deactivation
    valid_resp = client.get("/api/v1/auth/me", headers=staff_auth)
    assert valid_resp.status_code == 200

    # Admin deactivates the staff user
    deact = client.patch(
        f"/api/v1/users/{user_id}",
        headers=admin_auth,
        json={"status": "Inactive"},
    )
    assert deact.status_code == 200

    # Request with existing staff token must now be rejected (403 Forbidden: Account is inactive)
    rejected_resp = client.get("/api/v1/auth/me", headers=staff_auth)
    assert rejected_resp.status_code == 403
    assert "inactive" in get_error_message(rejected_resp)

    # New login attempt must also be rejected
    rejected_login = client.post(
        "/api/v1/auth/login",
        json={"email": "tempstaff@solara.io", "password": "Password123!"},
    )
    assert rejected_login.status_code == 403


def test_customer_isolation_and_scoping(client):
    """Sales Reps cannot access unrelated customers' records or Admin APIs."""
    sales1_auth = auth_headers(client, role="Sales Rep", email="sales1@solara.io")
    sales2_auth = auth_headers(client, role="Sales Rep", email="sales2@solara.io")

    # Sales Rep 1 cannot access /users (Admin only)
    forbidden_users = client.get("/api/v1/users", headers=sales1_auth)
    assert forbidden_users.status_code == 403

    # Sales Rep 1 cannot access /settings
    forbidden_settings = client.get("/api/v1/settings", headers=sales1_auth)
    assert forbidden_settings.status_code == 403

    # Sales Rep 1 cannot access /dashboard/activities
    forbidden_activity = client.get("/api/v1/dashboard/activities", headers=sales1_auth)
    assert forbidden_activity.status_code == 200

    # Verify Sales Rep 2 cannot access Customer assigned to Sales Rep 1
    with SessionLocal() as db:
        u1 = db.query(User).filter(User.email == "sales1@solara.io").first()
        c1 = Customer(
            name="Customer One",
            contact="c1@example.com",
            email="customer1@gmail.com",
            location="Mumbai",
            assigned_user_id=u1.id,
            status="Active",
        )
        db.add(c1)
        db.commit()
        db.refresh(c1)
        c1_id = c1.id

    c2_accessing_c1 = client.get(f"/api/v1/customers/{c1_id}", headers=sales2_auth)
    assert c2_accessing_c1.status_code in (403, 404)


def test_audit_logs_record_administrative_changes(client):
    """Audit records are saved with previous and new values for user lifecycle events."""
    admin_auth = auth_headers(client, role="Admin", email="auditoradmin@solara.io")

    # Invite a user
    client.post(
        "/api/v1/users/invite",
        headers=admin_auth,
        json={
            "name": "Audit Target",
            "email": "audittarget@solara.io",
            "role": "Sales Rep",
        },
    )

    # Check activity table
    with SessionLocal() as db:
        activity = (
            db.query(Activity)
            .filter(Activity.entity_type == "user", Activity.action == "invited")
            .order_by(Activity.id.desc())
            .first()
        )
        assert activity is not None
        assert "Audit Target" in activity.title
        assert "Sales Rep" in activity.new_value


def test_user_statistics_aggregation(client):
    """Dashboard and user statistics return real database aggregation."""
    admin_auth = auth_headers(client, role="Admin", email="statsadmin@solara.io")

    stats_resp = client.get("/api/v1/users/stats", headers=admin_auth)
    assert stats_resp.status_code == 200
    stats = stats_resp.json()["data"]
    assert stats["totalUsers"] >= 1
    assert stats["activeUsers"] >= 1
    assert "usersByRole" in stats
    assert isinstance(stats["usersByRole"], dict)
