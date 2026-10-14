from .conftest import auth_headers


def test_complete_crm_workflow_lifecycle(client):
    headers = auth_headers(client)

    # 1. Create a new lead: "Devendra Patil"
    lead_payload = {
        "name": "Devendra Patil",
        "contact": "+91 98220 99887",
        "email": "devendra.patil@example.com",
        "phone": "+91 98220 99887",
        "location": "Pune, MH",
        "property_type": "Residential",
        "source": "Website",
        "status": "New",
        "estimated_value": 450000.0,
    }
    lead_res = client.post("/api/v1/leads", json=lead_payload, headers=headers)
    assert lead_res.status_code == 201
    lead_data = lead_res.json()["data"]
    lead_id = lead_data["id"]
    assert lead_data["status"] == "New"
    assert lead_data["customer_id"] is None

    # 2. Transition lead from New -> Contacted via workflow endpoint
    contact_res = client.post(f"/api/v1/leads/{lead_id}/contact", headers=headers)
    assert contact_res.status_code == 200
    contacted_lead = contact_res.json()["data"]
    assert contacted_lead["status"] == "Contacted"
    customer_id = contacted_lead["customer_id"]
    assert customer_id is not None

    # Verify customer was created in PostgreSQL with Active status
    cust_res = client.get(f"/api/v1/customers/{customer_id}", headers=headers)
    assert cust_res.status_code == 200
    customer_data = cust_res.json()["data"]
    assert customer_data["name"] == "Devendra Patil"
    assert customer_data["status"] == "Active"

    # 3. Schedule Site Survey for lead
    survey_payload = {
        "survey_date": "2026-10-15",
        "time_slot": "10:30 AM",
        "assigned_to": "Karan",
        "roof_information": "RCC flat roof with 1200 sq ft shadow-free area",
        "capacity_estimate": "12 kW",
        "notes": "Customer interested in high-efficiency mono PERC panels",
    }
    survey_res = client.post(
        f"/api/v1/leads/{lead_id}/schedule-survey",
        json=survey_payload,
        headers=headers,
    )
    assert survey_res.status_code == 200
    survey_id = survey_res.json()["data"]["survey_id"]

    # Verify lead status moved to Site Survey
    lead_check = client.get(f"/api/v1/leads/{lead_id}", headers=headers)
    assert lead_check.json()["data"]["status"] == "Site Survey"

    # Verify survey is Scheduled
    get_survey = client.get(f"/api/v1/site-surveys/{survey_id}", headers=headers)
    assert get_survey.status_code == 200
    assert get_survey.json()["data"]["status"] == "Scheduled"

    # Verify direct jump Scheduled -> Completed is strictly REJECTED (sequential rule)
    invalid_jump = client.patch(
        f"/api/v1/site-surveys/{survey_id}",
        json={"status": "Completed"},
        headers=headers,
    )
    assert invalid_jump.status_code == 400

    # 4. Start survey: Scheduled -> In Progress
    start_survey = client.post(f"/api/v1/site-surveys/{survey_id}/start", headers=headers)
    assert start_survey.status_code == 200
    assert start_survey.json()["data"]["status"] == "In Progress"

    # 5. Complete survey: In Progress -> Completed
    comp_survey = client.post(
        f"/api/v1/site-surveys/{survey_id}/complete",
        json={"notes": "Final inspection clear"},
        headers=headers,
    )
    assert comp_survey.status_code == 200
    assert comp_survey.json()["data"]["survey"]["status"] == "Completed"

    # Verify lead was AUTOMATICALLY updated to Quoted in database transaction
    lead_quoted = client.get(f"/api/v1/leads/{lead_id}", headers=headers)
    assert lead_quoted.json()["data"]["status"] == "Quoted"

    # 6. Convert lead to Project (Must start in Planning!)
    convert_res = client.post(
        f"/api/v1/leads/{lead_id}/convert",
        json={
            "project_name": "Devendra Patil 12kW Rooftop Solar",
            "capacity": "12 kW",
            "capacity_kw": 12.0,
            "estimated_cost": 480000.0,
        },
        headers=headers,
    )
    assert convert_res.status_code == 200
    project_id = convert_res.json()["data"]["project_id"]

    # Verify project starts in Planning (NOT In Progress)
    proj_res = client.get(f"/api/v1/projects/{project_id}", headers=headers)
    assert proj_res.status_code == 200
    proj_data = proj_res.json()["data"]
    assert proj_data["status"] == "Planning"
    assert proj_data["customer_id"] == customer_id
    assert proj_data["source_lead_id"] == lead_id

    # 7. Start project: Planning -> In Progress
    start_proj = client.post(f"/api/v1/projects/{project_id}/start", headers=headers)
    assert start_proj.status_code == 200
    assert start_proj.json()["data"]["status"] == "In Progress"

    # 8. Complete project: In Progress -> Completed
    comp_proj = client.post(f"/api/v1/projects/{project_id}/complete", headers=headers)
    assert comp_proj.status_code == 200
    assert comp_proj.json()["data"]["status"] == "Completed"

    # 9. Verify Customer 360 overview shows all connected entities
    overview_res = client.get(f"/api/v1/customers/{customer_id}/overview", headers=headers)
    assert overview_res.status_code == 200
    overview = overview_res.json()["data"]
    assert overview["total_projects"] == 1
    assert overview["status"] == "Active"
    assert len(overview["leads"]) >= 1
    assert len(overview["site_surveys"]) >= 1
    assert len(overview["projects"]) >= 1


