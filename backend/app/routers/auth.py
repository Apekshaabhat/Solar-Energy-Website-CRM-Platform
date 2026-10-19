from typing import Optional
from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.limiter import limiter
from app.dependencies.auth import get_current_user, oauth2_scheme
from app.models.user import User
from app.schemas.auth import (
    Token,
    LoginRequest,
    RegisterRequest,
    ActivateAccountRequest,
    ForgotPasswordRequest,
    ResetPasswordRequest,
    ActivateRequest,
    ChangePasswordRequest,
    ProfileUpdateRequest,
)
from app.schemas.user import UserResponse
from app.schemas.common import APIResponse
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/register",
    response_model=APIResponse[Optional[UserResponse]],
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user account",
    description="Registers a new customer account in Pending status. Does not reveal whether email exists.",
)
@limiter.limit(settings.AUTH_RATE_LIMIT)
def register(
    request: Request,
    body: RegisterRequest,
    db: Session = Depends(get_db),
):
    AuthService.register_user(db, body)
    return APIResponse(
        success=True,
        message="Registration request submitted. Your account is pending administrator approval.",
        data=None,
    )


@router.post(
    "/activate",
    response_model=APIResponse[UserResponse],
    summary="Activate invited user account",
    description="Validates single-use expiring invitation token and sets the initial account password.",
)
def activate(request: ActivateAccountRequest, db: Session = Depends(get_db)):
    user = AuthService.activate_account(db, request)
    return APIResponse(
        success=True,
        message="Account activated successfully. You may now log in.",
        data=UserResponse.model_validate(user),
    )



@router.post(
    "/login",
    response_model=Token,
    summary="User login",
    description="Authenticates user credentials, enforces lockout policy, and returns a signed JWT access token.",
)
@limiter.limit(settings.AUTH_RATE_LIMIT)
def login(
    request: Request,
    body: LoginRequest,
    db: Session = Depends(get_db),
):
    return AuthService.authenticate_user(db, body)


@router.get(
    "/me",
    response_model=APIResponse[UserResponse],
    summary="Get current user profile",
    description="Authoritative current-user endpoint that retrieves validated user profile from database.",
)
def get_me(current_user: User = Depends(get_current_user)):
    return APIResponse(
        success=True,
        message="Current user profile fetched",
        data=UserResponse.model_validate(current_user),
    )


@router.patch(
    "/profile",
    response_model=APIResponse[UserResponse],
    summary="Update current user personal profile",
    description="Allows authenticated user to update name, email, and phone number.",
)
def update_profile(
    request: ProfileUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    updated = AuthService.update_profile(db, current_user, request)
    return APIResponse(
        success=True,
        message="Profile updated successfully",
        data=UserResponse.model_validate(updated),
    )


@router.post(
    "/change-password",
    response_model=APIResponse[bool],
    summary="Change user password",
    description="Changes password after validating the current password, and invalidates other active sessions.",
)
def change_password(
    request: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    AuthService.update_password(db, current_user, request)
    return APIResponse(
        success=True,
        message="Password updated successfully",
        data=True,
    )


@router.post(
    "/forgot-password",
    response_model=APIResponse[bool],
    summary="Forgot password request",
    description="Sends password reset instructions if account exists and is active without revealing status.",
)
@limiter.limit(settings.AUTH_RATE_LIMIT)
def forgot_password(
    request: Request,
    body: ForgotPasswordRequest,
    db: Session = Depends(get_db),
):
    AuthService.request_password_reset(db, body.email)
    return APIResponse(
        success=True,
        message="If an account with this email exists, password reset instructions have been sent.",
        data=True,
    )


@router.post(
    "/reset-password",
    response_model=APIResponse[bool],
    summary="Reset password with token",
    description="Verifies single-use reset token and updates password while invalidating old sessions.",
)
def reset_password(
    body: ResetPasswordRequest,
    db: Session = Depends(get_db),
):
    AuthService.reset_password(db, body.token, body.new_password)
    return APIResponse(
        success=True,
        message="Password reset successfully. You can now log in.",
        data=True,
    )


@router.post(
    "/activate",
    response_model=APIResponse[bool],
    summary="Activate invited user account",
    description="Verifies activation token, sets initial password, and activates account.",
)
def activate(
    body: ActivateRequest,
    db: Session = Depends(get_db),
):
    AuthService.activate_account(db, body.token, body.password)
    return APIResponse(
        success=True,
        message="Account activated successfully. You can now log in.",
        data=True,
    )


@router.post(
    "/logout",
    response_model=APIResponse[bool],
    summary="User logout",
    description="Revokes current token's jti claim.",
)
def logout(
    token: Optional[str] = Depends(oauth2_scheme),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if token:
        AuthService.revoke_token(db, token)
    return APIResponse(
        success=True,
        message="Logged out successfully",
        data=True,
    )
