# SOLARA Solar Energy Website & CRM Platform

SOLARA is an enterprise-grade solar energy website and integrated CRM platform built with a high-performance **React (Vite)** frontend and a robust **FastAPI + PostgreSQL** backend. The platform combines customer-facing solar calculators and informational pages with an authenticated, unified CRM system for managing leads, customers, site surveys, projects, blogs, FAQs, and executive reporting.

---

## Architecture & Unified CRM Data Model

All five core CRM modules (**Dashboard**, **Leads**, **Customers**, **Site Surveys**, and **Projects**) are fully synchronized with **PostgreSQL as the single source of truth**. Every transition links entities through strict database foreign keys:

```
                      ┌──────────────────────┐
                      │      LEAD (New)      │
                      └──────────┬───────────┘
                                 │
                 Lead Contacted  │ Creates/links Customer
                                 ▼
                      ┌──────────────────────┐
                      │       CUSTOMER       │◄─────────────────────┐
                      └────┬────────────┬────┘                      │
                           │            │                           │
          Schedule Survey  │            │  Convert to Project       │
                           ▼            ▼                           │
        ┌──────────────────────┐    ┌──────────────────────┐        │
        │     SITE SURVEY      │    │       PROJECT        │        │
        │                      │    │                      │        │
        │ • customer_id (FK)───┼────┤ • customer_id (FK)───┘        │
        │ • lead_id (FK)───────┼─┐  │ • source_lead_id (FK)─────────┘
        └──────────────────────┘ │  └──────────────────────┘
                                 │
                                 └─► Linked to Source Lead
```

### Foreign-Key Relationships
- `Lead`: `customer_id` → `Customer.id` (optional foreign key until contacted/linked).
- `SiteSurvey`:
  - `customer_id` → `Customer.id` (foreign key)
  - `lead_id` → `Lead.id` (foreign key)
  - `project_id` → `Project.id` (optional foreign key)
- `Project`:
  - `customer_id` → `Customer.id` (foreign key)
  - `source_lead_id` → `Lead.id` (foreign key)
- `Activity`: Audit trail log table recording every state transition (`lead_created`, `lead_contacted`, `survey_scheduled`, `survey_completed`, `project_created`, `project_status_changed`, `customer_created`).

### End-to-End CRM Lifecycle
1. **Lead Intake**: Leads enter the CRM via customer inquiries, calculators, or administrative entry (`Lead` record created, status `New`).
2. **Contact Lead**: Contacting the lead triggers `POST /api/v1/leads/{id}/contact`. The system automatically creates or associates a `Customer` record, sets `lead.customer_id`, updates status to `Contacted`, and logs an audit activity.
3. **Site Survey Scheduling**: Scheduling a survey triggers `POST /api/v1/leads/{id}/schedule-survey`. The system provisions a `SiteSurvey` record linked to both the `Customer` and `Lead`, moving the lead to `Site Survey Scheduled`.
4. **Survey Completion & Quoting**: The site assessment is executed, technical parameters (roof type, azimuth, capacity) are recorded, and the lead advances to `Quoted`.
5. **Project Conversion**: Converting the lead triggers `POST /api/v1/leads/{id}/convert`. The system provisions a `Project` with explicit foreign keys to `Customer` and `source_lead_id`, marks the lead `Converted`, and records an audit activity.
6. **Customer 360 & Real-Time Sync**: Every page dynamically reflects updates via PostgreSQL queries and cross-tab/cross-component reactive event synchronization (`crm:record-updated`). The Customers page includes a full 360-degree timeline view of all linked leads, surveys, and projects.

---

## Tech Stack

### Frontend
- **Framework**: React 18.3.1 with Vite 6.4.3
- **Routing**: React Router DOM 7.18.3
- **Styling**: Tailwind CSS 3.4.19
- **Charts & Visuals**: Recharts 3.10.1
- **Icons**: Lucide React 0.469.0

### Backend
- **Framework**: FastAPI 0.115.6 with Uvicorn 0.34.0
- **Database & ORM**: PostgreSQL 16+ via SQLAlchemy 2.0.36
- **Migrations**: Alembic 1.14.0
- **Validation & Settings**: Pydantic 2.10.5 & Pydantic Settings 2.7.1
- **Authentication**: JWT (`pyjwt==2.10.1`), `bcrypt==4.2.1`
- **Testing**: Pytest 8.3.4, Pytest-Cov 6.0.0, HTTPX 0.28.1

---

## Prerequisites

- **Python**: 3.12.x
- **pip**: 24.x or newer
- **Node.js**: 20.18.1 LTS
- **npm**: 10.8.2 or newer
- **PostgreSQL**: 16.x

Verify installed versions before running:
```powershell
python --version
pip --version
node --version
npm --version
psql --version
```

---

## Quick Start Guide

### 1. Database Setup
Create a PostgreSQL database named `solar_crm`:
```powershell
psql -U postgres -c "CREATE DATABASE solar_crm;"
```

### 2. Backend Setup
From the repository root:
```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
```

Ensure `backend/.env` contains your PostgreSQL credentials:
```env
DATABASE_URL=postgresql+psycopg2://postgres:your_password@localhost:5432/solar_crm
SECRET_KEY=your-super-secret-key-change-this-in-production-min-32-chars
CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000
```

