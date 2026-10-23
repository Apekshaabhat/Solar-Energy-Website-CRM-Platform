import secrets
from datetime import datetime, timedelta, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.config import settings
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
from app.core.security import get_password_hash, hash_token
from app.dependencies.auth import get_current_user, require_roles
from app.models.user import User
from app.models.token import PasswordResetToken
from app.schemas.user import UserCreate, UserUpdate, UserResponse
from app.schemas.common import APIResponse
from app.services.email_service import EmailService

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
    user, activation_token = UserService.invite_user(db, request, acting_user=current_user)
    if not EmailService.send_account_invitation_email(user.email, activation_token):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "The user was created, but the activation email could not be sent. "
                "Check the SMTP configuration and resend the invitation."
            ),
        )
    return APIResponse(
        success=True,
        message="User invitation created and activation email sent successfully.",
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
    existing = db.query(User).filter(User.email == request.email.lower().strip()).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A user with this email address already exists"
        )
    
    # Generate secure random initial password hash if none provided
    initial_pwd = request.password if request.password else secrets.token_urlsafe(32)
    user = User(
        name=request.name.strip(),
        email=request.email.lower().strip(),
        password_hash=get_password_hash(initial_pwd),
        phone=request.phone.strip() if request.phone else None,
        role=request.role,
        status="Invited" if not request.status or request.status == "Active" else request.status,
        failed_attempts=0,
        token_version=0,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # Generate single-use expiring activation token using the reset mechanism
    raw_token = secrets.token_urlsafe(32)
    token_sha256 = hash_token(raw_token)
    expires_at = datetime.now(timezone.utc) + timedelta(hours=settings.ACCOUNT_ACTIVATION_TOKEN_EXPIRE_HOURS)
    activation_record = PasswordResetToken(
        user_id=user.id,
        token_hash=token_sha256,
        token_type="activate",
        expires_at=expires_at,
    )
    db.add(activation_record)
    db.commit()

    # Emit invitation email / dev console log
    if not EmailService.send_account_invitation_email(user.email, raw_token):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "The user was created, but the activation email could not be sent. "
                "Check the SMTP configuration and resend the invitation."
            ),
        )

    return APIResponse(
        success=True,
        message="User created successfully. Account activation invitation has been generated.",
        data=UserResponse.model_validate(user)
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
    description=(
        "Creates CRM customer records for Customer accounts without a legacy customer association. "
        "Existing records are not matched by email or phone."
    ),
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
