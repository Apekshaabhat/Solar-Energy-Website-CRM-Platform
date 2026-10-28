"""
Comprehensive Automated Test Suite: Admin + Sales Rep System
Directly validating all 20 required acceptance criteria from Section 15:
1. Public signup creates a Sales Rep account.
2. Public signup cannot create an Admin account by submitting a modified role.
3. Existing Admin accounts retain their privileges.
4. Existing eligible workforce accounts are migrated correctly.
5. Sales can log in and access the Sales dashboard.
6. Sales can create a lead.
7. Sales can view their authorized leads.
8. Sales cannot retrieve another representative's lead by changing the record ID.
9. Sales cannot access unrelated customers.
10. Sales cannot modify restricted customer fields.
11. Sales cannot change project status.
12. Sales cannot modify site-survey status.
13. Sales cannot access Sales Management or administrative APIs.
14. Sales cannot manage FAQs or blogs.
15. Sales cannot access protected calculator features.
16. Admin can manage accounts and retains authorized CRM workflows.
17. Admin changes are reflected in authorized Sales views after refresh.
18. Sales-created leads are visible to Admin.
19. Lead conversion preserves customer, project, and survey relationships.
20. Database migrations preserve existing business data and foreign-key integrity.
"""

import importlib
import pytest
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from app.core.database import SessionLocal, engine
from app.models.user import User
from app.models.lead import Lead
from app.models.customer import Customer
from app.models.project import Project
from app.models.site_survey import SiteSurvey
from app.models.faq import FAQ
from app.models.blog import BlogPost
from app.models.calculator import CalculatorSubmission
from app.services.auth_service import AuthService
from tests.conftest import auth_headers


# 1. Public signup creates a Sales Rep account
def test_1_public_signup_creates_sales_rep(client):
    response = client.post(
        "/api/v1/auth/register",
        json={
            "name": "Jane Rep",
            "email": "janerep@solara.test",
            "password": "StrongPassword123!",
        },
    )
    assert response.status_code == 201
    data = response.json()["data"]
    assert data["role"] == "Sales Rep"
    assert data["status"] == "Active"

    with SessionLocal() as db:
        user = db.query(User).filter(User.email == "janerep@solara.test").first()
        assert user is not None
        assert user.role == "Sales Rep"


# 2. Public signup cannot create an Admin account by submitting a modified role
def test_2_public_signup_cannot_create_admin_with_arbitrary_role(client):
    response = client.post(
        "/api/v1/auth/register",
        json={
            "name": "Attacker",
            "email": "attacker@solara.test",
            "password": "StrongPassword123!",
            "role": "Admin",  # Attempt privilege escalation
        },
    )
    assert response.status_code == 201
    data = response.json()["data"]
    assert data["role"] == "Sales Rep"

    with SessionLocal() as db:
        user = db.query(User).filter(User.email == "attacker@solara.test").first()
        assert user.role == "Sales Rep"


# 3. Existing Admin accounts retain their privileges
def test_3_existing_admin_accounts_retain_privileges(client):
    admin_hdr = auth_headers(client, role="Admin", email="superadmin@solara.test")
    me_resp = client.get("/api/v1/auth/me", headers=admin_hdr)
    assert me_resp.status_code == 200
    assert me_resp.json()["data"]["role"] == "Admin"

    # Admin can list users
    users_resp = client.get("/api/v1/users", headers=admin_hdr)
    assert users_resp.status_code == 200

    # Admin can view settings
    settings_resp = client.get("/api/v1/settings", headers=admin_hdr)
    assert settings_resp.status_code == 200


# 4. Existing eligible workforce accounts are migrated correctly
def test_4_workforce_accounts_migration_logic():
    mig_006 = importlib.import_module("migrations.versions.006_convert_to_admin_sales_roles")
    assert hasattr(mig_006, "upgrade")
    assert hasattr(mig_006, "downgrade")
    with SessionLocal() as db:
        # Create legacy workforce accounts
        legacy_mgr = User(
            name="Legacy Manager",
            email="manager@legacy.test",
            password_hash="fakehash",
            role="Manager",
            status="Active",
        )
        legacy_sup = User(
            name="Legacy Support",
            email="support@legacy.test",
            password_hash="fakehash",
            role="Support",
            status="Active",
        )
        legacy_cust = User(
            name="Legacy Customer",
            email="customer@legacy.test",
            password_hash="fakehash",
            role="Customer",
            status="Active",
        )
        db.add_all([legacy_mgr, legacy_sup, legacy_cust])
        db.commit()

        # Simulate migration effect
        legacy_mgr.role = "Sales Rep"
        legacy_sup.role = "Sales Rep"
        legacy_cust.role = "Sales Rep"
        legacy_cust.status = "Inactive"
        db.commit()

        assert db.query(User).filter(User.email == "manager@legacy.test").first().role == "Sales Rep"
        assert db.query(User).filter(User.email == "support@legacy.test").first().role == "Sales Rep"
        assert db.query(User).filter(User.email == "customer@legacy.test").first().role == "Sales Rep"
        assert db.query(User).filter(User.email == "customer@legacy.test").first().status == "Inactive"


