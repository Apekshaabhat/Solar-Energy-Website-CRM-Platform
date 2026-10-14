from sqlalchemy.orm import Session
from app.core.database import engine
from datetime import timedelta

from app.core.security import create_access_token
from app.core.database import SessionLocal
from app.models.customer import Customer
from app.models.lead import Lead
from app.models.user import User
from .conftest import auth_headers


def staff_headers(client, email, role):
    headers = auth_headers(client, role=role, email=email)
    with SessionLocal() as db:
        db.query(User).filter(User.email == email).update({"role": role})
        db.commit()
    return headers


def test_seeded_admin_login_uses_dev_password(client):
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@solara.com", "password": "admin123"},
    )
    assert response.status_code == 200
    assert response.json()["user"]["email"] == "admin@solara.com"
    assert response.json()["user"]["role"] == "Admin"


def test_register_login_and_me(client):
    # Registration with strong password meets policy
    response = client.post(
        "/api/v1/auth/register",
        json={
            "name": "Asha Rao",
            "email": "asha@example.com",
            "password": "StrongPassword123",
            "phone": "+91 90000 00000",
        },
    )
    assert response.status_code == 201
    assert response.json()["success"] is True
    assert response.json()["data"]["email"] == "asha@example.com"
    assert response.json()["data"]["role"] == "Customer"

    # Duplicate registration returns identical generic response without revealing account existence
    duplicate = client.post(
        "/api/v1/auth/register",
        json={
            "name": "Asha Rao",
            "email": "asha@example.com",
            "password": "StrongPassword123",
        },
    )
    assert duplicate.status_code == 201
    assert duplicate.json()["success"] is True

    # Pending user cannot log in
    pending_login = client.post(
        "/api/v1/auth/login",
        json={"email": "asha@example.com", "password": "StrongPassword123"},
    )
    assert pending_login.status_code == 401
    assert pending_login.json()["message"] == "Incorrect email or password"

    # Once user is set to Active, login succeeds
    with Session(engine) as db:
        user = db.query(User).filter(User.email == "asha@example.com").first()
        user.status = "Active"
        db.commit()

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
        json={"email": "asha@example.com", "password": "StrongPassword123"},
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
        "email": "public-regression@solara.test",
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
    listed = client.get(
        "/api/v1/leads",
        params={"search": "public-regression@solara.test"},
        headers=headers,
    )
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


def test_lead_access_is_scoped_to_assigned_staff_and_preserves_manager_access(client):
    admin_headers = auth_headers(client, email="lead-admin@solara.test")
    sales_headers = staff_headers(client, "sales-one@solara.test", "Sales Rep")
    other_sales_headers = staff_headers(client, "sales-two@solara.test", "Sales Rep")
    manager_headers = staff_headers(client, "lead-manager@solara.test", "Manager")
    initial_admin_total = client.get("/api/v1/leads", headers=admin_headers).json()["total"]

    def create_lead(name, email, status, assigned_user_id=None):
        response = client.post(
            "/api/v1/leads",
            json={
                "name": name,
                "contact": "+91 90000 00000",
                "email": email,
                "location": "Pune",
                "property_type": "Residential",
                "source": "Website",
                "status": status,
                "assigned_user_id": assigned_user_id,
            },
            headers=admin_headers,
        )
        assert response.status_code == 201
        return response.json()["data"]["id"]

    db = SessionLocal()
    try:
        sales_user_id = db.query(User.id).filter(User.email == "sales-one@solara.test").scalar()
        other_sales_user_id = db.query(User.id).filter(User.email == "sales-two@solara.test").scalar()
    finally:
        db.close()

    own_lead_id = create_lead("Own Lead", "own@solara.test", "New", sales_user_id)
    own_followup_id = create_lead(
        "Own Follow-up", "followup@solara.test", "Contacted", sales_user_id
    )
    other_lead_id = create_lead("Other Rep Lead", "other@solara.test", "Lost", other_sales_user_id)
    create_lead("Unassigned Lead", "unassigned@solara.test", "New")

    own_leads = client.get("/api/v1/leads", headers=sales_headers)
    assert own_leads.status_code == 200
    assert own_leads.json()["total"] == 2
    assert {lead["id"] for lead in own_leads.json()["items"]} == {own_lead_id, own_followup_id}
    assert other_lead_id not in {lead["id"] for lead in own_leads.json()["items"]}
    assert own_leads.json()["tab_counts"]["All Leads"] == 2
    assert own_leads.json()["tab_counts"]["New"] == 1
    assert own_leads.json()["tab_counts"]["Contacted"] == 1
    assert own_leads.json()["tab_counts"]["Lost"] == 0

    hidden_search = client.get(
        "/api/v1/leads",
        params={"search": "Other Rep Lead", "status": "Lost"},
        headers=sales_headers,
    )
    assert hidden_search.status_code == 200
    assert hidden_search.json()["total"] == 0
    assert hidden_search.json()["tab_counts"]["All Leads"] == 0

    hidden_status = client.get(
        "/api/v1/leads",
        params={"status": "Lost"},
        headers=sales_headers,
    )
    assert hidden_status.status_code == 200
    assert hidden_status.json()["total"] == 0
    assert hidden_status.json()["tab_counts"]["All Leads"] == 2
    assert hidden_status.json()["tab_counts"]["Lost"] == 0

    second_page = client.get(
        "/api/v1/leads",
        params={"page": 2, "limit": 1},
        headers=sales_headers,
    )
    assert second_page.status_code == 200
    assert second_page.json()["total"] == 2
    assert len(second_page.json()["items"]) == 1
    assert second_page.json()["items"][0]["id"] != other_lead_id

    assert client.get(f"/api/v1/leads/{other_lead_id}", headers=sales_headers).status_code == 404
    assert client.patch(
        f"/api/v1/leads/{other_lead_id}",
        json={"status": "Contacted"},
        headers=sales_headers,
    ).status_code == 404

    admin_leads = client.get("/api/v1/leads", headers=admin_headers)
    manager_leads = client.get("/api/v1/leads", headers=manager_headers)
    assert admin_leads.status_code == 200
    assert manager_leads.status_code == 200
    assert admin_leads.json()["total"] == initial_admin_total + 4
    assert manager_leads.json()["total"] == initial_admin_total + 4
    assert client.get(f"/api/v1/leads/{other_lead_id}", headers=manager_headers).status_code == 200
    assert {lead["id"] for lead in client.get(
        "/api/v1/leads", headers=other_sales_headers
    ).json()["items"]} == {other_lead_id}


