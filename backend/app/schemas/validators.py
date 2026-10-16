import re
from typing import Annotated

from email_validator import EmailNotValidError, validate_email
from pydantic import BeforeValidator, AfterValidator


def normalize_email(value: str) -> str:
    email = str(value).strip().lower()
    try:
        return validate_email(
            email,
            check_deliverability=False,
            test_environment=True,
        ).normalized
    except EmailNotValidError as exc:
        raise ValueError(str(exc)) from exc


AppEmailStr = Annotated[str, BeforeValidator(normalize_email)]


def validate_password_policy(value: str) -> str:
    if not isinstance(value, str):
        raise ValueError("Password must be a string")
    if len(value) < 10:
        raise ValueError("Password must be at least 10 characters long")
    if not re.search(r"[A-Z]", value):
        raise ValueError("Password must contain at least one uppercase letter")
    if not re.search(r"[a-z]", value):
        raise ValueError("Password must contain at least one lowercase letter")
    if not re.search(r"\d", value):
        raise ValueError("Password must contain at least one digit")
    return value


StrongPasswordStr = Annotated[str, AfterValidator(validate_password_policy)]