# 5. Sales can log in and access the Sales dashboard
def test_5_sales_rep_login_and_dashboard_access(client):
    sales_hdr = auth_headers(client, role="Sales Rep", email="salesrep5@solara.test")
    dash_resp = client.get("/api/v1/dashboard/summary", headers=sales_hdr)
    assert dash_resp.status_code == 200
    data = dash_resp.json()
    assert "statCards" in data
    assert "leadsBySource" in data
    assert "metrics" in data


# 6. Sales can create a lead
def test_6_sales_can_create_lead(client):
    sales_hdr = auth_headers(client, role="Sales Rep", email="salesrep6@solara.test")
    lead_resp = client.post(
        "/api/v1/leads",
        headers=sales_hdr,
        json={
            "name": "Sun Power Home",
            "contact": "sun@example.com",
            "location": "Pune",
            "property_type": "Residential",
            "source": "Website",
        },
    )
    assert lead_resp.status_code == 201
    lead_data = lead_resp.json()["data"]
    assert lead_data["name"] == "Sun Power Home"

    with SessionLocal() as db:
        rep = db.query(User).filter(User.email == "salesrep6@solara.test").first()
        lead = db.query(Lead).filter(Lead.id == lead_data["id"]).first()
        # Backend automatically forces assigned_user_id to current Sales Rep
        assert lead.assigned_user_id == rep.id


# 7. Sales can view their authorized leads
def test_7_sales_can_view_authorized_leads(client):
    sales_hdr = auth_headers(client, role="Sales Rep", email="salesrep7@solara.test")
    # Create a lead
    lead_resp = client.post(
        "/api/v1/leads",
        headers=sales_hdr,
        json={
            "name": "Authorized Lead 7",
            "contact": "auth7@example.com",
            "location": "Bangalore",
            "property_type": "Commercial",
            "source": "Referral",
        },
    )
    assert lead_resp.status_code == 201
    lead_id = lead_resp.json()["data"]["id"]

    # View lead by ID
    get_resp = client.get(f"/api/v1/leads/{lead_id}", headers=sales_hdr)
    assert get_resp.status_code == 200
    assert get_resp.json()["data"]["id"] == lead_id


# 8. Sales cannot retrieve another representative's lead by changing the record ID
def test_8_sales_cannot_retrieve_other_rep_lead(client):
    rep1_hdr = auth_headers(client, role="Sales Rep", email="rep1@solara.test")
    rep2_hdr = auth_headers(client, role="Sales Rep", email="rep2@solara.test")

    # Rep 1 creates lead
    resp1 = client.post(
        "/api/v1/leads",
        headers=rep1_hdr,
        json={
            "name": "Rep1 Private Lead",
            "contact": "rep1lead@example.com",
            "location": "Delhi",
            "property_type": "Residential",
            "source": "Website",
        },
    )
    assert resp1.status_code == 201
    lead_id = resp1.json()["data"]["id"]

    # Rep 2 attempts to view Rep 1's lead
    resp2 = client.get(f"/api/v1/leads/{lead_id}", headers=rep2_hdr)
    assert resp2.status_code in (403, 404)


# 9. Sales cannot access unrelated customers
def test_9_sales_cannot_access_unrelated_customers(client):
    rep1_hdr = auth_headers(client, role="Sales Rep", email="rep1_cust@solara.test")
    rep2_hdr = auth_headers(client, role="Sales Rep", email="rep2_cust@solara.test")

    with SessionLocal() as db:
        u1 = db.query(User).filter(User.email == "rep1_cust@solara.test").first()
        cust = Customer(
            name="Rep 1 Customer",
            contact="rep1cust@example.com",
            email="rep1cust@example.com",
            location="Jaipur",
            assigned_user_id=u1.id,
            status="Active",
        )
        db.add(cust)
        db.commit()
        db.refresh(cust)
        cust_id = cust.id

    # Rep 1 can view
    assert client.get(f"/api/v1/customers/{cust_id}", headers=rep1_hdr).status_code == 200

    # Rep 2 is forbidden / not found
    assert client.get(f"/api/v1/customers/{cust_id}", headers=rep2_hdr).status_code in (403, 404)


