import pytest
from fastapi.testclient import TestClient
from tests.conftest import auth_headers


def test_blog_management_lifecycle(client: TestClient):
    admin_hdr = auth_headers(client, role="Admin", email="admin_blog@solara.test")
    sales_hdr = auth_headers(client, role="Sales Rep", email="sales_blog@solara.test")

    # 1. Admin creates a Draft blog post
    create_draft_resp = client.post(
        "/api/v1/blogs",
        headers=admin_hdr,
        json={
            "title": "Draft Article On Solar Future",
            "category": "Technology",
            "status": "Draft",
            "author": "Tech Lead",
            "excerpt": "A short summary of what is coming.",
            "content": "Full article body content explaining microgrids.",
            "cover_image": "https://example.com/cover1.jpg",
            "read_time": "7 min read",
        },
    )
    assert create_draft_resp.status_code == 201
    draft_data = create_draft_resp.json()["data"]
    draft_id = draft_data["id"]
    draft_slug = draft_data["slug"]
    assert draft_data["status"] == "Draft"
    assert draft_data["read_time"] == "7 min read"
    assert draft_data["cover_image"] == "https://example.com/cover1.jpg"

    # 2. Admin creates a Published blog post
    create_pub_resp = client.post(
        "/api/v1/blogs",
        headers=admin_hdr,
        json={
            "title": "Published Solar Innovations",
            "category": "Guides",
            "status": "Published",
            "author": "Solar Expert",
            "excerpt": "Clean energy breakthroughs in 2026.",
            "content": "Deep dive into new solar cells.",
            "cover_image": "https://example.com/cover2.jpg",
            "read_time": "4 min read",
        },
    )
    assert create_pub_resp.status_code == 201
    pub_data = create_pub_resp.json()["data"]
    pub_id = pub_data["id"]

    # 3. Public (unauthenticated) listing should ONLY show published post
    public_list = client.get("/api/v1/blogs")
    assert public_list.status_code == 200
    pub_items = public_list.json()["items"]
    slugs = [p["slug"] for p in pub_items]
    assert pub_data["slug"] in slugs
    assert draft_slug not in slugs

    # 4. Public access to draft by slug or id should return 404
    public_draft = client.get(f"/api/v1/blogs/{draft_slug}")
    assert public_draft.status_code == 404

    # 5. Staff access to blogs sees drafts
    staff_list = client.get("/api/v1/blogs", headers=sales_hdr)
    assert staff_list.status_code == 200
    staff_slugs = [p["slug"] for p in staff_list.json()["items"]]
    assert draft_slug in staff_slugs

    # 6. Non-admin/manager cannot create or update blogs
    unauth_create = client.post(
        "/api/v1/blogs",
        headers=sales_hdr,
        json={"title": "Unauthorized Article", "category": "Guides"},
    )
    assert unauth_create.status_code == 403

    # 7. Update draft to published
    update_resp = client.patch(
        f"/api/v1/blogs/{draft_id}",
        headers=admin_hdr,
        json={"status": "Published", "excerpt": "Updated excerpt for launch."},
    )
    assert update_resp.status_code == 200
    assert update_resp.json()["data"]["status"] == "Published"

    # 8. Now public can see it
    public_list_after = client.get("/api/v1/blogs")
    assert draft_slug in [p["slug"] for p in public_list_after.json()["items"]]

    # 9. Delete blog
    del_resp = client.delete(f"/api/v1/blogs/{pub_id}", headers=admin_hdr)
    assert del_resp.status_code == 200
    assert client.get(f"/api/v1/blogs/{pub_id}").status_code == 404


