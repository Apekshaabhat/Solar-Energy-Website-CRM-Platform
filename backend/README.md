# SOLARA Backend API

FastAPI service for the SOLARA solar CRM platform. It provides authentication, dynamic dashboard reporting, unified CRM lifecycle management (leads, customers, projects, site surveys, and activities), blogs, FAQs, calculators, and settings APIs.

---

## Unified CRM Architecture & Database Model

PostgreSQL serves as the single source of truth across all CRM entities with relational foreign keys:

- **Lead** (`leads`): Captures inquiries. Has foreign key `customer_id` → `customers.id`.
- **Customer** (`customers`): Created or linked upon lead contact or direct creation. Central entity linking projects, surveys, and leads.
- **Site Survey** (`site_surveys`): Technical feasibility assessment. Has foreign keys `customer_id` → `customers.id`, `lead_id` → `leads.id`, and `project_id` → `projects.id`.
- **Project** (`projects`): Solar installation pipeline. Has foreign keys `customer_id` → `customers.id` and `source_lead_id` → `leads.id`.
- **Activity** (`activities`): Audit logging table recording all lifecycle events (`lead_created`, `lead_contacted`, `survey_scheduled`, `survey_completed`, `project_created`, `project_status_changed`, `customer_created`).

---

## Setup

From the `backend/` directory, create and activate a Python virtual environment, then install dependencies:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
```

Configure `DATABASE_URL`, `SECRET_KEY`, `CORS_ORIGINS`, and token settings in `.env`. Generate a unique `SECRET_KEY` of at least 32 characters; do not use the example placeholder. Production requires `ENVIRONMENT=production`, `DEBUG=False`, a unique signing key, and a strong `SEED_ADMIN_PASSWORD`.

### Email configuration

Customer signup does not require email verification. Administrator invitations use single-use activation links. For local development, the default `EMAIL_BACKEND=console` prints invitation links in the backend terminal; it does not send email.

To send through Gmail, enable 2-Step Verification on the sending Google account, create a Google App Password, and set these values in `backend/.env`:

```env
EMAIL_BACKEND=smtp
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_TLS=True
SMTP_USER=your.name@gmail.com
SMTP_PASSWORD=your-16-character-google-app-password
EMAILS_FROM_EMAIL=your.name@gmail.com
FRONTEND_URL=http://localhost:5173
```

Use the App Password, not the account's regular password. Keep it private and do not commit `.env`. Restart the backend after changing settings. If invitation email delivery fails, correct the SMTP configuration and retry the invitation. The previous activation link is invalidated when a fresh one is issued.

---

## Database Migrations & Seeding

Apply all Alembic migrations (including `003_crm_relationships_and_activity`):

```powershell
alembic upgrade head
```

Set a unique `SEED_ADMIN_PASSWORD` of at least 12 characters, including uppercase, lowercase, and numeric characters, in `.env`. Run the seed command explicitly to create the initial administrator and sample CRM records:

```powershell
python seed.py
```

The seed admin login is `admin@solara.com` and uses the password configured in `SEED_ADMIN_PASSWORD`. Rerunning the seed command does not reset an existing administrator password. The seed script generates unknown random passwords for other sample users. Application startup does not automatically seed users or demo data.
- Database tables populated: `users`, `customers`, `leads`, `site_surveys`, `projects`, `activities`, `notifications`, `blogs`, `faqs`, `system_settings`.

---
## Customer account profiles

Migration `003_customer_account_relationship` adds a nullable, unique `customers.account_user_id` foreign key for the customer login account. It is separate from `assigned_user_id`, which identifies the staff member responsible for the CRM record. `users.customer_id` is retained as a legacy CRM association used by existing customer-facing scopes and token claims; it is not a replacement for either customer-side relationship. The migration does not infer or backfill ownership from email addresses. An administrator or manager must explicitly link a customer portal account through the customer create/update API using `account_user_id`. Signup and the administrator reconciliation operation do not associate accounts with existing customer records based on matching email or phone.

Once linked, the authenticated customer can read or update their own profile through `GET` and `PATCH /api/v1/customers/me`. Customer profile routes resolve the record from the authenticated account; they do not accept a customer ID.

---

## Running the API Server

```powershell
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

- **API Base URL**: `http://localhost:8000/api/v1`
- **Interactive OpenAPI / Swagger UI**: `http://localhost:8000/docs`
- **ReDoc Documentation**: `http://localhost:8000/redoc`

---

## Key CRM Workflow Endpoints

| Method | Endpoint | Action |
|---|---|---|
| `POST` | `/api/v1/leads/{id}/contact` | Marks lead as Contacted, creates or links a `Customer`, logs activity |
| `POST` | `/api/v1/leads/{id}/schedule-survey` | Provisions a `SiteSurvey` linked to `lead_id` and `customer_id`, moves lead to `Site Survey Scheduled` |
| `POST` | `/api/v1/leads/{id}/convert` | Creates a `Project` linked to `customer_id` and `source_lead_id`, marks lead `Converted` |
| `GET` | `/api/v1/customers/{id}/overview` | Returns Customer 360 view with all linked leads, surveys, projects, and chronological activities |
| `GET` | `/api/v1/dashboard/activities` | Returns real-time activity audit feed |
| `GET` | `/api/v1/dashboard/summary` | Dynamic dashboard statistics calculated directly via database aggregations |
| `GET` | `/api/v1/notifications?limit=20&offset=0` | Returns the authenticated user's notifications, with a maximum page size of 100 |
| `GET` | `/api/v1/notifications/unread-count` | Returns the authenticated user's unread notification count |
| `PATCH` | `/api/v1/notifications/mark-all-read` | Persists read state for the authenticated user's active notifications |
| `PATCH` | `/api/v1/notifications/{id}/read` | Persists read state only for a notification owned by the authenticated user |
| `DELETE` | `/api/v1/notifications/{id}` | Dismisses only a notification owned by the authenticated user |
| `GET` | `/api/v1/site-surveys/export` | Exports filtered site surveys as CSV |

Dashboard activity is restricted to authenticated staff and scoped to the records assigned to each staff member; administrators and managers see the full staff activity feed. Notification listing supports bounded `limit` and `offset` pagination and all read/dismiss operations are owner-scoped.

## API error responses

Errors use the existing envelope with `success: false`, a user-facing `message`, a stable `error_code`, and optional `details`. Authentication, authorization, missing-resource, and conflict errors use HTTP 401, 403, 404, and 409; application-level invalid requests use 400. FastAPI request-schema validation retains its standard 422 status for frontend compatibility and omits submitted values from error details. Integrity conflicts return 409, while database and unexpected server errors return a generic 500 message without exposing internal exception details.

---

## Running Automated Tests

Run the test suite:

```powershell
pytest -v
```

Run test suite with test coverage analysis:

```powershell
pytest --cov=app --cov-report=term-missing
```
