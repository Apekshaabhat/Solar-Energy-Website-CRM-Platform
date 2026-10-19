from datetime import datetime, timedelta, timezone
from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.core.database import SessionLocal, engine
from app.core.security import create_access_token, get_password_hash
from app.models.activity import Activity
from app.models.customer import Customer
from app.models.lead import Lead
from app.models.project import Project
from app.models.settings import SystemSettings
from app.models.site_survey import SiteSurvey
from app.models.user import User
from app.services.crm_service import CRMService

from .conftest import auth_headers


def staff_headers(client, email, role):
    headers = auth_headers(client, role=role, email=email)
    with SessionLocal() as db:
        db.query(User).filter(User.email == email).update({"role": role})
        db.commit()
    return headers


def test_seeded_admin_login_uses_dev_password(client):
    from seed import seed_data
    seed_data()
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
            "password": "StrongPassword123",
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


def test_my_profile_returns_authenticated_user_and_persists_updates(client):
    headers = auth_headers(client, email="my-profile@solara.test")

    profile = client.get("/api/v1/auth/me", headers=headers)
    assert profile.status_code == 200
    profile_data = profile.json()["data"]
    assert profile_data["email"] == "my-profile@solara.test"
    assert profile_data["name"] == "Solara Admin"
    assert not {"password_hash", "access_token", "token_version", "failed_attempts"} & profile_data.keys()

    updated = client.patch(
        "/api/v1/auth/profile",
        json={
            "name": "Updated Profile Name",
            "email": "updated-profile@solara.test",
            "phone": "  +1 555 0100  ",
        },
        headers=headers,
    )
    assert updated.status_code == 200
    assert updated.json()["success"] is True
    assert updated.json()["data"]["name"] == "Updated Profile Name"
    assert updated.json()["data"]["email"] == "updated-profile@solara.test"
    assert updated.json()["data"]["phone"] == "+1 555 0100"

    reloaded = client.get("/api/v1/auth/me", headers=headers)
    assert reloaded.status_code == 200
    assert reloaded.json()["data"]["email"] == "updated-profile@solara.test"
    assert reloaded.json()["data"]["name"] == "Updated Profile Name"
    assert reloaded.json()["data"]["phone"] == "+1 555 0100"
    assert not {"password_hash", "access_token", "token_version", "failed_attempts"} & reloaded.json()["data"].keys()

    with SessionLocal() as db:
        persisted = db.query(User).filter(User.email == "updated-profile@solara.test").one()
        assert persisted.name == "Updated Profile Name"
        assert persisted.phone == "+1 555 0100"


def test_my_profile_rejects_unauthorized_invalid_and_protected_updates(client):
    headers = auth_headers(client, email="my-profile-protected@solara.test")
    assert client.get("/api/v1/auth/me").status_code == 401
    assert client.patch(
        "/api/v1/auth/profile",
        json={"name": "Not Authorized"},
    ).status_code == 401
    nonexistent_user_headers = {
        "Authorization": f"Bearer {create_access_token('999999')}"
    }
    assert client.get(
        "/api/v1/auth/me",
        headers=nonexistent_user_headers,
    ).status_code == 401
    assert client.patch(
        "/api/v1/auth/profile",
        json={"name": "Not Authorized"},
        headers=nonexistent_user_headers,
    ).status_code == 401

    assert client.patch(
        "/api/v1/auth/profile",
        json={"name": "   "},
        headers=headers,
    ).status_code == 422
    assert client.patch(
        "/api/v1/auth/profile",
        json={"email": "not-an-email"},
        headers=headers,
    ).status_code == 422

    protected_update = client.patch(
        "/api/v1/auth/profile",
        json={
            "id": 999999,
            "role": "Admin",
            "status": "Inactive",
            "password_hash": "attacker-controlled",
            "token_version": 99,
        },
        headers=headers,
    )
    assert protected_update.status_code == 422

    with SessionLocal() as db:
        persisted = db.query(User).filter(User.email == "my-profile-protected@solara.test").one()
        assert persisted.role == "Admin"
        assert persisted.status == "Active"
        assert persisted.token_version == 0
        assert persisted.password_hash != "attacker-controlled"


def test_my_profile_rejects_duplicate_email(client):
    owner_headers = auth_headers(client, email="my-profile-email-owner@solara.test")
    auth_headers(client, email="my-profile-email-taken@solara.test")

    response = client.patch(
        "/api/v1/auth/profile",
        json={"email": "my-profile-email-taken@solara.test"},
        headers=owner_headers,
    )
    assert response.status_code == 400
    assert response.json()["success"] is False


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


def test_survey_cancellation_rejects_repeat_invalid_and_unassigned_staff(client):
    owner_headers = staff_headers(client, "survey-cancel-owner@solara.test", "Sales Rep")
    other_headers = staff_headers(client, "survey-cancel-other@solara.test", "Support")
    admin_headers = auth_headers(client, email="survey-cancel-admin@solara.test")
    manager_headers = staff_headers(client, "survey-cancel-manager@solara.test", "Manager")

    with Session(engine) as db:
        owner_id = db.query(User.id).filter(User.email == "survey-cancel-owner@solara.test").scalar()
        customer = Customer(name="Survey Customer", contact="123", location="Pune")
        db.add(customer)
        db.flush()
        lead = Lead(
            name="Survey Lead",
            contact="123",
            location="Pune",
            status="Site Survey",
            assigned_user_id=owner_id,
            customer_id=customer.id,
        )
        db.add(lead)
        db.flush()
        scheduled_survey = SiteSurvey(
            customer_name=customer.name,
            location=customer.location,
            survey_date="2026-10-20",
            time_slot="10:00 AM",
            assigned_to="Owner",
            status="Scheduled",
            notes="Customer requested the survey",
            updated_at=datetime(2000, 1, 1, tzinfo=timezone.utc),
            customer_id=customer.id,
            lead_id=lead.id,
            assigned_user_id=owner_id,
        )
        completed_survey = SiteSurvey(
            customer_name="Completed Customer",
            location="Pune",
            survey_date="2026-10-20",
            time_slot="11:00 AM",
            assigned_to="Owner",
            status="Completed",
            assigned_user_id=owner_id,
        )
        in_progress_survey = SiteSurvey(
            customer_name="In Progress Customer",
            location="Pune",
            survey_date="2026-10-20",
            time_slot="12:00 PM",
            assigned_to="Owner",
            status="In Progress",
            assigned_user_id=owner_id,
        )
        db.add_all([scheduled_survey, completed_survey, in_progress_survey])
        db.commit()
        scheduled_id = scheduled_survey.id
        completed_id = completed_survey.id
        in_progress_id = in_progress_survey.id
        lead_id = lead.id
        customer_id = customer.id

    unauthenticated = client.post(f"/api/v1/site-surveys/{scheduled_id}/cancel")
    assert unauthenticated.status_code == 401

    unauthorized = client.post(
        f"/api/v1/site-surveys/{scheduled_id}/cancel",
        headers=other_headers,
    )
    assert unauthorized.status_code == 404

    cancelled = client.post(
        f"/api/v1/site-surveys/{scheduled_id}/cancel",
        headers=owner_headers,
    )
    assert cancelled.status_code == 200
    assert cancelled.json()["data"]["status"] == "Cancelled"
    assert cancelled.json()["data"]["notes"] == "Customer requested the survey"

    manager_cancelled = client.post(
        f"/api/v1/site-surveys/{in_progress_id}/cancel",
        headers=manager_headers,
    )
    assert manager_cancelled.status_code == 200
    assert manager_cancelled.json()["data"]["status"] == "Cancelled"

    repeated = client.post(
        f"/api/v1/site-surveys/{scheduled_id}/cancel",
        headers=admin_headers,
    )
    assert repeated.status_code == 409

    completed = client.post(
        f"/api/v1/site-surveys/{completed_id}/cancel",
        headers=admin_headers,
    )
    assert completed.status_code == 400

    with Session(engine) as db:
        assert db.query(Lead.status).filter(Lead.id == lead_id).scalar() == "Cancelled"
        assert db.query(Customer.status).filter(Customer.id == customer_id).scalar() == "Inactive"
        assert db.query(SiteSurvey.status).filter(SiteSurvey.id == scheduled_id).scalar() == "Cancelled"
        assert (
            db.query(SiteSurvey.updated_at).filter(SiteSurvey.id == scheduled_id).scalar().year
            > 2000
        )
        assert (
            db.query(Activity.id)
            .filter(Activity.entity_type == "site_survey", Activity.entity_id == scheduled_id)
            .count()
            == 1
        )


