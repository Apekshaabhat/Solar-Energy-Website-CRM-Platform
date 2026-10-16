from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies.auth import get_current_user, require_roles
from app.models.user import User
from app.schemas.user import (
    UserCreate,
    UserInviteRequest,
    UserUpdate,
    UserResponse,
    UserStatsResponse,
)
from app.schemas.common import APIResponse
from app.services.user_service import UserService

router = APIRouter(prefix="/users", tags=["Users Management"])


@router.get(
    "/stats",
    response_model=APIResponse[UserStatsResponse],
    summary="Get aggregated user metrics and statistics",
    description="Returns total users, active/inactive counts, pending invitations, and users by role.",
)
def get_user_stats(
    current_user: User = Depends(require_roles(["Admin", "Manager"])),
    db: Session = Depends(get_db),
):
    stats_data = UserService.get_user_stats(db)
    return APIResponse(
        success=True,
        message="User statistics retrieved",
        data=UserStatsResponse(**stats_data),
    )


@router.get(
    "",
    response_model=APIResponse[List[UserResponse]],
    summary="List users with search, role, and status filters",
    description="Retrieve users list. Admin views all users; Managers view non-administrative staff.",
)
def list_users(
    search: Optional[str] = Query(None, description="Search by name, email, or phone"),
    role: Optional[str] = Query(None, description="Filter by role"),
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by status"),
    current_user: User = Depends(require_roles(["Admin", "Manager"])),
    db: Session = Depends(get_db),
):
    users = UserService.list_users(
        db=db,
        search=search,
        role=role,
        status_filter=status_filter,
        current_user=current_user,
    )
    return APIResponse(
        success=True,
        message="Users retrieved successfully",
        data=[UserResponse.model_validate(u) for u in users],
    )


@router.post(
    "/invite",
    response_model=APIResponse[UserResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Invite a new user with secure single-use token",
    description="Creates an account in Invited state and generates a single-use expiring invitation token.",
)
def invite_user(
    request: UserInviteRequest,
    current_user: User = Depends(require_roles(["Admin"])),
    db: Session = Depends(get_db),
):
    user, _ = UserService.invite_user(db, request, acting_user=current_user)
    return APIResponse(
        success=True,
        message="User invitation created successfully.",
        data=UserResponse.model_validate(user),
    )


@router.post(
    "",
    response_model=APIResponse[UserResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create or invite a new user",
    description="Allows administrators to add or invite new staff members with specified roles.",
)
def create_user(
    request: UserCreate,
    current_user: User = Depends(require_roles(["Admin"])),
    db: Session = Depends(get_db),
):
    invite_req = UserInviteRequest(
        name=request.name,
        email=request.email,
        phone=request.phone,
        role=request.role,
        customer_id=request.customer_id,
    )
    user, _ = UserService.invite_user(
        db=db,
        request=invite_req,
        acting_user=current_user,
        initial_password=request.password,
    )
    # If explicit password was provided, activate immediately
    if request.password and (request.status == "Active" or not request.status):
        user.status = "Active"
        user.invitation_token_hash = None
        user.invitation_expires_at = None
        db.commit()
        db.refresh(user)

    return APIResponse(
        success=True,
        message="User created successfully",
        data=UserResponse.model_validate(user),
    )


@router.get(
    "/{user_id}",
    response_model=APIResponse[UserResponse],
    summary="Get user details by ID",
    description="Retrieve details of a user. Scoped: Admin can view any user; Managers view non-admins; staff/customers view only self.",
)
def get_user(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    user = UserService.get_user_by_id(db, user_id, current_user)
    return APIResponse(success=True, data=UserResponse.model_validate(user))


@router.patch(
    "/{user_id}",
    response_model=APIResponse[UserResponse],
    summary="Update user details",
    description="Allows authorized updates. Only Admin can change roles; last admin cannot be demoted or deactivated.",
)
def update_user(
    user_id: int,
    request: UserUpdate,
    current_user: User = Depends(require_roles(["Admin", "Manager"])),
    db: Session = Depends(get_db),
):
    user = UserService.update_user(db, user_id, request, current_user)
    return APIResponse(
        success=True,
        message="User updated successfully",
        data=UserResponse.model_validate(user),
    )


@router.delete(
    "/{user_id}",
    response_model=APIResponse[bool],
    summary="Delete user account",
    description="Admin-only operation. Reassigns/preserves related CRM history and protects the last active administrator.",
)
def delete_user(
    user_id: int,
    current_user: User = Depends(require_roles(["Admin"])),
    db: Session = Depends(get_db),
):
    UserService.delete_user(db, user_id, current_user)
    return APIResponse(success=True, message="User deleted successfully", data=True)


@router.post(
    "/backfill-customers",
    response_model=APIResponse[dict],
    summary="Backfill Customer account linkings",
    description="Reconciles Customer login accounts with CRM customer records.",
)
def backfill_customers(
    current_user: User = Depends(require_roles(["Admin"])),
    db: Session = Depends(get_db),
):
    result = UserService.backfill_customer_users(db)
    return APIResponse(
        success=True,
        message="Customer-User reconciliation completed.",
        data=result,
    )
