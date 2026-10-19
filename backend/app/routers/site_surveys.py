import csv
import io
import math
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import or_, desc

from app.core.database import get_db
from app.dependencies.auth import (
    get_current_user,
    get_optional_current_user,
    is_staff_user,
    require_roles,
)
from app.models.user import User
from app.models.customer import Customer
from app.models.project import Project
from app.models.lead import Lead
from app.models.site_survey import SiteSurvey
from app.schemas.site_survey import (
    SiteSurveyCreate,
    SiteSurveyUpdate,
    SiteSurveyResponse,
    SiteSurveyListResponse,
    SiteSurveyCompleteRequest,
)
from app.schemas.common import APIResponse
from app.services.crm_service import CRMService
from app.services.notification_service import NotificationService

router = APIRouter(prefix="/site-surveys", tags=["Site Surveys Management"])

SURVEY_STATUSES = ["Scheduled", "In Progress", "Completed", "Cancelled"]
STAFF_ROLES = ["Admin", "Manager", "Sales Rep", "Support"]
NULLABLE_SURVEY_FIELDS = {
    "customer_id",
    "project_id",
    "lead_id",
    "assigned_user_id",
    "roof_information",
    "capacity_estimate",
    "notes",
}
SURVEY_MANAGER_ROLES = {"admin", "manager"}


def is_survey_manager(user: User) -> bool:
    return user.role.lower() in SURVEY_MANAGER_ROLES


def accessible_surveys_query(db: Session, current_user: User):
    query = db.query(SiteSurvey)
    if is_survey_manager(current_user):
        return query
    if is_staff_user(current_user):
        return query.filter(SiteSurvey.assigned_user_id == current_user.id)
    if current_user.role.lower() == "customer":
        return (
            query.join(Customer, SiteSurvey.customer_id == Customer.id)
            .outerjoin(Project, SiteSurvey.project_id == Project.id)
            .filter(
                Customer.account_user_id == current_user.id,
                or_(
                    SiteSurvey.project_id.is_(None),
                    Project.customer_id == SiteSurvey.customer_id,
                ),
            )
        )
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Operation not permitted")


def validate_user_reference(db: Session, user_id: Optional[int]) -> Optional[User]:
    if user_id is None:
        return None
    target_user = db.query(User).filter(User.id == user_id).first()
    if not target_user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Assigned user not found")
    if target_user.status != "Active":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot assign survey to an inactive user.")
    if target_user.role not in STAFF_ROLES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot assign survey to a non-staff user account.")
    return target_user


def validate_customer_reference(
    db: Session,
    customer_id: Optional[int],
    current_user: Optional[User] = None,
) -> Optional[Customer]:
    if customer_id is None:
        return None
    query = db.query(Customer).filter(Customer.id == customer_id)
    if current_user is not None and is_staff_user(current_user) and not is_survey_manager(current_user):
        query = query.filter(Customer.assigned_user_id == current_user.id)
    customer = query.first()
    if customer is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Customer not found")
    return customer


def validate_project_reference(
    db: Session,
    project_id: Optional[int],
    current_user: Optional[User] = None,
    customer_id: Optional[int] = None,
) -> Optional[Project]:
    if project_id is None:
        return None
    query = db.query(Project).filter(Project.id == project_id)
    if customer_id is not None:
        query = query.filter(Project.customer_id == customer_id)
    if current_user is not None and is_staff_user(current_user) and not is_survey_manager(current_user):
        query = query.join(Customer, Project.customer_id == Customer.id).filter(
            Customer.assigned_user_id == current_user.id
        )
    project = query.first()
    if project is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Project not found")
    if project.customer_id != customer_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Project must belong to the selected customer",
        )
    return project


def validate_survey_relationships(
    db: Session,
    customer_id: Optional[int],
    project_id: Optional[int],
    current_user: Optional[User] = None,
) -> None:
    validate_customer_reference(db, customer_id, current_user)
    validate_project_reference(db, project_id, current_user, customer_id)