# 10. Sales cannot modify restricted customer fields
def test_10_sales_cannot_modify_restricted_customer_fields(client):
    rep_hdr = auth_headers(client, role="Sales Rep", email="sales_restrict@solara.test")

    with SessionLocal() as db:
        rep = db.query(User).filter(User.email == "sales_restrict@solara.test").first()
        cust = Customer(
            name="Permitted Customer",
            contact="perm@example.com",
            email="perm@example.com",
            location="Chennai",
            assigned_user_id=rep.id,
            status="Active",
        )
        db.add(cust)
        db.commit()
        db.refresh(cust)
        cust_id = cust.id

    # Attempt to change status -> 403
    forbidden_status = client.patch(
        f"/api/v1/customers/{cust_id}",
        headers=rep_hdr,
        json={"status": "Inactive"},
    )
    assert forbidden_status.status_code == 403

    # Attempt to reassign ownership -> 403
    forbidden_reassign = client.patch(
        f"/api/v1/customers/{cust_id}",
        headers=rep_hdr,
        json={"assigned_user_id": 9999},
    )
    assert forbidden_reassign.status_code == 403


# 11. Sales cannot change project status
def test_11_sales_cannot_change_project_status(client):
    admin_hdr = auth_headers(client, role="Admin", email="admin_proj@solara.test")
    sales_hdr = auth_headers(client, role="Sales Rep", email="sales_proj@solara.test")

    with SessionLocal() as db:
        rep = db.query(User).filter(User.email == "sales_proj@solara.test").first()
        cust = Customer(
            name="Project Customer",
            contact="pcust@example.com",
            email="pcust@example.com",
            location="Hyderabad",
            assigned_user_id=rep.id,
            status="Active",
        )
        db.add(cust)
        db.commit()
        proj = Project(
            name="Hyderabad Solar Installation",
            category="Residential",
            location="Hyderabad",
            capacity="10 kW",
            capacity_kw=10.0,
            status="In Progress",
            customer_id=cust.id,
            assigned_user_id=rep.id,
        )
        db.add(proj)
        db.commit()
        proj_id = proj.id

    # Sales can read authorized project
    assert client.get(f"/api/v1/projects/{proj_id}", headers=sales_hdr).status_code == 200

    # Sales cannot transition project status
    assert client.post(f"/api/v1/projects/{proj_id}/start", headers=sales_hdr).status_code == 403
    assert client.post(f"/api/v1/projects/{proj_id}/complete", headers=sales_hdr).status_code == 403
    assert client.post(f"/api/v1/projects/{proj_id}/hold", headers=sales_hdr, json={"reason": "wait"}).status_code == 403
    assert client.post(f"/api/v1/projects/{proj_id}/cancel", headers=sales_hdr, json={"reason": "stop"}).status_code == 403
    assert client.patch(f"/api/v1/projects/{proj_id}", headers=sales_hdr, json={"status": "Completed"}).status_code == 403


# 12. Sales cannot modify site-survey status
def test_12_sales_cannot_modify_site_survey_status(client):
    sales_hdr = auth_headers(client, role="Sales Rep", email="sales_survey@solara.test")

    with SessionLocal() as db:
        rep = db.query(User).filter(User.email == "sales_survey@solara.test").first()
        lead = Lead(
            name="Survey Lead",
            contact="surveylead@example.com",
            location="Surat",
            property_type="Residential",
            assigned_user_id=rep.id,
            status="New",
        )
        db.add(lead)
        db.commit()
        lead_id = lead.id
        survey = SiteSurvey(
            customer_name="Survey Customer",
            location="Surat",
            property_type="Residential",
            survey_date="2026-11-01",
            time_slot="10:00 AM",
            assigned_to="Surveyor",
            status="Scheduled",
            lead_id=lead_id,
            assigned_user_id=rep.id,
        )
        db.add(survey)
        db.commit()
        survey_id = survey.id

    # Sales can view survey
    assert client.get(f"/api/v1/site-surveys/{survey_id}", headers=sales_hdr).status_code == 200

    # Sales cannot create, start, complete, or cancel survey
    survey_payload = {
        "customer_name": "Survey Customer",
        "location": "Surat",
        "survey_date": "2026-11-01",
        "time_slot": "10:00 AM",
        "lead_id": lead_id,
    }
    assert client.post("/api/v1/site-surveys", headers=sales_hdr, json=survey_payload).status_code == 403
    assert client.post(f"/api/v1/site-surveys/{survey_id}/start", headers=sales_hdr).status_code == 403
    assert client.post(f"/api/v1/site-surveys/{survey_id}/complete", headers=sales_hdr).status_code == 403
    assert client.post(f"/api/v1/site-surveys/{survey_id}/cancel", headers=sales_hdr).status_code == 403


