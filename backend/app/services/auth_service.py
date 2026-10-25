import hashlib
from datetime import datetime, timedelta, timezone
from typing import Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from jwt import PyJWTError
import secrets
from fastapi import HTTPException, status
from app.core.config import settings, validate_admin_seed_password
from app.core.security import (
    get_password_hash,
    verify_password,
    create_access_token,
    decode_access_token,
    dummy_verify_password,
    hash_token,
)
from app.models.user import User
from app.models.customer import Customer
from app.models.token import RevokedToken, PasswordResetToken
from app.schemas.auth import (
    RegisterRequest,
    LoginRequest,
    ChangePasswordRequest,
    ProfileUpdateRequest,
)

from app.services.crm_service import CRMService
from app.services.email_service import EmailService


def _credentials_exception() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )


def ensure_utc(dt: Optional[datetime]) -> Optional[datetime]:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)



class AuthService:
    @staticmethod
    def register_user(db: Session, request: RegisterRequest) -> Optional[User]:
        """
        Public registration endpoint.
        IMPORTANT: Public signup MUST NEVER grant Admin or Staff privileges.
        All public registrations are strictly assigned role='Customer'.
        """
        email_clean = request.email.lower().strip()
        existing = (
            db.query(User)
            .filter(User.email == email_clean)
            .with_for_update()
            .first()
        )
        if existing:
            return None

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

        user = User(
            name=request.name.strip(),
            email=email_clean,
            password_hash=get_password_hash(request.password),
            phone=request.phone.strip() if request.phone else None,
            role="Customer",
            status="Active",
            token_version=0,
            failed_attempts=0,
            locked_until=None,
            customer_id=new_customer.id,
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
            customer_id=new_customer.id,
            customer_name=user.name,
            status_val=user.status,
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
            if existing.role.strip().casefold() != role.strip().casefold():
                raise ValueError(
                    f"Account {email_clean} already exists with a different role."
                )
            return existing

        if role.strip().casefold() == "admin":
            try:
                password = validate_admin_seed_password(password)
            except ValueError as exc:
                raise ValueError(
                    "Administrator passwords must be at least 12 characters and "
                    "include uppercase, lowercase, and numeric characters."
                ) from exc

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
    def activate_account(
        db: Session,
        request: Any,
        password: Optional[str] = None,
        confirm_password: Optional[str] = None,
    ) -> User:
        """
        Secure activation and password-setup flow for invited users.
        Verifies cryptographically secure single-use expiring token.
        """
        if isinstance(request, str):
            token = request
            pwd = password or ""
            conf_pwd = confirm_password
        else:
            token = getattr(request, "token", "") or ""
            pwd = getattr(request, "password", "") or (password or "")
            conf_pwd = getattr(request, "confirm_password", None) or confirm_password

        if conf_pwd is not None and pwd != conf_pwd:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="New password and confirmation password do not match.",
            )

        now = datetime.now(timezone.utc)
        token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()

        # Check PasswordResetToken first (token_type='activate')
        token_rec = (
            db.query(PasswordResetToken)
            .filter(
                PasswordResetToken.token_hash == token_hash,
                PasswordResetToken.token_type == "activate",
                PasswordResetToken.used_at.is_(None),
            )
            .first()
        )

        user = None
        if token_rec:
            exp = token_rec.expires_at
            if exp.tzinfo is None:
                exp = exp.replace(tzinfo=timezone.utc)
            if exp < now:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invitation token has expired. Please contact an administrator.",
                )
            user = db.query(User).filter(User.id == token_rec.user_id).first()
            token_rec.used_at = now

        # Fallback to User.invitation_token_hash
        if not user:
            user = db.query(User).filter(User.invitation_token_hash == token_hash).first()
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid or expired invitation token.",
                )
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

        user.password_hash = get_password_hash(pwd)
        user.status = "Active"
        user.token_version = (user.token_version or 0) + 1
        user.invitation_token_hash = None
        user.invitation_expires_at = None

        # Legacy customer association: create a separate record rather than inferring
        # ownership from a matching email address.
        if user.role == "Customer" and not user.customer_id:
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
        """
        Authenticate user with account lockout and timing attack protection.
        Returns generic error for wrong email, wrong password, locked or inactive accounts.
        """
        now = datetime.now(timezone.utc)
        normalized_email = request.email.lower().strip()
        user = db.query(User).filter(User.email == normalized_email).first()

        generic_error = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

        if not user:
            # Perform dummy bcrypt calculation to mitigate email enumeration via timing
            dummy_verify_password(request.password)
            raise generic_error

        # Check account lockout
        if user.locked_until and ensure_utc(user.locked_until) > now:
            raise generic_error

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

        # Verify password
        if not verify_password(request.password, user.password_hash):
            user.failed_attempts = (user.failed_attempts or 0) + 1
            if user.failed_attempts >= 5:
                user.locked_until = now + timedelta(minutes=15)
            db.commit()
            raise generic_error

        # Older public signups were left Pending until email activation.
        if user.status == "Pending" and user.role == "Customer":
            user.status = "Active"
        elif user.status != "Active":
            if user.status == "Inactive":
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="User account is deactivated or inactive.",
                )
            raise generic_error

        # Successful authentication: reset failed attempts and unlock
        user.failed_attempts = 0
        user.locked_until = None
        user.last_login = now
        db.commit()
        db.refresh(user)

        extra_claims = {
            "email": user.email,
            "role": user.role,
            "name": user.name,
        }
        if user.customer_id:
            extra_claims["customer_id"] = user.customer_id

        # Session lifetime based on remember_me
        if request.remember_me:
            expires_delta = timedelta(days=settings.ACCESS_TOKEN_EXPIRE_REMEMBER_ME_DAYS)
        else:
            expires_delta = timedelta(hours=settings.ACCESS_TOKEN_EXPIRE_HOURS)

        access_token = create_access_token(
            subject=user.id,
            expires_delta=expires_delta,
            extra_claims=extra_claims,
            token_version=user.token_version or 0,
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
    def revoke_token(db: Session, token: str) -> bool:
        """Revoke a token by storing its jti claim in revoked_tokens table."""
        try:
            payload = decode_access_token(token)
        except PyJWTError:
            raise _credentials_exception()

        jti = payload["jti"]
        expires_at = datetime.fromtimestamp(payload["exp"], timezone.utc)
        existing = db.query(RevokedToken).filter(RevokedToken.jti == jti).first()
        if not existing:
            try:
                db.add(RevokedToken(jti=jti, expires_at=expires_at))
                db.commit()
            except SQLAlchemyError:
                db.rollback()
                raise
        return True

    @staticmethod
    def update_password(db: Session, user: User, request: ChangePasswordRequest) -> bool:
        """Change user password, increment token_version to terminate older sessions."""
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
        user.token_version = (user.token_version or 0) + 1
        db.commit()
        return True

    @staticmethod
    def request_password_reset(db: Session, email: str) -> bool:
        """
        Request a password reset link.
        Generates single-use 32-byte URL-safe token, stores SHA-256 hash with 30-min expiry.
        Always returns generic acknowledgment.
        """
        user = db.query(User).filter(User.email == email.lower().strip()).first()
        if user and user.status == "Active":
            raw_token = secrets.token_urlsafe(32)
            token_sha256 = hash_token(raw_token)
            expires_at = datetime.now(timezone.utc) + timedelta(minutes=settings.PASSWORD_RESET_TOKEN_EXPIRE_MINUTES)

            reset_record = PasswordResetToken(
                user_id=user.id,
                token_hash=token_sha256,
                token_type="reset",
                expires_at=expires_at,
            )
            db.add(reset_record)
            db.commit()

            EmailService.send_password_reset_email(user.email, raw_token)

        return True

    @staticmethod
    def reset_password(db: Session, token: str, new_password: str) -> bool:
        """
        Verify reset token hash, expiry, and unused state.
        Updates password, marks token used, and increments token_version.
        """
        now = datetime.now(timezone.utc)
        token_sha256 = hash_token(token)

        record = (
            db.query(PasswordResetToken)
            .filter(
                PasswordResetToken.token_hash == token_sha256,
                PasswordResetToken.token_type == "reset",
            )
            .first()
        )

        if not record or record.used_at is not None or ensure_utc(record.expires_at) < now:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid, expired, or already used reset token",
            )

        user = db.query(User).filter(User.id == record.user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid reset token",
            )

        user.password_hash = get_password_hash(new_password)
        user.token_version = (user.token_version or 0) + 1
        record.used_at = now
        db.commit()
        return True

    @staticmethod
    def update_profile(db: Session, user: User, request: ProfileUpdateRequest) -> User:
        try:
            if request.email and request.email.lower().strip() != user.email.lower():
                target_email = request.email.lower().strip()
                existing = db.query(User).filter(User.email == target_email).first()
                if existing and existing.id != user.id:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Email address is already in use by another account",
                    )
                user.email = target_email

            if request.name is not None:
                user.name = request.name
            if request.phone is not None:
                user.phone = request.phone or None

            db.commit()
            db.refresh(user)
        except SQLAlchemyError:
            db.rollback()
            raise
        return user
