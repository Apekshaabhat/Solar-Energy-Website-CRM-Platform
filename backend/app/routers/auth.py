from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.schemas.auth import (
    Token,
    LoginRequest,
    RegisterRequest,
    ActivateAccountRequest,
    ForgotPasswordRequest,
    ChangePasswordRequest,
    ProfileUpdateRequest,
)
from app.schemas.user import UserResponse
from app.schemas.common import APIResponse
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/register",
    response_model=APIResponse[UserResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user account",
    description="Registers a new customer user and returns user details. Passwords must be at least 6 characters.",
)
def register(request: RegisterRequest, db: Session = Depends(get_db)):
    user = AuthService.register_user(db, request)
    return APIResponse(
        success=True,
        message="User registered successfully",
        data=UserResponse.model_validate(user)
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
    description="Authenticates user credentials and returns a signed JWT access token.",
)
def login(request: LoginRequest, db: Session = Depends(get_db)):
    return AuthService.authenticate_user(db, request)


@router.get(
    "/me",
    response_model=APIResponse[UserResponse],
    summary="Get current user profile",
    description="Returns profile information for the authenticated user.",
)
def get_me(current_user: User = Depends(get_current_user)):
    return APIResponse(
        success=True,
        message="Current user profile fetched",
        data=UserResponse.model_validate(current_user)
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
        data=UserResponse.model_validate(updated)
    )


@router.post(
    "/change-password",
    response_model=APIResponse[bool],
    summary="Change user password",
    description="Changes password after validating the current password.",
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
        data=True
    )


@router.post(
    "/forgot-password",
    response_model=APIResponse[bool],
    summary="Forgot password request",
    description="Sends password reset instructions if account exists.",
)
def forgot_password(request: ForgotPasswordRequest, db: Session = Depends(get_db)):
    # Safely acknowledge without leaking account existence
    return APIResponse(
        success=True,
        message="If an account with this email exists, password reset instructions have been sent.",
        data=True
    )


@router.post(
    "/logout",
    response_model=APIResponse[bool],
    summary="User logout",
    description="Handles client logout acknowledgement.",
)
def logout(current_user: User = Depends(get_current_user)):
    return APIResponse(
        success=True,
        message="Logged out successfully",
        data=True
    )
