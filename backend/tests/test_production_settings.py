import pytest
from pydantic import ValidationError

from app.core.config import Settings


VALID_PRODUCTION_SETTINGS = {
    "ENVIRONMENT": "production",
    "DEBUG": False,
    "SECRET_KEY": "a-unique-random-signing-secret-with-more-than-32-characters",
    "SEED_ADMIN_PASSWORD": "SecureProductionAdminPassword123",
}


def test_production_accepts_strong_explicit_secrets():
    settings = Settings(_env_file=None, **VALID_PRODUCTION_SETTINGS)

    assert settings.ENVIRONMENT == "production"
    assert settings.SECRET_KEY == VALID_PRODUCTION_SETTINGS["SECRET_KEY"]


@pytest.mark.parametrize(
    "updates",
    [
        {"SECRET_KEY": None},
        {"SECRET_KEY": "short"},
        {"SECRET_KEY": "solara-crm-development-only-secret-key-change-before-production"},
        {"SECRET_KEY": "REPLACE_WITH_A_UNIQUE_RANDOM_SECRET_OF_AT_LEAST_32_CHARACTERS"},
        {"SEED_ADMIN_PASSWORD": None},
        {"SEED_ADMIN_PASSWORD": "admin123"},
        {"SEED_ADMIN_PASSWORD": "REPLACE_WITH_A_UNIQUE_STRONG_ADMIN_PASSWORD"},
        {"SEED_ADMIN_PASSWORD": "alllowercasepassword123"},
    ],
)
def test_production_rejects_missing_weak_or_placeholder_secrets(updates):
    settings = {**VALID_PRODUCTION_SETTINGS, **updates}

    with pytest.raises(ValidationError):
        Settings(_env_file=None, **settings)


def test_production_rejects_debug_mode():
    with pytest.raises(ValidationError, match="DEBUG must be false"):
        Settings(
            _env_file=None,
            **{**VALID_PRODUCTION_SETTINGS, "DEBUG": True},
        )


def test_development_does_not_require_production_seed_credentials():
    settings = Settings(_env_file=None, ENVIRONMENT="development")

    assert settings.SECRET_KEY
    assert settings.SEED_ADMIN_PASSWORD is None