def test_survey_cancellation_rolls_back_when_customer_recalculation_fails(client, monkeypatch):
    auth_headers(client, email="survey-cancel-rollback@solara.test")
    with Session(engine) as db:
        user = db.query(User).filter(User.email == "survey-cancel-rollback@solara.test").first()
        customer = Customer(name="Rollback Customer", contact="321", location="Pune")
        db.add(customer)
        db.flush()
        lead = Lead(
            name="Rollback Lead",
            contact="321",
            location="Pune",
            status="Site Survey",
            customer_id=customer.id,
            assigned_user_id=user.id,
        )
        db.add(lead)
        db.flush()
        survey = SiteSurvey(
            customer_name=customer.name,
            location=customer.location,
            survey_date="2026-10-21",
            time_slot="10:00 AM",
            assigned_to="Admin",
            status="Scheduled",
            customer_id=customer.id,
            lead_id=lead.id,
            assigned_user_id=user.id,
        )
        db.add(survey)
        db.commit()
        user_id = user.id
        survey_id = survey.id
        lead_id = lead.id

    def fail_customer_recalculation(_db, _customer_id):
        raise RuntimeError("injected customer recalculation failure")

    monkeypatch.setattr(
        CRMService,
        "recalculate_customer_status",
        staticmethod(fail_customer_recalculation),
    )
    with Session(engine) as db:
        user = db.query(User).filter(User.id == user_id).one()
        with pytest.raises(RuntimeError, match="injected customer recalculation failure"):
            CRMService.site_survey_cancel_workflow(db, survey_id, user)

    with Session(engine) as db:
        assert db.query(SiteSurvey.status).filter(SiteSurvey.id == survey_id).scalar() == "Scheduled"
        assert db.query(Lead.status).filter(Lead.id == lead_id).scalar() == "Site Survey"
        assert (
            db.query(Activity.id)
            .filter(Activity.entity_type == "site_survey", Activity.entity_id == survey_id)
            .count()
            == 0
        )


def test_concurrent_survey_cancellation_is_serialized(client):
    if engine.dialect.name != "postgresql":
        pytest.skip("PostgreSQL row-lock behavior requires the PostgreSQL test backend")

    auth_headers(client, email="survey-cancel-concurrency@solara.test")
    with Session(engine) as db:
        user_id = db.query(User.id).filter(User.email == "survey-cancel-concurrency@solara.test").scalar()
        survey = SiteSurvey(
            customer_name="Concurrent Customer",
            location="Pune",
            survey_date="2026-10-22",
            time_slot="10:00 AM",
            assigned_to="Admin",
            status="Scheduled",
            assigned_user_id=user_id,
        )
        db.add(survey)
        db.commit()
        survey_id = survey.id

    def cancel_once():
        with Session(engine) as db:
            user = db.query(User).filter(User.id == user_id).one()
            try:
                CRMService.site_survey_cancel_workflow(db, survey_id, user)
                return 200
            except HTTPException as exc:
                return exc.status_code

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(lambda _: cancel_once(), range(2)))

    assert sorted(results) == [200, 409]
    with Session(engine) as db:
        assert (
            db.query(Activity.id)
            .filter(Activity.entity_type == "site_survey", Activity.entity_id == survey_id)
            .count()
            == 1
        )


