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

from app.core.database import Base, SessionLocal, engine  # noqa: E402
import app.models  # noqa: E402,F401
from app.main import app  # noqa: E402
from app.models.user import User  # noqa: E402


@pytest.fixture(autouse=True)
def reset_database():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def client():
    with TestClient(app) as test_client:
        yield test_client


def auth_headers(client: TestClient, role: str = "Admin", email: str = "admin@solara.test"):
    register_response = client.post(
        "/api/v1/auth/register",
        json={
            "name": "Solara Admin",
            "email": email,
            "password": "StrongPass123",
            "phone": "+91 98765 43210",
            "role": role,
        },
    )
    assert register_response.status_code == 201

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
