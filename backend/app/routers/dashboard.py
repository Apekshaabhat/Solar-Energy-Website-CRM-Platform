from typing import List, Dict, Any
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies.auth import require_roles
from app.models.user import User
from app.schemas.dashboard import DashboardSummaryResponse
from app.schemas.common import APIResponse
from app.services.dashboard_service import DashboardService

_dashboard_access = require_roles(["Admin", "Manager", "Sales Rep", "Support"])

router = APIRouter(
    prefix="/dashboard",
    tags=["Dashboard"],
    dependencies=[Depends(_dashboard_access)],
)


@router.get(
    "/summary",
    response_model=DashboardSummaryResponse,
    summary="Get real-time dashboard analytics and statistics",
    description="Returns stat cards, leads trend overview, leads by source distribution, recent leads, and recent activities calculated directly from the database.",
)
def get_dashboard_summary(
    current_user: User = Depends(_dashboard_access),
    db: Session = Depends(get_db),
):
    return DashboardService.get_summary(db, current_user)


@router.get(
    "/activities",
    response_model=APIResponse[List[Dict[str, Any]]],
    summary="Get real-time CRM activity feed",
)
def get_dashboard_activities(
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(require_roles(["Admin", "Manager", "Sales Rep", "Support"])),
    db: Session = Depends(get_db),
):
    activities = DashboardService.get_activities(db, current_user, limit=limit)
    return APIResponse(success=True, data=activities)
