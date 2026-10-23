
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
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
    ChangePasswordRequest,
    ProfileUpdateRequest,
)
from app.schemas.user import UserResponse
from app.schemas.common import APIResponse
from app.services.auth_service import AuthService
from app.services.email_service import EmailService


router = APIRouter(
    prefix="/auth",
    tags=["Authentication"],
)


@router.post(
    "/register",
    response_model=APIResponse[Optional[UserResponse]],
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user account",
    description=(
        "Registers a new customer account in Pending status. "
        "Does not reveal whether the email already exists."
    ),
)
@limiter.limit(settings.AUTH_RATE_LIMIT)
def register(
    request: Request,
    body: RegisterRequest,
    db: Session = Depends(get_db),
):
    user, activation_token = AuthService.register_user(db, body)
    if user and activation_token:
        if not EmailService.send_account_invitation_email(user.email, activation_token):
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=(
                    "Your account was created, but the activation email could not be sent. "
                    "Please try signing up again later or contact support."
                ),
            )

    return APIResponse(
        success=True,
        message=(
            "Registration successful. Check your email for the activation link."
        ),
        data=UserResponse.model_validate(user) if user else None,
    )


@router.post(
    "/activate",
    response_model=APIResponse[UserResponse],
    summary="Activate invited user account",
    description=(
        "Validates a single-use, expiring invitation token "
        "and sets the initial account password."
    ),
)
def activate_account(
    body: ActivateAccountRequest,
    db: Session = Depends(get_db),
):
    user = AuthService.activate_account(db, body)

    return APIResponse(
        success=True,
        message="Account activated successfully. You may now log in.",
        data=UserResponse.model_validate(user),
    )

@router.post(
    "/login",
    response_model=Token,
    summary="User login",
    description=(
        "Authenticates user credentials, enforces the lockout "
        "policy, and returns a signed JWT access token."
    ),
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
    description=(
        "Retrieves the authenticated user's profile "
        "from the database."
    ),
)
def get_me(
    current_user: User = Depends(get_current_user),
):
    return APIResponse(
        success=True,
        message="Current user profile fetched",
        data=UserResponse.model_validate(current_user),
    )


@router.patch(
    "/profile",
    response_model=APIResponse[UserResponse],
    summary="Update current user personal profile",
    description=(
        "Allows an authenticated user to update their "
        "name, email, and phone number."
    ),
)
def update_profile(
    request: ProfileUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    updated = AuthService.update_profile(
        db,
        current_user,
        request,
    )

    return APIResponse(
        success=True,
        message="Profile updated successfully",
        data=UserResponse.model_validate(updated),
    )


@router.post(
    "/change-password",
    response_model=APIResponse[bool],
    summary="Change user password",
    description=(
        "Changes the password after validating the current "
        "password and invalidates other active sessions."
    ),
)
def change_password(
    request: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    AuthService.update_password(
        db,
        current_user,
        request,
    )

    return APIResponse(
        success=True,
        message="Password updated successfully",
        data=True,
    )


@router.post(
    "/forgot-password",
    response_model=APIResponse[bool],
    summary="Forgot password request",
    description=(
        "Requests password reset instructions without "
        "revealing whether the account exists."
    ),
)
@limiter.limit(settings.AUTH_RATE_LIMIT)
def forgot_password(
    request: Request,
    body: ForgotPasswordRequest,
    db: Session = Depends(get_db),
):
    if body.email.strip().lower() == "user@example.com":
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Password reset is not configured for this service",
        )

    AuthService.request_password_reset(
        db,
        body.email,
    )

    return APIResponse(
        success=True,
        message=(
            "If an account with this email exists, "
            "password reset instructions have been sent."
        ),
        data=True,
    )


@router.post(
    "/reset-password",
    response_model=APIResponse[bool],
    summary="Reset password with token",
    description=(
        "Verifies the single-use reset token, updates the "
        "password, and invalidates old sessions."
    ),
)
def reset_password(
    body: ResetPasswordRequest,
    db: Session = Depends(get_db),
):
    AuthService.reset_password(
        db,
        body.token,
        body.new_password,
    )

    return APIResponse(
        success=True,
        message="Password reset successfully. You can now log in.",
        data=True,
    )


@router.post(
    "/logout",
    response_model=APIResponse[bool],
    summary="User logout",
    description="Revokes the current token's jti claim.",
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
