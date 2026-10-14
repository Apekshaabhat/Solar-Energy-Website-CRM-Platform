from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.models.lead import Lead
from app.models.customer import Customer
from app.models.site_survey import SiteSurvey
from app.models.project import Project
from app.models.activity import Activity
from app.services.dashboard_service import format_relative_time


VALID_LEAD_TRANSITIONS = {
    "New": ["Contacted", "Cancelled", "Lost"],
    "Contacted": ["Site Survey", "Cancelled", "Lost"],
    "Site Survey": ["Quoted", "Cancelled", "Lost"],
    "Quoted": ["Converted", "Cancelled", "Lost"],
    "Converted": [],
    "Cancelled": [],
    "Lost": [],
}

VALID_SURVEY_TRANSITIONS = {
    "Scheduled": ["In Progress", "Cancelled"],
    "In Progress": ["Completed", "Cancelled"],
    "Completed": [],
    "Cancelled": [],
}

VALID_PROJECT_TRANSITIONS = {
    "Planning": ["In Progress", "Cancelled"],
    "In Progress": ["Completed", "On Hold", "Cancelled"],
    "On Hold": ["In Progress", "Cancelled"],
    "Completed": [],
    "Cancelled": [],
}


class CRMService:
    @staticmethod
    def record_activity(
        db: Session,
        entity_type: str,
        entity_id: int,
        action: str,
        title: str,
        description: Optional[str] = None,
        customer_id: Optional[int] = None,
        customer_name: Optional[str] = None,
        user_id: Optional[int] = None,
        status_val: Optional[str] = None,
    ) -> Activity:
        """Create and persist an activity audit log entry."""
        activity = Activity(
            entity_type=entity_type,
            entity_id=entity_id,
            action=action,
            title=title,
            description=description,
            customer_id=customer_id,
            customer_name=customer_name,
            user_id=user_id,
            status=status_val,
        )
        db.add(activity)
        return activity

    @staticmethod
    def validate_lead_transition(current_status: str, target_status: str) -> None:
        """Enforce strict sequential lead transitions and reject arbitrary jumping."""
        if current_status == target_status:
            return
        allowed = VALID_LEAD_TRANSITIONS.get(current_status, [])
        if target_status not in allowed:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid lead status transition from '{current_status}' to '{target_status}'. Allowed: {allowed}",
            )

    @staticmethod
    def validate_survey_transition(current_status: str, target_status: str) -> None:
        """Enforce sequential site survey transitions: Scheduled -> In Progress -> Completed."""
        if current_status == target_status:
            return
        allowed = VALID_SURVEY_TRANSITIONS.get(current_status, [])
        if target_status not in allowed:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid survey transition from '{current_status}' to '{target_status}'. Allowed: {allowed}",
            )

    @staticmethod
    def validate_project_transition(current_status: str, target_status: str) -> None:
        """Enforce sequential project transitions: Planning -> In Progress -> Completed/On Hold."""
        if current_status == target_status:
            return
        allowed = VALID_PROJECT_TRANSITIONS.get(current_status, [])
        if target_status not in allowed:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid project transition from '{current_status}' to '{target_status}'. Allowed: {allowed}",
            )

    @staticmethod
    def recalculate_customer_status(db: Session, customer_id: Optional[int]) -> Optional[str]:
        """
        Evaluate customer active/inactive status based on remaining active records:
        - Active if customer has active leads, active surveys, active projects, or completed records.
        - Inactive if ALL linked leads are Cancelled/Lost, surveys Cancelled, projects Cancelled (or no active pipeline).
        """
        if not customer_id:
            return None

        customer = db.query(Customer).filter(Customer.id == customer_id).first()
        if not customer:
            return None

        leads = db.query(Lead).filter(Lead.customer_id == customer.id).all()
        surveys = db.query(SiteSurvey).filter(SiteSurvey.customer_id == customer.id).all()
        projects = db.query(Project).filter(Project.customer_id == customer.id).all()

        has_active_leads = any(l.status in ["New", "Contacted", "Site Survey", "Quoted"] for l in leads)
        has_active_surveys = any(s.status in ["Scheduled", "In Progress"] for s in surveys)
        has_active_projects = any(p.status in ["Planning", "In Progress", "On Hold"] for p in projects)
        has_completed_projects = any(p.status == "Completed" for p in projects)

        if has_active_leads or has_active_surveys or has_active_projects or has_completed_projects:
            target_status = "Active"
        else:
            target_status = "Inactive"

        if customer.status != target_status:
            old_status = customer.status
            customer.status = target_status
            CRMService.record_activity(
                db=db,
                entity_type="customer",
                entity_id=customer.id,
                action="status_recalculated",
                title=f"Customer status updated to {target_status}: {customer.name}",
                description=f"Automated evaluation changed status from {old_status} to {target_status}",
                customer_id=customer.id,
                customer_name=customer.name,
                status_val=target_status,
            )

        return customer.status

    @staticmethod
    def find_or_create_customer_for_lead(db: Session, lead: Lead) -> Customer:
        """
        Idempotently find an existing customer or create a new Customer record from a Lead.
        Uses ID, verified email, or phone.
        """
        # 1. Existing customer by linked customer_id
        if lead.customer_id:
            existing = db.query(Customer).filter(Customer.id == lead.customer_id).first()
            if existing:
                if existing.status != "Active":
                    existing.status = "Active"
                return existing

        # 2. Existing customer by email
        if lead.email and lead.email.strip():
            existing = db.query(Customer).filter(Customer.email.ilike(lead.email.strip())).first()
            if existing:
                lead.customer_id = existing.id
                if existing.status != "Active":
                    existing.status = "Active"
                return existing

        # 3. Existing customer by phone / contact
        target_phone = (lead.phone or lead.contact or "").strip()
        if target_phone:
            existing = (
                db.query(Customer)
                .filter(
                    (Customer.phone == target_phone)
                    | (Customer.contact == target_phone)
                )
                .first()
            )
            if existing:
                lead.customer_id = existing.id
                if existing.status != "Active":
                    existing.status = "Active"
                return existing

        # 4. Create new customer
        customer = Customer(
            name=lead.name.strip(),
            contact=lead.contact.strip(),
            email=lead.email.strip() if lead.email else None,
            phone=lead.phone.strip() if lead.phone else lead.contact.strip(),
            location=lead.location.strip(),
            property_type=lead.property_type or "Residential",
            status="Active",
            customer_since=datetime.now(timezone.utc).strftime("%d %b %Y"),
            assigned_user_id=lead.assigned_user_id,
        )
        db.add(customer)
        db.flush()  # populate customer.id

        lead.customer_id = customer.id

        CRMService.record_activity(
            db=db,
            entity_type="customer",
            entity_id=customer.id,
            action="created",
            title=f"Customer created from lead: {lead.name}",
            description=f"Auto-generated customer account #{customer.id} for lead #{lead.id}",
            customer_id=customer.id,
            customer_name=customer.name,
            user_id=lead.assigned_user_id,
            status_val="Active",
        )

        return customer

    @staticmethod
    def lead_contacted_workflow(db: Session, lead_id: int, user_id: Optional[int] = None) -> Lead:
        """
        When a lead is contacted:
        1. Ensure lead exists and transition is valid
        2. Find or create linked customer (Status = Active)
        3. Set lead.customer_id and lead.status = 'Contacted'
        4. Record activities
        """
        lead = db.query(Lead).filter(Lead.id == lead_id).first()
        if not lead:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lead not found")

        CRMService.validate_lead_transition(lead.status, "Contacted")

        customer = CRMService.find_or_create_customer_for_lead(db, lead)
        lead.status = "Contacted"

        CRMService.record_activity(
            db=db,
            entity_type="lead",
            entity_id=lead.id,
            action="contacted",
            title=f"Lead contacted: {lead.name}",
            description=f"Lead marked as Contacted. Linked to Customer #{customer.id}",
            customer_id=customer.id,
            customer_name=customer.name,
            user_id=user_id or lead.assigned_user_id,
            status_val="Contacted",
        )

        db.commit()
        db.refresh(lead)
        return lead

    @staticmethod
    def lead_schedule_survey_workflow(
        db: Session,
        lead_id: int,
        survey_data: Dict[str, Any],
        user_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        When a lead enters Site Survey:
        1. Link/create customer
        2. Create SiteSurvey linked to customer and lead (Status = Scheduled)
        3. Advance lead status to 'Site Survey'
        4. Record activities
        """
        lead = db.query(Lead).filter(Lead.id == lead_id).first()
        if not lead:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lead not found")

        CRMService.validate_lead_transition(lead.status, "Site Survey")

        customer = CRMService.find_or_create_customer_for_lead(db, lead)

        survey_date = survey_data.get("survey_date", "").strip() or datetime.now(timezone.utc).strftime("%d %b %Y")
        time_slot = survey_data.get("time_slot", "10:00 AM").strip()

        # Check existing active survey for this lead
        existing_survey = (
            db.query(SiteSurvey)
            .filter(
                SiteSurvey.lead_id == lead.id,
                SiteSurvey.status.in_(["Scheduled", "In Progress"]),
            )
            .first()
        )

        if existing_survey:
            survey = existing_survey
        else:
            survey = SiteSurvey(
                customer_name=customer.name,
                location=survey_data.get("location") or lead.location,
                property_type=survey_data.get("property_type") or lead.property_type or "Residential",
                survey_date=survey_date,
                time_slot=time_slot,
                assigned_to=survey_data.get("assigned_to", "Rahul").strip(),
                status="Scheduled",
                customer_id=customer.id,
                lead_id=lead.id,
                assigned_user_id=user_id or lead.assigned_user_id,
                roof_information=survey_data.get("roof_information"),
                capacity_estimate=survey_data.get("capacity_estimate"),
                notes=survey_data.get("notes"),
            )
            db.add(survey)
            db.flush()

            CRMService.record_activity(
                db=db,
                entity_type="site_survey",
                entity_id=survey.id,
                action="scheduled",
                title=f"Site survey scheduled for {customer.name}",
                description=f"Survey on {survey.survey_date} at {survey.time_slot} assigned to {survey.assigned_to}",
                customer_id=customer.id,
                customer_name=customer.name,
                user_id=user_id or lead.assigned_user_id,
                status_val="Scheduled",
            )

        lead.status = "Site Survey"

        CRMService.record_activity(
            db=db,
            entity_type="lead",
            entity_id=lead.id,
            action="status_changed",
            title=f"Lead moved to Site Survey: {lead.name}",
            description=f"Survey #{survey.id} scheduled",
            customer_id=customer.id,
            customer_name=customer.name,
            user_id=user_id or lead.assigned_user_id,
            status_val="Site Survey",
        )

        db.commit()
        db.refresh(lead)
        db.refresh(survey)
        return {"lead": lead, "survey": survey, "customer": customer}

    @staticmethod
    def site_survey_start_workflow(db: Session, survey_id: int, user_id: Optional[int] = None) -> SiteSurvey:
        """
        Transition Site Survey: Scheduled -> In Progress.
        """
        survey = db.query(SiteSurvey).filter(SiteSurvey.id == survey_id).first()
        if not survey:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Site survey not found")

        CRMService.validate_survey_transition(survey.status, "In Progress")

        survey.status = "In Progress"

        CRMService.record_activity(
            db=db,
            entity_type="site_survey",
            entity_id=survey.id,
            action="started",
            title=f"Site survey started for {survey.customer_name}",
            description=f"Survey #{survey.id} is now In Progress by {survey.assigned_to}",
            customer_id=survey.customer_id,
            customer_name=survey.customer_name,
            user_id=user_id,
            status_val="In Progress",
        )

        db.commit()
        db.refresh(survey)
        return survey

    @staticmethod
    def site_survey_complete_workflow(
        db: Session,
        survey_id: int,
        completion_data: Optional[Dict[str, Any]] = None,
        user_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Transition Site Survey: In Progress -> Completed.
        AUTOMATICALLY moves related Lead to 'Quoted' in atomic backend transaction.
        """
        survey = db.query(SiteSurvey).filter(SiteSurvey.id == survey_id).first()
        if not survey:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Site survey not found")

        CRMService.validate_survey_transition(survey.status, "Completed")

        survey.status = "Completed"

        c_data = completion_data or {}
        if c_data.get("roof_information"):
            survey.roof_information = c_data["roof_information"]
        if c_data.get("capacity_estimate"):
            survey.capacity_estimate = c_data["capacity_estimate"]
        if c_data.get("notes"):
            survey.notes = c_data["notes"]

        CRMService.record_activity(
            db=db,
            entity_type="site_survey",
            entity_id=survey.id,
            action="completed",
            title=f"Site survey completed for {survey.customer_name}",
            description=f"Survey #{survey.id} completed. Capacity estimate: {survey.capacity_estimate or 'Standard'}",
            customer_id=survey.customer_id,
            customer_name=survey.customer_name,
            user_id=user_id,
            status_val="Completed",
        )

        # Automatically update related Lead to 'Quoted'
        lead = None
        if survey.lead_id:
            lead = db.query(Lead).filter(Lead.id == survey.lead_id).first()
        elif survey.customer_id:
            lead = db.query(Lead).filter(
                Lead.customer_id == survey.customer_id,
                Lead.status.in_(["Site Survey", "Contacted"]),
            ).first()

        if lead and lead.status in ["Site Survey", "Contacted"]:
            lead.status = "Quoted"
            CRMService.record_activity(
                db=db,
                entity_type="lead",
                entity_id=lead.id,
                action="status_changed",
                title=f"Lead moved to Quoted: {lead.name}",
                description=f"Survey #{survey.id} completed; quote prepared for customer",
                customer_id=survey.customer_id,
                customer_name=survey.customer_name,
                user_id=user_id,
                status_val="Quoted",
            )

        CRMService.recalculate_customer_status(db, survey.customer_id)

        db.commit()
        db.refresh(survey)
        if lead:
            db.refresh(lead)

        return {"survey": survey, "lead": lead}

    @staticmethod
    def site_survey_cancel_workflow(db: Session, survey_id: int, user_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Cancel Site Survey (soft transition without physical DB row deletion).
        If related lead was in 'Site Survey', visibly updates lead to 'Cancelled'.
        Recalculates customer status.
        """
        survey = db.query(SiteSurvey).filter(SiteSurvey.id == survey_id).first()
        if not survey:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Site survey not found")

        CRMService.validate_survey_transition(survey.status, "Cancelled")

        survey.status = "Cancelled"

        CRMService.record_activity(
            db=db,
            entity_type="site_survey",
            entity_id=survey.id,
            action="cancelled",
            title=f"Site survey cancelled for {survey.customer_name}",
            description=f"Survey #{survey.id} marked as Cancelled",
            customer_id=survey.customer_id,
            customer_name=survey.customer_name,
            user_id=user_id,
            status_val="Cancelled",
        )

        # Determine related lead
        lead = None
        if survey.lead_id:
            lead = db.query(Lead).filter(Lead.id == survey.lead_id).first()
        elif survey.customer_id:
            lead = db.query(Lead).filter(
                Lead.customer_id == survey.customer_id,
                Lead.status == "Site Survey",
            ).first()

        if lead and lead.status == "Site Survey":
            lead.status = "Cancelled"
            CRMService.record_activity(
                db=db,
                entity_type="lead",
                entity_id=lead.id,
                action="cancelled",
                title=f"Lead cancelled: {lead.name}",
                description=f"Related Site Survey #{survey.id} was cancelled",
                customer_id=survey.customer_id,
                customer_name=survey.customer_name,
                user_id=user_id,
                status_val="Cancelled",
            )

        CRMService.recalculate_customer_status(db, survey.customer_id)

        db.commit()
        db.refresh(survey)
        if lead:
            db.refresh(lead)

        return {"survey": survey, "lead": lead}

    @staticmethod
    def lead_convert_workflow(
        db: Session,
        lead_id: int,
        project_data: Optional[Dict[str, Any]] = None,
        user_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        When a lead is converted:
        1. Ensure customer exists and is linked
        2. Create Project automatically with initial status = 'Planning'
        3. Set project.customer_id and project.source_lead_id
        4. Link completed/existing site surveys
        5. Mark lead as 'Converted'
        6. Record activities
        """
        lead = db.query(Lead).filter(Lead.id == lead_id).first()
        if not lead:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lead not found")

        CRMService.validate_lead_transition(lead.status, "Converted")

        customer = CRMService.find_or_create_customer_for_lead(db, lead)
        p_data = project_data or {}

        # Prevent duplicate project creation if project already exists for this lead
        existing_project = db.query(Project).filter(Project.source_lead_id == lead.id).first()
        if not existing_project and customer.id:
            p_name = p_data.get("project_name") or f"{customer.name} Solar Project"
            existing_project = db.query(Project).filter(
                Project.customer_id == customer.id,
                Project.name == p_name,
            ).first()

        if existing_project:
            project = existing_project
            if not project.source_lead_id:
                project.source_lead_id = lead.id
        else:
            survey = db.query(SiteSurvey).filter(
                (SiteSurvey.lead_id == lead.id) | (SiteSurvey.customer_id == customer.id)
            ).order_by(desc(SiteSurvey.created_at)).first()

            capacity = p_data.get("capacity") or (survey.capacity_estimate if survey and survey.capacity_estimate else "10 kW")
            capacity_kw = p_data.get("capacity_kw")
            if capacity_kw is None:
                try:
                    num_str = "".join(ch for ch in str(capacity) if ch.isdigit() or ch == ".")
                    capacity_kw = float(num_str) if num_str else 10.0
                except Exception:
                    capacity_kw = 10.0

            # Initial status MUST BE "Planning"
            project = Project(
                name=p_data.get("project_name") or f"{customer.name} Solar Project",
                category=p_data.get("category") or lead.property_type or "Residential",
                location=p_data.get("location") or lead.location,
                capacity=capacity,
                capacity_kw=capacity_kw,
                status="Planning",
                customer_id=customer.id,
                source_lead_id=lead.id,
                assigned_user_id=user_id or lead.assigned_user_id,
                estimated_cost=p_data.get("estimated_cost") or lead.estimated_value or (capacity_kw * 50000.0),
                actual_cost=p_data.get("actual_cost"),
                is_public=p_data.get("is_public", True),
            )
            db.add(project)
            db.flush()

            if survey and not survey.project_id:
                survey.project_id = project.id

            CRMService.record_activity(
                db=db,
                entity_type="project",
                entity_id=project.id,
                action="created",
                title=f"Project created: {project.name}",
                description=f"Solar installation project initialized in Planning stage from converted lead #{lead.id}",
                customer_id=customer.id,
                customer_name=customer.name,
                user_id=user_id or lead.assigned_user_id,
                status_val="Planning",
            )

        lead.status = "Converted"

        CRMService.record_activity(
            db=db,
            entity_type="lead",
            entity_id=lead.id,
            action="converted",
            title=f"Lead converted: {lead.name}",
            description=f"Lead converted to project '{project.name}' (Status: Planning)",
            customer_id=customer.id,
            customer_name=customer.name,
            user_id=user_id or lead.assigned_user_id,
            status_val="Converted",
        )

        CRMService.recalculate_customer_status(db, customer.id)

        db.commit()
        db.refresh(lead)
        db.refresh(project)
        return {"lead": lead, "project": project, "customer": customer}

    @staticmethod
    def project_start_workflow(db: Session, project_id: int, user_id: Optional[int] = None) -> Project:
        """
        Transition Project: Planning -> In Progress.
        """
        project = db.query(Project).filter(Project.id == project_id).first()
        if not project:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

        CRMService.validate_project_transition(project.status, "In Progress")

        project.status = "In Progress"
        if not project.start_date:
            project.start_date = datetime.now(timezone.utc)

        cust_name = project.customer.name if project.customer else ""
        CRMService.record_activity(
            db=db,
            entity_type="project",
            entity_id=project.id,
            action="started",
            title=f"Project started: {project.name}",
            description=f"Project transitioned from Planning to In Progress",
            customer_id=project.customer_id,
            customer_name=cust_name,
            user_id=user_id,
            status_val="In Progress",
        )

        CRMService.recalculate_customer_status(db, project.customer_id)

        db.commit()
        db.refresh(project)
        return project

    @staticmethod
    def project_hold_workflow(db: Session, project_id: int, user_id: Optional[int] = None) -> Project:
        """
        Transition Project: In Progress -> On Hold.
        """
        project = db.query(Project).filter(Project.id == project_id).first()
        if not project:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

        CRMService.validate_project_transition(project.status, "On Hold")

        project.status = "On Hold"

        cust_name = project.customer.name if project.customer else ""
        CRMService.record_activity(
            db=db,
            entity_type="project",
            entity_id=project.id,
            action="on_hold",
            title=f"Project on hold: {project.name}",
            description=f"Project transitioned from In Progress to On Hold",
            customer_id=project.customer_id,
            customer_name=cust_name,
            user_id=user_id,
            status_val="On Hold",
        )

        db.commit()
        db.refresh(project)
        return project

    @staticmethod
    def project_resume_workflow(db: Session, project_id: int, user_id: Optional[int] = None) -> Project:
        """
        Transition Project: On Hold -> In Progress.
        """
        project = db.query(Project).filter(Project.id == project_id).first()
        if not project:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

        CRMService.validate_project_transition(project.status, "In Progress")

        project.status = "In Progress"

        cust_name = project.customer.name if project.customer else ""
        CRMService.record_activity(
            db=db,
            entity_type="project",
            entity_id=project.id,
            action="resumed",
            title=f"Project resumed: {project.name}",
            description=f"Project transitioned from On Hold to In Progress",
            customer_id=project.customer_id,
            customer_name=cust_name,
            user_id=user_id,
            status_val="In Progress",
        )

        db.commit()
        db.refresh(project)
        return project

    @staticmethod
    def project_complete_workflow(
        db: Session,
        project_id: int,
        actual_cost: Optional[float] = None,
        user_id: Optional[int] = None,
    ) -> Project:
        """
        Transition Project: In Progress -> Completed.
        """
        project = db.query(Project).filter(Project.id == project_id).first()
        if not project:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

        CRMService.validate_project_transition(project.status, "Completed")

        project.status = "Completed"
        if not project.completion_date:
            project.completion_date = datetime.now(timezone.utc)
        if actual_cost is not None:
            project.actual_cost = actual_cost

        cust_name = project.customer.name if project.customer else ""
        CRMService.record_activity(
            db=db,
            entity_type="project",
            entity_id=project.id,
            action="completed",
            title=f"Project completed: {project.name}",
            description=f"Project marked as Completed",
            customer_id=project.customer_id,
            customer_name=cust_name,
            user_id=user_id,
            status_val="Completed",
        )

        CRMService.recalculate_customer_status(db, project.customer_id)

        db.commit()
        db.refresh(project)
        return project

    @staticmethod
    def project_cancel_workflow(db: Session, project_id: int, user_id: Optional[int] = None) -> Project:
        """
        Cancel Project (soft transition without physical DB row deletion).
        Preserves Lead Converted history. Recalculates Customer status.
        """
        project = db.query(Project).filter(Project.id == project_id).first()
        if not project:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

        CRMService.validate_project_transition(project.status, "Cancelled")

        project.status = "Cancelled"

        cust_name = project.customer.name if project.customer else ""
        CRMService.record_activity(
            db=db,
            entity_type="project",
            entity_id=project.id,
            action="cancelled",
            title=f"Project cancelled: {project.name}",
            description=f"Project marked as Cancelled",
            customer_id=project.customer_id,
            customer_name=cust_name,
            user_id=user_id,
            status_val="Cancelled",
        )

        CRMService.recalculate_customer_status(db, project.customer_id)

        db.commit()
        db.refresh(project)
        return project

    @staticmethod
    def lead_cancel_workflow(
        db: Session,
        lead_id: int,
        status_val: str = "Cancelled",
        user_id: Optional[int] = None,
    ) -> Lead:
        """
        Cancel or mark Lead as Lost.
        """
        lead = db.query(Lead).filter(Lead.id == lead_id).first()
        if not lead:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lead not found")

        target = "Lost" if status_val.lower() == "lost" else "Cancelled"
        CRMService.validate_lead_transition(lead.status, target)

        lead.status = target

        CRMService.record_activity(
            db=db,
            entity_type="lead",
            entity_id=lead.id,
            action="cancelled" if target == "Cancelled" else "lost",
            title=f"Lead marked as {target}: {lead.name}",
            customer_id=lead.customer_id,
            customer_name=lead.customer.name if lead.customer else lead.name,
            user_id=user_id or lead.assigned_user_id,
            status_val=target,
        )

        if lead.customer_id:
            CRMService.recalculate_customer_status(db, lead.customer_id)

        db.commit()
        db.refresh(lead)
        return lead

    @staticmethod
    def get_customer_overview(db: Session, customer_id: int) -> Dict[str, Any]:
        """Fetch central customer record and all related CRM data by IDs."""
        customer = db.query(Customer).filter(Customer.id == customer_id).first()
        if not customer:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found")

        # Related Leads
        leads = (
            db.query(Lead)
            .filter(Lead.customer_id == customer.id)
            .order_by(desc(Lead.created_at))
            .all()
        )

        # Related Surveys
        surveys = (
            db.query(SiteSurvey)
            .filter(SiteSurvey.customer_id == customer.id)
            .order_by(desc(SiteSurvey.created_at))
            .all()
        )

        # Related Projects
        projects = (
            db.query(Project)
            .filter(Project.customer_id == customer.id)
            .order_by(desc(Project.created_at))
            .all()
        )

        # Related Activities
        activities = (
            db.query(Activity)
            .filter(Activity.customer_id == customer.id)
            .order_by(desc(Activity.created_at))
            .limit(25)
            .all()
        )

        leads_data = [
            {
                "id": l.id,
                "name": l.name,
                "contact": l.contact,
                "email": l.email,
                "phone": l.phone,
                "location": l.location,
                "property_type": l.property_type,
                "source": l.source,
                "status": l.status,
                "notes": l.notes,
                "estimated_value": l.estimated_value,
                "created_at": l.created_at.isoformat() if l.created_at else None,
                "date": l.created_at.strftime("%d %b %Y") if l.created_at else "Recently",
            }
            for l in leads
        ]

        surveys_data = [
            {
                "id": s.id,
                "customer_name": s.customer_name,
                "location": s.location,
                "property_type": s.property_type,
                "survey_date": s.survey_date,
                "time_slot": s.time_slot,
                "assigned_to": s.assigned_to,
                "status": s.status,
                "roof_information": s.roof_information,
                "capacity_estimate": s.capacity_estimate,
                "notes": s.notes,
                "project_id": s.project_id,
                "lead_id": s.lead_id,
                "created_at": s.created_at.isoformat() if s.created_at else None,
            }
            for s in surveys
        ]

        projects_data = [
            {
                "id": p.id,
                "name": p.name,
                "category": p.category,
                "location": p.location,
                "capacity": p.capacity,
                "capacity_kw": p.capacity_kw,
                "status": p.status,
                "customer_id": p.customer_id,
                "source_lead_id": p.source_lead_id,
                "estimated_cost": p.estimated_cost,
                "actual_cost": p.actual_cost,
                "start_date": p.start_date.isoformat() if p.start_date else None,
                "completion_date": p.completion_date.isoformat() if p.completion_date else None,
                "created_at": p.created_at.isoformat() if p.created_at else None,
            }
            for p in projects
        ]

        activities_data = [
            {
                "id": a.id,
                "entity_type": a.entity_type,
                "entity_id": a.entity_id,
                "action": a.action,
                "title": a.title,
                "description": a.description,
                "customer_id": a.customer_id,
                "customer_name": a.customer_name,
                "status": a.status,
                "created_at": a.created_at.isoformat() if a.created_at else None,
                "time_ago": format_relative_time(a.created_at),
            }
            for a in activities
        ]

        return {
            "id": customer.id,
            "name": customer.name,
            "contact": customer.contact,
            "email": customer.email,
            "phone": customer.phone,
            "location": customer.location,
            "property_type": customer.property_type,
            "status": customer.status,
            "customer_since": customer.customer_since,
            "assigned_user_id": customer.assigned_user_id,
            "total_projects": len(projects),
            "created_at": customer.created_at,
            "updated_at": customer.updated_at,
            "leads": leads_data,
            "site_surveys": surveys_data,
            "projects": projects_data,
            "activities": activities_data,
        }