def customer_profile_for_user(db: Session, user: User) -> Optional[Customer]:
    profiles = (
        db.query(Customer)
        .filter(Customer.account_user_id == user.id)
        .limit(2)
        .all()
    )
    if len(profiles) > 1:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer profile not found")
    return profiles[0] if profiles else None


def validate_lead_reference(db: Session, lead_id: Optional[int]) -> None:
    if lead_id is None:
        return
    exists = db.query(Lead.id).filter(Lead.id == lead_id).first()
    if not exists:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Lead not found")


def check_survey_access(survey: SiteSurvey, current_user: User) -> None:
    if current_user.role in ["Admin", "Manager"]:
        return
    if current_user.role == "Customer":
        if not current_user.customer_id or survey.customer_id != current_user.customer_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: You are not authorized to view this site survey."
            )
        return
    if current_user.role in ["Sales Rep", "Support"]:
        if survey.assigned_user_id != current_user.id and survey.assigned_to != current_user.name:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: You may only access site surveys assigned to you."
            )
        return
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")


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
    current_user: User = Depends(require_roles(["Admin", "Manager", "Sales Rep", "Support", "Customer"])),
    db: Session = Depends(get_db),
):
    query = accessible_surveys_query(db, current_user)

    # Scoping
    if current_user.role in ["Sales Rep", "Support"]:
        query = query.filter(or_(SiteSurvey.assigned_user_id == current_user.id, SiteSurvey.assigned_to == current_user.name))
    elif current_user.role == "Customer":
        if current_user.customer_id:
            query = query.filter(SiteSurvey.customer_id == current_user.customer_id)
        else:
            query = query.filter(SiteSurvey.customer_name == current_user.name)


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
    query = accessible_surveys_query(db, current_user)

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
    customer_id = None
    project_id = None
    lead_id = None
    assigned_user_id = None
    if current_user is not None and is_staff:
        if is_survey_manager(current_user):
            assigned_user_id = request.assigned_user_id
            validate_user_reference(db, assigned_user_id)
        else:
            if request.assigned_user_id not in (None, current_user.id):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Only administrators and managers can assign surveys to other users",
                )
            assigned_user_id = current_user.id
        customer_id = request.customer_id
        project_id = request.project_id
        lead_id = request.lead_id
        validate_survey_relationships(db, customer_id, project_id, current_user)
        validate_lead_reference(db, lead_id)
    elif current_user is not None and current_user.role.lower() == "customer":
        customer = customer_profile_for_user(db, current_user)
        if request.customer_id is not None and (
            customer is None or request.customer_id != customer.id
        ):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Customer access denied")
        if request.project_id is not None:
            if customer is None:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
            validate_project_reference(db, request.project_id, customer_id=customer.id)
        customer_id = customer.id if customer is not None else None
        project_id = request.project_id

    customer_name = request.customer_name.strip()
    if request.customer_id:
        cust = db.query(Customer).filter(Customer.id == request.customer_id).first()
        if cust:
            customer_name = cust.name

    survey = SiteSurvey(
        customer_name=customer_name,
        location=request.location.strip(),
        property_type=request.property_type,
        survey_date=request.survey_date.strip(),
        time_slot=request.time_slot.strip(),
        assigned_to=request.assigned_to.strip(),
        status=request.status if request.status else "Scheduled",
        customer_id=customer_id,
        project_id=project_id,
        lead_id=lead_id,
        assigned_user_id=assigned_user_id,
        roof_information=request.roof_information,
        capacity_estimate=request.capacity_estimate,
        notes=request.notes,
    )
    db.add(survey)
    db.flush()

    CRMService.record_activity(
        db=db,
        entity_type="site_survey",
        entity_id=survey.id,
        action="scheduled",
        title=f"Site survey scheduled for {survey.customer_name}",
        description=f"Survey on {survey.survey_date} at {survey.time_slot} assigned to {survey.assigned_to}",
        customer_id=survey.customer_id,
        customer_name=survey.customer_name,
        user_id=current_user.id if current_user else None,
        status_val=survey.status,
    )

    # If linked to lead, move lead to Site Survey
    if survey.lead_id:
        lead = db.query(Lead).filter(Lead.id == survey.lead_id).first()
        if lead and lead.status in ["New", "Contacted"]:
            lead.status = "Site Survey"

    if survey.assigned_user_id:
        NotificationService.create_notification(
            db=db,
            user_id=survey.assigned_user_id,
            title="Site Survey Scheduled",
            message=f"Site survey scheduled for {survey.customer_name} on {survey.survey_date} ({survey.time_slot}).",
            notification_type="survey_scheduled",
            entity_type="site_survey",
            entity_id=survey.id,
        )
    if survey.lead_id:
        lead = db.query(Lead).filter(Lead.id == survey.lead_id).first()
        if lead and lead.assigned_user_id and lead.assigned_user_id != survey.assigned_user_id:
            NotificationService.create_notification(
                db=db,
                user_id=lead.assigned_user_id,
                title="Site Survey Scheduled",
                message=f"Site survey scheduled for your lead {survey.customer_name} on {survey.survey_date}.",
                notification_type="survey_scheduled",
                entity_type="site_survey",
                entity_id=survey.id,
            )

    db.commit()
    db.refresh(survey)
    return APIResponse(
        success=True,
        message="Site survey booked successfully",
        data=SiteSurveyResponse.model_validate(survey),
    )


