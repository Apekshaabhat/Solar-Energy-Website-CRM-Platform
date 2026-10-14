import os
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))

os.environ["DATABASE_URL"] = "sqlite:///./.test_solara.db"
os.environ["SECRET_KEY"] = "test-secret-key-for-solara-api-suite"
os.environ["ACCESS_TOKEN_EXPIRE_MINUTES"] = "60"

from sqlalchemy.orm import Session
from app.core.database import Base, engine  # noqa: E402
from app.core.security import get_password_hash  # noqa: E402
from app.core.limiter import limiter  # noqa: E402
from app.models.user import User  # noqa: E402
from app.core.database import Base, SessionLocal, engine  # noqa: E402
import app.models  # noqa: E402,F401
from app.main import app  # noqa: E402
from app.models.user import User  # noqa: E402


@pytest.fixture(autouse=True)
def reset_database():
    limiter.reset()
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def client():
    with TestClient(app) as test_client:
        yield test_client


def auth_headers(client: TestClient, role: str = "Admin", email: str = "admin@solara.test"):
    """Provision an active user with required role directly in DB, then login."""
    with Session(engine) as db:
        user = db.query(User).filter(User.email == email.lower()).first()
        if not user:
            user = User(
                name="Solara Admin",
                email=email.lower(),
                password_hash=get_password_hash("StrongPass123"),
                phone="+91 98765 43210",
                role=role,
                status="Active",
                failed_attempts=0,
                token_version=0,
            )
            db.add(user)
            db.commit()
        else:
            user.status = "Active"
            user.role = role
            user.password_hash = get_password_hash("StrongPass123")
            user.failed_attempts = 0
            user.locked_until = None
            db.commit()

    db = SessionLocal()
    try:
        db.query(User).filter(User.email == email).update({"role": "Admin"})
        db.commit()
    finally:
        db.close()

    login_response = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "StrongPass123"},
    )
    assert login_response.status_code == 200
    token = login_response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