def test_calculator_management_lifecycle(client: TestClient):
    admin_hdr = auth_headers(client, role="Admin", email="admin_calc@solara.test")
    sales_hdr = auth_headers(client, role="Sales Rep", email="sales_calc@solara.test")

    # 1. Public submits a calculator estimate
    submit_resp = client.post(
        "/api/v1/calculators/submissions",
        json={
            "name": "Public Visitor",
            "phone": "+91 91122 33445",
            "email": "visitor@example.com",
            "property_type": "Commercial",
            "monthly_bill": 15000,
            "roof_area": 1200,
            "system_size_kw": 12.5,
            "annual_savings": 140000,
            "payback_years": 4.5,
            "co2_tons": 15.0,
        },
    )
    assert submit_resp.status_code == 201
    submission_id = submit_resp.json()["data"]["id"]

    # 2. Public estimate calculation endpoints
    savings_resp = client.post(
        "/api/v1/calculators/savings-estimate",
        json={"monthly_bill": 8000, "roof_area": 600},
    )
    assert savings_resp.status_code == 200
    assert savings_resp.json()["data"]["annual_savings"] > 0

    roof_resp = client.post(
        "/api/v1/calculators/roof-capacity",
        json={"roof_area": 800, "shading": "None", "orientation": "South-facing"},
    )
    assert roof_resp.status_code == 200
    assert roof_resp.json()["data"]["panel_count"] > 0

    roi_resp = client.post(
        "/api/v1/calculators/roi-estimate",
        json={"system_size_kw": 5, "monthly_savings": 6000, "subsidy": 78000},
    )
    assert roi_resp.status_code == 200
    assert roi_resp.json()["data"]["net_investment"] >= 0

    # 3. Settings endpoint requires staff authentication
    unauth_settings = client.get("/api/v1/calculators/settings")
    assert unauth_settings.status_code in [401, 403]

    # Staff can view settings
    staff_settings = client.get("/api/v1/calculators/settings", headers=sales_hdr)
    assert staff_settings.status_code == 200
    orig_rate = staff_settings.json()["data"]["electricity_rate"]

    # 4. Updating settings requires Admin/Manager
    forbidden_update = client.put(
        "/api/v1/calculators/settings",
        headers=sales_hdr,
        json={"electricity_rate": 12.0},
    )
    assert forbidden_update.status_code == 403

    admin_update = client.put(
        "/api/v1/calculators/settings",
        headers=admin_hdr,
        json={"electricity_rate": 10.5, "bill_offset_percent": 90.0},
    )
    assert admin_update.status_code == 200
    assert admin_update.json()["data"]["electricity_rate"] == 10.5

    # 5. List submissions as staff
    subs_list = client.get("/api/v1/calculators/submissions", headers=sales_hdr)
    assert subs_list.status_code == 200
    ids = [s["id"] for s in subs_list.json()["items"]]
    assert submission_id in ids

    # 6. Delete submission requires Admin/Manager
    forbidden_del = client.delete(
        f"/api/v1/calculators/submissions/{submission_id}",
        headers=sales_hdr,
    )
    assert forbidden_del.status_code == 403

    admin_del = client.delete(
        f"/api/v1/calculators/submissions/{submission_id}",
        headers=admin_hdr,
    )
    assert admin_del.status_code == 200


def test_notifications_system(client: TestClient):
    admin_hdr = auth_headers(client, role="Admin", email="admin_notif@solara.test")
    sales_hdr = auth_headers(client, role="Sales Rep", email="sales_notif@solara.test")

    # Get user profiles to know IDs
    admin_me = client.get("/api/v1/auth/me", headers=admin_hdr).json()["data"]
    sales_me = client.get("/api/v1/auth/me", headers=sales_hdr).json()["data"]
    sales_id = sales_me["id"]

    # 1. Admin creates a Lead assigned to sales rep -> sales rep receives notification
    lead_resp = client.post(
        "/api/v1/leads",
        headers=admin_hdr,
        json={
            "name": "Arjun Rao",
            "contact": "+91 99887 11223",
            "location": "Bengaluru",
            "property_type": "Residential",
            "source": "Website",
            "assigned_user_id": sales_id,
        },
    )
    assert lead_resp.status_code == 201

    # 2. Check Sales Rep's notifications
    sales_notifs = client.get("/api/v1/notifications", headers=sales_hdr)
    assert sales_notifs.status_code == 200
    items = sales_notifs.json()["data"]
    assert len(items) >= 1
    lead_notif = next((n for n in items if "Arjun Rao" in n["message"]), None)
    assert lead_notif is not None
    assert lead_notif["is_read"] is False

    # 3. Check unread count
    unread_resp = client.get("/api/v1/notifications/unread-count", headers=sales_hdr)
    assert unread_resp.status_code == 200
    assert unread_resp.json()["data"]["unread_count"] >= 1

    # 4. User isolation: Admin does NOT see sales rep's notifications
    admin_notifs = client.get("/api/v1/notifications", headers=admin_hdr)
    admin_ids = [n["id"] for n in admin_notifs.json()["data"]]
    assert lead_notif["id"] not in admin_ids

    # 5. Mark single notification as read
    read_resp = client.patch(f"/api/v1/notifications/{lead_notif['id']}/read", headers=sales_hdr)
    assert read_resp.status_code == 200
    assert read_resp.json()["data"]["is_read"] is True

    # Check persistence
    check_read = client.get("/api/v1/notifications", headers=sales_hdr)
    item_updated = next(n for n in check_read.json()["data"] if n["id"] == lead_notif["id"])
    assert item_updated["is_read"] is True

    # 6. Mark all as read
    mark_all = client.patch("/api/v1/notifications/mark-all-read", headers=sales_hdr)
    assert mark_all.status_code == 200
    unread_after = client.get("/api/v1/notifications/unread-count", headers=sales_hdr).json()["data"]["unread_count"]
    assert unread_after == 0

    # 7. Dismiss notification
    dismiss_resp = client.delete(f"/api/v1/notifications/{lead_notif['id']}", headers=sales_hdr)
    assert dismiss_resp.status_code == 200

    notifs_after_dismiss = client.get("/api/v1/notifications", headers=sales_hdr).json()["data"]
    assert lead_notif["id"] not in [n["id"] for n in notifs_after_dismiss]


