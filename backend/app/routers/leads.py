import math
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Query as SQLAlchemyQuery, Session
from sqlalchemy import or_, desc, func

from app.core.database import get_db
from app.dependencies.auth import get_optional_current_user, is_staff_user, require_roles
from app.models.user import User
from app.models.customer import Customer
from app.models.lead import Lead
from app.models.site_survey import SiteSurvey
from app.models.project import Project
from app.schemas.lead import (
    LeadCreate,
    LeadUpdate,
    LeadResponse,
    LeadListResponse,
    LeadScheduleSurveyRequest,
    LeadConvertRequest,
)
from app.schemas.site_survey import SiteSurveyResponse
from app.schemas.project import ProjectResponse
from app.schemas.common import APIResponse
from app.services.crm_service import CRMService
from app.services.notification_service import NotificationService

router = APIRouter(prefix="/leads", tags=["Leads Management"])

LEAD_STATUSES = ["New", "Contacted", "Site Survey", "Quoted", "Converted", "Cancelled", "Lost"]

STAFF_ROLES = ["Admin", "Manager", "Sales Rep", "Support"]
LEAD_MANAGER_ROLES = {"admin", "manager"}
NULLABLE_LEAD_FIELDS = {"email", "phone", "notes", "estimated_value", "assigned_user_id", "customer_id"}


def is_lead_manager(user: User) -> bool:
    return user.role.lower() in LEAD_MANAGER_ROLES


def validate_user_reference(db: Session, user_id: Optional[int]) -> None:
    if user_id is None:
        return None
    target_user = db.query(User).filter(User.id == user_id).first()
    if not target_user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Assigned user not found")
    if target_user.status != "Active":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot assign lead to an inactive user account."
        )
    if target_user.role not in STAFF_ROLES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot assign lead to a non-staff user account."
        )
    return target_user


def validate_customer_reference(db: Session, customer_id: Optional[int]) -> None:
    if customer_id is None:
        return
    exists = db.query(Customer.id).filter(Customer.id == customer_id).first()
    if not exists:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Customer not found")


def check_lead_access(lead: Lead, current_user: User) -> None:
    if current_user.role in ["Admin", "Manager"]:
        return
    if current_user.role == "Customer":
        if not current_user.customer_id or lead.customer_id != current_user.customer_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: You are not authorized to view this lead."
            )
        return
    if current_user.role in ["Sales Rep", "Support"]:
        if lead.assigned_user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: You may only access leads assigned to you."
            )
        return
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")


def apply_lead_update(lead: Lead, update_data: dict) -> None:
    for field, val in update_data.items():
        if val is None and field not in NULLABLE_LEAD_FIELDS:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"{field} cannot be null",
            )
        setattr(lead, field, val)


def accessible_leads_query(db: Session, current_user: User) -> SQLAlchemyQuery[Lead]:
    query = db.query(Lead)
    if not is_lead_manager(current_user):
        query = query.filter(Lead.assigned_user_id == current_user.id)
    return query
def build_lead_response(lead: Lead, db: Session) -> LeadResponse:
    resp = LeadResponse.model_validate(lead)
    resp.date = lead.created_at.strftime("%d %b %Y") if lead.created_at else "Recently"
    if lead.customer:
        resp.customer_name = lead.customer.name
    resp.surveys_count = db.query(func.count(SiteSurvey.id)).filter(SiteSurvey.lead_id == lead.id).scalar() or 0
    resp.projects_count = db.query(func.count(Project.id)).filter(Project.source_lead_id == lead.id).scalar() or 0
    return resp


