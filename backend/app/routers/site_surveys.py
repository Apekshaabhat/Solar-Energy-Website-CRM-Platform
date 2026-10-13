import csv
import io
import math
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import or_, desc

from app.core.database import get_db
from app.dependencies.auth import get_optional_current_user, is_staff_user, require_roles
from app.models.user import User
from app.models.customer import Customer
from app.models.project import Project
from app.models.site_survey import SiteSurvey
from app.schemas.site_survey import SiteSurveyCreate, SiteSurveyUpdate, SiteSurveyResponse, SiteSurveyListResponse
from app.schemas.common import APIResponse

router = APIRouter(prefix="/site-surveys", tags=["Site Surveys Management"])

SURVEY_STATUSES = ["Scheduled", "In Progress", "Completed", "Cancelled"]
STAFF_ROLES = ["Admin", "Manager", "Sales Rep", "Support"]
NULLABLE_SURVEY_FIELDS = {
    "customer_id",
    "project_id",
    "assigned_user_id",
    "roof_information",
    "capacity_estimate",
    "notes",
}


def validate_user_reference(db: Session, user_id: Optional[int]) -> None:
    if user_id is None:
        return
    exists = db.query(User.id).filter(User.id == user_id).first()
    if not exists:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Assigned user not found")


def validate_customer_reference(db: Session, customer_id: Optional[int]) -> None:
    if customer_id is None:
        return
    exists = db.query(Customer.id).filter(Customer.id == customer_id).first()
    if not exists:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Customer not found")


def validate_project_reference(db: Session, project_id: Optional[int]) -> None:
    if project_id is None:
        return
    exists = db.query(Project.id).filter(Project.id == project_id).first()
    if not exists:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Project not found")


def apply_survey_update(survey: SiteSurvey, update_data: dict) -> None:
    for field, val in update_data.items():
        if val is None and field not in NULLABLE_SURVEY_FIELDS:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"{field} cannot be null",
            )
        setattr(survey, field, val)


def escape_spreadsheet_formula(value: str) -> str:
    if value.lstrip(" \t\r\n").startswith(("=", "+", "-", "@")):
        return f"'{value}"
    return value


@router.get(
    "",
    response_model=SiteSurveyListResponse,
    summary="List site surveys with status tabs and filters",
)
def list_surveys(
    search: Optional[str] = Query(None, description="Search by customer, location, surveyor"),
    status_filter: Optional[str] = Query(None, alias="status"),
    surveyor: Optional[str] = Query(None),
    property_type: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    current_user: User = Depends(require_roles(STAFF_ROLES)),
    db: Session = Depends(get_db),
):
    query = db.query(SiteSurvey)

    if search:
        s = f"%{search.strip()}%"
        query = query.filter(
            or_(
                SiteSurvey.customer_name.ilike(s),
                SiteSurvey.location.ilike(s),
                SiteSurvey.assigned_to.ilike(s),
            )
        )

    if surveyor and surveyor not in ["All", "All Surveyors"]:
        query = query.filter(SiteSurvey.assigned_to.ilike(surveyor))

    if property_type and property_type not in ["All", "All Property Types"]:
        query = query.filter(SiteSurvey.property_type.ilike(property_type))

    # Calculate status counts across all matches before applying status filter
    tab_counts = {"All Surveys": query.count()}
    for st in SURVEY_STATUSES:
        tab_counts[st] = query.filter(SiteSurvey.status == st).count()

    if status_filter and status_filter not in ["All Surveys", "All Status", "All Statuses"]:
        query = query.filter(SiteSurvey.status == status_filter)

    total = query.count()
    total_pages = math.ceil(total / limit) if total > 0 else 1

    surveys = (
        query.order_by(desc(SiteSurvey.created_at))
        .offset((page - 1) * limit)
        .limit(limit)
        .all()
    )

    return SiteSurveyListResponse(
        success=True,
        items=[SiteSurveyResponse.model_validate(s) for s in surveys],
        total=total,
        page=page,
        limit=limit,
        total_pages=total_pages,
        tab_counts=tab_counts,
    )


