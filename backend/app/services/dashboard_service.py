from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Query as SQLAlchemyQuery, Session
from sqlalchemy import and_, func, desc, or_, select

from app.models.lead import Lead
from app.models.site_survey import SiteSurvey
from app.models.project import Project
from app.models.customer import Customer
from app.models.activity import Activity
from app.models.user import User
from app.schemas.dashboard import (
    DashboardSummaryResponse,
    StatCardItem,
    LeadsChartPoint,
    SourceDonutItem,
    RecentLeadItem,
    RecentActivityItem,
)


SOURCE_COLORS = {
    "Website": "#24b368",
    "Social Media": "#f0a94e",
    "Referral": "#4a8fe0",
    "Direct Enquiry": "#f2c14e",
    "Calculator": "#9066e0",
    "Cold Call": "#e0564a",
    "Ad Campaign": "#4ae0cf",
    "Google Ads": "#f0a94e",
}

ACTIVITY_CONFIGS = {
    "lead": {"icon": "user", "tint": "bg-blue-accent"},
    "customer": {"icon": "user", "tint": "bg-leaf-600"},
    "site_survey": {"icon": "calendar", "tint": "bg-leaf-600"},
    "project": {"icon": "check", "tint": "bg-amber-accent"},
}
MANAGER_ROLES = {"admin", "manager"}


def _is_manager(user: User) -> bool:
    return user.role.lower() in MANAGER_ROLES


def _leads_query(db: Session, user: User) -> SQLAlchemyQuery[Lead]:
    query = db.query(Lead)
    if not _is_manager(user):
        query = query.filter(Lead.assigned_user_id == user.id)
    return query


def _customers_query(db: Session, user: User) -> SQLAlchemyQuery[Customer]:
    query = db.query(Customer)
    if not _is_manager(user):
        query = query.filter(Customer.assigned_user_id == user.id)
    return query


def _surveys_query(db: Session, user: User) -> SQLAlchemyQuery[SiteSurvey]:
    query = db.query(SiteSurvey)
    if not _is_manager(user):
        query = query.filter(SiteSurvey.assigned_user_id == user.id)
    return query


def _projects_query(db: Session, user: User) -> SQLAlchemyQuery[Project]:
    query = db.query(Project)
    if not _is_manager(user):
        query = query.outerjoin(Customer, Project.customer_id == Customer.id).filter(
            or_(
                Project.assigned_user_id == user.id,
                Customer.assigned_user_id == user.id,
            )
        )
    return query


def _activities_query(db: Session, user: User) -> SQLAlchemyQuery[Activity]:
    query = db.query(Activity)
    if _is_manager(user):
        return query

    visible_leads = select(Lead.id).where(Lead.assigned_user_id == user.id)
    visible_customers = select(Customer.id).where(Customer.assigned_user_id == user.id)
    visible_surveys = select(SiteSurvey.id).where(SiteSurvey.assigned_user_id == user.id)
    visible_projects = select(Project.id).outerjoin(
        Customer, Project.customer_id == Customer.id
    ).where(
        or_(
            Project.assigned_user_id == user.id,
            Customer.assigned_user_id == user.id,
        )
    )

    return query.filter(
        or_(
            and_(Activity.entity_type == "lead", Activity.entity_id.in_(visible_leads)),
            and_(Activity.entity_type == "customer", Activity.entity_id.in_(visible_customers)),
            and_(Activity.entity_type == "site_survey", Activity.entity_id.in_(visible_surveys)),
            and_(Activity.entity_type == "project", Activity.entity_id.in_(visible_projects)),
        )
    )


def format_relative_time(dt: Optional[datetime]) -> str:
    """Format datetime into human-friendly relative string."""
    if not dt:
        return "recently"
    now = datetime.now(timezone.utc)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    diff = now - dt
    seconds = int(diff.total_seconds())

    if seconds < 60:
        return "just now"
    elif seconds < 3600:
        mins = seconds // 60
        return f"{mins} min{'s' if mins > 1 else ''} ago"
    elif seconds < 86400:
        hrs = seconds // 3600
        return f"{hrs} hour{'s' if hrs > 1 else ''} ago"
    else:
        days = seconds // 86400
        return f"{days} day{'s' if days > 1 else ''} ago"


def calculate_change_str(current: int, previous: int) -> str:
    """Calculate actual month-over-month percentage change string."""
    if previous == 0:
        if current > 0:
            return f"+{current} this month"
        return "0% from last month"
    pct = round(((current - previous) / previous) * 100)
    sign = "+" if pct >= 0 else ""
    return f"{sign}{pct}% from last month"