def test_crm_cancellation_and_customer_evaluation(client):
    headers = auth_headers(client)

    # Create Lead 2
    l_res = client.post(
        "/api/v1/leads",
        json={
            "name": "Suresh Raina",
            "contact": "+91 91111 22222",
            "email": "suresh.raina@example.com",
            "location": "Mumbai, MH",
            "property_type": "Commercial",
            "source": "Calculator",
            "status": "New",
        },
        headers=headers,
    )
    assert l_res.status_code == 201
    lead2_id = l_res.json()["data"]["id"]

    # Contact Lead 2 -> Customer created with status Active
    c_res = client.post(f"/api/v1/leads/{lead2_id}/contact", headers=headers)
    assert c_res.status_code == 200
    customer2_id = c_res.json()["data"]["customer_id"]

    # Schedule survey
    s_res = client.post(
        f"/api/v1/leads/{lead2_id}/schedule-survey",
        json={"survey_date": "2026-10-20", "time_slot": "11:00 AM", "assigned_to": "Priya"},
        headers=headers,
    )
    assert s_res.status_code == 200
    survey2_id = s_res.json()["data"]["survey_id"]

    # Cancel survey -> Survey Cancelled, Lead Cancelled, Customer evaluated to Inactive
    cancel_res = client.post(f"/api/v1/site-surveys/{survey2_id}/cancel", headers=headers)
    assert cancel_res.status_code == 200
    assert cancel_res.json()["data"]["status"] == "Cancelled"

    # Verify Lead 2 reflected cancellation
    l2_check = client.get(f"/api/v1/leads/{lead2_id}", headers=headers)
    assert l2_check.json()["data"]["status"] == "Cancelled"

    # Verify Customer 2 status is Inactive because all linked records are cancelled
    cust2_check = client.get(f"/api/v1/customers/{customer2_id}", headers=headers)
    assert cust2_check.json()["data"]["status"] == "Inactive"

    # Verify historical records still exist (NOT physically deleted!)
    surv_check = client.get(f"/api/v1/site-surveys/{survey2_id}", headers=headers)
    assert surv_check.status_code == 200
    assert surv_check.json()["data"]["id"] == survey2_id


def test_project_cancellation_and_customer_evaluation(client):
    headers = auth_headers(client)

    # 31. Create lead and advance to Converted
    lead_res = client.post(
        "/api/v1/leads",
        json={
            "name": "Ajinkya Rahane",
            "contact": "+91 95555 44444",
            "email": "ajinkya.rahane@example.com",
            "location": "Mumbai",
            "property_type": "Residential",
            "source": "Website",
            "status": "New",
        },
        headers=headers,
    )
    assert lead_res.status_code == 201
    lead_id = lead_res.json()["data"]["id"]

    # Contact lead -> Customer created
    client.post(f"/api/v1/leads/{lead_id}/contact", headers=headers)

    # Schedule survey
    survey_res = client.post(
        f"/api/v1/leads/{lead_id}/schedule-survey",
        json={"survey_date": "2026-11-01", "time_slot": "10:00 AM"},
        headers=headers,
    )
    survey_id = survey_res.json()["data"]["survey_id"]

    # Start and complete survey -> Lead becomes Quoted
    client.post(f"/api/v1/site-surveys/{survey_id}/start", headers=headers)
    client.post(f"/api/v1/site-surveys/{survey_id}/complete", json={}, headers=headers)

    # 32. Convert lead -> Project starts as Planning
    conv_res = client.post(
        f"/api/v1/leads/{lead_id}/convert",
        json={"project_name": "Rahane Rooftop", "capacity": "8 kW"},
        headers=headers,
    )
    assert conv_res.status_code == 200
    project_id = conv_res.json()["data"]["project_id"]

    p_check = client.get(f"/api/v1/projects/{project_id}", headers=headers)
    assert p_check.json()["data"]["status"] == "Planning"

    # 33. Start Project: Planning -> In Progress
    start_res = client.post(f"/api/v1/projects/{project_id}/start", headers=headers)
    assert start_res.status_code == 200
    assert start_res.json()["data"]["status"] == "In Progress"

    # 34. Cancel Project
    cancel_res = client.post(f"/api/v1/projects/{project_id}/cancel", headers=headers)
    assert cancel_res.status_code == 200

    # 35. Verify Project = Cancelled
    p_after = client.get(f"/api/v1/projects/{project_id}", headers=headers)
    assert p_after.json()["data"]["status"] == "Cancelled"

    # 36. Customer status is recalculated (no active projects/leads/surveys, so Inactive)
    customer_id = p_after.json()["data"]["customer_id"]
    cust_after = client.get(f"/api/v1/customers/{customer_id}", headers=headers)
    assert cust_after.json()["data"]["status"] == "Inactive"

    # 37. Verify Lead history is preserved as Converted (not reverted to New!)
    l_after = client.get(f"/api/v1/leads/{lead_id}", headers=headers)
    assert l_after.json()["data"]["status"] == "Converted"

    # 38. Verify dashboard summary endpoint works without error
    dash_res = client.get("/api/v1/dashboard/summary", headers=headers)
    assert dash_res.status_code == 200
