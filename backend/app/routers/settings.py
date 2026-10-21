<<<<<<< HEAD
from fastapi import APIRouter, Depends
=======
import json
from fastapi import APIRouter, Depends, HTTPException, status
>>>>>>> 1d42b23b15dd322cb75cb755085a881817f909a4
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from app.core.database import get_db
from app.dependencies.auth import require_roles
from app.models.user import User
from app.models.settings import SystemSettings
from app.models.activity import Activity
from app.schemas.settings import SystemSettingsUpdate, SystemSettingsResponse
from app.schemas.common import APIResponse

router = APIRouter(prefix="/settings", tags=["System Settings"])


@router.get(
    "",
    response_model=APIResponse[SystemSettingsResponse],
    summary="Get system and workspace settings",
    description="Retrieve workspace preferences. Restricted to Administrators and Managers.",
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
        data=SystemSettingsResponse.model_validate(settings_obj),
    )


@router.put(
    "",
    response_model=APIResponse[SystemSettingsResponse],
    summary="Update system and workspace settings",
    description="Update workspace preferences. Global company details and 2FA require Administrator privileges.",
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
        db.flush()

    update_data = request.model_dump(exclude_unset=True)

    # Restriction: Managers may only update notification preferences
    privileged_fields = {"company_name", "support_email", "two_factor_auth"}
    if current_user.role == "Manager":
        for pf in privileged_fields:
            if pf in update_data and getattr(settings_obj, pf) != update_data[pf]:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Managers are not permitted to change '{pf}'. Administrator privileges required.",
                )

    old_state = {
        "company_name": settings_obj.company_name,
        "support_email": settings_obj.support_email,
        "email_notifications": settings_obj.email_notifications,
        "sms_notifications": settings_obj.sms_notifications,
        "lead_alerts": settings_obj.lead_alerts,
        "two_factor_auth": settings_obj.two_factor_auth,
    }

    for field, val in update_data.items():
        if val is not None:
            setattr(settings_obj, field, val)

<<<<<<< HEAD
    try:
        db.commit()
        db.refresh(settings_obj)
    except SQLAlchemyError:
        db.rollback()
        raise
=======
    new_state = {
        "company_name": settings_obj.company_name,
        "support_email": settings_obj.support_email,
        "email_notifications": settings_obj.email_notifications,
        "sms_notifications": settings_obj.sms_notifications,
        "lead_alerts": settings_obj.lead_alerts,
        "two_factor_auth": settings_obj.two_factor_auth,
    }

    # Audit logging
    activity = Activity(
        entity_type="settings",
        entity_id=settings_obj.id,
        action="updated",
        title="System settings updated",
        description=f"Settings modified by {current_user.name} ({current_user.role})",
        user_id=current_user.id,
        status="Active",
        previous_value=json.dumps(old_state),
        new_value=json.dumps(new_state),
    )
    db.add(activity)

    db.commit()
    db.refresh(settings_obj)

>>>>>>> 1d42b23b15dd322cb75cb755085a881817f909a4
    return APIResponse(
        success=True,
        message="Settings updated successfully",
        data=SystemSettingsResponse.model_validate(settings_obj),
    )
