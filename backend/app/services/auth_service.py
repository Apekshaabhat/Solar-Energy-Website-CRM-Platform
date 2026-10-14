from datetime import datetime, timezone
from typing import Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.models.user import User
from app.core.security import get_password_hash, verify_password, create_access_token
from app.schemas.auth import RegisterRequest, LoginRequest, ChangePasswordRequest, ProfileUpdateRequest


class AuthService:
    @staticmethod
    def register_user(db: Session, request: RegisterRequest) -> User:
        existing = db.query(User).filter(User.email == request.email.lower()).first()
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
            role="Customer",
            status="Active"
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user

    @staticmethod
    def authenticate_user(db: Session, request: LoginRequest) -> dict:
        user = db.query(User).filter(User.email == request.email.lower().strip()).first()
        if not user or not verify_password(request.password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        if user.status != "Active":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account is deactivated or inactive"
            )

        # Update last login timestamp
        user.last_login = datetime.now(timezone.utc)
        db.commit()
        db.refresh(user)

        access_token = create_access_token(
            subject=user.id,
            extra_claims={"email": user.email, "role": user.role, "name": user.name}
        )

        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user": {
                "id": user.id,
                "name": user.name,
                "email": user.email,
                "role": user.role,
                "status": user.status,
                "phone": user.phone
            }
        }

    @staticmethod
    def update_password(db: Session, user: User, request: ChangePasswordRequest) -> bool:
        if not verify_password(request.current_password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Current password verification failed"
            )
        
        if request.new_password != request.confirm_password:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="New passwords do not match"
            )

        user.password_hash = get_password_hash(request.new_password)
        db.commit()
        return True

    @staticmethod
    def update_profile(db: Session, user: User, request: ProfileUpdateRequest) -> User:
        if request.email and request.email.lower() != user.email.lower():
            existing = db.query(User).filter(User.email == request.email.lower()).first()
            if existing and existing.id != user.id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Email address is already in use by another account"
                )
            user.email = request.email.lower().strip()

        if request.name:
            user.name = request.name.strip()
        if request.phone is not None:
            user.phone = request.phone.strip() if request.phone else None

        db.commit()
        db.refresh(user)
        return user
