import math
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Query as SQLAlchemyQuery, Session
from sqlalchemy import or_, desc, func

from app.core.database import get_db
from app.dependencies.auth import get_current_user, require_roles
from app.models.user import User
from app.models.customer import Customer
from app.models.project import Project
from app.models.lead import Lead
from app.models.site_survey import SiteSurvey
from app.models.activity import Activity
from app.schemas.customer import (
    CustomerCreate,
    CustomerProfileUpdate,
    CustomerUpdate,
    CustomerResponse,
    CustomerOverviewResponse,
)
from app.schemas.lead import LeadResponse
from app.schemas.site_survey import SiteSurveyResponse
from app.schemas.project import ProjectResponse
from app.schemas.activity import ActivityResponse
from app.schemas.common import APIResponse, PaginatedResponse, PaginationMeta
from app.services.crm_service import CRMService
from app.services.dashboard_service import format_relative_time

router = APIRouter(prefix="/customers", tags=["Customers Management"])
STAFF_ROLES = ["Admin", "Manager", "Sales Rep", "Support"]
ALL_ROLES = ["Admin", "Manager", "Sales Rep", "Support", "Customer"]
NULLABLE_CUSTOMER_FIELDS = {"email", "phone", "customer_since", "assigned_user_id"}
CUSTOMER_MANAGER_ROLES = {"admin", "manager"}


def is_customer_manager(user: User) -> bool:
    return user.role.lower() in CUSTOMER_MANAGER_ROLES


def accessible_customers_query(db: Session, current_user: User) -> SQLAlchemyQuery[Customer]:
    query = db.query(Customer)
    if not is_customer_manager(current_user):
        query = query.filter(Customer.assigned_user_id == current_user.id)
    return query


def validate_user_reference(db: Session, user_id: Optional[int]) -> None:
    if user_id is None:
        return None
    target_user = db.query(User).filter(User.id == user_id).first()
    if not target_user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Assigned user not found")
    if target_user.status != "Active":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot assign to an inactive user account.")
    if target_user.role not in STAFF_ROLES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot assign customer to a non-staff account.")
    return target_user


def check_customer_access(customer: Customer, current_user: User) -> None:
    if current_user.role in ["Admin", "Manager"]:
        return
    if current_user.role == "Customer":
        if not current_user.customer_id or customer.id != current_user.customer_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: You are only authorized to access your own customer account."
            )
        return
    if current_user.role in ["Sales Rep", "Support"]:
        if customer.assigned_user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Customer not found"
            )
        return
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")


def validate_customer_account_reference(
    db: Session,
    user_id: Optional[int],
    customer_id: Optional[int] = None,
) -> None:
    if user_id is None:
        return
    user = db.query(User).filter(User.id == user_id).first()
    if user is None or user.role.lower() != "customer":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Customer account not found",
        )
    existing_link_query = db.query(Customer.id).filter(Customer.account_user_id == user_id)
    if customer_id is not None:
        existing_link_query = existing_link_query.filter(Customer.id != customer_id)
    existing_link = existing_link_query.first()
    if existing_link:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Customer account is already linked to another customer record",
        )


def apply_customer_update(customer: Customer, update_data: dict) -> None:
    for field, val in update_data.items():
        if val is None and field not in NULLABLE_CUSTOMER_FIELDS:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"{field} cannot be null",
            )
        setattr(customer, field, val)