def test_dashboard_summary_scopes_metrics_and_activities_by_assignment(client):
    admin_headers = auth_headers(client, email="dashboard-scope-admin@solara.test")
    manager_headers = staff_headers(client, "dashboard-scope-manager@solara.test", "Manager")
    owner_headers = staff_headers(client, "dashboard-scope-owner@solara.test", "Sales Rep")
    other_headers = staff_headers(client, "dashboard-scope-other@solara.test", "Support")

    with Session(engine) as db:
        owner_id = db.query(User.id).filter(User.email == "dashboard-scope-owner@solara.test").scalar()
        other_id = db.query(User.id).filter(User.email == "dashboard-scope-other@solara.test").scalar()
        customer_user = User(
            name="Dashboard Customer",
            email="dashboard-scope-customer@solara.test",
            password_hash=get_password_hash("StrongPass123"),
            role="Customer",
            status="Active",
        )
        db.add(customer_user)
        db.flush()

        owner_customer = Customer(
            name="Owner Customer",
            contact="111",
            location="Pune",
            assigned_user_id=owner_id,
        )
        other_customer = Customer(
            name="Other Customer",
            contact="222",
            location="Mumbai",
            assigned_user_id=other_id,
            account_user_id=customer_user.id,
        )
        unassigned_customer = Customer(
            name="Unassigned Customer",
            contact="555",
            location="Delhi",
        )
        db.add_all([owner_customer, other_customer, unassigned_customer])
        db.flush()

        owner_lead = Lead(
            name="Owner Lead",
            contact="333",
            location="Pune",
            status="New",
            estimated_value=100.0,
            assigned_user_id=owner_id,
            customer_id=owner_customer.id,
        )
        other_lead = Lead(
            name="Other Lead",
            contact="444",
            location="Mumbai",
            status="Lost",
            estimated_value=900.0,
            assigned_user_id=other_id,
            customer_id=other_customer.id,
        )
        unassigned_lead = Lead(
            name="Unassigned Lead",
            contact="666",
            location="Delhi",
            status="Contacted",
            estimated_value=500.0,
            customer_id=unassigned_customer.id,
        )
        owner_survey = SiteSurvey(
            customer_name=owner_customer.name,
            location="Pune",
            survey_date="2026-10-10",
            time_slot="10:00 AM",
            assigned_to="Owner",
            status="Scheduled",
            customer_id=owner_customer.id,
            assigned_user_id=owner_id,
        )
        other_survey = SiteSurvey(
            customer_name=other_customer.name,
            location="Mumbai",
            survey_date="2026-10-10",
            time_slot="11:00 AM",
            assigned_to="Other",
            status="Completed",
            customer_id=other_customer.id,
            assigned_user_id=other_id,
        )
        unassigned_survey = SiteSurvey(
            customer_name=unassigned_customer.name,
            location="Delhi",
            survey_date="2026-10-10",
            time_slot="12:00 PM",
            assigned_to="Unassigned",
            status="In Progress",
            customer_id=unassigned_customer.id,
        )
        owner_project = Project(
            name="Owner Project",
            category="Residential",
            location="Pune",
            capacity="5 kW",
            status="Completed",
            customer_id=owner_customer.id,
            assigned_user_id=owner_id,
            is_public=False,
            actual_cost=300.0,
        )
        other_project = Project(
            name="Other Project",
            category="Residential",
            location="Mumbai",
            capacity="6 kW",
            status="In Progress",
            customer_id=other_customer.id,
            assigned_user_id=other_id,
            is_public=False,
            estimated_cost=800.0,
        )
        unassigned_project = Project(
            name="Unassigned Project",
            category="Residential",
            location="Delhi",
            capacity="7 kW",
            status="Planning",
            customer_id=unassigned_customer.id,
            is_public=False,
            estimated_cost=700.0,
        )
        db.add_all(
            [
                owner_lead,
                other_lead,
                unassigned_lead,
                owner_survey,
                other_survey,
                unassigned_survey,
                owner_project,
                other_project,
                unassigned_project,
            ]
        )
        db.flush()
        db.add_all(
            [
                Activity(
                    entity_type="lead",
                    entity_id=owner_lead.id,
                    action="created",
                    title="Owner lead activity",
                ),
                Activity(
                    entity_type="lead",
                    entity_id=other_lead.id,
                    action="created",
                    title="Other lead activity",
                ),
                Activity(
                    entity_type="lead",
                    entity_id=unassigned_lead.id,
                    action="created",
                    title="Unassigned lead activity",
                ),
            ]
        )
        customer_user_id = customer_user.id
        db.commit()

    owner_summary_response = client.get("/api/v1/dashboard/summary", headers=owner_headers)
    assert owner_summary_response.status_code == 200
    owner_summary = owner_summary_response.json()
    assert owner_summary["metrics"]["totalLeads"] == 1
    assert owner_summary["metrics"]["newLeads"] == 1
    assert owner_summary["metrics"]["lostLeads"] == 0
    assert owner_summary["metrics"]["totalCustomers"] == 1
    assert owner_summary["metrics"]["totalSurveys"] == 1
    assert owner_summary["metrics"]["scheduledSurveys"] == 1
    assert owner_summary["metrics"]["completedSurveys"] == 0
    assert owner_summary["metrics"]["completedProjects"] == 1
    assert owner_summary["metrics"]["ongoingProjects"] == 0
    assert owner_summary["metrics"]["estimatedPipelineValue"] == 100.0
    assert owner_summary["metrics"]["projectRevenue"] == 300.0
    assert [lead["name"] for lead in owner_summary["recentLeads"]] == ["Owner Lead"]
    assert {activity["title"] for activity in owner_summary["recentActivity"]} == {
        "Owner lead activity"
    }
    owner_activities = client.get("/api/v1/dashboard/activities", headers=owner_headers)
    assert owner_activities.status_code == 200
    assert {activity["title"] for activity in owner_activities.json()["data"]} == {
        "Owner lead activity"
    }

    manager_summary_response = client.get("/api/v1/dashboard/summary", headers=manager_headers)
    assert manager_summary_response.status_code == 200
    manager_metrics = manager_summary_response.json()["metrics"]
    assert manager_metrics["lostLeads"] == 1
    assert manager_metrics["contactedLeads"] == 1
    assert manager_metrics["totalLeads"] == 3
    assert manager_metrics["totalCustomers"] == 3
    assert manager_metrics["totalSurveys"] == 3
    assert manager_metrics["completedSurveys"] == 1
    assert manager_metrics["completedProjects"] == 1
    assert manager_metrics["ongoingProjects"] == 2
    assert manager_metrics["estimatedPipelineValue"] == 600.0
    assert manager_metrics["projectRevenue"] == 300.0
    assert {activity["title"] for activity in manager_summary_response.json()["recentActivity"]} == {
        "Owner lead activity",
        "Other lead activity",
        "Unassigned lead activity",
    }

    admin_summary_response = client.get("/api/v1/dashboard/summary", headers=admin_headers)
    assert admin_summary_response.status_code == 200
    assert admin_summary_response.json()["metrics"] == manager_metrics

    assert client.get("/api/v1/dashboard/summary", headers=other_headers).json()["metrics"]["totalLeads"] == 1
    customer_token = create_access_token(customer_user_id)
    customer_dashboard = client.get(
        "/api/v1/dashboard/summary",
        headers={"Authorization": f"Bearer {customer_token}"},
    )
    assert customer_dashboard.status_code == 403
    assert client.get("/api/v1/dashboard/summary").status_code == 401
    assert client.get(
        "/api/v1/dashboard/summary",
        headers={"Authorization": "Bearer invalid-token"},
    ).status_code == 401


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