def test_lead_record_routes_enforce_auth_ownership_and_assignment_permissions(client):
    admin_headers = auth_headers(client, email="record-admin@solara.test")
    owner_headers = staff_headers(client, "record-owner@solara.test", "Sales Rep")
    other_headers = staff_headers(client, "record-other@solara.test", "Support")
    manager_headers = staff_headers(client, "record-manager@solara.test", "Manager")

    with SessionLocal() as db:
        owner_id = db.query(User.id).filter(User.email == "record-owner@solara.test").scalar()
        other_id = db.query(User.id).filter(User.email == "record-other@solara.test").scalar()

    lead_payload = {
        "name": "Record Authorization Lead",
        "contact": "+91 91111 22222",
        "email": "record-authorization@solara.test",
        "location": "Pune",
        "property_type": "Residential",
        "source": "Website",
    }

    own_created = client.post("/api/v1/leads", json=lead_payload, headers=owner_headers)
    assert own_created.status_code == 201
    own_lead_id = own_created.json()["data"]["id"]
    assert own_created.json()["data"]["assigned_user_id"] == owner_id
    assert client.get(f"/api/v1/leads/{own_lead_id}", headers=other_headers).status_code == 404
    assert client.patch(
        f"/api/v1/leads/{own_lead_id}",
        json={"status": "Lost"},
        headers=other_headers,
    ).status_code == 404

    forged_assignment = client.post(
        "/api/v1/leads",
        json={**lead_payload, "email": "forged-assignment@solara.test", "assigned_user_id": other_id},
        headers=owner_headers,
    )
    assert forged_assignment.status_code == 403

    other_lead = client.post(
        "/api/v1/leads",
        json={**lead_payload, "email": "manager-assigned@solara.test", "assigned_user_id": other_id},
        headers=admin_headers,
    )
    assert other_lead.status_code == 201
    other_lead_id = other_lead.json()["data"]["id"]

    for method, path, kwargs in [
        ("get", f"/api/v1/leads/{other_lead_id}", {}),
        ("patch", f"/api/v1/leads/{other_lead_id}", {"json": {"status": "Lost"}}),
        ("delete", f"/api/v1/leads/{other_lead_id}", {}),
    ]:
        assert getattr(client, method)(path, **kwargs).status_code == 401
        assert getattr(client, method)(
            path,
            headers={"Authorization": "Bearer invalid-token"},
            **kwargs,
        ).status_code == 401

    assert client.get(f"/api/v1/leads/{other_lead_id}", headers=owner_headers).status_code == 404
    denied_update = client.patch(
        f"/api/v1/leads/{own_lead_id}",
        json={"assigned_user_id": other_id},
        headers=owner_headers,
    )
    assert denied_update.status_code == 403

    with SessionLocal() as db:
        still_owned = db.query(Lead).filter(Lead.id == own_lead_id).one()
        assert still_owned.assigned_user_id == owner_id

    assert client.get("/api/v1/leads/not-an-id", headers=owner_headers).status_code == 422
    assert client.patch(
        "/api/v1/leads/not-an-id",
        json={"status": "Lost"},
        headers=owner_headers,
    ).status_code == 422
    assert client.get("/api/v1/leads/999999", headers=owner_headers).status_code == 404
    assert client.patch(
        "/api/v1/leads/999999",
        json={"status": "Lost"},
        headers=owner_headers,
    ).status_code == 404
    assert client.delete("/api/v1/leads/999999", headers=admin_headers).status_code == 404

    reassign = client.patch(
        f"/api/v1/leads/{other_lead_id}",
        json={"assigned_user_id": owner_id},
        headers=manager_headers,
    )
    assert reassign.status_code == 200
    assert reassign.json()["data"]["assigned_user_id"] == owner_id
    assert client.get(f"/api/v1/leads/{other_lead_id}", headers=owner_headers).status_code == 200

    forbidden_delete = client.delete(f"/api/v1/leads/{own_lead_id}", headers=owner_headers)
    assert forbidden_delete.status_code == 403
    deleted = client.delete(f"/api/v1/leads/{other_lead_id}", headers=manager_headers)
    assert deleted.status_code == 200
    assert client.get(f"/api/v1/leads/{other_lead_id}", headers=admin_headers).status_code == 404