@router.get(
    "",
    response_model=PaginatedResponse[CustomerResponse],
    summary="List customers with filtering and pagination",
)
def list_customers(
    search: Optional[str] = Query(None, description="Search by name, contact, location"),
    location: Optional[str] = Query(None),
    property_type: Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    current_user: User = Depends(require_roles(ALL_ROLES)),
    db: Session = Depends(get_db),
):
    query = accessible_customers_query(db, current_user)

    # Scoping
    if current_user.role in ["Sales Rep", "Support"]:
        query = query.filter(Customer.assigned_user_id == current_user.id)
    elif current_user.role == "Customer":
        if current_user.customer_id:
            query = query.filter(Customer.id == current_user.customer_id)
        else:
            query = query.filter(Customer.email == current_user.email)

    if search:
        s = f"%{search.strip()}%"
        query = query.filter(
            or_(
                Customer.name.ilike(s),
                Customer.contact.ilike(s),
                Customer.email.ilike(s),
                Customer.phone.ilike(s),
                Customer.location.ilike(s),
            )
        )

    if location and location != "All Locations":
        query = query.filter(Customer.location.ilike(f"%{location}%"))

    if property_type and property_type not in ["All", "All Property Types"]:
        query = query.filter(Customer.property_type.ilike(property_type))

    if status_filter and status_filter not in ["All", "All Status", "All Statuses"]:
        query = query.filter(Customer.status.ilike(status_filter))

    total = query.count()
    total_pages = math.ceil(total / limit) if total > 0 else 1

    customers = (
        query.order_by(desc(Customer.created_at))
        .offset((page - 1) * limit)
        .limit(limit)
        .all()
    )

    items = []
    for c in customers:
        resp = CustomerResponse.model_validate(c)
        resp.total_projects = db.query(func.count(Project.id)).filter(Project.customer_id == c.id).scalar() or 0
        items.append(resp)

    return PaginatedResponse(
        success=True,
        items=items,
        meta=PaginationMeta(page=page, limit=limit, total=total, total_pages=total_pages),
    )


@router.post(
    "",
    response_model=APIResponse[CustomerResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create a new customer",
)
def create_customer(
    request: CustomerCreate,
    current_user: User = Depends(require_roles(STAFF_ROLES)),
    db: Session = Depends(get_db),
):
    if is_customer_manager(current_user):
        assigned_user_id = request.assigned_user_id
        validate_user_reference(db, assigned_user_id)
        validate_customer_account_reference(db, request.account_user_id)
    else:
        if request.assigned_user_id not in (None, current_user.id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only administrators and managers can assign customers to other users",
            )
        if request.account_user_id is not None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only administrators and managers can link customer accounts",
            )
        assigned_user_id = current_user.id

    customer = Customer(
        name=request.name.strip(),
        contact=request.contact.strip(),
        email=request.email.strip() if request.email else None,
        phone=request.phone.strip() if request.phone else None,
        location=request.location.strip(),
        property_type=request.property_type,
        status=request.status or "Active",
        customer_since=request.customer_since or datetime.now(timezone.utc).strftime("%d %b %Y"),
        assigned_user_id=assigned_user_id,
        account_user_id=request.account_user_id if is_customer_manager(current_user) else None,
    )
    db.add(customer)
    db.flush()

    CRMService.record_activity(
        db=db,
        entity_type="customer",
        entity_id=customer.id,
        action="created",
        title=f"Customer created: {customer.name}",
        description=f"Location: {customer.location}, Property: {customer.property_type}",
        customer_id=customer.id,
        customer_name=customer.name,
        user_id=current_user.id,
        status_val=customer.status,
    )

    db.commit()
    db.refresh(customer)

    resp = CustomerResponse.model_validate(customer)
    resp.total_projects = 0
    return APIResponse(success=True, message="Customer created successfully", data=resp)


def get_linked_customer(db: Session, current_user: User) -> Customer:
    if current_user.role.lower() != "customer":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Customer account access required",
        )
    customers = (
        db.query(Customer)
        .filter(Customer.account_user_id == current_user.id)
        .limit(2)
        .all()
    )
    if len(customers) != 1:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer profile not found")
    return customers[0]


