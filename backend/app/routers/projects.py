from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import or_, desc

from app.core.database import get_db
from app.dependencies.auth import get_optional_current_user, is_staff_user, require_roles
from app.models.user import User
from app.models.project import Project
from app.models.customer import Customer
from app.models.lead import Lead
from app.models.site_survey import SiteSurvey
from app.schemas.project import ProjectCreate, ProjectUpdate, ProjectResponse
from app.schemas.common import APIResponse
from app.services.crm_service import CRMService

router = APIRouter(prefix="/projects", tags=["Projects Management"])
STAFF_ROLES = ["Admin", "Manager", "Sales Rep", "Support"]
NULLABLE_PROJECT_FIELDS = {
    "capacity_kw",
    "customer_id",
    "source_lead_id",
    "assigned_user_id",
    "image_url",
    "estimated_cost",
    "actual_cost",
    "start_date",
    "completion_date",
}


def validate_user_reference(db: Session, user_id: Optional[int]) -> None:
    if user_id is None:
        return
    exists = db.query(User.id).filter(User.id == user_id).first()
    if not exists:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Assigned user not found")


def validate_customer_reference(db: Session, customer_id: Optional[int]) -> None:
    if customer_id is None:
        return
    exists = db.query(Customer.id).filter(Customer.id == customer_id).first()
    if not exists:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Customer not found")


def validate_lead_reference(db: Session, lead_id: Optional[int]) -> None:
    if lead_id is None:
        return
    exists = db.query(Lead.id).filter(Lead.id == lead_id).first()
    if not exists:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Source lead not found")


def apply_project_update(project: Project, update_data: dict) -> None:
    for field, val in update_data.items():
        if val is None and field not in NULLABLE_PROJECT_FIELDS:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"{field} cannot be null",
            )
        setattr(project, field, val)


def build_project_response(project: Project) -> ProjectResponse:
    resp = ProjectResponse.model_validate(project)
    if project.customer:
        resp.customer_name = project.customer.name
    if project.source_lead:
        resp.source_lead_name = project.source_lead.name
    return resp


@router.get(
    "",
    response_model=APIResponse[List[ProjectResponse]],
    summary="List all projects with category and status filter",
)
def list_projects(
    search: Optional[str] = Query(None, description="Search by name, location, capacity"),
    category: Optional[str] = Query(None, description="Filter by category (Residential, Commercial, Industrial)"),
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by status"),
    is_public: Optional[bool] = Query(None, description="Filter public showcase projects"),
    current_user: Optional[User] = Depends(get_optional_current_user),
    db: Session = Depends(get_db),
):
    query = db.query(Project)
    is_staff = is_staff_user(current_user)

    if not is_staff:
        query = query.filter(Project.is_public == True)

    if search:
        s = f"%{search.strip()}%"
        query = query.filter(
            or_(
                Project.name.ilike(s),
                Project.location.ilike(s),
                Project.capacity.ilike(s),
            )
        )

    if category and category not in ["All", "All Categories"]:
        query = query.filter(Project.category.ilike(category))

    if status_filter and status_filter not in ["All", "All Status", "All Statuses"]:
        query = query.filter(Project.status.ilike(status_filter))

    if is_public is not None and is_staff:
        query = query.filter(Project.is_public == is_public)

    projects = query.order_by(desc(Project.created_at)).all()
    items = [build_project_response(p) for p in projects]

    return APIResponse(success=True, message="Projects retrieved", data=items)


