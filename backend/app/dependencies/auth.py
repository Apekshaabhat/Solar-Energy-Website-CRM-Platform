from typing import List, Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from jwt import PyJWTError

from app.core.config import settings
from app.core.database import get_db
from app.core.security import decode_access_token
from app.models.token import RevokedToken
from app.models.user import User

STAFF_ROLES = ["Admin", "Manager", "Sales Rep", "Support"]
STAFF_ROLE_SET = {role.lower() for role in STAFF_ROLES}

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_STR}/auth/login",
    auto_error=False
)


def get_current_user(
    token: Optional[str] = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> User:
    """
    Retrieve and validate the current authenticated user from DB on every request.
    Rejects revoked tokens, inactive users (401), and outdated token versions.
    Never trusts role/status stored in the JWT claims.
    """
    if not token:
        raise _credentials_exception()

    try:
        payload = decode_access_token(token)
        subject = payload.get("sub")
        jti = payload.get("jti")
        token_ver = payload.get("ver")
        if (
            not isinstance(subject, str)
            or not subject.isdecimal()
            or int(subject) < 1
            or not isinstance(jti, str)
            or not jti
            or type(token_ver) is not int
            or token_ver < 0
        ):
            raise _credentials_exception()
        user_id = int(subject)
    except (PyJWTError, TypeError, ValueError, OverflowError):
        raise _credentials_exception()

    # Check token revocation via jti
    is_revoked = db.query(RevokedToken.id).filter(RevokedToken.jti == jti).first() is not None
    if is_revoked:
        raise _credentials_exception()

    # Load fresh user from database on every request
    user = db.query(User).filter(User.id == user_id).first()
    if user is None or user.status != "Active":
        raise _credentials_exception()

    # Reject token if token_version doesn't match current user token_version
    current_version = user.token_version or 0
    if token_ver != current_version:
        raise _credentials_exception()

    return user


def get_optional_current_user(
    token: Optional[str] = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> Optional[User]:
    """Allow anonymous requests, but reject any supplied invalid credential."""
    if not token:
        return None
    return get_current_user(token=token, db=db)


def _credentials_exception() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )


def require_roles(allowed_roles: List[str]):
    """Role-based authorization dependency factory."""
    def role_checker(current_user: User = Depends(get_current_user)) -> User:
        # Normalize comparison (case-insensitive)
        normalized_allowed = [r.lower() for r in allowed_roles]
        if current_user.role.lower() not in normalized_allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Operation not permitted. Required roles: {', '.join(allowed_roles)}"
            )
        return current_user
    return role_checker


def require_admin(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != "Admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Operation requires Administrator privileges."
        )
    return current_user


def require_staff(current_user: User = Depends(get_current_user)) -> User:
    if not is_staff_user(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Operation requires staff privileges."
        )
    return current_user


def is_staff_user(user: Optional[User]) -> bool:
    return user is not None and user.role.lower() in STAFF_ROLE_SET
