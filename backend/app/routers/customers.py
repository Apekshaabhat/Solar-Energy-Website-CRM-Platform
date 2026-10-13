import math
from typing import Optional, List
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import or_, desc, func

from app.core.database import get_db
from app.dependencies.auth import require_roles
from app.models.user import User
from app.models.customer import Customer
from app.models.project import Project
from app.schemas.customer import CustomerCreate, CustomerUpdate, CustomerResponse
from app.schemas.common import APIResponse, PaginatedResponse, PaginationMeta

router = APIRouter(prefix="/customers", tags=["Customers Management"])
STAFF_ROLES = ["Admin", "Manager", "Sales Rep", "Support"]
NULLABLE_CUSTOMER_FIELDS = {"email", "phone", "customer_since", "assigned_user_id"}


def validate_user_reference(db: Session, user_id: Optional[int]) -> None:
    if user_id is None:
        return
    exists = db.query(User.id).filter(User.id == user_id).first()
    if not exists:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Assigned user not found")


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
    current_user: User = Depends(require_roles(STAFF_ROLES)),
    db: Session = Depends(get_db),
):
    query = db.query(Customer)

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
        # Compute real project count
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
    validate_user_reference(db, request.assigned_user_id)

    customer = Customer(
        name=request.name.strip(),
        contact=request.contact.strip(),
        email=request.email.strip() if request.email else None,
        phone=request.phone.strip() if request.phone else None,
        location=request.location.strip(),
        property_type=request.property_type,
        status=request.status or "Active",
        customer_since=request.customer_since or datetime.now(timezone.utc).strftime("%d %b %Y"),
        assigned_user_id=request.assigned_user_id,
    )
    db.add(customer)
    db.commit()
    db.refresh(customer)

    resp = CustomerResponse.model_validate(customer)
    resp.total_projects = 0
    return APIResponse(success=True, message="Customer created successfully", data=resp)


@router.get(
    "/{customer_id}",
    response_model=APIResponse[CustomerResponse],
    summary="Get customer details by ID",
)
def get_customer(
    customer_id: int,
    current_user: User = Depends(require_roles(STAFF_ROLES)),
    db: Session = Depends(get_db),
):
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not customer:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found")
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
    current_user: User = Depends(require_roles(STAFF_ROLES)),
    db: Session = Depends(get_db),
):
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not customer:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found")

    update_data = request.model_dump(exclude_unset=True)
    validate_user_reference(db, update_data.get("assigned_user_id"))
    apply_customer_update(customer, update_data)

    db.commit()
    db.refresh(customer)

    resp = CustomerResponse.model_validate(customer)
    resp.total_projects = db.query(func.count(Project.id)).filter(Project.customer_id == customer.id).scalar() or 0
    return APIResponse(success=True, message="Customer updated successfully", data=resp)


@router.delete(
    "/{customer_id}",
    response_model=APIResponse[bool],
    summary="Delete customer",
)
def delete_customer(
    customer_id: int,
    current_user: User = Depends(require_roles(["Admin", "Manager"])),
    db: Session = Depends(get_db),
):
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not customer:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found")

    db.delete(customer)
    db.commit()
    return APIResponse(success=True, message="Customer deleted successfully", data=True)
