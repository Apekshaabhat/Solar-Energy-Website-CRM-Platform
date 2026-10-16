import math
from typing import Optional, List
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import or_, desc

from app.core.database import get_db
from app.dependencies.auth import require_roles
from app.models.user import User
from app.models.calculator import CalculatorSubmission, CalculatorSettings
from app.schemas.calculator import (
    CalculatorSubmissionCreate,
    CalculatorSubmissionResponse,
    CalculatorSettingsUpdate,
    CalculatorSettingsResponse,
    ROIEstimateRequest,
    ROIEstimateResponse,
    RoofCapacityRequest,
    RoofCapacityResponse,
    SavingsEstimateRequest,
    SavingsEstimateResponse,
)
from app.schemas.common import APIResponse, PaginatedResponse, PaginationMeta

router = APIRouter(prefix="/calculators", tags=["Calculators"])
STAFF_ROLES = ["Admin", "Manager", "Sales Rep", "Support"]


def get_or_create_settings(db: Session) -> CalculatorSettings:
    settings_obj = db.query(CalculatorSettings).order_by(CalculatorSettings.id.asc()).first()
    if not settings_obj:
        try:
            settings_obj = CalculatorSettings(
                electricity_rate=8.0,
                generation_per_kw=120.0,
                installation_cost_per_kw=55000.0,
                bill_offset_percent=85.0,
            )
            db.add(settings_obj)
            db.commit()
            db.refresh(settings_obj)
        except Exception:
            db.rollback()
            settings_obj = db.query(CalculatorSettings).order_by(CalculatorSettings.id.asc()).first()
    else:
        duplicates = db.query(CalculatorSettings).filter(CalculatorSettings.id != settings_obj.id).all()
        if duplicates:
            for dup in duplicates:
                db.delete(dup)
            db.commit()
    return settings_obj


def round_one(value: float) -> float:
    return round(value * 10) / 10


@router.post(
    "/savings-estimate",
    response_model=APIResponse[SavingsEstimateResponse],
    summary="Calculate a solar savings estimate",
)
def calculate_savings_estimate(
    request: SavingsEstimateRequest,
    db: Session = Depends(get_db),
):
    settings_obj = get_or_create_settings(db)
    monthly_units = request.monthly_bill / settings_obj.electricity_rate
    system_size_kw = max(1.0, round_one(monthly_units / settings_obj.generation_per_kw))
    annual_savings = round(request.monthly_bill * 12 * (settings_obj.bill_offset_percent / 100))
    payback_years = round_one(
        (system_size_kw * settings_obj.installation_cost_per_kw) / max(annual_savings, 1)
    )
    co2_tons = round_one(system_size_kw * 1.2)

    return APIResponse(
        success=True,
        message="Savings estimate calculated successfully",
        data=SavingsEstimateResponse(
            system_size_kw=system_size_kw,
            annual_savings=annual_savings,
            payback_years=payback_years,
            co2_tons=co2_tons,
        ),
    )


@router.post(
    "/roof-capacity",
    response_model=APIResponse[RoofCapacityResponse],
    summary="Calculate roof solar capacity",
)
def calculate_roof_capacity(request: RoofCapacityRequest):
    shading_factor = {"None": 1.0, "Partial": 0.8, "Heavy": 0.55}.get(request.shading, 1.0)
    orientation_factor = {
        "South-facing": 1.0,
        "East/West-facing": 0.88,
        "North-facing": 0.65,
    }.get(request.orientation, 1.0)

    usable_area = request.roof_area * shading_factor * orientation_factor
    panel_count = max(1, math.floor(usable_area / 17.5))
    system_size_kw = round_one(panel_count * 0.4)
    annual_generation = round(system_size_kw * 1400)

    return APIResponse(
        success=True,
        message="Roof capacity calculated successfully",
        data=RoofCapacityResponse(
            panel_count=panel_count,
            system_size_kw=system_size_kw,
            annual_generation=annual_generation,
        ),
    )


@router.post(
    "/roi-estimate",
    response_model=APIResponse[ROIEstimateResponse],
    summary="Calculate solar return on investment",
)
def calculate_roi_estimate(
    request: ROIEstimateRequest,
    db: Session = Depends(get_db),
):
    settings_obj = get_or_create_settings(db)
    gross_cost = request.system_size_kw * settings_obj.installation_cost_per_kw
    net_investment = max(0, gross_cost - request.subsidy)
    annual_savings = request.monthly_savings * 12
    payback_years = round_one(net_investment / max(annual_savings, 1))
    lifetime_savings = round((annual_savings * 25) - net_investment)
    roi_percent = round((lifetime_savings / net_investment) * 100) if net_investment > 0 else 0

    return APIResponse(
        success=True,
        message="ROI estimate calculated successfully",
        data=ROIEstimateResponse(
            net_investment=net_investment,
            payback_years=payback_years,
            lifetime_savings=lifetime_savings,
            roi_percent=roi_percent,
        ),
    )