def test_customer_profile_uses_explicit_account_relationship(client):
    admin_headers = auth_headers(client, email="profile-admin@solara.test")
    staff_headers_for_owner = staff_headers(client, "profile-staff@solara.test", "Sales Rep")
    first_register = client.post(
        "/api/v1/auth/register",
        json={
            "name": "Profile Customer",
            "email": "profile-customer@solara.test",
            "password": "password123",
        },
    )
    second_register = client.post(
        "/api/v1/auth/register",
        json={
            "name": "Other Customer",
            "email": "other-customer@solara.test",
            "password": "password123",
        },
    )
    assert first_register.status_code == second_register.status_code == 201

    def login_headers(email):
        response = client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": "password123"},
        )
        assert response.status_code == 200
        token = response.json()["access_token"]
        return {"Authorization": "Bearer " + token}

    customer_headers = login_headers("profile-customer@solara.test")
    other_customer_headers = login_headers("other-customer@solara.test")

    unlinked = client.get("/api/v1/customers/me", headers=customer_headers)
    assert unlinked.status_code == 404
    assert client.patch(
        "/api/v1/customers/me",
        json={"location": "Spoofed City"},
        headers=customer_headers,
    ).status_code == 404

    with SessionLocal() as db:
        customer_user_id = db.query(User.id).filter(
            User.email == "profile-customer@solara.test"
        ).scalar()
        other_user_id = db.query(User.id).filter(
            User.email == "other-customer@solara.test"
        ).scalar()

    created = client.post(
        "/api/v1/customers",
        json={
            "name": "Linked Customer",
            "contact": "profile-customer@solara.test",
            "email": "profile-customer@solara.test",
            "location": "Pune",
            "account_user_id": customer_user_id,
        },
        headers=admin_headers,
    )
    assert created.status_code == 201
    customer_id = created.json()["data"]["id"]

    own_profile = client.get("/api/v1/customers/me", headers=customer_headers)
    assert own_profile.status_code == 200
    assert own_profile.json()["data"]["id"] == customer_id
    assert own_profile.json()["data"]["account_user_id"] == customer_user_id
    assert client.get(f"/api/v1/customers/{customer_id}", headers=customer_headers).status_code == 403
    assert client.patch(
        f"/api/v1/customers/{customer_id}",
        json={"location": "Unauthorized City"},
        headers=customer_headers,
    ).status_code == 403

    updated_profile = client.patch(
        "/api/v1/customers/me",
        json={"location": "Mumbai", "phone": "+91 90000 00000"},
        headers=customer_headers,
    )
    assert updated_profile.status_code == 200
    assert updated_profile.json()["data"]["location"] == "Mumbai"
    assert updated_profile.json()["data"]["phone"] == "+91 90000 00000"
    assert client.get("/api/v1/customers/me", headers=other_customer_headers).status_code == 404

    with SessionLocal() as db:
        linked_user = db.query(User).filter(
            User.email == "profile-customer@solara.test"
        ).one()
        linked_user.role = "Sales Rep"
        db.commit()
    assert client.get("/api/v1/customers/me", headers=customer_headers).status_code == 403
    with SessionLocal() as db:
        linked_user = db.query(User).filter(
            User.email == "profile-customer@solara.test"
        ).one()
        linked_user.role = "Customer"
        db.commit()

    denied_link = client.post(
        "/api/v1/customers",
        json={
            "name": "Staff Cannot Link",
            "contact": "staff@example.test",
            "location": "Pune",
            "account_user_id": other_user_id,
        },
        headers=staff_headers_for_owner,
    )
    assert denied_link.status_code == 403

    duplicate_link = client.post(
        "/api/v1/customers",
        json={
            "name": "Duplicate Link",
            "contact": "duplicate@example.test",
            "location": "Pune",
            "account_user_id": customer_user_id,
        },
        headers=admin_headers,
    )
    assert duplicate_link.status_code == 400
    invalid_link = client.post(
        "/api/v1/customers",
        json={
            "name": "Invalid Link",
            "contact": "invalid@example.test",
            "location": "Pune",
            "account_user_id": 999999,
        },
        headers=admin_headers,
    )
    assert invalid_link.status_code == 400

    manager_headers = staff_headers(client, "profile-manager@solara.test", "Manager")
    with SessionLocal() as db:
        staff_user_id = db.query(User.id).filter(
            User.email == "profile-staff@solara.test"
        ).scalar()
    manager_link = client.post(
        "/api/v1/customers",
        json={
            "name": "Manager Linked Customer",
            "contact": "other-customer@solara.test",
            "location": "Pune",
            "assigned_user_id": staff_user_id,
            "account_user_id": other_user_id,
        },
        headers=manager_headers,
    )
    assert manager_link.status_code == 201
    manager_link_data = manager_link.json()["data"]
    assert manager_link_data["assigned_user_id"] == staff_user_id
    assert manager_link_data["account_user_id"] == other_user_id
    assert client.get("/api/v1/customers/me", headers=other_customer_headers).json()["data"]["id"] == (
        manager_link_data["id"]
    )

    with SessionLocal() as db:
        linked = db.query(Customer).filter(Customer.id == customer_id).one()
        assert linked.location == "Mumbai"
        assert db.query(Customer).filter(Customer.account_user_id == other_user_id).count() == 1


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


def test_project_status_transition_matrix_is_enforced(client):
    admin_headers = auth_headers(client, email="project-transition-admin@solara.test")
    route_by_target = {
        "In Progress": "start",
        "On Hold": "hold",
        "Completed": "complete",
        "Cancelled": "cancel",
    }
    allowed = {
        "Planning": {"In Progress", "Cancelled"},
        "In Progress": {"Completed", "On Hold", "Cancelled"},
        "On Hold": {"In Progress", "Cancelled"},
        "Completed": set(),
        "Cancelled": set(),
    }
    states = ["Planning", "In Progress", "On Hold", "Completed", "Cancelled"]

    with Session(engine) as db:
        admin_id = db.query(User.id).filter(User.email == "project-transition-admin@solara.test").scalar()

    for current_status in states:
        for target_status in states:
            with Session(engine) as db:
                project = Project(
                    name=f"{current_status} to {target_status}",
                    category="Residential",
                    location="Pune",
                    capacity="5 kW",
                    status=current_status,
                    assigned_user_id=admin_id,
                    is_public=False,
                )
                db.add(project)
                db.commit()
                project_id = project.id

            response = client.post(
                f"/api/v1/projects/{project_id}/{route_by_target[target_status]}",
                headers=admin_headers,
            )
            transition_allowed = (
                current_status == target_status
                or target_status in allowed[current_status]
            )
            assert response.status_code == (200 if transition_allowed else 409), (
                current_status,
                target_status,
                response.text,
            )
            with Session(engine) as db:
                stored_status = db.query(Project.status).filter(Project.id == project_id).scalar()
                assert stored_status == (target_status if transition_allowed else current_status)


def test_project_creation_starts_in_planning_and_rejects_status_bypass(client):
    headers = auth_headers(client, email="project-create-status@solara.test")
    payload = {
        "name": "New Planning Project",
        "category": "Residential",
        "location": "Pune",
        "capacity": "5 kW",
    }
    created = client.post("/api/v1/projects", json=payload, headers=headers)
    assert created.status_code == 201
    assert created.json()["data"]["status"] == "Planning"

    bypass = client.post(
        "/api/v1/projects",
        json={**payload, "name": "Completed at Creation", "status": "Completed"},
        headers=headers,
    )
    assert bypass.status_code == 409

    extra_create_field = client.post(
        "/api/v1/projects",
        json={**payload, "name": "Unexpected Field", "role": "Admin"},
        headers=headers,
    )
    assert extra_create_field.status_code == 422
    extra_update_field = client.patch(
        f"/api/v1/projects/{created.json()['data']['id']}",
        json={"password_hash": "not-an-approved-field"},
        headers=headers,
    )
    assert extra_update_field.status_code == 422