@router.get(
    "/export",
    summary="Export filtered site surveys as CSV",
)
def export_surveys(
    search: Optional[str] = Query(None, description="Search by customer, location, surveyor"),
    status_filter: Optional[str] = Query(None, alias="status"),
    surveyor: Optional[str] = Query(None),
    property_type: Optional[str] = Query(None),
    current_user: User = Depends(require_roles(STAFF_ROLES)),
    db: Session = Depends(get_db),
):
    query = db.query(SiteSurvey)

    if search:
        search_value = f"%{search.strip()}%"
        query = query.filter(
            or_(
                SiteSurvey.customer_name.ilike(search_value),
                SiteSurvey.location.ilike(search_value),
                SiteSurvey.assigned_to.ilike(search_value),
            )
        )
    if surveyor and surveyor not in ["All", "All Surveyors"]:
        query = query.filter(SiteSurvey.assigned_to.ilike(surveyor))
    if property_type and property_type not in ["All", "All Property Types"]:
        query = query.filter(SiteSurvey.property_type.ilike(property_type))
    if status_filter and status_filter not in ["All Surveys", "All Status", "All Statuses"]:
        query = query.filter(SiteSurvey.status == status_filter)

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Customer", "Location", "Property Type", "Survey Date", "Time Slot", "Assigned To", "Status"])
    for survey in query.order_by(desc(SiteSurvey.created_at)).all():
        writer.writerow([
            escape_spreadsheet_formula(survey.customer_name),
            escape_spreadsheet_formula(survey.location),
            escape_spreadsheet_formula(survey.property_type),
            escape_spreadsheet_formula(survey.survey_date),
            escape_spreadsheet_formula(survey.time_slot),
            escape_spreadsheet_formula(survey.assigned_to),
            escape_spreadsheet_formula(survey.status),
        ])

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=site-surveys.csv"},
    )


@router.post(
    "",
    response_model=APIResponse[SiteSurveyResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Book a new site survey",
)
def create_survey(
    request: SiteSurveyCreate,
    current_user: Optional[User] = Depends(get_optional_current_user),
    db: Session = Depends(get_db),
):
    is_staff = is_staff_user(current_user)
    if is_staff:
        validate_customer_reference(db, request.customer_id)
        validate_project_reference(db, request.project_id)
        validate_user_reference(db, request.assigned_user_id)

    survey = SiteSurvey(
        customer_name=request.customer_name.strip(),
        location=request.location.strip(),
        property_type=request.property_type,
        survey_date=request.survey_date.strip(),
        time_slot=request.time_slot.strip(),
        assigned_to=request.assigned_to.strip(),
        status=request.status or "Scheduled",
        customer_id=request.customer_id if is_staff else None,
        project_id=request.project_id if is_staff else None,
        assigned_user_id=request.assigned_user_id if is_staff else None,
        roof_information=request.roof_information,
        capacity_estimate=request.capacity_estimate,
        notes=request.notes,
    )
    db.add(survey)
    db.commit()
    db.refresh(survey)
    return APIResponse(
        success=True,
        message="Site survey booked successfully",
        data=SiteSurveyResponse.model_validate(survey)
    )


@router.get(
    "/{survey_id}",
    response_model=APIResponse[SiteSurveyResponse],
    summary="Get site survey by ID",
)
def get_survey(
    survey_id: int,
    current_user: User = Depends(require_roles(STAFF_ROLES)),
    db: Session = Depends(get_db),
):
    survey = db.query(SiteSurvey).filter(SiteSurvey.id == survey_id).first()
    if not survey:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Site survey not found")
    return APIResponse(success=True, data=SiteSurveyResponse.model_validate(survey))


@router.patch(
    "/{survey_id}",
    response_model=APIResponse[SiteSurveyResponse],
    summary="Update site survey details",
)
def update_survey(
    survey_id: int,
    request: SiteSurveyUpdate,
    current_user: User = Depends(require_roles(STAFF_ROLES)),
    db: Session = Depends(get_db),
):
    survey = db.query(SiteSurvey).filter(SiteSurvey.id == survey_id).first()
    if not survey:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Site survey not found")

    update_data = request.model_dump(exclude_unset=True)
    validate_customer_reference(db, update_data.get("customer_id"))
    validate_project_reference(db, update_data.get("project_id"))
    validate_user_reference(db, update_data.get("assigned_user_id"))
    apply_survey_update(survey, update_data)

    db.commit()
    db.refresh(survey)
    return APIResponse(
        success=True,
        message="Site survey updated successfully",
        data=SiteSurveyResponse.model_validate(survey)
    )


@router.delete(
    "/{survey_id}",
    response_model=APIResponse[bool],
    summary="Delete or cancel site survey",
)
def delete_survey(
    survey_id: int,
    current_user: User = Depends(require_roles(["Admin", "Manager"])),
    db: Session = Depends(get_db),
):
    survey = db.query(SiteSurvey).filter(SiteSurvey.id == survey_id).first()
    if not survey:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Site survey not found")

    db.delete(survey)
    db.commit()
    return APIResponse(success=True, message="Site survey deleted successfully", data=True)
