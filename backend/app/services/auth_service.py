import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from app.core.config import settings
from app.core.security import (
    get_password_hash,
    verify_password,
    create_access_token,
    decode_access_token,
    dummy_verify_password,
    hash_token,
)
from app.models.user import User
from app.models.token import RevokedToken, PasswordResetToken
from app.schemas.auth import (
    RegisterRequest,
    LoginRequest,
    ChangePasswordRequest,
    ProfileUpdateRequest,
)
from app.services.email_service import EmailService


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
        Public user registration.
        Always assigns role="Customer" and status="Pending".
        Does not reveal if the email already exists to prevent user enumeration.
        """
        normalized_email = request.email.lower().strip()
        existing = db.query(User).filter(User.email == normalized_email).first()
        if existing:
            # Silently succeed without revealing email existence
            return None

        user = User(
            name=request.name.strip(),
            email=normalized_email,
            password_hash=get_password_hash(request.password),
            phone=request.phone.strip() if request.phone else None,
            role="Customer",
            status="Pending",
            token_version=0,
            failed_attempts=0,
            locked_until=None,
        )
        db.add(user)
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

        # Verify password
        if not verify_password(request.password, user.password_hash):
            user.failed_attempts = (user.failed_attempts or 0) + 1
            if user.failed_attempts >= 5:
                user.locked_until = now + timedelta(minutes=15)
            db.commit()
            raise generic_error

        # User is active check - reject non-Active users with same generic error
        if user.status != "Active":
            raise generic_error

        # Successful authentication: reset failed attempts and unlock
        user.failed_attempts = 0
        user.locked_until = None
        user.last_login = now
        db.commit()
        db.refresh(user)

        # Session lifetime based on remember_me
        if request.remember_me:
            expires_delta = timedelta(days=settings.ACCESS_TOKEN_EXPIRE_REMEMBER_ME_DAYS)
        else:
            expires_delta = timedelta(hours=settings.ACCESS_TOKEN_EXPIRE_HOURS)

        access_token = create_access_token(
            subject=user.id,
            expires_delta=expires_delta,
            extra_claims={"email": user.email, "role": user.role, "name": user.name},
            token_version=user.token_version,
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
            },
        }

    @staticmethod
    def revoke_token(db: Session, token: str) -> bool:
        """Revoke a token by storing its jti claim in revoked_tokens table."""
        try:
            payload = decode_access_token(token)
            jti = payload.get("jti")
            exp = payload.get("exp")
            if not jti:
                return True

            expires_at = (
                datetime.fromtimestamp(exp, timezone.utc)
                if exp
                else datetime.now(timezone.utc) + timedelta(hours=settings.ACCESS_TOKEN_EXPIRE_HOURS)
            )

            existing = db.query(RevokedToken).filter(RevokedToken.jti == jti).first()
            if not existing:
                revoked = RevokedToken(jti=jti, expires_at=expires_at)
                db.add(revoked)
                db.commit()
            return True
        except Exception:
            # Even if token is already expired or malformed, succeed gracefully
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
    def activate_account(db: Session, token: str, password: str) -> bool:
        """
        Activate user account after verifying invitation/activation token.
        Sets password, status="Active", increments token_version, marks token used.
        """
        now = datetime.now(timezone.utc)
        token_sha256 = hash_token(token)

        record = (
            db.query(PasswordResetToken)
            .filter(
                PasswordResetToken.token_hash == token_sha256,
                PasswordResetToken.token_type == "activate",
            )
            .first()
        )

        if not record or record.used_at is not None or ensure_utc(record.expires_at) < now:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid, expired, or already used activation token",
            )

        user = db.query(User).filter(User.id == record.user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User account not found",
            )

        user.password_hash = get_password_hash(password)
        user.status = "Active"
        user.token_version = (user.token_version or 0) + 1
        record.used_at = now
        db.commit()
        return True

    @staticmethod
    def update_profile(db: Session, user: User, request: ProfileUpdateRequest) -> User:
        try:
            if request.email and request.email.lower() != user.email.lower():
                existing = db.query(User).filter(User.email == request.email.lower()).first()
                if existing and existing.id != user.id:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Email address is already in use by another account",
                    )
                user.email = request.email.lower().strip()

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