def test_project_status_updates_require_ownership_and_use_workflows(client):
    owner_headers = staff_headers(client, "project-status-owner@solara.test", "Sales Rep")
    other_headers = staff_headers(client, "project-status-other@solara.test", "Support")
    with Session(engine) as db:
        owner_id = db.query(User.id).filter(User.email == "project-status-owner@solara.test").scalar()
        project = Project(
            name="Owned project status test",
            category="Residential",
            location="Pune",
            capacity="5 kW",
            status="Planning",
            assigned_user_id=owner_id,
            is_public=False,
        )
        db.add(project)
        db.commit()
        project_id = project.id

    assert client.patch(
        f"/api/v1/projects/{project_id}",
        json={"status": "Completed"},
        headers=owner_headers,
    ).status_code == 409
    assert client.patch(
        f"/api/v1/projects/{project_id}",
        json={"status": "Not a project status"},
        headers=owner_headers,
    ).status_code == 422
    assert client.patch(
        f"/api/v1/projects/{project_id}",
        json={"status": "In Progress", "name": "Validated transition"},
        headers=other_headers,
    ).status_code == 404

    updated = client.patch(
        f"/api/v1/projects/{project_id}",
        json={"status": "In Progress", "name": "Validated transition"},
        headers=owner_headers,
    )
    assert updated.status_code == 200
    assert updated.json()["data"]["status"] == "In Progress"
    assert updated.json()["data"]["name"] == "Validated transition"
    with Session(engine) as db:
        assert (
            db.query(Activity.id)
            .filter(Activity.entity_type == "project", Activity.entity_id == project_id)
            .count()
            == 1
        )

    assert client.post(f"/api/v1/projects/{project_id}/hold").status_code == 401


def test_concurrent_project_transition_is_serialized(client):
    if engine.dialect.name != "postgresql":
        pytest.skip("PostgreSQL row-lock behavior requires the PostgreSQL test backend")

    auth_headers(client, email="project-transition-concurrency@solara.test")
    with Session(engine) as db:
        user = db.query(User).filter(User.email == "project-transition-concurrency@solara.test").one()
        project = Project(
            name="Concurrent transition",
            category="Residential",
            location="Pune",
            capacity="5 kW",
            status="Planning",
            assigned_user_id=user.id,
            is_public=False,
        )
        db.add(project)
        db.commit()
        project_id = project.id
        user_id = user.id

    def start_once():
        with Session(engine) as db:
            try:
                CRMService.project_start_workflow(db, project_id, user_id)
                return 200
            except HTTPException as exc:
                return exc.status_code

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(lambda _: start_once(), range(2)))

    assert sorted(results) == [200, 409]
    with Session(engine) as db:
        assert (
            db.query(Activity.id)
            .filter(Activity.entity_type == "project", Activity.entity_id == project_id)
            .count()
            == 1
        )


def test_project_transition_rolls_back_if_customer_recalculation_fails(client, monkeypatch):
    admin_headers = auth_headers(client, email="project-transition-rollback@solara.test")
    with Session(engine) as db:
        admin_id = db.query(User.id).filter(User.email == "project-transition-rollback@solara.test").scalar()
        customer = Customer(name="Transition rollback customer", contact="123", location="Pune")
        db.add(customer)
        db.flush()
        project = Project(
            name="Transition rollback project",
            category="Residential",
            location="Pune",
            capacity="5 kW",
            status="In Progress",
            customer_id=customer.id,
            assigned_user_id=admin_id,
            is_public=False,
        )
        db.add(project)
        db.commit()
        project_id = project.id

    def fail_recalculation(_db, _customer_id):
        raise RuntimeError("injected customer recalculation failure")

    monkeypatch.setattr(
        CRMService,
        "recalculate_customer_status",
        staticmethod(fail_recalculation),
    )
    response = client.post(
        f"/api/v1/projects/{project_id}/complete",
        headers=admin_headers,
    )
    assert response.status_code == 500
    with Session(engine) as db:
        assert db.query(Project.status).filter(Project.id == project_id).scalar() == "In Progress"
        assert (
            db.query(Activity.id)
            .filter(Activity.entity_type == "project", Activity.entity_id == project_id)
            .count()
            == 0
        )


