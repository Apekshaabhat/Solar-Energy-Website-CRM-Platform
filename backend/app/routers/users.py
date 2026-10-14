from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import or_, desc

from app.core.database import get_db
from app.core.security import get_password_hash
from app.dependencies.auth import get_current_user, require_roles
from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate, UserResponse
from app.schemas.common import APIResponse

router = APIRouter(prefix="/users", tags=["Users Management"])


@router.get(
    "",
    response_model=APIResponse[List[UserResponse]],
    summary="List all users",
    description="Retrieve users list with optional search query and role filter.",
)
def list_users(
    search: Optional[str] = Query(None, description="Search by name or email"),
    role: Optional[str] = Query(None, description="Filter by role"),
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by status"),
    current_user: User = Depends(require_roles(["Admin", "Manager"])),
    db: Session = Depends(get_db),
):
    query = db.query(User)
    if search:
        s = f"%{search.strip()}%"
        query = query.filter(or_(User.name.ilike(s), User.email.ilike(s)))
    if role and role not in ["All", "All Roles"]:
        query = query.filter(User.role.ilike(role))
    if status_filter and status_filter not in ["All", "All Status", "All Statuses"]:
        query = query.filter(User.status.ilike(status_filter))

    users = query.order_by(desc(User.created_at)).all()
    return APIResponse(
        success=True,
        message="Users retrieved successfully",
        data=[UserResponse.model_validate(u) for u in users]
    )


@router.post(
    "",
    response_model=APIResponse[UserResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Invite or create a new user",
    description="Allows administrators to add or invite new staff members with specified roles.",
)
def create_user(
    request: UserCreate,
    current_user: User = Depends(require_roles(["Admin"])),
    db: Session = Depends(get_db),
):
    existing = db.query(User).filter(User.email == request.email.lower().strip()).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A user with this email address already exists"
        )
    
    user = User(
        name=request.name.strip(),
        email=request.email.lower().strip(),
        password_hash=get_password_hash(request.password),
        phone=request.phone.strip() if request.phone else None,
        role=request.role,
        status=request.status or "Invited"
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return APIResponse(
        success=True,
        message="User created successfully",
        data=UserResponse.model_validate(user)
    )


@router.get(
    "/{user_id}",
    response_model=APIResponse[UserResponse],
    summary="Get user details by ID",
)
def get_user(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if current_user.role not in ["Admin", "Manager"] and current_user.id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to view this user profile"
        )
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return APIResponse(success=True, data=UserResponse.model_validate(user))


@router.patch(
    "/{user_id}",
    response_model=APIResponse[UserResponse],
    summary="Update user details",
)
def update_user(
    user_id: int,
    request: UserUpdate,
    current_user: User = Depends(require_roles(["Admin", "Manager"])),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    if request.email and request.email.lower() != user.email.lower():
        existing = db.query(User).filter(User.email == request.email.lower()).first()
        if existing and existing.id != user.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email is already used by another user"
            )
        user.email = request.email.lower().strip()

    if request.name is not None:
        user.name = request.name.strip()
    if request.phone is not None:
        user.phone = request.phone.strip() if request.phone else None
    if request.role is not None:
        # Only admin can change roles
        if current_user.role != "Admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only administrators can update user roles"
            )
        user.role = request.role
    if request.status is not None:
        user.status = request.status
    if request.password:
        user.password_hash = get_password_hash(request.password)

    db.commit()
    db.refresh(user)
    return APIResponse(
        success=True,
        message="User updated successfully",
        data=UserResponse.model_validate(user)
    )


@router.delete(
    "/{user_id}",
    response_model=APIResponse[bool],
    summary="Delete user account",
)
def delete_user(
    user_id: int,
    current_user: User = Depends(require_roles(["Admin"])),
    db: Session = Depends(get_db),
):
    if current_user.id == user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete your own administrator account"
        )
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    db.delete(user)
    db.commit()
    return APIResponse(success=True, message="User deleted successfully", data=True)
