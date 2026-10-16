from typing import List, Optional
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app.models.notification import Notification
from app.models.user import User


def format_time_ago(dt: Optional[datetime]) -> str:
    if not dt:
        return "Just now"
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    now = datetime.now(timezone.utc)
    diff = now - dt
    seconds = int(diff.total_seconds())
    if seconds < 60:
        return "Just now"
    minutes = seconds // 60
    if minutes < 60:
        return f"{minutes} min ago"
    hours = minutes // 60
    if hours < 24:
        return f"{hours} hour{'s' if hours > 1 else ''} ago"
    days = hours // 24
    if days < 7:
        return f"{days} day{'s' if days > 1 else ''} ago"
    return dt.strftime("%b %d, %Y")


class NotificationService:
    @staticmethod
    def create_notification(
        db: Session,
        user_id: int,
        title: str,
        message: str,
        notification_type: str = "info",
        entity_type: Optional[str] = None,
        entity_id: Optional[int] = None,
    ) -> Notification:
        notification = Notification(
            user_id=user_id,
            title=title.strip(),
            message=message.strip(),
            notification_type=notification_type,
            entity_type=entity_type,
            entity_id=entity_id,
            is_read=False,
            is_dismissed=False,
        )
        db.add(notification)
        db.flush()
        return notification

    @staticmethod
    def notify_roles(
        db: Session,
        roles: List[str],
        title: str,
        message: str,
        notification_type: str = "info",
        entity_type: Optional[str] = None,
        entity_id: Optional[int] = None,
    ) -> List[Notification]:
        users = (
            db.query(User)
            .filter(User.role.in_(roles), User.status == "Active")
            .all()
        )
        notifications = []
        for u in users:
            n = Notification(
                user_id=u.id,
                title=title.strip(),
                message=message.strip(),
                notification_type=notification_type,
                entity_type=entity_type,
                entity_id=entity_id,
                is_read=False,
                is_dismissed=False,
            )
            db.add(n)
            notifications.append(n)
        db.flush()
        return notifications