@router.get(
    "/me",
    response_model=APIResponse[CustomerResponse],
    summary="Get the authenticated customer's profile",
)
def get_my_customer_profile(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    customer = get_linked_customer(db, current_user)
    resp = CustomerResponse.model_validate(customer)
    resp.total_projects = (
        db.query(func.count(Project.id)).filter(Project.customer_id == customer.id).scalar() or 0
    )
    return APIResponse(success=True, data=resp)


@router.patch(
    "/me",
    response_model=APIResponse[CustomerResponse],
    summary="Update the authenticated customer's profile",
)
def update_my_customer_profile(
    request: CustomerProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    customer = get_linked_customer(db, current_user)
    update_data = request.model_dump(exclude_unset=True)
    changed_fields = [
        field for field, value in update_data.items()
        if getattr(customer, field) != value
    ]
    apply_customer_update(customer, update_data)
    CRMService.record_update_activity(
        db=db,
        entity_type="customer",
        entity_id=customer.id,
        title=f"Customer profile updated: {customer.name}",
        changed_fields=changed_fields,
        customer_id=customer.id,
        customer_name=customer.name,
        user_id=current_user.id,
        status_val=customer.status,
    )
    db.commit()
    db.refresh(customer)
    resp = CustomerResponse.model_validate(customer)
    resp.total_projects = (
        db.query(func.count(Project.id)).filter(Project.customer_id == customer.id).scalar() or 0
    )
    return APIResponse(success=True, message="Customer profile updated successfully", data=resp)


@router.get(
    "/{customer_id}/overview",
    response_model=APIResponse[CustomerOverviewResponse],
    summary="Get central customer record with all linked CRM entities",
)
def get_customer_overview(
    customer_id: int,
    current_user: User = Depends(require_roles(ALL_ROLES)),
    db: Session = Depends(get_db),
):
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not customer:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found")
    check_customer_access(customer, current_user)
    overview_data = CRMService.get_customer_overview(db, customer_id)
    return APIResponse(success=True, data=CustomerOverviewResponse(**overview_data))


@router.get(
    "/{customer_id}/leads",
    response_model=APIResponse[List[LeadResponse]],
    summary="Get all leads for customer",
)
def get_customer_leads(
    customer_id: int,
    current_user: User = Depends(require_roles(ALL_ROLES)),
    db: Session = Depends(get_db),
):
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not customer:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found")
    check_customer_access(customer, current_user)

    leads = db.query(Lead).filter(Lead.customer_id == customer_id).order_by(desc(Lead.created_at)).all()
    items = []
    for l in leads:
        r = LeadResponse.model_validate(l)
        r.date = l.created_at.strftime("%d %b %Y") if l.created_at else "Recently"
        r.customer_name = l.customer.name if l.customer else None
        items.append(r)
    return APIResponse(success=True, data=items)


@router.get(
    "/{customer_id}/site-surveys",
    response_model=APIResponse[List[SiteSurveyResponse]],
    summary="Get all site surveys for customer",
)
def get_customer_site_surveys(
    customer_id: int,
    current_user: User = Depends(require_roles(ALL_ROLES)),
    db: Session = Depends(get_db),
):
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not customer:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found")
    check_customer_access(customer, current_user)

    surveys = db.query(SiteSurvey).filter(SiteSurvey.customer_id == customer_id).order_by(desc(SiteSurvey.created_at)).all()
    return APIResponse(success=True, data=[SiteSurveyResponse.model_validate(s) for s in surveys])


@router.get(
    "/{customer_id}/projects",
    response_model=APIResponse[List[ProjectResponse]],
    summary="Get all projects for customer",
)
def get_customer_projects(
    customer_id: int,
    current_user: User = Depends(require_roles(ALL_ROLES)),
    db: Session = Depends(get_db),
):
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not customer:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found")
    check_customer_access(customer, current_user)

    projects = db.query(Project).filter(Project.customer_id == customer_id).order_by(desc(Project.created_at)).all()
    items = []
    for p in projects:
        r = ProjectResponse.model_validate(p)
        if p.customer:
            r.customer_name = p.customer.name
        if p.source_lead:
            r.source_lead_name = p.source_lead.name
        items.append(r)
    return APIResponse(success=True, data=items)


@router.get(
    "/{customer_id}/activities",
    response_model=APIResponse[List[ActivityResponse]],
    summary="Get all activities for customer",
)
def get_customer_activities(
    customer_id: int,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0, le=10000),
    current_user: User = Depends(require_roles(ALL_ROLES)),
    db: Session = Depends(get_db),
):
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not customer:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found")
    check_customer_access(customer, current_user)

    activities = (
        db.query(Activity)
        .filter(Activity.customer_id == customer_id)
        .order_by(desc(Activity.created_at), desc(Activity.id))
        .limit(limit)
        .offset(offset)
        .all()
    )
    items = []
    for a in activities:
        r = ActivityResponse.model_validate(a)
        r.time_ago = format_relative_time(a.created_at)
        items.append(r)
    return APIResponse(success=True, data=items)


@router.get(
    "/{customer_id}",
    response_model=APIResponse[CustomerResponse],
    summary="Get customer details by ID",
)
def get_customer(
    customer_id: int,
    current_user: User = Depends(require_roles(ALL_ROLES)),
    db: Session = Depends(get_db),
):
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not customer:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found")
    check_customer_access(customer, current_user)

    resp = CustomerResponse.model_validate(customer)
    resp.total_projects = db.query(func.count(Project.id)).filter(Project.customer_id == customer.id).scalar() or 0
    return APIResponse(success=True, data=resp)


@router.patch(
    "/{customer_id}",
    response_model=APIResponse[CustomerResponse],
    summary="Update customer details",
)
def update_customer(
    customer_id: int,
    request: CustomerUpdate,
    current_user: User = Depends(require_roles(ALL_ROLES)),
    db: Session = Depends(get_db),
):
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not customer:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found")
    check_customer_access(customer, current_user)

    update_data = request.model_dump(exclude_unset=True)

    # Customers cannot reassign staff or alter status
    if current_user.role == "Customer":
        update_data.pop("assigned_user_id", None)
        update_data.pop("status", None)
    elif "assigned_user_id" in update_data:
        if current_user.role not in ["Admin", "Manager"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only administrators and managers can assign or reassign customers."
            )
        validate_user_reference(db, update_data.get("assigned_user_id"))

    old_status = customer.status
    changed_fields = [
        field for field, value in update_data.items()
        if getattr(customer, field) != value
    ]
    if "account_user_id" in update_data and not is_customer_manager(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators and managers can link customer accounts",
        )
    if (
        "assigned_user_id" in update_data
        and not is_customer_manager(current_user)
        and update_data["assigned_user_id"] != current_user.id
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators and managers can change customer assignments",
        )
    validate_user_reference(db, update_data.get("assigned_user_id"))
    if "account_user_id" in update_data:
        validate_customer_account_reference(db, update_data["account_user_id"], customer.id)
    apply_customer_update(customer, update_data)

    if customer.status != old_status:
        CRMService.record_activity(
            db=db,
            entity_type="customer",
            entity_id=customer.id,
            action="status_changed",
            title=f"Customer status updated to {customer.status}: {customer.name}",
            customer_id=customer.id,
            customer_name=customer.name,
            user_id=current_user.id,
            status_val=customer.status,
        )

    CRMService.record_update_activity(
        db=db,
        entity_type="customer",
        entity_id=customer.id,
        title=f"Customer updated: {customer.name}",
        changed_fields=[field for field in changed_fields if field != "status"],
        customer_id=customer.id,
        customer_name=customer.name,
        user_id=current_user.id,
        status_val=customer.status,
    )

    db.commit()
    db.refresh(customer)

    resp = CustomerResponse.model_validate(customer)
    resp.total_projects = db.query(func.count(Project.id)).filter(Project.customer_id == customer.id).scalar() or 0
    return APIResponse(success=True, message="Customer updated successfully", data=resp)


@router.delete(
    "/{customer_id}",
    response_model=APIResponse[bool],
    summary="Inactivate customer (soft transition preserving history)",
)
def delete_customer(
    customer_id: int,
    current_user: User = Depends(require_roles(["Admin", "Manager"])),
    db: Session = Depends(get_db),
):
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not customer:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found")

    customer.status = "Inactive"
    CRMService.record_activity(
        db=db,
        entity_type="customer",
        entity_id=customer.id,
        action="inactivated",
        title=f"Customer marked inactive: {customer.name}",
        description="Customer marked as Inactive; CRM history preserved",
        customer_id=customer.id,
        customer_name=customer.name,
        user_id=current_user.id,
        status_val="Inactive",
    )
    db.commit()
    return APIResponse(success=True, message="Customer marked inactive successfully (history preserved)", data=True)