def test_faq_management_lifecycle(client: TestClient):
    admin_hdr = auth_headers(client, role="Admin", email="admin_faq@solara.test")
    sales_hdr = auth_headers(client, role="Sales Rep", email="sales_faq@solara.test")

    # 1. Admin creates an Unpublished FAQ
    create_unpub = client.post(
        "/api/v1/faqs",
        headers=admin_hdr,
        json={
            "question": "What is the warranty period for inverters?",
            "answer": "Most standard inverters have a 10 to 12 year manufacturer warranty.",
            "category": "Maintenance",
            "display_order": 10,
            "is_published": False,
        },
    )
    assert create_unpub.status_code == 201
    unpub_id = create_unpub.json()["data"]["id"]

    # 2. Admin creates a Published FAQ
    create_pub = client.post(
        "/api/v1/faqs",
        headers=admin_hdr,
        json={
            "question": "Can I expand my solar setup in the future?",
            "answer": "Yes, modular hybrid inverters allow adding more solar panels and battery storage.",
            "category": "Installation",
            "display_order": 1,
            "is_published": True,
        },
    )
    assert create_pub.status_code == 201
    pub_id = create_pub.json()["data"]["id"]

    # 3. Public listing should only show published
    public_faqs = client.get("/api/v1/faqs")
    assert public_faqs.status_code == 200
    public_ids = [f["id"] for f in public_faqs.json()["data"]]
    assert pub_id in public_ids
    assert unpub_id not in public_ids

    # 4. Public direct access to unpublished FAQ returns 404
    assert client.get(f"/api/v1/faqs/{unpub_id}").status_code == 404

    # 5. Staff access returns unpublished FAQs
    staff_faqs = client.get("/api/v1/faqs", headers=sales_hdr)
    assert staff_faqs.status_code == 200
    staff_ids = [f["id"] for f in staff_faqs.json()["data"]]
    assert unpub_id in staff_ids

    # 6. Non-admin cannot create/edit/delete FAQ
    forbidden_create = client.post(
        "/api/v1/faqs",
        headers=sales_hdr,
        json={"question": "Bad question", "answer": "Bad answer"},
    )
    assert forbidden_create.status_code == 403

    # 7. Admin updates FAQ to published and edits display order
    update_faq = client.patch(
        f"/api/v1/faqs/{unpub_id}",
        headers=admin_hdr,
        json={"is_published": True, "display_order": 2},
    )
    assert update_faq.status_code == 200
    assert update_faq.json()["data"]["is_published"] is True
    assert update_faq.json()["data"]["display_order"] == 2

    # 8. Delete FAQ
    del_faq = client.delete(f"/api/v1/faqs/{pub_id}", headers=admin_hdr)
    assert del_faq.status_code == 200
    assert client.get(f"/api/v1/faqs/{pub_id}").status_code == 404
