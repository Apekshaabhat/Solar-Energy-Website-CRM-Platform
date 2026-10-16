import hashlib
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.models.user import User
from app.models.customer import Customer
from app.core.security import get_password_hash, verify_password, create_access_token
from app.schemas.auth import (
    RegisterRequest,
    LoginRequest,
    ChangePasswordRequest,
    ProfileUpdateRequest,
    ActivateAccountRequest,
)
from app.services.crm_service import CRMService


class AuthService:
    @staticmethod
    def register_user(db: Session, request: RegisterRequest) -> User:
        """
        Public registration endpoint.
        IMPORTANT: Public signup MUST NEVER grant Admin or Staff privileges.
        All public registrations are strictly assigned role='Customer'.
        """
        email_clean = request.email.lower().strip()
        existing = db.query(User).filter(User.email == email_clean).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A user with this email address already exists.",
            )

        # Enforce Customer role unconditionally for public signup
        role = "Customer"

        # Check or create linked customer record
        matched_customer = db.query(Customer).filter(Customer.email.ilike(email_clean)).first()
        if not matched_customer and request.phone:
            matched_customer = db.query(Customer).filter(Customer.phone == request.phone.strip()).first()

        if matched_customer:
            customer_id = matched_customer.id
        else:
            new_customer = Customer(
                name=request.name.strip(),
                contact=request.phone.strip() if request.phone else email_clean,
                email=email_clean,
                phone=request.phone.strip() if request.phone else None,
                location="Not specified",
                property_type="Residential",
                status="Active",
                customer_since=datetime.now(timezone.utc).strftime("%d %b %Y"),
            )
            db.add(new_customer)
            db.flush()
            customer_id = new_customer.id

        user = User(
            name=request.name.strip(),
            email=email_clean,
            password_hash=get_password_hash(request.password),
            phone=request.phone.strip() if request.phone else None,
            role=role,
            status="Active",
            customer_id=customer_id,
        )
        db.add(user)
        db.flush()

        CRMService.record_activity(
            db=db,
            entity_type="user",
            entity_id=user.id,
            action="registered",
            title=f"Customer registered: {user.name}",
            description=f"Public registration completed for {user.email}",
            customer_id=customer_id,
            customer_name=user.name,
            status_val="Active",
        )

        db.commit()
        db.refresh(user)
        return user

    @staticmethod
    def bootstrap_admin(
        db: Session,
        name: str,
        email: str,
        password: str,
        role: str = "Admin",
        phone: Optional[str] = None,
    ) -> User:
        """
        Controlled initial-admin/privileged user provisioning method that CANNOT be invoked
        through public registration. Used by CLI/seed scripts and test fixtures.
        """
        email_clean = email.lower().strip()
        existing = db.query(User).filter(User.email == email_clean).first()
        if existing:
            existing.name = name.strip()
            existing.role = role
            existing.status = "Active"
            existing.password_hash = get_password_hash(password)
            if phone:
                existing.phone = phone.strip()
            db.commit()
            db.refresh(existing)
            return existing

        admin_user = User(
            name=name.strip(),
            email=email_clean,
            password_hash=get_password_hash(password),
            phone=phone.strip() if phone else None,
            role=role,
            status="Active",
        )
        if role == "Customer":
            cust = Customer(
                name=name.strip(),
                contact=phone.strip() if phone else email_clean,
                email=email_clean,
                phone=phone.strip() if phone else None,
                location="Residential Address",
                property_type="Residential",
                status="Active",
                customer_since="01 Jan 2026",
            )
            db.add(cust)
            db.flush()
            admin_user.customer_id = cust.id

        db.add(admin_user)
        db.commit()
        db.refresh(admin_user)
        return admin_user

    @staticmethod
    def activate_account(db: Session, request: ActivateAccountRequest) -> User:
        """
        Secure activation and password-setup flow for invited users.
        Verifies cryptographically secure single-use expiring token.
        """
        if request.password != request.confirm_password:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="New password and confirmation password do not match.",
            )

        token_hash = hashlib.sha256(request.token.encode("utf-8")).hexdigest()
        user = db.query(User).filter(User.invitation_token_hash == token_hash).first()

        if not user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired invitation token.",
            )

        now = datetime.now(timezone.utc)
        if user.invitation_expires_at is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invitation token is invalid.",
            )

        expires_at = user.invitation_expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)

        if expires_at < now:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invitation token has expired. Please contact an administrator.",
            )

        if user.status != "Invited":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Account is not in an invited state or has already been activated.",
            )

        user.password_hash = get_password_hash(request.password)
        user.status = "Active"
        user.invitation_token_hash = None
        user.invitation_expires_at = None

        # If role is Customer and no customer_id is linked yet, link or create
        if user.role == "Customer" and not user.customer_id:
            matched_customer = db.query(Customer).filter(Customer.email.ilike(user.email)).first()
            if matched_customer:
                user.customer_id = matched_customer.id
            else:
                new_customer = Customer(
                    name=user.name,
                    contact=user.phone or user.email,
                    email=user.email,
                    phone=user.phone,
                    location="Not specified",
                    property_type="Residential",
                    status="Active",
                    customer_since=now.strftime("%d %b %Y"),
                )
                db.add(new_customer)
                db.flush()
                user.customer_id = new_customer.id

        CRMService.record_activity(
            db=db,
            entity_type="user",
            entity_id=user.id,
            action="activated",
            title=f"User activated account: {user.name}",
            description=f"Account activated via secure token for role {user.role}",
            user_id=user.id,
            status_val="Active",
        )

        db.commit()
        db.refresh(user)
        return user

    @staticmethod
    def authenticate_user(db: Session, request: LoginRequest) -> dict:
        user = db.query(User).filter(User.email == request.email.lower().strip()).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

        if user.status == "Invited":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is pending activation. Please use the activation link sent to your email.",
            )

        if user.status == "Inactive":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account is deactivated or inactive.",
            )

        if not verify_password(request.password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Update last login timestamp
        user.last_login = datetime.now(timezone.utc)
        db.commit()
        db.refresh(user)

        extra_claims = {
            "email": user.email,
            "role": user.role,
            "name": user.name,
        }
        if user.customer_id:
            extra_claims["customer_id"] = user.customer_id

        access_token = create_access_token(
            subject=user.id,
            extra_claims=extra_claims,
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
                "phone": user.phone,
                "customer_id": user.customer_id,
            },
        }

    @staticmethod
    def update_password(db: Session, user: User, request: ChangePasswordRequest) -> bool:
        if not verify_password(request.current_password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Current password verification failed",
            )

        if request.new_password != request.confirm_password:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="New passwords do not match",
            )

        user.password_hash = get_password_hash(request.new_password)
        db.commit()
        return True

    @staticmethod
    def update_profile(db: Session, user: User, request: ProfileUpdateRequest) -> User:
        if request.email and request.email.lower().strip() != user.email.lower():
            target_email = request.email.lower().strip()
            existing = db.query(User).filter(User.email == target_email).first()
            if existing and existing.id != user.id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Email address is already in use by another account",
                )
            user.email = target_email

        if request.name:
            user.name = request.name.strip()
        if request.phone is not None:
            user.phone = request.phone.strip() if request.phone else None

        db.commit()
        db.refresh(user)
        return user