Run database migrations and seed sample CRM data:
```powershell
alembic upgrade head
python seed.py
```

Start the FastAPI application:
```powershell
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The API is available at `http://localhost:8001`.
Interactive API documentation is available at `http://localhost:8001/docs`.
The frontend expects the backend at `http://localhost:8001/api/v1` by default. If you run the API on a different port, set `VITE_API_BASE_URL` in `frontend/.env.local` to match that URL.

If port `8000` is available in your environment, it can still be used by setting `VITE_API_BASE_URL` to the matching API URL. The repository default is `8001` because port `8000` may already be in use by another local process.

### 2. Start the frontend

Keep the backend terminal running. Open a second PowerShell window in the repository root:
- API Base URL: `http://localhost:8000/api/v1`
- Interactive Swagger UI: `http://localhost:8000/docs`
- Redoc Documentation: `http://localhost:8000/redoc`

### 3. Frontend Setup
In a second terminal window from the repository root:
```powershell
cd frontend
npm ci
npm run dev
```

The frontend is available at `http://localhost:5173`.
Set `VITE_API_BASE_URL` in `frontend/.env.local` when the API uses a different base URL.
The frontend will be available at `http://localhost:5173`.

---

## Default Admin Credentials

The initial seed creates an administrative account:
- **Email**: `admin@solara.com`
- **Password**: `admin123`

> [!WARNING]
> Change the default credentials and set a secure `SECRET_KEY` in `backend/.env` prior to deploying to staging or production.

---

## Core API Endpoints

### CRM Lifecycle & Synchronization
| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/v1/leads/{id}/contact` | Marks lead as contacted, automatically provisions/links Customer entity, and logs activity |
| `POST` | `/api/v1/leads/{id}/schedule-survey` | Provisions Site Survey with foreign keys to Lead and Customer |
| `POST` | `/api/v1/leads/{id}/convert` | Converts lead into an active Project with `customer_id` and `source_lead_id` |
| `GET` | `/api/v1/customers/{id}/overview` | Returns Customer 360-degree timeline including linked Leads, Surveys, Projects, and audit trail |
| `GET` | `/api/v1/dashboard/activities` | Returns real-time chronological activity feed across all CRM events |
| `GET` | `/api/v1/dashboard/summary` | Dynamic dashboard statistics calculated directly from PostgreSQL |

### Entity CRUD & Utilities
| Module | Primary Endpoints | Features |
|---|---|---|
| **Leads** | `/api/v1/leads` | Filter by status/source, search by name/email/phone, pipeline tracking |
| **Customers** | `/api/v1/customers` | Filter by status/type, search, Customer 360 overview modal |
| **Site Surveys** | `/api/v1/site-surveys` | Filter by status, assign surveyor, CSV export (`/api/v1/site-surveys/export`) |
| **Projects** | `/api/v1/projects` | System capacity, quote tracking, stage transitions, source lead links |
| **Calculators** | `/api/v1/calculator` | Solar savings calculation and submission capture |
| **Auth** | `/api/v1/auth` | JWT login, registration, token refresh, and profile management |

---

## Verification & Testing

### Backend Test Suite
Run the automated test suite covering authentication, API endpoints, and CRM lifecycle workflows:
```powershell
cd backend
pytest -v
```

Run tests with test coverage reporting:
```powershell
cd backend
pytest --cov=app --cov-report=term-missing
```

### Frontend Checks
Run static code linting and production build verification:
```powershell
cd frontend
npm run lint
npm run build
```

## Admin Login

The seeded admin account in this project is:

---

## Repository Structure

```text
Solar-Energy-Website-CRM-Platform/
├── backend/
│   ├── app/
│   │   ├── core/           # Security, config, database session
│   │   ├── models/         # SQLAlchemy models (Lead, Customer, Project, SiteSurvey, Activity, etc.)
│   │   ├── routers/        # FastAPI endpoint routers
│   │   ├── schemas/        # Pydantic v2 validation and response models
│   │   └── services/       # CRM workflow engine, dashboard stats, auth services
│   ├── migrations/         # Alembic database migrations (001 -> 003)
│   ├── tests/              # Pytest test suite and test database fixtures
│   ├── seed.py             # Database seeding script with realistic solar data
│   ├── requirements.txt    # Pinned Python package dependencies
│   └── README.md           # Backend-specific architecture guide
├── frontend/
│   ├── src/
│   │   ├── components/     # UI components, layout, dashboard widgets
│   │   ├── context/        # DashboardDataContext & reactive CRM synchronization
│   │   ├── pages/          # CRM pages (Dashboard, Leads, Customers, Projects, Surveys, etc.)
│   │   └── services/       # Axios API client and entity mappers
│   ├── package.json        # Frontend dependencies and npm scripts
│   └── vite.config.js      # Vite build configuration
├── requirements.txt        # Root requirements pointer (-r backend/requirements.txt)
├── .gitignore              # Git ignore rules for Python, Node, Vite, and SQLite
└── README.md               # Main project documentation
```

---

Change these seeded credentials before using the application outside local development.

## Environment Variables
## License

This project is licensed under the MIT License.