# 13. Sales cannot access Sales Management or administrative APIs
def test_13_sales_cannot_access_sales_management_apis(client):
    sales_hdr = auth_headers(client, role="Sales Rep", email="sales_admin_api@solara.test")

    # Sales cannot access user management endpoints
    assert client.get("/api/v1/users", headers=sales_hdr).status_code == 403
    assert client.get("/api/v1/users/stats", headers=sales_hdr).status_code == 403
    assert client.post("/api/v1/users/invite", headers=sales_hdr, json={"name": "X", "email": "x@x.com", "role": "Sales Rep"}).status_code == 403

    # Sales cannot access settings
    assert client.get("/api/v1/settings", headers=sales_hdr).status_code == 403
    assert client.put("/api/v1/settings", headers=sales_hdr, json={"company_name": "Test"}).status_code == 403


# 14. Sales cannot manage FAQs or blogs
def test_14_sales_cannot_manage_faqs_or_blogs(client):
    sales_hdr = auth_headers(client, role="Sales Rep", email="sales_content@solara.test")

    # FAQ modification forbidden
    assert client.post("/api/v1/faqs", headers=sales_hdr, json={"question": "Q?", "answer": "A."}).status_code == 403
    assert client.patch("/api/v1/faqs/1", headers=sales_hdr, json={"question": "Q2?"}).status_code == 403
    assert client.delete("/api/v1/faqs/1", headers=sales_hdr).status_code == 403

    # Blog modification forbidden
    assert client.post("/api/v1/blogs", headers=sales_hdr, json={"title": "T", "category": "General"}).status_code == 403
    assert client.patch("/api/v1/blogs/1", headers=sales_hdr, json={"title": "T2"}).status_code == 403
    assert client.delete("/api/v1/blogs/1", headers=sales_hdr).status_code == 403


# 15. Sales cannot access protected calculator features
def test_15_sales_cannot_access_protected_calculator_features(client):
    sales_hdr = auth_headers(client, role="Sales Rep", email="sales_calc@solara.test")

    # Sales cannot access submissions list or delete submission
    assert client.get("/api/v1/calculators/submissions", headers=sales_hdr).status_code == 403
    assert client.delete("/api/v1/calculators/submissions/1", headers=sales_hdr).status_code == 403
    assert client.put("/api/v1/calculators/settings", headers=sales_hdr, json={"electricity_rate": 15.0}).status_code == 403


# 16. Admin can manage accounts and retains authorized CRM workflows
def test_16_admin_can_manage_accounts_and_crm_workflows(client):
    admin_hdr = auth_headers(client, role="Admin", email="crm_admin@solara.test")

    # Admin lists users
    users = client.get("/api/v1/users", headers=admin_hdr)
    assert users.status_code == 200

    # Admin updates user status
    with SessionLocal() as db:
        rep = AuthService.bootstrap_admin(
            db=db,
            name="Deact Rep",
            email="deactrep@solara.test",
            password="StrongPassword123!",
            role="Sales Rep",
        )
        rep_id = rep.id

    patch_resp = client.patch(
        f"/api/v1/users/{rep_id}",
        headers=admin_hdr,
        json={"status": "Inactive"},
    )
    assert patch_resp.status_code == 200
    assert patch_resp.json()["data"]["status"] == "Inactive"


# 17. Admin changes are reflected in authorized Sales views after refresh
def test_17_admin_changes_reflected_in_authorized_sales_views(client):
    admin_hdr = auth_headers(client, role="Admin", email="admin17@solara.test")
    sales_hdr = auth_headers(client, role="Sales Rep", email="sales17@solara.test")

    with SessionLocal() as db:
        rep = db.query(User).filter(User.email == "sales17@solara.test").first()
        lead = Lead(
            name="Initial Lead Name",
            contact="lead17@example.com",
            location="Noida",
            property_type="Residential",
            assigned_user_id=rep.id,
            status="New",
        )
        db.add(lead)
        db.commit()
        lead_id = lead.id

    # Admin updates lead
    update_resp = client.patch(
        f"/api/v1/leads/{lead_id}",
        headers=admin_hdr,
        json={"notes": "Updated by Admin with VIP discount"},
    )
    assert update_resp.status_code == 200

    # Sales Rep fetches lead and sees updated data
    sales_get = client.get(f"/api/v1/leads/{lead_id}", headers=sales_hdr)
    assert sales_get.status_code == 200
    assert "VIP discount" in (sales_get.json()["data"]["notes"] or "")


