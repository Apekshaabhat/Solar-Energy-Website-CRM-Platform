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

Configure `DATABASE_URL`, `SECRET_KEY`, `CORS_ORIGINS`, and token settings in `.env`. Generate a unique `SECRET_KEY` of at least 32 characters; do not use the example placeholder. PostgreSQL is the default database for local development and production.

---

## Database Migrations & Seeding

Apply all Alembic migrations (including `003_crm_relationships_and_activity`):

```powershell
alembic upgrade head
```

Set a unique `SEED_ADMIN_PASSWORD` of at least 12 characters in `.env`, then seed the local database with the admin account and sample CRM records:
Seed the database with the admin account and interconnected sample CRM records:

```powershell
python seed.py
```

The seed admin login is `admin@solara.com` and uses the password configured in `SEED_ADMIN_PASSWORD`. The seed script generates unknown random passwords for other sample users.
- Seed admin account: `admin@solara.com` / `admin123`
- Database tables populated: `users`, `customers`, `leads`, `site_surveys`, `projects`, `activities`, `blogs`, `faqs`, `system_settings`.

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
| `GET` | `/api/v1/site-surveys/export` | Exports filtered site surveys as CSV |

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
