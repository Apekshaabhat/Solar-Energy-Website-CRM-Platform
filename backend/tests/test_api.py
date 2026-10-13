from datetime import timedelta

from app.core.security import create_access_token
from .conftest import auth_headers


def test_seeded_admin_login_uses_dev_password(client):
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@solara.com", "password": "admin123"},
    )
    assert response.status_code == 200
    assert response.json()["user"]["email"] == "admin@solara.com"
    assert response.json()["user"]["role"] == "Admin"


def test_register_login_and_me(client):
    response = client.post(
        "/api/v1/auth/register",
        json={
            "name": "Asha Rao",
            "email": "asha@example.com",
            "password": "password123",
            "phone": "+91 90000 00000",
        },
    )
    assert response.status_code == 201
    assert response.json()["data"]["email"] == "asha@example.com"
    assert response.json()["data"]["role"] == "Customer"

    duplicate = client.post(
        "/api/v1/auth/register",
        json={
            "name": "Asha Rao",
            "email": "asha@example.com",
            "password": "password123",
        },
    )
    assert duplicate.status_code == 400

    escalated = client.post(
        "/api/v1/auth/register",
        json={
            "name": "Mallory Singh",
            "email": "mallory@example.com",
            "password": "password123",
            "role": "Admin",
        },
    )
    assert escalated.status_code == 201
    assert escalated.json()["data"]["role"] == "Customer"

    first_admin_attempt = client.post(
        "/api/v1/auth/register",
        json={
            "name": "First User",
            "email": "first@example.com",
            "password": "password123",
            "role": "Admin",
        },
    )
    assert first_admin_attempt.status_code == 201
    assert first_admin_attempt.json()["data"]["role"] == "Customer"

    login = client.post(
        "/api/v1/auth/login",
        json={"email": "asha@example.com", "password": "password123"},
    )
    assert login.status_code == 200
    token = login.json()["access_token"]

    me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["data"]["name"] == "Asha Rao"


def test_forgot_password_is_not_reported_as_sent_when_unconfigured(client):
    response = client.post(
        "/api/v1/auth/forgot-password",
        json={"email": "user@example.com"},
    )
    assert response.status_code == 501


def test_expired_access_token_is_rejected(client):
    expired_token = create_access_token("1", expires_delta=timedelta(seconds=-1))
    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {expired_token}"},
    )
    assert response.status_code == 401


def test_dashboard_summary_requires_valid_authentication(client):
    path = "/api/v1/dashboard/summary"

    assert client.get(path).status_code == 401
    assert client.get(path, headers={"Authorization": "Bearer invalid-token"}).status_code == 401

    expired_token = create_access_token("1", expires_delta=timedelta(seconds=-1))
    expired = client.get(
        path,
        headers={"Authorization": f"Bearer {expired_token}"},
    )
    assert expired.status_code == 401

    authenticated = client.get(path, headers=auth_headers(client))
    assert authenticated.status_code == 200


def test_staff_dashboard_apis_require_valid_authentication(client):
    paths = [
        "/api/v1/dashboard/summary",
        "/api/v1/customers",
        "/api/v1/leads",
        "/api/v1/site-surveys",
        "/api/v1/site-surveys/export",
        "/api/v1/calculators/submissions",
        "/api/v1/users",
        "/api/v1/settings",
    ]
    expired_token = create_access_token("1", expires_delta=timedelta(seconds=-1))
    credential_headers = [
        None,
        {"Authorization": "Bearer invalid-token"},
        {"Authorization": f"Bearer {expired_token}"},
    ]

    for path in paths:
        for headers in credential_headers:
            response = client.get(path, headers=headers)
            assert response.status_code == 401, path

    authenticated_headers = auth_headers(client)
    for path in paths:
        response = client.get(path, headers=authenticated_headers)
        assert response.status_code == 200, path


def test_public_lead_submission_and_staff_lead_management(client):
    lead_payload = {
        "name": "Rohan Patil",
        "contact": "+91 98765 43210",
        "email": "rohan@example.com",
        "location": "Mumbai",
        "property_type": "Residential",
        "source": "Website",
    }
    created = client.post("/api/v1/leads", json=lead_payload)
    assert created.status_code == 201
    assert created.json()["data"]["assigned_user_id"] is None

    blocked = client.get("/api/v1/leads")
    assert blocked.status_code == 401

    headers = auth_headers(client)
    listed = client.get("/api/v1/leads", headers=headers)
    assert listed.status_code == 200
    assert listed.json()["total"] == 1

    lead_id = listed.json()["items"][0]["id"]
    updated = client.patch(
        f"/api/v1/leads/{lead_id}",
        json={"status": "Contacted"},
        headers=headers,
    )
    assert updated.status_code == 200
    assert updated.json()["data"]["status"] == "Contacted"