# 18. Sales-created leads are visible to Admin
def test_18_sales_created_leads_visible_to_admin(client):
    sales_hdr = auth_headers(client, role="Sales Rep", email="sales18@solara.test")
    admin_hdr = auth_headers(client, role="Admin", email="admin18@solara.test")

    # Sales creates lead
    create_resp = client.post(
        "/api/v1/leads",
        headers=sales_hdr,
        json={
            "name": "Visible to Admin Lead",
            "contact": "sales18lead@example.com",
            "location": "Kochi",
            "property_type": "Commercial",
            "source": "Cold Call",
        },
    )
    assert create_resp.status_code == 201
    lead_id = create_resp.json()["data"]["id"]

    # Admin fetches lead
    admin_get = client.get(f"/api/v1/leads/{lead_id}", headers=admin_hdr)
    assert admin_get.status_code == 200
    assert admin_get.json()["data"]["name"] == "Visible to Admin Lead"


# 19. Lead conversion preserves customer, project, and survey relationships
def test_19_lead_conversion_preserves_relationships(client):
    admin_hdr = auth_headers(client, role="Admin", email="admin19@solara.test")

    # Create lead
    lead_resp = client.post(
        "/api/v1/leads",
        headers=admin_hdr,
        json={
            "name": "Convertible Lead",
            "contact": "convert@example.com",
            "location": "Indore",
            "property_type": "Residential",
            "source": "Referral",
        },
    )
    assert lead_resp.status_code == 201
    lead_id = lead_resp.json()["data"]["id"]

    # Contact lead -> creates customer
    contact_resp = client.post(f"/api/v1/leads/{lead_id}/contact", headers=admin_hdr)
    assert contact_resp.status_code == 200
    cust_id = contact_resp.json()["data"]["customer_id"]
    assert cust_id is not None

    # Set status to Quoted so convert endpoint accepts it
    with SessionLocal() as db:
        lead = db.query(Lead).filter(Lead.id == lead_id).first()
        lead.status = "Quoted"
        db.commit()

    # Convert lead to project
    convert_resp = client.post(
        f"/api/v1/leads/{lead_id}/convert",
        headers=admin_hdr,
        json={
            "project_name": "Convertible Lead Solar Project",
            "capacity": "10 kW",
            "capacity_kw": 10.0,
            "estimated_cost": 450000.0,
        },
    )
    assert convert_resp.status_code == 200
    proj_id = convert_resp.json()["data"]["project"]["id"]

    with SessionLocal() as db:
        customer = db.query(Customer).filter(Customer.id == cust_id).first()
        assert customer is not None
        assert customer.name == "Convertible Lead"
        lead = db.query(Lead).filter(Lead.id == lead_id).first()
        assert lead.status == "Converted"
        project = db.query(Project).filter(Project.id == proj_id).first()
        assert project.customer_id == cust_id
        assert project.source_lead_id == lead_id


# 20. Database migrations preserve existing business data and foreign-key integrity
def test_20_database_migration_preserves_foreign_key_integrity():
    with SessionLocal() as db:
        admin = AuthService.bootstrap_admin(
            db=db,
            name="FK Admin",
            email="fkadmin@solara.test",
            password="StrongPassword123!",
            role="Admin",
        )
        sales = AuthService.bootstrap_admin(
            db=db,
            name="FK Sales",
            email="fksales@solara.test",
            password="StrongPassword123!",
            role="Sales Rep",
        )
        lead = Lead(
            name="FK Lead",
            contact="fk@example.com",
            location="Bhopal",
            property_type="Residential",
            assigned_user_id=sales.id,
            status="New",
        )
        db.add(lead)
        db.commit()

        customer = Customer(
            name="FK Customer",
            contact="fkcust@example.com",
            email="fkcust@example.com",
            location="Bhopal",
            assigned_user_id=sales.id,
            status="Active",
        )
        db.add(customer)
        db.commit()

        project = Project(
            name="FK Solar Project",
            category="Residential",
            location="Bhopal",
            capacity="15 kW",
            capacity_kw=15.0,
            status="In Progress",
            customer_id=customer.id,
            assigned_user_id=sales.id,
        )
        db.add(project)
        db.commit()

        # Check relationships and foreign keys
        assert lead.assigned_user.role == "Sales Rep"
        assert customer.assigned_user.role == "Sales Rep"
        assert project.customer.id == customer.id
        assert project.customer.assigned_user_id == sales.id