def test_project_access_is_scoped_to_roles_assignments_and_customers(client):
    admin_headers = auth_headers(client, email="project-auth-admin@solara.test")
    manager_headers = staff_headers(client, "project-auth-manager@solara.test", "Manager")
    owner_headers = staff_headers(client, "project-auth-owner@solara.test", "Sales Rep")
    other_headers = staff_headers(client, "project-auth-other@solara.test", "Support")

    def register_customer(name, email):
        register = client.post(
            "/api/v1/auth/register",
            json={"name": name, "email": email, "password": "password123"},
        )
        assert register.status_code == 201
        login = client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": "password123"},
        )
        assert login.status_code == 200
        return register.json()["data"], {"Authorization": "Bearer " + login.json()["access_token"]}

    customer_user, customer_headers = register_customer(
        "Linked Project Customer", "linked-project-customer@solara.test"
    )
    with SessionLocal() as db:
        owner_id = db.query(User.id).filter(User.email == "project-auth-owner@solara.test").scalar()
        other_id = db.query(User.id).filter(User.email == "project-auth-other@solara.test").scalar()

    def create_customer(name, email, assigned_id, account_user_id=None, headers=admin_headers):
        result = client.post(
            "/api/v1/customers",
            json={
                "name": name,
                "contact": email,
                "email": email,
                "location": "Pune",
                "assigned_user_id": assigned_id,
                "account_user_id": account_user_id,
            },
            headers=headers,
        )
        assert result.status_code == 201, result.text
        return result.json()["data"]["id"]

    owner_customer_id = create_customer(
        "Owner Project Customer", "owner-project-customer@solara.test", owner_id
    )
    other_customer_id = create_customer(
        "Other Project Customer", "other-project-customer@solara.test", other_id
    )
    account_customer_id = create_customer(
        "Linked Project Customer",
        "linked-project-customer@solara.test",
        owner_id,
        customer_user["id"],
    )

    def project_payload(name, **kwargs):
        return {
            "name": name,
            "category": "Residential",
            "location": "Pune",
            "capacity": "5 kW",
            **kwargs,
        }

    def create_project(name, headers, **kwargs):
        result = client.post(
            "/api/v1/projects",
            json=project_payload(name, **kwargs),
            headers=headers,
        )
        assert result.status_code == 201, result.text
        return result.json()["data"]

    owner_project = create_project(
        "Owner Private Project",
        owner_headers,
        customer_id=owner_customer_id,
        is_public=False,
    )
    other_project = create_project(
        "Other Private Project",
        manager_headers,
        customer_id=other_customer_id,
        assigned_user_id=other_id,
        is_public=False,
    )
    customer_project = create_project(
        "Customer Private Project",
        manager_headers,
        customer_id=account_customer_id,
        assigned_user_id=other_id,
        is_public=False,
    )
    manager_only_project = create_project(
        "Unassigned Private Project",
        manager_headers,
        is_public=False,
    )
    public_project = create_project("Public Project", admin_headers, is_public=True)

    assert owner_project["assigned_user_id"] == owner_id
    assert client.get("/api/v1/projects").status_code == 200
    public_ids = {item["id"] for item in client.get("/api/v1/projects").json()["data"]}
    assert public_project["id"] in public_ids
    assert owner_project["id"] not in public_ids
    assert client.get(
        f"/api/v1/projects/{owner_project['id']}", headers=owner_headers
    ).status_code == 200
    assert client.get(
        f"/api/v1/projects/{owner_project['id']}", headers=other_headers
    ).status_code == 404
    assert client.get(f"/api/v1/projects/{owner_project['id']}").status_code == 404
    assert client.get(
        f"/api/v1/projects/{other_project['id']}", headers=owner_headers
    ).status_code == 404
    assert client.get(
        f"/api/v1/projects/{owner_project['id']}/related-data",
        headers=owner_headers,
    ).status_code == 200
    assert client.get(
        f"/api/v1/projects/{other_project['id']}/related-data",
        headers=owner_headers,
    ).status_code == 404
    assert client.get(
        f"/api/v1/projects/{other_project['id']}/related-data",
        headers=manager_headers,
    ).status_code == 200
    assert client.get(
        f"/api/v1/projects/{manager_only_project['id']}", headers=owner_headers
    ).status_code == 404
    assert client.get(
        f"/api/v1/projects/{customer_project['id']}", headers=customer_headers
    ).status_code == 200
    assert client.patch(
        f"/api/v1/projects/{customer_project['id']}",
        json={"name": "Customer Changed Project"},
        headers=customer_headers,
    ).status_code == 403
    assert client.delete(
        f"/api/v1/projects/{customer_project['id']}", headers=customer_headers
    ).status_code == 403
    assert client.get(
        f"/api/v1/projects/{other_project['id']}", headers=customer_headers
    ).status_code == 404
    assert client.get(
        f"/api/v1/projects/{other_project['id']}", headers=other_headers
    ).status_code == 200
    customer_private_projects = client.get(
        "/api/v1/projects", params={"is_public": False}, headers=customer_headers
    ).json()["data"]
    assert {item["id"] for item in customer_private_projects} == {customer_project["id"]}

    owner_list = client.get("/api/v1/projects", headers=owner_headers)
    assert owner_list.status_code == 200
    owner_ids = {item["id"] for item in owner_list.json()["data"]}
    assert owner_project["id"] in owner_ids
    assert public_project["id"] in owner_ids
    assert other_project["id"] not in owner_ids
    assert manager_only_project["id"] not in owner_ids
    assert client.get(
        "/api/v1/projects", params={"search": "Other Private Project"}, headers=owner_headers
    ).json()["data"] == []
    owner_private_projects = client.get(
        "/api/v1/projects", params={"is_public": False}, headers=owner_headers
    ).json()["data"]
    assert all(not item["is_public"] for item in owner_private_projects)
    assert {item["id"] for item in owner_private_projects}.issubset(
        {owner_project["id"], customer_project["id"]}
    )
    assert {item["id"] for item in client.get(
        "/api/v1/projects", headers=manager_headers
    ).json()["data"]}.issuperset(
        {
            owner_project["id"],
            other_project["id"],
            customer_project["id"],
            manager_only_project["id"],
            public_project["id"],
        }
    )

    customer_cannot_create = client.post(
        "/api/v1/projects",
        json=project_payload("Customer Project Attempt"),
        headers=customer_headers,
    )
    assert customer_cannot_create.status_code == 403

    cannot_reassign_create = client.post(
        "/api/v1/projects",
        json=project_payload(
            "Forged Assignment",
            customer_id=owner_customer_id,
            assigned_user_id=other_id,
        ),
        headers=owner_headers,
    )
    assert cannot_reassign_create.status_code == 403
    cannot_link_other_customer = client.post(
        "/api/v1/projects",
        json=project_payload("Forged Customer", customer_id=other_customer_id),
        headers=owner_headers,
    )
    assert cannot_link_other_customer.status_code == 400
    invalid_customer = client.post(
        "/api/v1/projects",
        json=project_payload("Missing Customer", customer_id=999999),
        headers=manager_headers,
    )
    assert invalid_customer.status_code == 400
    customer_as_assignee = client.post(
        "/api/v1/projects",
        json=project_payload("Customer As Staff", assigned_user_id=customer_user["id"]),
        headers=manager_headers,
    )
    assert customer_as_assignee.status_code == 400

    cannot_update_others = client.patch(
        f"/api/v1/projects/{other_project['id']}",
        json={"name": "Hijacked Project"},
        headers=owner_headers,
    )
    assert cannot_update_others.status_code == 404
    cannot_change_assignment = client.patch(
        f"/api/v1/projects/{owner_project['id']}",
        json={"assigned_user_id": other_id},
        headers=owner_headers,
    )
    assert cannot_change_assignment.status_code == 403
    cannot_change_customer = client.patch(
        f"/api/v1/projects/{owner_project['id']}",
        json={"customer_id": other_customer_id},
        headers=owner_headers,
    )
    assert cannot_change_customer.status_code == 400
    cannot_edit_public_unowned = client.patch(
        f"/api/v1/projects/{public_project['id']}",
        json={"name": "Public project hijacked"},
        headers=owner_headers,
    )
    assert cannot_edit_public_unowned.status_code == 404

    owner_update = client.patch(
        f"/api/v1/projects/{owner_project['id']}",
        json={"status": "In Progress", "name": "Owner Updated Project"},
        headers=owner_headers,
    )
    assert owner_update.status_code == 200
    invalid_manager_assignment = client.patch(
        f"/api/v1/projects/{manager_only_project['id']}",
        json={"assigned_user_id": 999999},
        headers=manager_headers,
    )
    assert invalid_manager_assignment.status_code == 400
    manager_update = client.patch(
        f"/api/v1/projects/{other_project['id']}",
        json={"assigned_user_id": owner_id},
        headers=manager_headers,
    )
    assert manager_update.status_code == 200
    assert manager_update.json()["data"]["assigned_user_id"] == owner_id
    assert client.get(
        f"/api/v1/projects/{other_project['id']}", headers=owner_headers
    ).status_code == 200
    assert client.get(
        "/api/v1/projects/999999", headers=manager_headers
    ).status_code == 404
    assert client.patch(
        "/api/v1/projects/999999", json={"name": "Missing"}, headers=manager_headers
    ).status_code == 404
    assert client.delete(
        f"/api/v1/projects/{owner_project['id']}", headers=owner_headers
    ).status_code == 403
    assert client.delete(
        f"/api/v1/projects/{manager_only_project['id']}", headers=manager_headers
    ).status_code == 200
    assert client.delete(
        f"/api/v1/projects/{public_project['id']}", headers=admin_headers
    ).status_code == 200


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