@router.get(
    "/submissions",
    response_model=PaginatedResponse[CalculatorSubmissionResponse],
    summary="List calculator submissions",
)
def list_submissions(
    search: Optional[str] = Query(None, description="Search by submitter name or phone"),
    property_type: Optional[str] = Query(None, description="Filter by property type"),
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    current_user: User = Depends(require_roles(STAFF_ROLES)),
    db: Session = Depends(get_db),
):
    query = db.query(CalculatorSubmission)

    if search:
        s = f"%{search.strip()}%"
        query = query.filter(
            or_(
                CalculatorSubmission.name.ilike(s),
                CalculatorSubmission.phone.ilike(s),
                CalculatorSubmission.email.ilike(s),
            )
        )

    if property_type and property_type not in ["All", "All Property Types"]:
        query = query.filter(CalculatorSubmission.property_type.ilike(property_type))

    total = query.count()
    total_pages = math.ceil(total / limit) if total > 0 else 1

    subs = (
        query.order_by(desc(CalculatorSubmission.created_at))
        .offset((page - 1) * limit)
        .limit(limit)
        .all()
    )

    items = []
    for s in subs:
        resp = CalculatorSubmissionResponse.model_validate(s)
        resp.date = s.created_at.strftime("%Y-%m-%d") if s.created_at else "2026-09-15"
        items.append(resp)

    return PaginatedResponse(
        success=True,
        items=items,
        meta=PaginationMeta(page=page, limit=limit, total=total, total_pages=total_pages),
    )


@router.post(
    "/submissions",
    response_model=APIResponse[CalculatorSubmissionResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Submit calculator estimate",
)
def create_submission(
    request: CalculatorSubmissionCreate,
    db: Session = Depends(get_db),
):
    submission = CalculatorSubmission(
        name=request.name.strip(),
        phone=request.phone.strip(),
        email=request.email.strip() if request.email else None,
        property_type=request.property_type,
        monthly_bill=request.monthly_bill,
        roof_area=request.roof_area,
        system_size_kw=request.system_size_kw,
        annual_savings=request.annual_savings,
        payback_years=request.payback_years,
        co2_tons=request.co2_tons,
        date=datetime.now().strftime("%Y-%m-%d"),
    )
    db.add(submission)
    db.commit()
    db.refresh(submission)

    resp = CalculatorSubmissionResponse.model_validate(submission)
    resp.date = submission.created_at.strftime("%Y-%m-%d")
    return APIResponse(
        success=True,
        message="Calculator estimate submitted successfully",
        data=resp
    )


@router.get(
    "/submissions/{submission_id}",
    response_model=APIResponse[CalculatorSubmissionResponse],
    summary="Get calculator submission details",
)
def get_submission(
    submission_id: int,
    current_user: User = Depends(require_roles(STAFF_ROLES)),
    db: Session = Depends(get_db),
):
    sub = db.query(CalculatorSubmission).filter(CalculatorSubmission.id == submission_id).first()
    if not sub:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Submission not found")

    resp = CalculatorSubmissionResponse.model_validate(sub)
    resp.date = sub.created_at.strftime("%Y-%m-%d") if sub.created_at else "2026-09-15"
    return APIResponse(success=True, data=resp)


@router.delete(
    "/submissions/{submission_id}",
    response_model=APIResponse[bool],
    summary="Delete calculator submission",
)
def delete_submission(
    submission_id: int,
    current_user: User = Depends(require_roles(["Admin", "Manager"])),
    db: Session = Depends(get_db),
):
    sub = db.query(CalculatorSubmission).filter(CalculatorSubmission.id == submission_id).first()
    if not sub:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Submission not found")

    db.delete(sub)
    db.commit()
    return APIResponse(success=True, message="Submission deleted successfully", data=True)


@router.get(
    "/settings",
    response_model=APIResponse[CalculatorSettingsResponse],
    summary="Get calculation settings",
)
def get_calculator_settings(
    db: Session = Depends(get_db),
):
    settings_obj = get_or_create_settings(db)

    return APIResponse(
        success=True,
        message="Calculator settings retrieved",
        data=CalculatorSettingsResponse.model_validate(settings_obj)
    )


@router.put(
    "/settings",
    response_model=APIResponse[CalculatorSettingsResponse],
    summary="Update calculation settings",
)
def update_calculator_settings(
    request: CalculatorSettingsUpdate,
    current_user: User = Depends(require_roles(["Admin", "Manager"])),
    db: Session = Depends(get_db),
):
    settings_obj = get_or_create_settings(db)

    update_data = request.model_dump(exclude_unset=True)
    for field, val in update_data.items():
        if val is not None:
            setattr(settings_obj, field, val)

    db.commit()
    db.refresh(settings_obj)
    return APIResponse(
        success=True,
        message="Calculator settings updated successfully",
        data=CalculatorSettingsResponse.model_validate(settings_obj)
    )
