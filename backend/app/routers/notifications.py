from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import desc
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.models.notification import Notification
from app.schemas.notification import NotificationResponse, NotificationUnreadCountResponse
from app.schemas.common import APIResponse
from app.services.notification_service import format_time_ago

router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.get(
    "",
    response_model=APIResponse[List[NotificationResponse]],
    summary="List authenticated user notifications",
)
def list_notifications(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0, le=10000),
    include_dismissed: bool = Query(False),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = db.query(Notification).filter(Notification.user_id == current_user.id)
    if not include_dismissed:
        query = query.filter(Notification.is_dismissed.is_(False))

    notifications = (
        query.order_by(desc(Notification.created_at), desc(Notification.id))
        .limit(limit)
        .offset(offset)
        .all()
    )

    items = []
    for n in notifications:
        resp = NotificationResponse.model_validate(n)
        resp.time = format_time_ago(n.created_at)
        items.append(resp)

    return APIResponse(
        success=True,
        message="Notifications retrieved successfully",
        data=items,
    )


@router.get(
    "/unread-count",
    response_model=APIResponse[NotificationUnreadCountResponse],
    summary="Get unread notification count for authenticated user",
)
def get_unread_count(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    count = (
        db.query(Notification)
        .filter(
            Notification.user_id == current_user.id,
            Notification.is_read.is_(False),
            Notification.is_dismissed.is_(False),
        )
        .count()
    )
    return APIResponse(
        success=True,
        message="Unread notification count retrieved",
        data=NotificationUnreadCountResponse(unread_count=count),
    )


@router.patch(
    "/{notification_id}/read",
    response_model=APIResponse[NotificationResponse],
    summary="Mark single notification as read",
)
def mark_notification_read(
    notification_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    notif = (
        db.query(Notification)
        .filter(Notification.id == notification_id, Notification.user_id == current_user.id)
        .first()
    )
    if not notif:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found",
        )

    notif.is_read = True
    try:
        db.commit()
        db.refresh(notif)
    except SQLAlchemyError:
        db.rollback()
        raise

    resp = NotificationResponse.model_validate(notif)
    resp.time = format_time_ago(notif.created_at)
    return APIResponse(
        success=True,
        message="Notification marked as read",
        data=resp,
    )


@router.patch(
    "/mark-all-read",
    response_model=APIResponse[bool],
    summary="Mark all user notifications as read",
)
def mark_all_read(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    db.query(Notification).filter(
        Notification.user_id == current_user.id,
        Notification.is_read.is_(False),
        Notification.is_dismissed.is_(False),
    ).update({"is_read": True}, synchronize_session=False)
    try:
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        raise

    return APIResponse(
        success=True,
        message="All notifications marked as read",
        data=True,
    )


@router.delete(
    "/{notification_id}",
    response_model=APIResponse[bool],
    summary="Dismiss or delete single notification",
)
def dismiss_notification(
    notification_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    notif = (
        db.query(Notification)
        .filter(Notification.id == notification_id, Notification.user_id == current_user.id)
        .first()
    )
    if not notif:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found",
        )

    notif.is_dismissed = True
    try:
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        raise
    return APIResponse(
        success=True,
        message="Notification dismissed successfully",
        data=True,
    )


@router.delete(
    "/dismiss-all",
    response_model=APIResponse[bool],
    summary="Dismiss all notifications for authenticated user",
)
def dismiss_all_notifications(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    db.query(Notification).filter(
        Notification.user_id == current_user.id,
        Notification.is_dismissed.is_(False),
    ).update({"is_dismissed": True}, synchronize_session=False)
    try:
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        raise

    return APIResponse(
        success=True,
        message="All notifications dismissed",
        data=True,
    )