@router.get(
    "/{survey_id}",
    response_model=APIResponse[SiteSurveyResponse],
    summary="Get site survey by ID",
)
def get_survey(
    survey_id: int,
    current_user: User = Depends(require_roles(["Admin", "Manager", "Sales Rep", "Support", "Customer"])),
    db: Session = Depends(get_db),
):
    survey = accessible_surveys_query(db, current_user).filter(SiteSurvey.id == survey_id).first()
    if not survey:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Site survey not found")
    check_survey_access(survey, current_user)
    return APIResponse(success=True, data=SiteSurveyResponse.model_validate(survey))


@router.post(
    "/{survey_id}/start",
    response_model=APIResponse[SiteSurveyResponse],
    summary="Start site survey (transitions Scheduled -> In Progress)",
)
def start_survey(
    survey_id: int,
    current_user: User = Depends(require_roles(STAFF_ROLES)),
    db: Session = Depends(get_db),
):
    survey = db.query(SiteSurvey).filter(SiteSurvey.id == survey_id).first()
    if not survey:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Site survey not found")
    check_survey_access(survey, current_user)
    survey = CRMService.site_survey_start_workflow(db, survey_id, current_user.id)
    return APIResponse(
        success=True,
        message="Site survey started successfully",
        data=SiteSurveyResponse.model_validate(survey),
    )


@router.post(
    "/{survey_id}/complete",
    response_model=APIResponse[Dict[str, Any]],
    summary="Complete site survey (transitions In Progress -> Completed, automatically sets Lead to Quoted)",
)
def complete_survey(
    survey_id: int,
    request: Optional[SiteSurveyCompleteRequest] = None,
    current_user: User = Depends(require_roles(STAFF_ROLES)),
    db: Session = Depends(get_db),
):
    survey = db.query(SiteSurvey).filter(SiteSurvey.id == survey_id).first()
    if not survey:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Site survey not found")
    check_survey_access(survey, current_user)
    c_data = request.model_dump(exclude_unset=True) if request else {}
    result = CRMService.site_survey_complete_workflow(db, survey_id, c_data, current_user.id)
    return APIResponse(
        success=True,
        message="Site survey completed and lead advanced to Quoted",
        data={
            "survey": SiteSurveyResponse.model_validate(result["survey"]).model_dump(),
            "lead_id": result["lead"].id if result.get("lead") else None,
            "lead_status": result["lead"].status if result.get("lead") else None,
        },
    )


