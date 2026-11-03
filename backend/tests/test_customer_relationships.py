from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.core.database import engine
from app.core.security import get_password_hash, hash_token
from app.models.customer import Customer
from app.models.token import PasswordResetToken
from app.models.user import User
from tests.conftest import auth_headers


def make_customer(email):
    return Customer(
        name="Existing CRM Customer",
        contact=email,
        email=email,
        location="Pune",
        property_type="Residential",
        status="Active",
    )


def test_signup_does_not_link_existing_customer_by_email(client, monkeypatch):
    monkeypatch.setattr(
        "app.services.email_service.EmailService.send_account_invitation_email",
        lambda to_email, token: True,
    )
    with Session(engine) as db:
        existing_customer = make_customer("signup-existing@example.com")
        db.add(existing_customer)
        db.commit()
        existing_customer_id = existing_customer.id

    response = client.post(
        "/api/v1/auth/register",
        json={
            "name": "New Account",
            "email": "signup-existing@example.com",
            "password": "StrongPassword123",
        },
    )

    assert response.status_code == 201
    with Session(engine) as db:
        user = db.query(User).filter_by(email="signup-existing@example.com").one()
        assert user.customer_id != existing_customer_id
        assert db.query(Customer).filter_by(id=existing_customer_id).one().account_user_id is None
        if user.customer_id:
            assert db.query(Customer).filter_by(id=user.customer_id).one().account_user_id is None


def test_activation_does_not_link_existing_customer_by_email(client):
    activation_token = "existing-customer-activation-token"
    with Session(engine) as db:
        existing_customer = make_customer("legacy-existing@example.com")
        db.add(existing_customer)
        db.flush()
        existing_customer_id = existing_customer.id

        user = User(
            name="Legacy Account",
            email="legacy-existing@example.com",
            password_hash=get_password_hash("TemporaryPassword123"),
            role="Customer",
            status="Pending",
            customer_id=None,
        )
        db.add(user)
        db.flush()
        db.add(
            PasswordResetToken(
                user_id=user.id,
                token_hash=hash_token(activation_token),
                token_type="activate",
                expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
            )
        )
        db.commit()
        user_id = user.id

    response = client.post(
        "/api/v1/auth/activate",
        json={
            "token": activation_token,
            "password": "NewStrongPassword123",
        },
    )

    assert response.status_code == 200
    with Session(engine) as db:
        user = db.query(User).filter_by(id=user_id).one()
        assert user.customer_id != existing_customer_id
        assert db.query(Customer).filter_by(id=existing_customer_id).one().account_user_id is None


def test_customer_backfill_creates_record_instead_of_email_matching(client):
    admin_headers = auth_headers(
        client,
        role="Admin",
        email="customer-backfill-admin@solara.test",
    )
    with Session(engine) as db:
        existing_customer = make_customer("backfill-existing@example.com")
        db.add(existing_customer)
        user = User(
            name="Unlinked Customer Account",
            email="backfill-existing@example.com",
            password_hash=get_password_hash("StrongPassword123"),
            role="Customer",
            status="Active",
            customer_id=None,
        )
        db.add(user)
        db.commit()
        existing_customer_id = existing_customer.id
        user_id = user.id

    response = client.post(
        "/api/v1/users/backfill-customers",
        headers=admin_headers,
    )

    assert response.status_code == 200
    assert response.json()["data"]["linked_to_existing"] == 0
    assert response.json()["data"]["created_new_customer"] == 1
    with Session(engine) as db:
        user = db.query(User).filter_by(id=user_id).one()
        assert user.customer_id != existing_customer_id
