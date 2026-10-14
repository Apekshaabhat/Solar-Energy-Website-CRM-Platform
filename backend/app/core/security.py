import hashlib
import hmac
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Optional, Union
import jwt
import bcrypt
from app.core.config import settings

# Precomputed dummy hash for timing attack mitigation during invalid login
_DUMMY_BCRYPT_HASH = "$2b$12$K1d0w3h4k1l2m3n4o5p6q7r8s9t0u1v2w3x4y5z6a7b8c9d0e1f2g"


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain-text password against a hashed password."""
    try:
        if not plain_password or not hashed_password:
            return False
        password_bytes = plain_password.encode("utf-8")
        hashed_bytes = hashed_password.encode("utf-8")
        return bcrypt.checkpw(password_bytes, hashed_bytes)
    except Exception:
        return False


def dummy_verify_password(plain_password: str) -> bool:
    """Perform dummy bcrypt check to equalize response time when user doesn't exist."""
    try:
        password_bytes = (plain_password or "dummy").encode("utf-8")
        bcrypt.checkpw(password_bytes, _DUMMY_BCRYPT_HASH.encode("utf-8"))
    except Exception:
        pass
    return False


def get_password_hash(password: str) -> str:
    """Generate a secure salted hash for a plain-text password."""
    salt = bcrypt.gensalt(rounds=12)
    hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
    return hashed.decode("utf-8")


def hash_token(raw_token: str) -> str:
    """Compute SHA-256 hash of a raw token."""
    return hashlib.sha256(raw_token.strip().encode("utf-8")).hexdigest()


def constant_time_compare(val1: str, val2: str) -> bool:
    """Compare two secret strings in constant time."""
    return hmac.compare_digest(str(val1), str(val2))


def create_access_token(
    subject: Union[str, Any],
    expires_delta: Optional[timedelta] = None,
    extra_claims: Optional[dict] = None,
    token_version: int = 0,
    jti: Optional[str] = None,
) -> str:
    """Create a signed JWT access token with unique jti and token version."""
    now = datetime.now(timezone.utc)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(hours=settings.ACCESS_TOKEN_EXPIRE_HOURS)

    unique_jti = jti or str(uuid.uuid4())

    to_encode = {
        "sub": str(subject),
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
        "jti": unique_jti,
        "ver": int(token_version),
    }

    if extra_claims:
        to_encode.update(extra_claims)

    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def decode_access_token(token: str) -> dict:
    """Decode and validate a JWT access token."""
    return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])