def test_customer_token_cannot_assign_public_lead_ownership(client):
    register = client.post(
        "/api/v1/auth/register",
        json={
            "name": "Customer User",
            "email": "customer@example.com",
            "password": "password123",
        },
    )
    assert register.status_code == 201
    assert register.json()["data"]["role"] == "Customer"

    login = client.post(
        "/api/v1/auth/login",
        json={"email": "customer@example.com", "password": "password123"},
    )
    token = login.json()["access_token"]

    created = client.post(
        "/api/v1/leads",
        json={
            "name": "Nisha Shah",
            "contact": "+91 98989 00000",
            "location": "Surat",
            "property_type": "Residential",
            "assigned_user_id": 999,
            "customer_id": 999,
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert created.status_code == 201
    assert created.json()["data"]["assigned_user_id"] is None
    assert created.json()["data"]["customer_id"] is None


def test_customer_project_survey_and_dashboard_summary(client):
    headers = auth_headers(client)

    customer = client.post(
        "/api/v1/customers",
        json={
            "name": "Sneha Sharma",
            "contact": "+91 91234 56789",
            "location": "Pune",
            "property_type": "Commercial",
        },
        headers=headers,
    )
    assert customer.status_code == 201
    customer_id = customer.json()["data"]["id"]

    project = client.post(
        "/api/v1/projects",
        json={
            "name": "Pune Rooftop Solar",
            "category": "Commercial",
            "location": "Pune",
            "capacity": "25 kW",
            "capacity_kw": 25,
            "status": "Completed",
            "customer_id": customer_id,
            "is_public": False,
        },
        headers=headers,
    )
    assert project.status_code == 201

    public_projects = client.get("/api/v1/projects")
    assert public_projects.status_code == 200
    assert public_projects.json()["data"] == []

    staff_projects = client.get("/api/v1/projects", headers=headers)
    assert staff_projects.status_code == 200
    assert len(staff_projects.json()["data"]) == 1

    survey = client.post(
        "/api/v1/site-surveys",
        json={
            "customer_name": "Sneha Sharma",
            "location": "Pune",
            "property_type": "Commercial",
            "survey_date": "2026-09-24",
            "time_slot": "10:00 AM",
            "assigned_to": "Priya",
        },
    )
    assert survey.status_code == 201

    dashboard = client.get("/api/v1/dashboard/summary", headers=headers)
    assert dashboard.status_code == 200
    stat_cards = {item["id"]: item["value"] for item in dashboard.json()["statCards"]}
    assert stat_cards["site-surveys"] == "1"
    assert stat_cards["completed-projects"] == "1"


def test_calculator_submission_public_create_staff_manage_settings(client):
    submission = client.post(
        "/api/v1/calculators/submissions",
        json={
            "name": "Amit Verma",
            "phone": "+91 99887 66554",
            "property_type": "Residential",
            "monthly_bill": 5000,
            "roof_area": 800,
            "system_size_kw": 5.2,
            "annual_savings": 51000,
            "payback_years": 5.6,
            "co2_tons": 6.2,
        },
    )
    assert submission.status_code == 201

    blocked = client.get("/api/v1/calculators/submissions")
    assert blocked.status_code == 401

    headers = auth_headers(client)
    listed = client.get("/api/v1/calculators/submissions", headers=headers)
    assert listed.status_code == 200
    assert listed.json()["meta"]["total"] == 1

    public_settings = client.get("/api/v1/calculators/settings")
    assert public_settings.status_code == 200
    assert public_settings.json()["data"]["electricity_rate"] == 8.0

    updated_settings = client.put(
        "/api/v1/calculators/settings",
        json={"electricity_rate": 9.5},
        headers=headers,
    )
    assert updated_settings.status_code == 200
    assert updated_settings.json()["data"]["electricity_rate"] == 9.5


def test_frontend_service_contracts_for_admin_resources(client):
    headers = auth_headers(client)

    invited = client.post(
        "/api/v1/users",
        json={
            "name": "Support Agent",
            "email": "support-agent@solara.test",
            "role": "Support",
            "status": "Active",
            "password": "Support123",
        },
        headers=headers,
    )
    assert invited.status_code == 201

    users = client.get(
        "/api/v1/users",
        params={"role": "All Roles", "status": "All Statuses"},
        headers=headers,
    )
    assert users.status_code == 200
    assert len(users.json()["data"]) == 2

    settings = client.put(
        "/api/v1/settings",
        json={"support_email": "care@solara.test", "sms_notifications": True},
        headers=headers,
    )
    assert settings.status_code == 200
    assert settings.json()["data"]["support_email"] == "care@solara.test"
    assert settings.json()["data"]["sms_notifications"] is True

    customer = client.post(
        "/api/v1/customers",
        json={
            "name": "Contract Customer",
            "contact": "+91 90000 11111",
            "email": "contract-customer@solara.test",
            "phone": "+91 90000 11111",
            "location": "Bengaluru",
            "property_type": "Residential",
        },
        headers=headers,
    )
    assert customer.status_code == 201

    customers = client.get(
        "/api/v1/customers",
        params={
            "search": "contract-customer@solara.test",
            "property_type": "All Property Types",
            "status": "All Statuses",
        },
        headers=headers,
    )
    assert customers.status_code == 200
    assert customers.json()["meta"]["total"] == 1

    calc = client.post(
        "/api/v1/calculators/submissions",
        json={
            "name": "Calculator Contract",
            "phone": "+91 90000 22222",
            "email": "calculator-contract@solara.test",
            "property_type": "Commercial",
            "monthly_bill": 7500,
            "roof_area": 900,
            "system_size_kw": 7.1,
            "annual_savings": 76500,
        },
    )
    assert calc.status_code == 201

    calc_list = client.get(
        "/api/v1/calculators/submissions",
        params={"search": "calculator-contract@solara.test", "property_type": "All Property Types"},
        headers=headers,
    )
    assert calc_list.status_code == 200
    assert calc_list.json()["meta"]["total"] == 1

    published = client.post(
        "/api/v1/blogs",
        json={"title": "Published Solar Guide", "category": "Guides", "status": "Published"},
        headers=headers,
    )
    draft = client.post(
        "/api/v1/blogs",
        json={"title": "Draft Solar Guide", "category": "Guides", "status": "Draft"},
        headers=headers,
    )
    assert published.status_code == 201
    assert draft.status_code == 201

    public_blogs = client.get("/api/v1/blogs", params={"status": "All Statuses"})
    assert public_blogs.status_code == 200
    assert public_blogs.json()["meta"]["total"] == 1

    staff_blogs = client.get(
        "/api/v1/blogs",
        params={"category": "All Categories", "status": "All Statuses"},
        headers=headers,
    )
    assert staff_blogs.status_code == 200
    assert staff_blogs.json()["meta"]["total"] == 2

    public_draft = client.get(f"/api/v1/blogs/{draft.json()['data']['id']}")
    assert public_draft.status_code == 404

    faq_public = client.post(
        "/api/v1/faqs",
        json={"question": "What is solar payback?", "answer": "Most systems pay back over time.", "is_published": True},
        headers=headers,
    )
    faq_private = client.post(
        "/api/v1/faqs",
        json={"question": "Internal process note?", "answer": "Visible only to staff.", "is_published": False},
        headers=headers,
    )
    assert faq_public.status_code == 201
    assert faq_private.status_code == 201

    public_faqs = client.get("/api/v1/faqs")
    assert public_faqs.status_code == 200
    assert len(public_faqs.json()["data"]) == 1

    staff_faqs = client.get("/api/v1/faqs", headers=headers)
    assert staff_faqs.status_code == 200
    assert len(staff_faqs.json()["data"]) == 2


def test_site_survey_export_requires_staff_and_escapes_formulas(client):
    payload = {
        "customer_name": "=HYPERLINK(\"https://example.invalid\")",
        "location": "Pune",
        "survey_date": "2026-09-24",
        "time_slot": "10:00 AM",
        "assigned_to": "Priya",
    }
    created = client.post("/api/v1/site-surveys", json=payload)
    assert created.status_code == 201

    unauthenticated = client.get("/api/v1/site-surveys/export")
    assert unauthenticated.status_code == 401

    exported = client.get("/api/v1/site-surveys/export", headers=auth_headers(client))
    assert exported.status_code == 200
    assert exported.headers["content-type"].startswith("text/csv")
    assert "'=HYPERLINK" in exported.text
