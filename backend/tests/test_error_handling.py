import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from pydantic import BaseModel
from sqlalchemy.exc import IntegrityError, OperationalError

from app.main import app


class ErrorTestPayload(BaseModel):
    count: int


@pytest.fixture
def error_test_client():
    async def raise_http_error(status_code: int):
        headers = {"WWW-Authenticate": "Bearer"} if status_code == 401 else None
        raise HTTPException(
            status_code=status_code,
            detail="Request could not be completed.",
            headers=headers,
        )

    async def validate_body(payload: ErrorTestPayload):
        return payload

    async def raise_integrity_error():
        raise IntegrityError(
            "INSERT INTO users (password) VALUES (?)",
            {"password": "database-secret"},
            Exception("constraint detail"),
        )

    async def raise_database_error():
        raise OperationalError("SELECT ?", {"token": "database-secret"}, Exception("db detail"))

    async def raise_unexpected_error():
        raise RuntimeError("private token: unexpected-secret")

    routes = [
        ("/__test_errors/http/{status_code}", raise_http_error, ["GET"]),
        ("/__test_errors/validation", validate_body, ["POST"]),
        ("/__test_errors/integrity", raise_integrity_error, ["GET"]),
        ("/__test_errors/database", raise_database_error, ["GET"]),
        ("/__test_errors/unexpected", raise_unexpected_error, ["GET"]),
    ]
    for path, endpoint, methods in routes:
        app.add_api_route(path, endpoint, methods=methods)

    try:
        with TestClient(app, raise_server_exceptions=False) as client:
            yield client
    finally:
        paths = {path for path, _, _ in routes}
        app.router.routes[:] = [
            route for route in app.router.routes if getattr(route, "path", None) not in paths
        ]


@pytest.mark.parametrize(
    ("status_code", "error_code"),
    [
        (400, "BAD_REQUEST"),
        (401, "UNAUTHORIZED"),
        (403, "FORBIDDEN"),
        (404, "NOT_FOUND"),
        (409, "CONFLICT"),
        (500, "INTERNAL_SERVER_ERROR"),
    ],
)
def test_http_errors_use_standard_error_envelope(error_test_client, status_code, error_code):
    response = error_test_client.get(f"/__test_errors/http/{status_code}")

    assert response.status_code == status_code
    assert response.json()["success"] is False
    assert response.json()["error_code"] == error_code
    assert response.json()["details"] is None
    assert response.json()["message"] == (
        "An unexpected server error occurred."
        if status_code == 500
        else "Request could not be completed."
    )
    if status_code == 401:
        assert response.headers["www-authenticate"] == "Bearer"


def test_validation_errors_do_not_echo_submitted_values(error_test_client):
    secret_input = "private-validation-secret"
    response = error_test_client.post(
        "/__test_errors/validation",
        json={"count": secret_input},
    )

    assert response.status_code == 422
    assert response.json()["success"] is False
    assert response.json()["error_code"] == "VALIDATION_ERROR"
    assert response.json()["details"][0]["location"] == ["body", "count"]
    assert secret_input not in response.text
    assert "input" not in response.json()["details"][0]


def test_integrity_errors_are_safe_conflicts(error_test_client):
    response = error_test_client.get("/__test_errors/integrity")

    assert response.status_code == 409
    assert response.json()["error_code"] == "CONFLICT"
    assert response.json()["message"] == "The requested change conflicts with existing data."
    assert "database-secret" not in response.text
    assert "constraint detail" not in response.text


def test_database_errors_are_safe_server_errors(error_test_client):
    response = error_test_client.get("/__test_errors/database")

    assert response.status_code == 500
    assert response.json()["error_code"] == "DATABASE_ERROR"
    assert "database-secret" not in response.text
    assert "db detail" not in response.text


def test_async_unexpected_errors_return_without_exposing_details(error_test_client):
    response = error_test_client.get("/__test_errors/unexpected")

    assert response.status_code == 500
    assert response.json()["error_code"] == "INTERNAL_SERVER_ERROR"
    assert response.json()["message"] == "An unexpected server error occurred."
    assert "unexpected-secret" not in response.text


def test_successful_response_shape_is_unchanged(error_test_client):
    response = error_test_client.get("/")

    assert response.status_code == 200
    assert set(response.json()) == {"status", "app", "version", "docs"}