class DashboardService:
    @staticmethod
    def get_summary(db: Session, current_user: User) -> DashboardSummaryResponse:
        now = datetime.now(timezone.utc)
        thirty_days_ago = now - timedelta(days=30)
        sixty_days_ago = now - timedelta(days=60)
        leads_query = _leads_query(db, current_user)
        customers_query = _customers_query(db, current_user)
        surveys_query = _surveys_query(db, current_user)
        projects_query = _projects_query(db, current_user)
        activities_query = _activities_query(db, current_user)

        # 1. Total counts
        total_leads_count = leads_query.with_entities(func.count(Lead.id)).scalar() or 0
        total_surveys_count = surveys_query.with_entities(func.count(SiteSurvey.id)).scalar() or 0
        ongoing_projects_count = (
            projects_query.with_entities(func.count(Project.id))
            .filter(Project.status.in_(["In Progress", "Planning", "On Hold"]))
            .scalar()
            or 0
        )
        completed_projects_count = (
            projects_query.with_entities(func.count(Project.id))
            .filter(Project.status == "Completed")
            .scalar()
            or 0
        )

        # 2. Month-over-month real calculation
        leads_current_30d = (
            leads_query.with_entities(func.count(Lead.id))
            .filter(Lead.created_at >= thirty_days_ago)
            .scalar()
            or 0
        )
        leads_prev_30d = (
            leads_query.with_entities(func.count(Lead.id))
            .filter(Lead.created_at >= sixty_days_ago, Lead.created_at < thirty_days_ago)
            .scalar()
            or 0
        )

        surveys_current_30d = (
            surveys_query.with_entities(func.count(SiteSurvey.id))
            .filter(SiteSurvey.created_at >= thirty_days_ago)
            .scalar()
            or 0
        )
        surveys_prev_30d = (
            surveys_query.with_entities(func.count(SiteSurvey.id))
            .filter(SiteSurvey.created_at >= sixty_days_ago, SiteSurvey.created_at < thirty_days_ago)
            .scalar()
            or 0
        )

        ongoing_current_30d = (
            projects_query.with_entities(func.count(Project.id))
            .filter(
                Project.status.in_(["In Progress", "Planning"]),
                Project.created_at >= thirty_days_ago,
            )
            .scalar()
            or 0
        )
        ongoing_prev_30d = (
            projects_query.with_entities(func.count(Project.id))
            .filter(
                Project.status.in_(["In Progress", "Planning"]),
                Project.created_at >= sixty_days_ago,
                Project.created_at < thirty_days_ago,
            )
            .scalar()
            or 0
        )

        completed_current_30d = (
            projects_query.with_entities(func.count(Project.id))
            .filter(
                Project.status == "Completed",
                Project.updated_at >= thirty_days_ago,
            )
            .scalar()
            or 0
        )
        completed_prev_30d = (
            projects_query.with_entities(func.count(Project.id))
            .filter(
                Project.status == "Completed",
                Project.updated_at >= sixty_days_ago,
                Project.updated_at < thirty_days_ago,
            )
            .scalar()
            or 0
        )

        # 3. Stat Cards with real calculated changes
        stat_cards = [
            StatCardItem(
                id="total-leads",
                label="Total Leads",
                value=str(total_leads_count),
                change=calculate_change_str(leads_current_30d, leads_prev_30d),
                icon="users",
                tint="bg-leaf-100 text-leaf-600",
            ),
            StatCardItem(
                id="site-surveys",
                label="Site Surveys",
                value=str(total_surveys_count),
                change=calculate_change_str(surveys_current_30d, surveys_prev_30d),
                icon="calendar",
                tint="bg-blue-50 text-blue-accent",
            ),
            StatCardItem(
                id="ongoing-projects",
                label="Ongoing Projects",
                value=str(ongoing_projects_count),
                change=calculate_change_str(ongoing_current_30d, ongoing_prev_30d),
                icon="folder",
                tint="bg-amber-50 text-amber-accent",
            ),
            StatCardItem(
                id="completed-projects",
                label="Completed Projects",
                value=str(completed_projects_count),
                change=calculate_change_str(completed_current_30d, completed_prev_30d),
                icon="check",
                tint="bg-leaf-100 text-leaf-600",
            ),
        ]

        # 4. Granular CRM Metrics for full database reflection
        new_leads = leads_query.with_entities(func.count(Lead.id)).filter(Lead.status == "New").scalar() or 0
        contacted_leads = leads_query.with_entities(func.count(Lead.id)).filter(Lead.status == "Contacted").scalar() or 0
        survey_leads = leads_query.with_entities(func.count(Lead.id)).filter(Lead.status == "Site Survey").scalar() or 0
        quoted_leads = leads_query.with_entities(func.count(Lead.id)).filter(Lead.status == "Quoted").scalar() or 0
        converted_leads = leads_query.with_entities(func.count(Lead.id)).filter(Lead.status == "Converted").scalar() or 0
        lost_leads = leads_query.with_entities(func.count(Lead.id)).filter(Lead.status == "Lost").scalar() or 0

        total_customers = customers_query.with_entities(func.count(Customer.id)).scalar() or 0
        active_customers = customers_query.with_entities(func.count(Customer.id)).filter(Customer.status == "Active").scalar() or 0

        scheduled_surveys = surveys_query.with_entities(func.count(SiteSurvey.id)).filter(SiteSurvey.status == "Scheduled").scalar() or 0
        completed_surveys = surveys_query.with_entities(func.count(SiteSurvey.id)).filter(SiteSurvey.status == "Completed").scalar() or 0

        pipeline_value = (
            leads_query.with_entities(func.sum(Lead.estimated_value))
            .filter(Lead.status.notin_(["Lost", "Converted"]))
            .scalar()
            or 0.0
        )
        completed_project_value = (
            projects_query.with_entities(func.sum(func.coalesce(Project.actual_cost, Project.estimated_cost, 0)))
            .filter(Project.status == "Completed")
            .scalar()
            or 0.0
        )

        metrics = {
            "totalLeads": total_leads_count,
            "newLeads": new_leads,
            "contactedLeads": contacted_leads,
            "surveyLeads": survey_leads,
            "quotedLeads": quoted_leads,
            "convertedLeads": converted_leads,
            "lostLeads": lost_leads,
            "totalCustomers": total_customers,
            "activeCustomers": active_customers,
            "totalSurveys": total_surveys_count,
            "scheduledSurveys": scheduled_surveys,
            "completedSurveys": completed_surveys,
            "ongoingProjects": ongoing_projects_count,
            "completedProjects": completed_projects_count,
            "estimatedPipelineValue": float(pipeline_value),
            "projectRevenue": float(completed_project_value),
        }

        # User aggregations for Admin & Manager
        if current_user and current_user.role in ["Admin", "Manager"]:
            total_users = db.query(func.count(User.id)).scalar() or 0
            active_users = db.query(func.count(User.id)).filter(User.status == "Active").scalar() or 0
            inactive_users = db.query(func.count(User.id)).filter(User.status == "Inactive").scalar() or 0
            invited_users = db.query(func.count(User.id)).filter(User.status == "Invited").scalar() or 0
            roles_query = db.query(User.role, func.count(User.id)).group_by(User.role).all()
            metrics["totalUsers"] = total_users
            metrics["activeUsers"] = active_users
            metrics["inactiveUsers"] = inactive_users
            metrics["invitedUsers"] = invited_users
            metrics["usersByRole"] = {r: cnt for r, cnt in roles_query}


        # 5. Leads by Source (real database counts)
        source_counts = (
            leads_query.with_entities(Lead.source, func.count(Lead.id))
            .group_by(Lead.source)
            .all()
        )
        leads_by_source: List[SourceDonutItem] = []
        if source_counts:
            total_source_leads = sum(cnt for _, cnt in source_counts) or 1
            for source, count in source_counts:
                pct = round((count / total_source_leads) * 100)
                leads_by_source.append(
                    SourceDonutItem(
                        name=source or "Other",
                        value=pct,
                        color=SOURCE_COLORS.get(source, "#8A968C"),
                    )
                )
        else:
            leads_by_source = [
                SourceDonutItem(name="Website", value=100, color="#24b368")
            ]

        # 6. Leads Overview (Daily Trend without artificial floors)
        recent_leads = (
            leads_query.with_entities(Lead.created_at)
            .filter(Lead.created_at >= thirty_days_ago)
            .all()
        )
        date_map: Dict[str, int] = {}
        for i in range(16):
            day = thirty_days_ago + timedelta(days=i * 2)
            formatted_date = day.strftime("%b %d").replace(" 0", " ")
            date_map[formatted_date] = 0

        for l in recent_leads:
            if l.created_at:
                l_dt = l.created_at
                if l_dt.tzinfo is None:
                    l_dt = l_dt.replace(tzinfo=timezone.utc)
                bucket_idx = min(15, max(0, int((l_dt - thirty_days_ago).total_seconds() // (2 * 86400))))
                day = thirty_days_ago + timedelta(days=bucket_idx * 2)
                key = day.strftime("%b %d").replace(" 0", " ")
                date_map[key] = date_map.get(key, 0) + 1

        leads_overview = [
            LeadsChartPoint(date=k, leads=v)
            for k, v in date_map.items()
        ]

        # 7. Recent Leads (Top 5 actual leads)
        top_leads = (
            leads_query
            .order_by(desc(Lead.created_at))
            .limit(5)
            .all()
        )
        recent_leads_list = [
            RecentLeadItem(
                id=lead.id,
                name=lead.name,
                contact=lead.contact,
                location=lead.location,
                propertyType=lead.property_type,
                source=lead.source,
                status=lead.status,
                createdAt=lead.created_at.strftime("%d %b %Y") if lead.created_at else "Recently",
            )
            for lead in top_leads
        ]

        # 8. Real Recent Activity Feed
        recent_activity_query = (
            activities_query
            .order_by(desc(Activity.created_at))
            .limit(6)
            .all()
        )
        recent_activity: List[RecentActivityItem] = []

        if recent_activity_query:
            for act in recent_activity_query:
                cfg = ACTIVITY_CONFIGS.get(act.entity_type, {"icon": "user", "tint": "bg-blue-accent"})
                tint = cfg["tint"]
                icon = cfg["icon"]
                if act.entity_type == "project" and act.status == "Completed":
                    icon = "check"
                    tint = "bg-leaf-600"

                recent_activity.append(
                    RecentActivityItem(
                        id=act.id,
                        title=act.title,
                        subtitle=act.customer_name or act.description or "",
                        time=format_relative_time(act.created_at),
                        icon=icon,
                        tint=tint,
                        entity_type=act.entity_type,
                        entity_id=act.entity_id,
                        status=act.status,
                    )
                )
        else:
            # Fallback to recent entities if activity table is brand new
            act_id = 1
            for l in top_leads[:2]:
                recent_activity.append(
                    RecentActivityItem(
                        id=act_id,
                        title=f"Lead created: {l.name}",
                        subtitle=l.source,
                        time=format_relative_time(l.created_at),
                        icon="user",
                        tint="bg-blue-accent",
                        entity_type="lead",
                        entity_id=l.id,
                        status=l.status,
                    )
                )
                act_id += 1

            for s in surveys_query.order_by(desc(SiteSurvey.created_at)).limit(2).all():
                recent_activity.append(
                    RecentActivityItem(
                        id=act_id,
                        title=f"Site survey scheduled for {s.customer_name}",
                        subtitle=f"{s.survey_date} at {s.time_slot}",
                        time=format_relative_time(s.created_at),
                        icon="calendar",
                        tint="bg-leaf-600",
                        entity_type="site_survey",
                        entity_id=s.id,
                        status=s.status,
                    )
                )
                act_id += 1

            for p in projects_query.order_by(desc(Project.created_at)).limit(2).all():
                recent_activity.append(
                    RecentActivityItem(
                        id=act_id,
                        title=f"Project: {p.name}",
                        subtitle=f"Status: {p.status}",
                        time=format_relative_time(p.created_at),
                        icon="check" if p.status == "Completed" else "folder",
                        tint="bg-leaf-600" if p.status == "Completed" else "bg-amber-accent",
                        entity_type="project",
                        entity_id=p.id,
                        status=p.status,
                    )
                )
                act_id += 1

        return DashboardSummaryResponse(
            statCards=stat_cards,
            leadsOverview=leads_overview,
            leadsBySource=leads_by_source,
            recentLeads=recent_leads_list,
            recentActivity=recent_activity,
            metrics=metrics,
        )

    @staticmethod
    def get_activities(
        db: Session,
        current_user: User,
        limit: int = 20,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        activities = (
            _activities_query(db, current_user)
            .order_by(desc(Activity.created_at), desc(Activity.id))
            .limit(limit)
            .offset(offset)
            .all()
        )
        return [
            {
                "id": a.id,
                "entity_type": a.entity_type,
                "entity_id": a.entity_id,
                "action": a.action,
                "title": a.title,
                "description": a.description,
                "subtitle": a.description or a.customer_name or "",
                "customer_id": a.customer_id,
                "customer_name": a.customer_name,
                "status": a.status,
                "created_at": a.created_at.isoformat() if a.created_at else None,
                "time_ago": format_relative_time(a.created_at),
                "time": format_relative_time(a.created_at),
            }
            for a in activities
        ]