@router.get(
    "",
    response_model=LeadListResponse,
    summary="List leads with filtering and pagination",
)
def list_leads(
    search: Optional[str] = Query(None, description="Search by name, phone, email, location"),
    status_filter: Optional[str] = Query(None, alias="status"),
    property_type: Optional[str] = Query(None),
    location: Optional[str] = Query(None),
    source: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    current_user: User = Depends(require_roles(["Admin", "Manager", "Sales Rep", "Support", "Customer"])),
    db: Session = Depends(get_db),
):
    query = accessible_leads_query(db, current_user)

    # Record-level access scoping
    if current_user.role in ["Sales Rep", "Support"]:
        query = query.filter(Lead.assigned_user_id == current_user.id)
    elif current_user.role == "Customer":
        if current_user.customer_id:
            query = query.filter(Lead.customer_id == current_user.customer_id)
        else:
            query = query.filter(Lead.email == current_user.email)


    if search:
        s = f"%{search.strip()}%"
        query = query.filter(
            or_(
                Lead.name.ilike(s),
                Lead.contact.ilike(s),
                Lead.email.ilike(s),
                Lead.phone.ilike(s),
                Lead.location.ilike(s),
            )
        )

    if property_type and property_type != "All Property Types":
        query = query.filter(Lead.property_type.ilike(property_type))

    if location and location != "All Locations":
        query = query.filter(Lead.location.ilike(f"%{location}%"))

    if source and source != "All Sources":
        query = query.filter(Lead.source.ilike(source))

    # Calculate status counts across all matches before applying status filter
    tab_counts = {"All Leads": query.count()}
    for st in LEAD_STATUSES:
        tab_counts[st] = query.filter(Lead.status == st).count()

    if status_filter and status_filter not in ["All Leads", "All Status", "All Statuses"]:
        query = query.filter(Lead.status == status_filter)

    total = query.count()
    total_pages = math.ceil(total / limit) if total > 0 else 1

    leads = (
        query.order_by(desc(Lead.created_at))
        .offset((page - 1) * limit)
        .limit(limit)
        .all()
    )

    items = [build_lead_response(l, db) for l in leads]

    return LeadListResponse(
        success=True,
        items=items,
        total=total,
        page=page,
        limit=limit,
        total_pages=total_pages,
        tab_counts=tab_counts,
    )


@router.post(
    "",
    response_model=APIResponse[LeadResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create or submit a new lead",
)
def create_lead(
    request: LeadCreate,
    current_user: Optional[User] = Depends(get_optional_current_user),
    db: Session = Depends(get_db),
):
    is_staff = is_staff_user(current_user)
    assigned_user_id = None
    if is_staff:
        if is_lead_manager(current_user):
            assigned_user_id = request.assigned_user_id
            validate_user_reference(db, assigned_user_id)
        else:
            if request.assigned_user_id not in (None, current_user.id):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Only administrators and managers can assign leads to other users",
                )
            assigned_user_id = current_user.id
        validate_customer_reference(db, request.customer_id)

    lead = Lead(
        name=request.name.strip(),
        contact=request.contact.strip(),
        email=request.email.strip() if request.email else None,
        phone=request.phone.strip() if request.phone else None,
        location=request.location.strip(),
        property_type=request.property_type,
        source=request.source,
        status=request.status or "New",
        notes=request.notes,
        estimated_value=request.estimated_value,
        assigned_user_id=assigned_user_id,
        customer_id=request.customer_id if is_staff else None,
    )
    db.add(lead)
    db.flush()

    CRMService.record_activity(
        db=db,
        entity_type="lead",
        entity_id=lead.id,
        action="created",
        title=f"Lead created: {lead.name}",
        description=f"Source: {lead.source}, Location: {lead.location}",
        customer_id=lead.customer_id,
        customer_name=lead.name,
        user_id=lead.assigned_user_id,
        status_val=lead.status,
    )

    # If created directly in Contacted or beyond, ensure customer is linked
    if is_staff and lead.status in ["Contacted", "Site Survey", "Quoted", "Converted"]:
        CRMService.find_or_create_customer_for_lead(db, lead)

    if lead.assigned_user_id:
        NotificationService.create_notification(
            db=db,
            user_id=lead.assigned_user_id,
            title="New Lead Assigned",
            message=f"You have been assigned to lead '{lead.name}'.",
            notification_type="lead_assigned",
            entity_type="lead",
            entity_id=lead.id,
        )
    else:
        NotificationService.notify_roles(
            db=db,
            roles=["Admin", "Manager"],
            title="New Lead Received",
            message=f"New lead received: '{lead.name}' from {lead.source}.",
            notification_type="new_lead",
            entity_type="lead",
            entity_id=lead.id,
        )

    db.commit()
    db.refresh(lead)

    return APIResponse(success=True, message="Lead created successfully", data=build_lead_response(lead, db))