@router.post(
    "",
    response_model=APIResponse[ProjectResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create a new project",
)
def create_project(
    request: ProjectCreate,
    current_user: User = Depends(require_roles(STAFF_ROLES)),
    db: Session = Depends(get_db),
):
    validate_customer_reference(db, request.customer_id)
    validate_lead_reference(db, request.source_lead_id)
    validate_user_reference(db, request.assigned_user_id)

    project = Project(
        name=request.name.strip(),
        category=request.category,
        location=request.location.strip(),
        capacity=request.capacity.strip(),
        capacity_kw=request.capacity_kw,
        status=request.status or "Planning",
        customer_id=request.customer_id,
        source_lead_id=request.source_lead_id,
        assigned_user_id=request.assigned_user_id,
        image_url=request.image_url,
        is_public=request.is_public,
        estimated_cost=request.estimated_cost,
        actual_cost=request.actual_cost,
        start_date=request.start_date,
        completion_date=request.completion_date,
    )
    db.add(project)
    db.flush()

    cust_name = project.customer.name if project.customer else "Direct Customer"

    # If linked to lead, ensure lead is marked as Converted
    if project.source_lead_id:
        lead = db.query(Lead).filter(Lead.id == project.source_lead_id).first()
        if lead and lead.status != "Converted":
            lead.status = "Converted"

    CRMService.record_activity(
        db=db,
        entity_type="project",
        entity_id=project.id,
        action="created",
        title=f"Project created: {project.name}",
        description=f"Capacity: {project.capacity}, Customer: {cust_name} (Status: {project.status})",
        customer_id=project.customer_id,
        customer_name=cust_name,
        user_id=current_user.id,
        status_val=project.status,
    )

    db.commit()
    db.refresh(project)

    return APIResponse(success=True, message="Project created successfully", data=build_project_response(project))


@router.post(
    "/{project_id}/start",
    response_model=APIResponse[ProjectResponse],
    summary="Start project (transitions Planning -> In Progress)",
)
def start_project(
    project_id: int,
    current_user: User = Depends(require_roles(STAFF_ROLES)),
    db: Session = Depends(get_db),
):
    project = CRMService.project_start_workflow(db, project_id, current_user.id)
    return APIResponse(
        success=True,
        message="Project started successfully",
        data=build_project_response(project),
    )


@router.post(
    "/{project_id}/hold",
    response_model=APIResponse[ProjectResponse],
    summary="Put project on hold (transitions In Progress -> On Hold)",
)
def hold_project(
    project_id: int,
    current_user: User = Depends(require_roles(STAFF_ROLES)),
    db: Session = Depends(get_db),
):
    project = CRMService.project_hold_workflow(db, project_id, current_user.id)
    return APIResponse(
        success=True,
        message="Project put on hold",
        data=build_project_response(project),
    )


@router.post(
    "/{project_id}/resume",
    response_model=APIResponse[ProjectResponse],
    summary="Resume project (transitions On Hold -> In Progress)",
)
def resume_project(
    project_id: int,
    current_user: User = Depends(require_roles(STAFF_ROLES)),
    db: Session = Depends(get_db),
):
    project = CRMService.project_resume_workflow(db, project_id, current_user.id)
    return APIResponse(
        success=True,
        message="Project resumed successfully",
        data=build_project_response(project),
    )


@router.post(
    "/{project_id}/complete",
    response_model=APIResponse[ProjectResponse],
    summary="Complete project (transitions In Progress -> Completed)",
)
def complete_project(
    project_id: int,
    actual_cost: Optional[float] = Query(None),
    current_user: User = Depends(require_roles(STAFF_ROLES)),
    db: Session = Depends(get_db),
):
    project = CRMService.project_complete_workflow(db, project_id, actual_cost, current_user.id)
    return APIResponse(
        success=True,
        message="Project completed successfully",
        data=build_project_response(project),
    )


@router.post(
    "/{project_id}/cancel",
    response_model=APIResponse[ProjectResponse],
    summary="Cancel project (soft transition preserving history)",
)
def cancel_project(
    project_id: int,
    current_user: User = Depends(require_roles(STAFF_ROLES)),
    db: Session = Depends(get_db),
):
    project = CRMService.project_cancel_workflow(db, project_id, current_user.id)
    return APIResponse(
        success=True,
        message="Project cancelled successfully",
        data=build_project_response(project),
    )


@router.get(
    "/{project_id}",
    response_model=APIResponse[ProjectResponse],
    summary="Get project details by ID",
)
def get_project(
    project_id: int,
    current_user: Optional[User] = Depends(get_optional_current_user),
    db: Session = Depends(get_db),
):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    is_staff = is_staff_user(current_user)
    if not project.is_public and not is_staff:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    return APIResponse(success=True, data=build_project_response(project))


@router.patch(
    "/{project_id}",
    response_model=APIResponse[ProjectResponse],
    summary="Update project details",
)
def update_project(
    project_id: int,
    request: ProjectUpdate,
    current_user: User = Depends(require_roles(STAFF_ROLES)),
    db: Session = Depends(get_db),
):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    old_status = project.status
    update_data = request.model_dump(exclude_unset=True)
    target_status = update_data.get("status")

    if target_status and target_status != old_status:
        CRMService.validate_project_transition(old_status, target_status)
        if target_status == "In Progress":
            if old_status == "On Hold":
                project = CRMService.project_resume_workflow(db, project_id, current_user.id)
            else:
                project = CRMService.project_start_workflow(db, project_id, current_user.id)
        elif target_status == "On Hold":
            project = CRMService.project_hold_workflow(db, project_id, current_user.id)
        elif target_status == "Completed":
            project = CRMService.project_complete_workflow(db, project_id, update_data.get("actual_cost"), current_user.id)
        elif target_status == "Cancelled":
            project = CRMService.project_cancel_workflow(db, project_id, current_user.id)
        update_data.pop("status", None)

    validate_customer_reference(db, update_data.get("customer_id"))
    validate_lead_reference(db, update_data.get("source_lead_id"))
    validate_user_reference(db, update_data.get("assigned_user_id"))
    apply_project_update(project, update_data)

    db.commit()
    db.refresh(project)

    return APIResponse(success=True, message="Project updated successfully", data=build_project_response(project))


@router.get(
    "/{project_id}/related-data",
    response_model=APIResponse[Dict[str, Any]],
    summary="Get all CRM data linked to this project",
)
def get_project_related_data(
    project_id: int,
    current_user: User = Depends(require_roles(STAFF_ROLES)),
    db: Session = Depends(get_db),
):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    surveys = db.query(SiteSurvey).filter(SiteSurvey.project_id == project.id).all()
    source_lead = None
    if project.source_lead_id:
        source_lead = db.query(Lead).filter(Lead.id == project.source_lead_id).first()

    return APIResponse(
        success=True,
        data={
            "project": build_project_response(project).model_dump(),
            "customer": {
                "id": project.customer.id,
                "name": project.customer.name,
                "contact": project.customer.contact,
                "location": project.customer.location,
            } if project.customer else None,
            "source_lead": {
                "id": source_lead.id,
                "name": source_lead.name,
                "status": source_lead.status,
                "source": source_lead.source,
            } if source_lead else None,
            "surveys": [
                {
                    "id": s.id,
                    "date": s.survey_date,
                    "status": s.status,
                    "capacity_estimate": s.capacity_estimate,
                }
                for s in surveys
            ],
        },
    )


@router.delete(
    "/{project_id}",
    response_model=APIResponse[bool],
    summary="Cancel project (soft transition preserving history)",
)
def delete_project(
    project_id: int,
    current_user: User = Depends(require_roles(["Admin", "Manager"])),
    db: Session = Depends(get_db),
):
    CRMService.project_cancel_workflow(db, project_id, current_user.id)
    return APIResponse(success=True, message="Project cancelled successfully (history preserved)", data=True)

