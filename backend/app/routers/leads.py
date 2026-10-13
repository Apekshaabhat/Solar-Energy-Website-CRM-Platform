import math
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Query as SQLAlchemyQuery, Session
from sqlalchemy import or_, desc, func

from app.core.database import get_db
from app.dependencies.auth import get_optional_current_user, is_staff_user, require_roles
from app.models.user import User
from app.models.customer import Customer
from app.models.lead import Lead
from app.schemas.lead import LeadCreate, LeadUpdate, LeadResponse, LeadListResponse
from app.schemas.common import APIResponse

router = APIRouter(prefix="/leads", tags=["Leads Management"])

LEAD_STATUSES = ["New", "Contacted", "Site Survey", "Quoted", "Converted", "Lost"]
STAFF_ROLES = ["Admin", "Manager", "Sales Rep", "Support"]
LEAD_MANAGER_ROLES = {"admin", "manager"}
NULLABLE_LEAD_FIELDS = {"email", "phone", "notes", "estimated_value", "assigned_user_id", "customer_id"}


def is_lead_manager(user: User) -> bool:
    return user.role.lower() in LEAD_MANAGER_ROLES


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
    current_user: User = Depends(require_roles(STAFF_ROLES)),
    db: Session = Depends(get_db),
):
    query = accessible_leads_query(db, current_user)

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

    items = []
    for l in leads:
        lead_dict = LeadResponse.model_validate(l)
        lead_dict.date = l.created_at.strftime("%d %b %Y") if l.created_at else "Recently"
        items.append(lead_dict)

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
    db.commit()
    db.refresh(lead)

    resp = LeadResponse.model_validate(lead)
    resp.date = lead.created_at.strftime("%d %b %Y") if lead.created_at else "Recently"
    return APIResponse(success=True, message="Lead created successfully", data=resp)


@router.get(
    "/{lead_id}",
    response_model=APIResponse[LeadResponse],
    summary="Get lead by ID",
)
def get_lead(
    lead_id: int,
    current_user: User = Depends(require_roles(STAFF_ROLES)),
    db: Session = Depends(get_db),
):
    lead = accessible_leads_query(db, current_user).filter(Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lead not found")
    resp = LeadResponse.model_validate(lead)
    resp.date = lead.created_at.strftime("%d %b %Y") if lead.created_at else "Recently"
    return APIResponse(success=True, data=resp)


@router.patch(
    "/{lead_id}",
    response_model=APIResponse[LeadResponse],
    summary="Update lead info or status",
)
def update_lead(
    lead_id: int,
    request: LeadUpdate,
    current_user: User = Depends(require_roles(STAFF_ROLES)),
    db: Session = Depends(get_db),
):
    lead = accessible_leads_query(db, current_user).filter(Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lead not found")

    update_data = request.model_dump(exclude_unset=True)
    if (
        "assigned_user_id" in update_data
        and not is_lead_manager(current_user)
        and update_data["assigned_user_id"] != current_user.id
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators and managers can change lead assignments",
        )
    validate_user_reference(db, update_data.get("assigned_user_id"))
    validate_customer_reference(db, update_data.get("customer_id"))
    apply_lead_update(lead, update_data)

    db.commit()
    db.refresh(lead)

    resp = LeadResponse.model_validate(lead)
    resp.date = lead.created_at.strftime("%d %b %Y") if lead.created_at else "Recently"
    return APIResponse(success=True, message="Lead updated successfully", data=resp)


@router.delete(
    "/{lead_id}",
    response_model=APIResponse[bool],
    summary="Delete lead",
)
def delete_lead(
    lead_id: int,
    current_user: User = Depends(require_roles(["Admin", "Manager"])),
    db: Session = Depends(get_db),
):
    lead = accessible_leads_query(db, current_user).filter(Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lead not found")

    db.delete(lead)
    db.commit()
    return APIResponse(success=True, message="Lead deleted successfully", data=True)
