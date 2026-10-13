# SOLARA Backend API

FastAPI service for the SOLARA solar CRM platform. It provides authentication, dashboard reporting, leads, customers, projects, site surveys, blogs, FAQs, calculators, and settings APIs.

## Setup

From this directory, create and activate a virtual environment, then install the pinned dependencies:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
```

Configure `DATABASE_URL`, `SECRET_KEY`, `CORS_ORIGINS`, and token settings in `.env`. Generate a unique `SECRET_KEY` of at least 32 characters; do not use the example placeholder. PostgreSQL is the default database for local development and production.

## Database

Apply all Alembic migrations before starting the API:

```powershell
alembic upgrade head
```

Set a unique `SEED_ADMIN_PASSWORD` of at least 12 characters in `.env`, then seed the local database with the admin account and sample CRM records:

```powershell
python seed.py
```

The seed admin login is `admin@solara.com` and uses the password configured in `SEED_ADMIN_PASSWORD`. The seed script generates unknown random passwords for other sample users.

## Run

```powershell
uvicorn app.main:app --reload --host 0.0.0.0 --port 8001
```

API base URL: `http://localhost:8001/api/v1`  
Swagger UI: `http://localhost:8001/docs`

## Tests

```powershell
pytest tests/test_api.py -q
pytest --cov=app --cov-report=term-missing
```

The site survey API includes filtered listing, create/update/delete operations, and CSV export at `GET /api/v1/site-surveys/export`.