@router.get(
    "/{lead_id}",
    response_model=APIResponse[LeadResponse],
    summary="Get lead by ID",
)
def get_lead(
    lead_id: int,
    current_user: User = Depends(require_roles(["Admin", "Manager", "Sales Rep", "Support", "Customer"])),
    db: Session = Depends(get_db),
):
    lead = accessible_leads_query(db, current_user).filter(Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lead not found")
    check_lead_access(lead, current_user)
    return APIResponse(success=True, data=build_lead_response(lead, db))


@router.patch(
    "/{lead_id}",
    response_model=APIResponse[LeadResponse],
    summary="Update lead info or status",
)
def update_lead(
    lead_id: int,
    request: LeadUpdate,
    current_user: User = Depends(require_roles(["Admin", "Manager", "Sales Rep", "Support", "Customer"])),
    db: Session = Depends(get_db),
):
    lead = accessible_leads_query(db, current_user).filter(Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lead not found")
    check_lead_access(lead, current_user)

    old_status = lead.status
    update_data = request.model_dump(exclude_unset=True)
    changed_fields = [
        field for field, value in update_data.items()
        if getattr(lead, field) != value
    ]
    target_status = update_data.get("status")

    if target_status and target_status != old_status:
        CRMService.validate_lead_transition(old_status, target_status)
        if target_status == "Contacted":
            lead = CRMService.lead_contacted_workflow(db, lead.id, current_user.id)
        elif target_status == "Converted":
            res = CRMService.lead_convert_workflow(db, lead.id, None, current_user.id)
            lead = res["lead"]
        elif target_status in ["Cancelled", "Lost"]:
            lead = CRMService.lead_cancel_workflow(db, lead.id, target_status, current_user.id)
        update_data.pop("status", None)

    # Lead assignment validation & audit
    if "assigned_user_id" in update_data and update_data["assigned_user_id"] != lead.assigned_user_id:
        if current_user.role not in ["Admin", "Manager"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only administrators and managers can assign or reassign leads."
            )
        target_user = validate_user_reference(db, update_data["assigned_user_id"])
        old_user = db.query(User).filter(User.id == lead.assigned_user_id).first() if lead.assigned_user_id else None
        old_name = old_user.name if old_user else "Unassigned"
        new_name = target_user.name if target_user else "Unassigned"

        CRMService.record_activity(
            db=db,
            entity_type="lead",
            entity_id=lead.id,
            action="reassigned",
            title=f"Lead reassigned: {lead.name}",
            description=f"Assigned staff member changed from {old_name} to {new_name}",
            customer_id=lead.customer_id,
            customer_name=lead.name,
            user_id=current_user.id,
            status_val=lead.status,
        )

        if update_data["assigned_user_id"]:
            NotificationService.create_notification(
                db=db,
                user_id=update_data["assigned_user_id"],
                title="Lead Assigned",
                message=f"You have been assigned to lead '{lead.name}'.",
                notification_type="lead_assigned",
                entity_type="lead",
                entity_id=lead.id,
            )

    validate_customer_reference(db, update_data.get("customer_id"))
    apply_lead_update(lead, update_data)
    CRMService.record_update_activity(
        db=db,
        entity_type="lead",
        entity_id=lead.id,
        title=f"Lead updated: {lead.name}",
        changed_fields=[
            field for field in changed_fields
            if field not in {"status", "assigned_user_id"}
        ],
        customer_id=lead.customer_id,
        customer_name=lead.name,
        user_id=current_user.id,
        status_val=lead.status,
    )

    db.commit()
    db.refresh(lead)

    return APIResponse(success=True, message="Lead updated successfully", data=build_lead_response(lead, db))



@router.post(
    "/{lead_id}/contact",
    response_model=APIResponse[LeadResponse],
    summary="Mark lead as contacted and link/create customer",
)
def contact_lead(
    lead_id: int,
    current_user: User = Depends(require_roles(STAFF_ROLES)),
    db: Session = Depends(get_db),
):
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lead not found")
    check_lead_access(lead, current_user)
    lead = CRMService.lead_contacted_workflow(db, lead_id, current_user.id)
    return APIResponse(success=True, message="Lead contacted and customer linked", data=build_lead_response(lead, db))



@router.post(
    "/{lead_id}/schedule-survey",
    response_model=APIResponse[Dict[str, Any]],
    summary="Schedule site survey for lead",
)
def schedule_lead_survey(
    lead_id: int,
    request: LeadScheduleSurveyRequest,
    current_user: User = Depends(require_roles(STAFF_ROLES)),
    db: Session = Depends(get_db),
):
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lead not found")
    check_lead_access(lead, current_user)

    result = CRMService.lead_schedule_survey_workflow(
        db,
        lead_id,
        request.model_dump(),
        current_user.id,
    )
    return APIResponse(
        success=True,
        message="Site survey scheduled successfully",
        data={
            "lead": build_lead_response(result["lead"], db).model_dump(),
            "survey": SiteSurveyResponse.model_validate(result["survey"]).model_dump(),
            "survey_id": result["survey"].id,
            "customer_id": result["customer"].id,
            "customer_name": result["customer"].name,
        },
    )


@router.post(
    "/{lead_id}/convert",
    response_model=APIResponse[Dict[str, Any]],
    summary="Convert lead to project and customer",
)
def convert_lead(
    lead_id: int,
    request: LeadConvertRequest = None,
    current_user: User = Depends(require_roles(STAFF_ROLES)),
    db: Session = Depends(get_db),
):
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lead not found")
    check_lead_access(lead, current_user)

    project_data = request.model_dump() if request else {}
    result = CRMService.lead_convert_workflow(
        db,
        lead_id,
        project_data,
        current_user.id,
    )
    return APIResponse(
        success=True,
        message="Lead successfully converted to project",
        data={
            "lead": build_lead_response(result["lead"], db).model_dump(),
            "project": ProjectResponse.model_validate(result["project"]).model_dump(),
            "project_id": result["project"].id,
            "project_name": result["project"].name,
            "customer_id": result["customer"].id,
            "customer_name": result["customer"].name,
        },
    )


@router.get(
    "/{lead_id}/related-data",
    response_model=APIResponse[Dict[str, Any]],
    summary="Get all CRM data linked to this lead",
)
def get_lead_related_data(
    lead_id: int,
    current_user: User = Depends(require_roles(STAFF_ROLES)),
    db: Session = Depends(get_db),
):
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lead not found")
    check_lead_access(lead, current_user)

    surveys = db.query(SiteSurvey).filter(SiteSurvey.lead_id == lead.id).all()
    projects = db.query(Project).filter(Project.source_lead_id == lead.id).all()

    return APIResponse(
        success=True,
        data={
            "lead": build_lead_response(lead, db).model_dump(),
            "customer": {
                "id": lead.customer.id,
                "name": lead.customer.name,
                "contact": lead.customer.contact,
                "location": lead.customer.location,
            } if lead.customer else None,
            "surveys": [
                {
                    "id": s.id,
                    "date": s.survey_date,
                    "timeSlot": s.time_slot,
                    "status": s.status,
                    "assignedTo": s.assigned_to,
                }
                for s in surveys
            ],
            "projects": [
                {
                    "id": p.id,
                    "name": p.name,
                    "capacity": p.capacity,
                    "status": p.status,
                }
                for p in projects
            ],
        },
    )


@router.post(
    "/{lead_id}/cancel",
    response_model=APIResponse[LeadResponse],
    summary="Cancel or mark lead as Lost (soft transition)",
)
def cancel_lead(
    lead_id: int,
    status_val: str = Query("Cancelled", description="'Cancelled' or 'Lost'"),
    current_user: User = Depends(require_roles(STAFF_ROLES)),
    db: Session = Depends(get_db),
):
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lead not found")
    check_lead_access(lead, current_user)
    lead = CRMService.lead_cancel_workflow(db, lead_id, status_val, current_user.id)
    return APIResponse(
        success=True,
        message=f"Lead marked as {lead.status}",
        data=build_lead_response(lead, db),
    )


@router.delete(
    "/{lead_id}",
    response_model=APIResponse[bool],
    summary="Cancel lead (soft transition preserving CRM history)",
)
def delete_lead(
    lead_id: int,
    current_user: User = Depends(require_roles(["Admin", "Manager"])),
    db: Session = Depends(get_db),
):
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lead not found")
    check_lead_access(lead, current_user)
    CRMService.lead_cancel_workflow(db, lead_id, "Cancelled", current_user.id)
    return APIResponse(success=True, message="Lead cancelled successfully (history preserved)", data=True)

