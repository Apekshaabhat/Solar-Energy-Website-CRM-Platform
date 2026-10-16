from app.routers.auth import router as auth_router
from app.routers.users import router as users_router
from app.routers.customers import router as customers_router
from app.routers.leads import router as leads_router
from app.routers.projects import router as projects_router
from app.routers.site_surveys import router as site_surveys_router
from app.routers.blogs import router as blogs_router
from app.routers.faqs import router as faqs_router
from app.routers.calculators import router as calculators_router
from app.routers.settings import router as settings_router
from app.routers.dashboard import router as dashboard_router
from app.routers.notifications import router as notifications_router

__all__ = [
    "auth_router",
    "users_router",
    "customers_router",
    "leads_router",
    "projects_router",
    "site_surveys_router",
    "blogs_router",
    "faqs_router",
    "calculators_router",
    "settings_router",
    "dashboard_router",
    "notifications_router",
]
