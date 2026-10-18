from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from app.core.database import get_db
from app.dependencies.auth import require_roles
from app.models.user import User
from app.models.settings import SystemSettings
from app.schemas.settings import SystemSettingsUpdate, SystemSettingsResponse
from app.schemas.common import APIResponse

router = APIRouter(prefix="/settings", tags=["System Settings"])


@router.get(
    "",
    response_model=APIResponse[SystemSettingsResponse],
    summary="Get system and workspace settings",
)
def get_settings(
    current_user: User = Depends(require_roles(["Admin", "Manager"])),
    db: Session = Depends(get_db),
):
    settings_obj = db.query(SystemSettings).order_by(SystemSettings.id.asc()).first()
    if not settings_obj:
        settings_obj = SystemSettings(
            company_name="SOLARA Energy Solutions",
            support_email="support@solara.com",
            email_notifications=True,
            sms_notifications=False,
            lead_alerts=True,
            two_factor_auth=False,
        )
        try:
            db.add(settings_obj)
            db.commit()
            db.refresh(settings_obj)
        except SQLAlchemyError:
            db.rollback()
            raise

    return APIResponse(
        success=True,
        message="Settings retrieved successfully",
        data=SystemSettingsResponse.model_validate(settings_obj)
    )


@router.put(
    "",
    response_model=APIResponse[SystemSettingsResponse],
    summary="Update system and workspace settings",
)
def update_settings(
    request: SystemSettingsUpdate,
    current_user: User = Depends(require_roles(["Admin", "Manager"])),
    db: Session = Depends(get_db),
):
    settings_obj = db.query(SystemSettings).order_by(SystemSettings.id.asc()).first()
    if not settings_obj:
        settings_obj = SystemSettings()
        db.add(settings_obj)

    update_data = request.model_dump(exclude_unset=True)
    for field, val in update_data.items():
        if val is not None:
            setattr(settings_obj, field, val)

    try:
        db.commit()
        db.refresh(settings_obj)
    except SQLAlchemyError:
        db.rollback()
        raise
    return APIResponse(
        success=True,
        message="Settings updated successfully",
        data=SystemSettingsResponse.model_validate(settings_obj)
    )
