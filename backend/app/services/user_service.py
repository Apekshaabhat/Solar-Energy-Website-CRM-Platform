import hashlib
import json
import secrets
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Tuple, Dict, Any
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import or_, desc, func

from app.core.security import get_password_hash
from app.models.user import User
from app.models.customer import Customer
from app.models.lead import Lead
from app.models.project import Project
from app.models.site_survey import SiteSurvey
from app.models.activity import Activity
from app.models.token import PasswordResetToken
from app.schemas.user import UserInviteRequest, UserUpdate, ALLOWED_ROLES, ALLOWED_STATUSES
from app.services.crm_service import CRMService
from app.services.notification_service import NotificationService


class UserService:
    @staticmethod
    def invite_user(
        db: Session,
        request: UserInviteRequest,
        acting_user: Optional[User] = None,
        initial_password: Optional[str] = None,
    ) -> Tuple[User, str]:
        """
        Creates or updates a user in 'Invited' state with a single-use cryptographically
        secure, expiring token. Stores the hashed token in database.
        Returns (user, raw_token). The raw_token is for sending via email or tests,
        and is NEVER exposed directly in standard public API responses or logs.
        """
        email_clean = request.email.lower().strip()
        existing = (
            db.query(User)
            .filter(User.email == email_clean)
            .with_for_update()
            .first()
        )

        if existing:
            if existing.status == "Active":
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="A user with this email address already exists and is active.",
                )
            now = datetime.now(timezone.utc)
            active_token = (
                db.query(PasswordResetToken.id)
                .filter(
                    PasswordResetToken.user_id == existing.id,
                    PasswordResetToken.token_type == "activate",
                    PasswordResetToken.used_at.is_(None),
                    PasswordResetToken.expires_at > now,
                )
                .first()
            )
            invitation_expiry = existing.invitation_expires_at
            if invitation_expiry is not None and invitation_expiry.tzinfo is None:
                invitation_expiry = invitation_expiry.replace(tzinfo=timezone.utc)
            if active_token or (
                existing.invitation_token_hash
                and invitation_expiry
                and invitation_expiry > now
            ):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="A valid invitation already exists for this email address.",
                )
            # Re-invite an existing invited/inactive account
            user = existing
            user.token_version = (user.token_version or 0) + 1
            user.name = request.name.strip()
            user.role = request.role
            user.status = "Invited"
            if request.phone:
                user.phone = request.phone.strip()
        else:
            # Generate random unmatchable password hash initially
            dummy_pwd = initial_password or secrets.token_urlsafe(32)
            user = User(
                name=request.name.strip(),
                email=email_clean,
                password_hash=get_password_hash(dummy_pwd),
                phone=request.phone.strip() if request.phone else None,
                role=request.role,
                status="Invited",
                customer_id=request.customer_id,
            )
            db.add(user)

        # Generate single-use token and store SHA-256 hash
        raw_token = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
        db.query(PasswordResetToken).filter(
            PasswordResetToken.user_id == user.id,
            PasswordResetToken.token_type == "activate",
            PasswordResetToken.used_at.is_(None),
        ).update(
            {"used_at": datetime.now(timezone.utc)},
            synchronize_session=False,
        )
        user.invitation_token_hash = token_hash
        user.invitation_expires_at = datetime.now(timezone.utc) + timedelta(hours=48)

        # If role is Customer and customer_id was supplied, validate customer
        if user.role == "Customer" and request.customer_id:
            cust = db.query(Customer).filter(Customer.id == request.customer_id).first()
            if not cust:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Customer #{request.customer_id} does not exist.",
                )
            user.customer_id = cust.id

        db.flush()

        # Audit log
        CRMService.record_activity(
            db=db,
            entity_type="user",
            entity_id=user.id,
            action="invited",
            title=f"User invitation created: {user.name} ({user.role})",
            description=f"Account created in Invited state for role {user.role}",
            user_id=acting_user.id if acting_user else None,
            status_val="Invited",
            new_value=json.dumps({"role": user.role, "status": "Invited", "email": user.email}),
        )

        db.commit()
        db.refresh(user)
        return user, raw_token

    @staticmethod
    def list_users(
        db: Session,
        search: Optional[str] = None,
        role: Optional[str] = None,
        status_filter: Optional[str] = None,
        current_user: Optional[User] = None,
    ) -> List[User]:
        query = db.query(User)

        # Scoping: Managers can only view non-admin users (or team members)
        if current_user and current_user.role == "Manager":
            query = query.filter(User.role != "Admin")

        if search:
            s = f"%{search.strip()}%"
            query = query.filter(or_(User.name.ilike(s), User.email.ilike(s), User.phone.ilike(s)))

        if role and role not in ["All", "All Roles"]:
            query = query.filter(User.role.ilike(role.strip()))

        if status_filter and status_filter not in ["All", "All Status", "All Statuses"]:
            query = query.filter(User.status.ilike(status_filter.strip()))

        return query.order_by(desc(User.created_at)).all()

    @staticmethod
    def get_user_by_id(db: Session, user_id: int, current_user: User) -> User:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

        # Authorization check
        if current_user.role == "Admin":
            return user
        elif current_user.role == "Manager":
            if user.role == "Admin":
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Managers cannot access administrator account details.",
                )
            return user
        elif current_user.id == user_id:
            return user
        else:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to view this user account.",
            )

    @staticmethod
    def update_user(
        db: Session,
        user_id: int,
        request: UserUpdate,
        current_user: User,
    ) -> User:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

        current_role = current_user.role.strip().casefold()
        target_role = user.role.strip().casefold()
        session_invalidated = False

        # Managers cannot touch Admin accounts
        if current_role == "manager" and target_role == "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Managers cannot modify administrator accounts.",
            )

        # Email change check
        if request.email and request.email.lower().strip() != user.email.lower():
            target_email = request.email.lower().strip()
            existing = db.query(User).filter(User.email == target_email).first()
            if existing and existing.id != user.id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Email address is already in use by another account.",
                )
            user.email = target_email
            session_invalidated = True

        if request.name is not None:
            user.name = request.name.strip()

        if request.phone is not None:
            user.phone = request.phone.strip() if request.phone else None

        # Role change validation
        if request.role is not None and request.role != user.role:
            if current_role != "admin":
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Only administrators can update user roles.",
                )
            if current_user.id == user.id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Administrators cannot modify their own role.",
                )
            # Demoting an Admin check
            if user.role == "Admin":
                active_admins = (
                    db.query(func.count(User.id))
                    .filter(User.role == "Admin", User.status == "Active", User.id != user.id)
                    .scalar()
                    or 0
                )
                if active_admins == 0:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Cannot demote the last active administrator.",
                    )

            old_role = user.role
            user.role = request.role
            session_invalidated = True
            activity = Activity(
                entity_type="user",
                entity_id=user.id,
                action="role_changed",
                title=f"User role updated: {user.name} ({old_role} -> {user.role})",
                description=f"Admin #{current_user.id} updated user #{user.id} role from {old_role} to {user.role}",
                user_id=current_user.id,
                status=user.status,
                previous_value=old_role,
                new_value=user.role,
            )
            db.add(activity)

            NotificationService.create_notification(
                db=db,
                user_id=user.id,
                title="Role Updated",
                message=f"Your account role has been updated to {user.role}.",
                notification_type="account_event",
                entity_type="user",
                entity_id=user.id,
            )

        # Status change validation (Deactivation / Activation)
        if request.status is not None and request.status != user.status:
            if current_role not in {"admin", "manager"}:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Insufficient permissions to change account status.",
                )
            if current_role == "manager" and user.role.strip().casefold() in {"admin", "manager"}:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Managers cannot modify status of administrative accounts.",
                )
            if request.status == "Inactive" and user.role == "Admin":
                active_admins = (
                    db.query(func.count(User.id))
                    .filter(User.role == "Admin", User.status == "Active", User.id != user.id)
                    .scalar()
                    or 0
                )
                if active_admins == 0:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Cannot deactivate the last active administrator.",
                    )

            old_status = user.status
            user.status = request.status
            session_invalidated = True
            activity = Activity(
                entity_type="user",
                entity_id=user.id,
                action="status_changed",
                title=f"User status updated: {user.name} ({old_status} -> {user.status})",
                description=f"Status changed from {old_status} to {user.status} by user #{current_user.id}",
                user_id=current_user.id,
                status=user.status,
                previous_value=old_status,
                new_value=user.status,
            )
            db.add(activity)

        if request.customer_id is not None:
            if user.role != "Customer" and request.customer_id is not None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="customer_id can only be set on accounts with Customer role.",
                )
            cust = db.query(Customer).filter(Customer.id == request.customer_id).first()
            if not cust:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Customer #{request.customer_id} does not exist.",
                )
            user.customer_id = cust.id

        if getattr(request, "password", None):
            # Only admin can force reset password, or manager for non-admin
            if current_role != "admin":
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Only administrators can update account passwords directly.",
                )
            user.password_hash = get_password_hash(request.password)
            session_invalidated = True

        if session_invalidated:
            user.token_version = (user.token_version or 0) + 1

        db.commit()
        db.refresh(user)
        return user

    @staticmethod
    def delete_user(db: Session, user_id: int, current_user: User) -> bool:
        if current_user.id == user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot delete your own administrator account.",
            )
        if current_user.role != "Admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only administrators can delete user accounts.",
            )

        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

        if user.role == "Admin" and user.status == "Active":
            active_admins = (
                db.query(func.count(User.id))
                .filter(User.role == "Admin", User.status == "Active", User.id != user.id)
                .scalar()
                or 0
            )
            if active_admins == 0:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Cannot delete the last active administrator.",
                )

        # Safe foreign key preservation: reassign or set NULL on CRM entities
        db.query(Lead).filter(Lead.assigned_user_id == user.id).update(
            {"assigned_user_id": None}, synchronize_session=False
        )
        db.query(Customer).filter(Customer.assigned_user_id == user.id).update(
            {"assigned_user_id": None}, synchronize_session=False
        )
        db.query(Project).filter(Project.assigned_user_id == user.id).update(
            {"assigned_user_id": None}, synchronize_session=False
        )
        db.query(SiteSurvey).filter(SiteSurvey.assigned_user_id == user.id).update(
            {"assigned_user_id": None}, synchronize_session=False
        )

        activity = Activity(
            entity_type="user",
            entity_id=user.id,
            action="deleted",
            title=f"User deleted: {user.name} ({user.email})",
            description=f"Account deleted by administrator #{current_user.id}. Associated CRM records preserved.",
            user_id=current_user.id,
            status="Deleted",
            previous_value=user.role,
        )
        db.add(activity)

        db.delete(user)
        db.commit()
        return True

    @staticmethod
    def get_user_stats(db: Session) -> Dict[str, Any]:
        total_users = db.query(func.count(User.id)).scalar() or 0
        active_users = db.query(func.count(User.id)).filter(User.status == "Active").scalar() or 0
        inactive_users = db.query(func.count(User.id)).filter(User.status == "Inactive").scalar() or 0
        invited_users = db.query(func.count(User.id)).filter(User.status == "Invited").scalar() or 0

        roles_query = db.query(User.role, func.count(User.id)).group_by(User.role).all()
        users_by_role = {r: count for r, count in roles_query}

        return {
            "total_users": total_users,
            "active_users": active_users,
            "inactive_users": inactive_users,
            "invited_users": invited_users,
            "users_by_role": users_by_role,
        }

    @staticmethod
    def backfill_customer_users(db: Session) -> Dict[str, int]:
        """
        Create legacy CRM customer associations for unlinked Customer accounts.
        Existing customer records are never linked based on email or phone.
        """
        unlinked_users = db.query(User).filter(
            User.role == "Customer",
            User.customer_id.is_(None)
        ).all()

        linked_count = 0
        created_count = 0

        for user in unlinked_users:
            new_customer = Customer(
                name=user.name,
                contact=user.phone or user.email,
                email=user.email,
                phone=user.phone,
                location="Not specified",
                property_type="Residential",
                status="Active",
                customer_since=datetime.now(timezone.utc).strftime("%d %b %Y"),
            )
            db.add(new_customer)
            db.flush()
            user.customer_id = new_customer.id
            created_count += 1

        db.commit()
        return {"unlinked_found": len(unlinked_users), "linked_to_existing": linked_count, "created_new_customer": created_count}