def test_customer_access_is_scoped_to_assigned_staff_and_preserves_manager_access(client):
    admin_headers = auth_headers(client, email="customer-admin@solara.test")
    owner_headers = staff_headers(client, "customer-owner@solara.test", "Sales Rep")
    other_headers = staff_headers(client, "customer-other@solara.test", "Support")
    manager_headers = staff_headers(client, "customer-manager@solara.test", "Manager")
    with SessionLocal() as db:
        owner_id = db.query(User.id).filter(User.email == "customer-owner@solara.test").scalar()
        other_id = db.query(User.id).filter(User.email == "customer-other@solara.test").scalar()

    location = "Task5 Access Pune"

    def create_customer(name, email, assigned_user_id=None, headers=admin_headers):
        response = client.post(
            "/api/v1/customers",
            json={
                "name": name,
                "contact": "+91 92222 33333",
                "email": email,
                "location": location,
                "property_type": "Residential",
                "assigned_user_id": assigned_user_id,
            },
            headers=headers,
        )
        assert response.status_code == 201
        return response.json()["data"]["id"]

    own_customer_id = create_customer(
        "Task5 Owner Created", "task5-owner-created@solara.test", headers=owner_headers
    )
    assigned_customer_id = create_customer(
        "Task5 Owner Assigned", "task5-owner-assigned@solara.test", owner_id
    )
    other_customer_id = create_customer(
        "Task5 Other Staff", "task5-other@solara.test", other_id
    )
    unassigned_customer_id = create_customer(
        "Task5 Unassigned", "task5-unassigned@solara.test"
    )

    assert client.get("/api/v1/customers", params={"location": location}).status_code == 401
    assert client.get(
        "/api/v1/customers",
        params={"location": location},
        headers={"Authorization": "Bearer invalid-token"},
    ).status_code == 401

    for method, path, kwargs in [
        ("get", f"/api/v1/customers/{other_customer_id}", {}),
        ("patch", f"/api/v1/customers/{other_customer_id}", {"json": {"status": "Inactive"}}),
        ("delete", f"/api/v1/customers/{other_customer_id}", {}),
    ]:
        assert getattr(client, method)(path, **kwargs).status_code == 401
        assert getattr(client, method)(
            path,
            headers={"Authorization": "Bearer invalid-token"},
            **kwargs,
        ).status_code == 401
    assert client.post(
        "/api/v1/customers",
        json={
            "name": "Task5 Unauthenticated",
            "contact": "+91 90000 12345",
            "location": location,
        },
    ).status_code == 401

    with SessionLocal() as db:
        own_customer = db.query(Customer).filter(Customer.id == own_customer_id).one()
        assert own_customer.assigned_user_id == owner_id

    owner_list = client.get(
        "/api/v1/customers",
        params={"location": location, "property_type": "Residential", "limit": 1},
        headers=owner_headers,
    )
    assert owner_list.status_code == 200
    assert owner_list.json()["meta"]["total"] == 2
    assert owner_list.json()["meta"]["total_pages"] == 2
    assert len(owner_list.json()["items"]) == 1
    assert owner_list.json()["items"][0]["assigned_user_id"] == owner_id
    owner_second_page = client.get(
        "/api/v1/customers",
        params={"location": location, "page": 2, "limit": 1},
        headers=owner_headers,
    )
    assert owner_second_page.status_code == 200
    assert owner_second_page.json()["meta"]["total"] == 2
    assert owner_second_page.json()["items"][0]["id"] in {
        own_customer_id,
        assigned_customer_id,
    }
    assert owner_second_page.json()["items"][0]["id"] != owner_list.json()["items"][0]["id"]

    owner_search = client.get(
        "/api/v1/customers",
        params={"search": "task5-other@solara.test", "location": location},
        headers=owner_headers,
    )
    assert owner_search.status_code == 200
    assert owner_search.json()["meta"]["total"] == 0
    assert owner_search.json()["items"] == []

    assert client.get(f"/api/v1/customers/{own_customer_id}", headers=owner_headers).status_code == 200
    assert client.get(
        f"/api/v1/customers/{other_customer_id}", headers=other_headers
    ).status_code == 200
    assert client.get(f"/api/v1/customers/{own_customer_id}", headers=other_headers).status_code == 404
    assert client.get(f"/api/v1/customers/{other_customer_id}", headers=owner_headers).status_code == 404
    assert client.get(
        f"/api/v1/customers/{unassigned_customer_id}", headers=owner_headers
    ).status_code == 404
    assert client.patch(
        f"/api/v1/customers/{other_customer_id}",
        json={"status": "Inactive"},
        headers=owner_headers,
    ).status_code == 404
    assert client.patch(
        f"/api/v1/customers/{unassigned_customer_id}",
        json={"status": "Inactive"},
        headers=owner_headers,
    ).status_code == 404

    spoofed_create = client.post(
        "/api/v1/customers",
        json={
            "name": "Task5 Spoofed Assignment",
            "contact": "+91 94444 55555",
            "location": location,
            "assigned_user_id": other_id,
        },
        headers=owner_headers,
    )
    assert spoofed_create.status_code == 403

    for assigned_user_id in (other_id, None):
        denied_reassignment = client.patch(
            f"/api/v1/customers/{own_customer_id}",
            json={"assigned_user_id": assigned_user_id},
            headers=owner_headers,
        )
        assert denied_reassignment.status_code == 403
    with SessionLocal() as db:
        unchanged = db.query(Customer).filter(Customer.id == own_customer_id).one()
        assert unchanged.assigned_user_id == owner_id

    assert client.get(f"/api/v1/customers/{other_customer_id}", headers=manager_headers).status_code == 200
    assert client.get(
        f"/api/v1/customers/{unassigned_customer_id}", headers=manager_headers
    ).status_code == 200
    manager_list = client.get(
        "/api/v1/customers", params={"location": location}, headers=manager_headers
    )
    assert manager_list.status_code == 200
    assert manager_list.json()["meta"]["total"] == 4
    manager_reassign = client.patch(
        f"/api/v1/customers/{unassigned_customer_id}",
        json={"assigned_user_id": owner_id},
        headers=manager_headers,
    )
    assert manager_reassign.status_code == 200
    assert manager_reassign.json()["data"]["assigned_user_id"] == owner_id
    assert client.get(
        f"/api/v1/customers/{unassigned_customer_id}", headers=owner_headers
    ).status_code == 200

    admin_list = client.get(
        "/api/v1/customers", params={"location": location}, headers=admin_headers
    )
    assert admin_list.status_code == 200
    assert admin_list.json()["meta"]["total"] == 4
    assert client.get(
        f"/api/v1/customers/{other_customer_id}", headers=admin_headers
    ).status_code == 200
    admin_update = client.patch(
        f"/api/v1/customers/{other_customer_id}",
        json={"status": "Inactive"},
        headers=admin_headers,
    )
    assert admin_update.status_code == 200
    assert admin_update.json()["data"]["status"] == "Inactive"

    assert client.get("/api/v1/customers/not-an-id", headers=owner_headers).status_code == 422
    assert client.patch(
        "/api/v1/customers/not-an-id",
        json={"status": "Inactive"},
        headers=owner_headers,
    ).status_code == 422
    assert client.get("/api/v1/customers/999999", headers=owner_headers).status_code == 404
    assert client.patch(
        "/api/v1/customers/999999",
        json={"status": "Inactive"},
        headers=owner_headers,
    ).status_code == 404
    assert client.delete(
        f"/api/v1/customers/{own_customer_id}", headers=owner_headers
    ).status_code == 403
    assert client.delete(
        "/api/v1/customers/999999", headers=admin_headers
    ).status_code == 404
    assert client.delete(
        f"/api/v1/customers/{unassigned_customer_id}", headers=manager_headers
    ).status_code == 200


def test_customer_token_cannot_assign_public_lead_ownership(client):
    headers = auth_headers(client, role="Customer", email="customer@example.com")

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
        headers=headers,
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