def test_system_settings_defaults_updates_and_persist_across_requests(client):
    admin_headers = auth_headers(client, email="system-settings-admin@solara.test")
    manager_headers = staff_headers(client, "system-settings-manager@solara.test", "Manager")

    defaults = client.get("/api/v1/settings", headers=admin_headers)
    assert defaults.status_code == 200
    assert defaults.json()["data"]["company_name"] == "SOLARA Energy Solutions"
    assert defaults.json()["data"]["email_notifications"] is True

    updated = client.put(
        "/api/v1/settings",
        json={
            "company_name": "  Solara Workspace  ",
            "support_email": "CARE@SOLARA.TEST",
            "email_notifications": False,
            "sms_notifications": True,
            "lead_alerts": False,
            "two_factor_auth": True,
        },
        headers=manager_headers,
    )
    assert updated.status_code == 200
    assert updated.json()["success"] is True
    assert updated.json()["data"]["company_name"] == "Solara Workspace"
    assert updated.json()["data"]["support_email"] == "care@solara.test"
    assert updated.json()["data"]["sms_notifications"] is True

    refreshed = client.get("/api/v1/settings", headers=admin_headers)
    assert refreshed.status_code == 200
    for field, expected in {
        "company_name": "Solara Workspace",
        "support_email": "care@solara.test",
        "email_notifications": False,
        "sms_notifications": True,
        "lead_alerts": False,
        "two_factor_auth": True,
    }.items():
        assert refreshed.json()["data"][field] == expected

    with SessionLocal() as db:
        settings_rows = db.query(SystemSettings).all()
        assert len(settings_rows) == 1
        assert settings_rows[0].company_name == "Solara Workspace"
        assert settings_rows[0].two_factor_auth is True


def test_system_settings_reject_invalid_and_unapproved_fields(client):
    headers = auth_headers(client, email="system-settings-validation@solara.test")
    assert client.get("/api/v1/settings", headers=headers).status_code == 200

    invalid_updates = [
        {"company_name": "   "},
        {"support_email": "not-an-email"},
        {"email_notifications": "false"},
        {"sms_notifications": 1},
        {"two_factor_auth": True, "user_id": 12345},
        {"id": 2},
        {"updated_at": "2026-01-01T00:00:00Z"},
    ]
    for update in invalid_updates:
        response = client.put("/api/v1/settings", json=update, headers=headers)
        assert response.status_code == 422, (update, response.text)

    unchanged = client.get("/api/v1/settings", headers=headers)
    assert unchanged.json()["data"]["company_name"] == "SOLARA Energy Solutions"
    assert unchanged.json()["data"]["lead_alerts"] is True


def test_system_settings_require_existing_admin_or_manager_authorization(client):
    manager_headers = staff_headers(client, "system-settings-authorized-manager@solara.test", "Manager")
    staff_user_headers = staff_headers(client, "system-settings-unauthorized-staff@solara.test", "Sales Rep")
    assert client.get("/api/v1/settings", headers=manager_headers).status_code == 200

    assert client.get("/api/v1/settings").status_code == 401
    assert client.put(
        "/api/v1/settings",
        json={"two_factor_auth": True},
    ).status_code == 401
    assert client.get("/api/v1/settings", headers=staff_user_headers).status_code == 403
    denied_update = client.put(
        "/api/v1/settings",
        json={"company_name": "Unauthorized Workspace", "two_factor_auth": True},
        headers=staff_user_headers,
    )
    assert denied_update.status_code == 403

    persisted = client.get("/api/v1/settings", headers=manager_headers)
    assert persisted.json()["data"]["company_name"] == "SOLARA Energy Solutions"
    assert persisted.json()["data"]["two_factor_auth"] is False


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