@router.post(
    "/{survey_id}/cancel",
    response_model=APIResponse[SiteSurveyResponse],
    summary="Cancel site survey (soft transition without deleting row)",
)
def cancel_survey(
    survey_id: int,
    current_user: User = Depends(require_roles(STAFF_ROLES)),
    db: Session = Depends(get_db),
):
    result = CRMService.site_survey_cancel_workflow(db, survey_id, current_user)
    return APIResponse(
        success=True,
        message="Site survey cancelled successfully",
        data=SiteSurveyResponse.model_validate(result["survey"]),
    )


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
    survey = accessible_surveys_query(db, current_user).filter(SiteSurvey.id == survey_id).first()
    if not survey:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Site survey not found")
    check_survey_access(survey, current_user)

    old_status = survey.status
    old_assigned_user_id = survey.assigned_user_id
    update_data = request.model_dump(exclude_unset=True)
    changed_fields = [
        field for field, value in update_data.items()
        if getattr(survey, field) != value
    ]
    target_status = update_data.get("status")

    if target_status and target_status != old_status:
        CRMService.validate_survey_transition(old_status, target_status)
        if target_status == "In Progress":
            survey = CRMService.site_survey_start_workflow(db, survey_id, current_user.id)
        elif target_status == "Completed":
            res = CRMService.site_survey_complete_workflow(db, survey_id, update_data, current_user.id)
            survey = res["survey"]
        elif target_status == "Cancelled":
            res = CRMService.site_survey_cancel_workflow(db, survey_id, current_user)
            survey = res["survey"]
        # Remove status so apply_survey_update doesn't re-set it
        update_data.pop("status", None)
    if (
        "assigned_user_id" in update_data
        and not is_survey_manager(current_user)
        and update_data["assigned_user_id"] != current_user.id
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators and managers can change survey assignments",
        )
    customer_id = update_data.get("customer_id", survey.customer_id)
    project_id = update_data.get("project_id", survey.project_id)
    validate_survey_relationships(db, customer_id, project_id, current_user)
    validate_lead_reference(db, update_data.get("lead_id"))
    validate_user_reference(db, update_data.get("assigned_user_id"))
    apply_survey_update(survey, update_data)
    CRMService.record_update_activity(
        db=db,
        entity_type="site_survey",
        entity_id=survey.id,
        title=f"Site survey updated for {survey.customer_name}",
        changed_fields=[
            field for field in changed_fields
            if field not in {"status", "assigned_user_id"}
        ],
        customer_id=survey.customer_id,
        customer_name=survey.customer_name,
        user_id=current_user.id,
        status_val=survey.status,
    )
    if (
        "assigned_user_id" in update_data
        and survey.assigned_user_id != old_assigned_user_id
    ):
        CRMService.record_activity(
            db=db,
            entity_type="site_survey",
            entity_id=survey.id,
            action="reassigned",
            title=f"Site survey reassigned for {survey.customer_name}",
            customer_id=survey.customer_id,
            customer_name=survey.customer_name,
            user_id=current_user.id,
            status_val=survey.status,
        )
        if survey.assigned_user_id:
            NotificationService.create_notification(
                db=db,
                user_id=survey.assigned_user_id,
                title="Site Survey Assigned",
                message=f"You have been assigned to the site survey for {survey.customer_name}.",
                notification_type="survey_assigned",
                entity_type="site_survey",
                entity_id=survey.id,
            )

    db.commit()
    db.refresh(survey)
    return APIResponse(
        success=True,
        message="Site survey updated successfully",
        data=SiteSurveyResponse.model_validate(survey),
    )



@router.delete(
    "/{survey_id}",
    response_model=APIResponse[bool],
    summary="Cancel site survey (soft transition preserving history)",
)
def delete_survey(
    survey_id: int,
    current_user: User = Depends(require_roles(["Admin", "Manager"])),
    db: Session = Depends(get_db),
):
    CRMService.site_survey_cancel_workflow(db, survey_id, current_user)
    return APIResponse(success=True, message="Site survey cancelled successfully (history preserved)", data=True)
