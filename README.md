# SOLARA Solar Energy Website and CRM Platform

SOLARA is a solar energy website with a React frontend and a FastAPI CRM backend. The platform includes public solar calculators and content pages alongside authenticated CRM workflows for leads, customers, projects, site surveys, blogs, FAQs, users, and dashboard reporting.

## Stack

- Frontend: React, Vite, React Router, Tailwind CSS, Recharts, and Lucide React
- Backend: FastAPI, SQLAlchemy, Alembic, Pydantic Settings, and PostgreSQL
- Tests: Pytest with an SQLite database for the test suite

## Project Structure

```text
frontend/   React and Vite application
backend/    FastAPI application, migrations, seed data, and tests
```

## Prerequisites

Use these versions for a reproducible local setup:

- Python 3.12.x
- pip 24.3.1 or newer
- Node.js 20.18.1 LTS
- npm 10.8.2
- PostgreSQL 16.x

Verify the tools before starting:

```powershell
python --version
python -m pip --version
node --version
npm --version
psql --version
```

The frontend package versions are locked by `frontend/package-lock.json`. The resolved direct versions are React 18.3.1, React DOM 18.3.1, React Router DOM 7.18.3, Recharts 3.10.1, Lucide React 0.469.0, Vite 6.4.3, Tailwind CSS 3.4.19, and the Vite React plugin 4.7.0.

## Quick Start

### 1. Start the backend

Open PowerShell in the repository root and run:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
```

Create a PostgreSQL database named `solar_crm`, then update `backend/.env` with the database connection and a secret key of at least 32 characters. Apply the schema and optional seed data:

```powershell
alembic upgrade head
python seed.py
```

Start the API:

```powershell
uvicorn app.main:app --reload --host 0.0.0.0 --port 8001
```

The API is available at `http://localhost:8001`.
Interactive API documentation is available at `http://localhost:8001/docs`.
The frontend expects the backend at `http://localhost:8001/api/v1` by default. If you run the API on a different port, set `VITE_API_BASE_URL` in `frontend/.env.local` to match that URL.

If port `8000` is available in your environment, it can still be used by setting `VITE_API_BASE_URL` to the matching API URL. The repository default is `8001` because port `8000` may already be in use by another local process.

### 2. Start the frontend

Keep the backend terminal running. Open a second PowerShell window in the repository root:

```powershell
cd frontend
npm ci
npm run dev
```

The frontend is available at `http://localhost:5173`.
Set `VITE_API_BASE_URL` in `frontend/.env.local` when the API uses a different base URL.

## CRM Workflows

Authenticated dashboard workflows include leads, customers, projects, and site surveys. Site survey records support create, edit, delete, filtering, and CSV export. The export endpoint is `GET /api/v1/site-surveys/export` and uses the same search and filter parameters as the list endpoint.

## Useful Commands

Run backend tests from `backend/`:

```powershell
cd backend
pytest
```

Run the backend tests with coverage:

```powershell
cd backend
pytest --cov=app --cov-report=term-missing
```

Run frontend checks from `frontend/`:

```powershell
cd frontend
npm run lint
npm run build
```

## Admin Login

The seeded admin account in this project is:

- Login ID / email: `admin@solara.com`
- Password: `admin123`

Change these seeded credentials before using the application outside local development.

## Environment Variables

The backend reads configuration from `backend/.env`. Start with `backend/.env.example` and configure `DATABASE_URL`, `SECRET_KEY`, `CORS_ORIGINS`, and the token settings for your environment. Never commit real credentials or production secrets.