def test_site_survey_access_is_scoped_and_relationships_are_validated(client):
    admin_headers = auth_headers(client, email="survey-admin@solara.test")
    manager_headers = staff_headers(client, "survey-manager@solara.test", "Manager")
    assigned_headers = staff_headers(client, "survey-assigned@solara.test", "Sales Rep")
    other_staff_headers = staff_headers(client, "survey-other-staff@solara.test", "Support")

    def register_customer(name, email):
        registered = client.post(
            "/api/v1/auth/register",
            json={"name": name, "email": email, "password": "password123"},
        )
        assert registered.status_code == 201
        token = client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": "password123"},
        )
        assert token.status_code == 200
        return registered.json()["data"], {"Authorization": "Bearer " + token.json()["access_token"]}

    first_user, first_customer_headers = register_customer(
        "Survey Customer One", "survey-customer-one@solara.test"
    )
    second_user, second_customer_headers = register_customer(
        "Survey Customer Two", "survey-customer-two@solara.test"
    )
    with SessionLocal() as db:
        assigned_user_id = db.query(User.id).filter(
            User.email == "survey-assigned@solara.test"
        ).scalar()
        other_staff_id = db.query(User.id).filter(
            User.email == "survey-other-staff@solara.test"
        ).scalar()

    def create_customer(name, email, account_user_id):
        response = client.post(
            "/api/v1/customers",
            json={
                "name": name,
                "contact": email,
                "email": email,
                "location": "Pune",
                "assigned_user_id": assigned_user_id,
                "account_user_id": account_user_id,
            },
            headers=admin_headers,
        )
        assert response.status_code == 201
        return response.json()["data"]["id"]

    customer_one_id = create_customer(
        "Survey Customer One", "survey-customer-one@solara.test", first_user["id"]
    )
    customer_two_id = create_customer(
        "Survey Customer Two", "survey-customer-two@solara.test", second_user["id"]
    )
    baseline_survey_count = client.get(
        "/api/v1/site-surveys", headers=manager_headers
    ).json()["total"]

    def create_project(name, customer_id, assigned_id):
        response = client.post(
            "/api/v1/projects",
            json={
                "name": name,
                "category": "Residential",
                "location": "Pune",
                "capacity": "5 kW",
                "customer_id": customer_id,
                "assigned_user_id": assigned_id,
            },
            headers=admin_headers,
        )
        assert response.status_code == 201
        return response.json()["data"]["id"]

    project_one_id = create_project("Survey Project One", customer_one_id, assigned_user_id)
    project_two_id = create_project("Survey Project Two", customer_two_id, other_staff_id)

    def create_survey(name, customer_id, project_id, assigned_id):
        response = client.post(
            "/api/v1/site-surveys",
            json={
                "customer_name": name,
                "location": "Pune",
                "survey_date": "2026-10-20",
                "time_slot": "10:00 AM",
                "customer_id": customer_id,
                "project_id": project_id,
                "assigned_user_id": assigned_id,
            },
            headers=manager_headers,
        )
        assert response.status_code == 201
        return response.json()["data"]["id"]

    survey_one_id = create_survey(
        "Survey Customer One", customer_one_id, project_one_id, assigned_user_id
    )
    survey_two_id = create_survey(
        "Survey Customer Two", customer_two_id, project_two_id, other_staff_id
    )

    public_booking = client.post(
        "/api/v1/site-surveys",
        json={
            "customer_name": "Public Booking",
            "location": "Pune",
            "survey_date": "2026-10-21",
            "time_slot": "11:00 AM",
            "customer_id": customer_two_id,
            "project_id": project_two_id,
            "assigned_user_id": other_staff_id,
            "status": "Completed",
            "assigned_to": "Forged Surveyor",
        },
    )
    assert public_booking.status_code == 201
    assert public_booking.json()["data"]["customer_id"] is None
    assert public_booking.json()["data"]["project_id"] is None
    assert public_booking.json()["data"]["assigned_user_id"] is None
    assert public_booking.json()["data"]["status"] == "Scheduled"
    assert public_booking.json()["data"]["assigned_to"] == "Rahul"
    customer_booking = client.post(
        "/api/v1/site-surveys",
        json={
            "customer_name": "Survey Customer One",
            "location": "Pune",
            "survey_date": "2026-10-22",
            "time_slot": "12:00 PM",
            "customer_id": customer_one_id,
            "project_id": project_one_id,
            "assigned_user_id": other_staff_id,
            "status": "Completed",
        },
        headers=first_customer_headers,
    )
    assert customer_booking.status_code == 201
    assert customer_booking.json()["data"]["customer_id"] == customer_one_id
    assert customer_booking.json()["data"]["project_id"] == project_one_id
    assert customer_booking.json()["data"]["assigned_user_id"] is None
    assert customer_booking.json()["data"]["status"] == "Scheduled"
    denied_customer_booking = client.post(
        "/api/v1/site-surveys",
        json={
            "customer_name": "Survey Customer One",
            "location": "Pune",
            "survey_date": "2026-10-23",
            "time_slot": "01:00 PM",
            "customer_id": customer_two_id,
            "project_id": project_two_id,
        },
        headers=first_customer_headers,
    )
    assert denied_customer_booking.status_code == 403

    assert client.get("/api/v1/site-surveys").status_code == 401
    assert client.get(f"/api/v1/site-surveys/{survey_one_id}").status_code == 401
    assert client.patch(
        f"/api/v1/site-surveys/{survey_one_id}", json={"status": "Completed"}
    ).status_code == 401
    assert client.delete(f"/api/v1/site-surveys/{survey_one_id}").status_code == 401

    customer_list = client.get("/api/v1/site-surveys", headers=first_customer_headers)
    assert customer_list.status_code == 200
    assert {survey["id"] for survey in customer_list.json()["items"]} == {
        survey_one_id,
        customer_booking.json()["data"]["id"],
    }
    assert client.get(
        f"/api/v1/site-surveys/{survey_one_id}", headers=first_customer_headers
    ).status_code == 200
    assert client.get(
        f"/api/v1/site-surveys/{survey_two_id}", headers=first_customer_headers
    ).status_code == 404
    assert client.get(
        "/api/v1/site-surveys", headers=second_customer_headers
    ).json()["items"][0]["id"] == survey_two_id
    assert client.patch(
        f"/api/v1/site-surveys/{survey_one_id}",
        json={"notes": "Customer cannot change survey"},
        headers=first_customer_headers,
    ).status_code == 403
    assert client.delete(
        f"/api/v1/site-surveys/{survey_one_id}", headers=first_customer_headers
    ).status_code == 403

    own_list = client.get("/api/v1/site-surveys", headers=assigned_headers)
    assert own_list.status_code == 200
    assert {survey["id"] for survey in own_list.json()["items"]} == {survey_one_id}
    assert client.get(
        f"/api/v1/site-surveys/{survey_one_id}", headers=assigned_headers
    ).status_code == 200
    assert client.get(
        f"/api/v1/site-surveys/{survey_two_id}", headers=assigned_headers
    ).status_code == 404
    assert client.patch(
        f"/api/v1/site-surveys/{survey_two_id}",
        json={"status": "Completed"},
        headers=assigned_headers,
    ).status_code == 404

    forbidden_assignment = client.patch(
        f"/api/v1/site-surveys/{survey_one_id}",
        json={"assigned_user_id": other_staff_id},
        headers=assigned_headers,
    )
    assert forbidden_assignment.status_code == 403
    mismatched_project = client.patch(
        f"/api/v1/site-surveys/{survey_one_id}",
        json={"project_id": project_two_id},
        headers=assigned_headers,
    )
    assert mismatched_project.status_code == 400
    mismatched_customer = client.patch(
        f"/api/v1/site-surveys/{survey_one_id}",
        json={"customer_id": customer_two_id},
        headers=assigned_headers,
    )
    assert mismatched_customer.status_code == 400
    invalid_assignment = client.post(
        "/api/v1/site-surveys",
        json={
            "customer_name": "Invalid Assignment",
            "location": "Pune",
            "survey_date": "2026-10-22",
            "time_slot": "11:00 AM",
            "customer_id": customer_one_id,
            "assigned_user_id": first_user["id"],
        },
        headers=manager_headers,
    )
    assert invalid_assignment.status_code == 400

    staff_update = client.patch(
        f"/api/v1/site-surveys/{survey_one_id}",
        json={"status": "In Progress", "notes": "Site access confirmed"},
        headers=assigned_headers,
    )
    assert staff_update.status_code == 200
    assert staff_update.json()["data"]["status"] == "In Progress"
    assert client.get("/api/v1/site-surveys", headers=other_staff_headers).json()["total"] == 1
    assert client.get("/api/v1/site-surveys", headers=manager_headers).json()["total"] == (
        baseline_survey_count + 4
    )
    assert client.get("/api/v1/site-surveys", headers=admin_headers).json()["total"] == (
        baseline_survey_count + 4
    )
    assert client.get(
        "/api/v1/site-surveys/999999", headers=manager_headers
    ).status_code == 404
    admin_assignment = client.patch(
        f"/api/v1/site-surveys/{survey_one_id}",
        json={"assigned_user_id": other_staff_id},
        headers=admin_headers,
    )
    assert admin_assignment.status_code == 200
    assert admin_assignment.json()["data"]["assigned_user_id"] == other_staff_id
    manager_assignment = client.patch(
        f"/api/v1/site-surveys/{survey_one_id}",
        json={"assigned_user_id": assigned_user_id},
        headers=manager_headers,
    )
    assert manager_assignment.status_code == 200
    assert manager_assignment.json()["data"]["assigned_user_id"] == assigned_user_id

    assert client.delete(
        f"/api/v1/site-surveys/{survey_one_id}", headers=assigned_headers
    ).status_code == 403
    deleted = client.delete(
        f"/api/v1/site-surveys/{survey_two_id}", headers=manager_headers
    )
    assert deleted.status_code == 200
    assert client.get(
        f"/api/v1/site-surveys/{survey_two_id}", headers=admin_headers
    ).status_code == 404
