from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import desc, or_

from app.core.database import get_db
from app.dependencies.auth import get_optional_current_user, is_staff_user, require_roles
from app.models.user import User
from app.models.faq import FAQ
from app.schemas.faq import FAQCreate, FAQUpdate, FAQResponse
from app.schemas.common import APIResponse

router = APIRouter(prefix="/faqs", tags=["FAQs Management"])
STAFF_ROLES = ["Admin", "Manager", "Sales Rep", "Support"]


@router.get(
    "",
    response_model=APIResponse[List[FAQResponse]],
    summary="List FAQs",
)
def list_faqs(
    published_only: Optional[bool] = Query(False, description="Filter published FAQs only"),
    search: Optional[str] = Query(None, description="Search by question or answer"),
    category: Optional[str] = Query(None, description="Filter by category"),
    current_user: Optional[User] = Depends(get_optional_current_user),
    db: Session = Depends(get_db),
):
    query = db.query(FAQ)
    is_staff = is_staff_user(current_user)
    if published_only or not is_staff:
        query = query.filter(FAQ.is_published == True)

    if search:
        s = f"%{search.strip()}%"
        query = query.filter(or_(FAQ.question.ilike(s), FAQ.answer.ilike(s)))

    if category and category not in ["All", "All Categories"]:
        query = query.filter(FAQ.category.ilike(category))

    faqs = query.order_by(FAQ.display_order.asc(), desc(FAQ.created_at)).all()
    return APIResponse(
        success=True,
        message="FAQs retrieved successfully",
        data=[FAQResponse.model_validate(f) for f in faqs]
    )


@router.post(
    "",
    response_model=APIResponse[FAQResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create a new FAQ",
)
def create_faq(
    request: FAQCreate,
    current_user: User = Depends(require_roles(["Admin", "Manager"])),
    db: Session = Depends(get_db),
):
    faq = FAQ(
        question=request.question.strip(),
        answer=request.answer.strip(),
        category=request.category,
        display_order=request.display_order,
        is_published=request.is_published,
    )
    db.add(faq)
    db.commit()
    db.refresh(faq)
    return APIResponse(
        success=True,
        message="FAQ created successfully",
        data=FAQResponse.model_validate(faq)
    )


@router.get(
    "/{faq_id}",
    response_model=APIResponse[FAQResponse],
    summary="Get FAQ by ID",
)
def get_faq(
    faq_id: int,
    current_user: Optional[User] = Depends(get_optional_current_user),
    db: Session = Depends(get_db),
):
    faq = db.query(FAQ).filter(FAQ.id == faq_id).first()
    if not faq:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="FAQ not found")
    is_staff = is_staff_user(current_user)
    if not faq.is_published and not is_staff:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="FAQ not found")
    return APIResponse(success=True, data=FAQResponse.model_validate(faq))


@router.patch(
    "/{faq_id}",
    response_model=APIResponse[FAQResponse],
    summary="Update FAQ",
)
def update_faq(
    faq_id: int,
    request: FAQUpdate,
    current_user: User = Depends(require_roles(["Admin", "Manager"])),
    db: Session = Depends(get_db),
):
    faq = db.query(FAQ).filter(FAQ.id == faq_id).first()
    if not faq:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="FAQ not found")

    update_data = request.model_dump(exclude_unset=True)
    for field, val in update_data.items():
        if val is not None:
            setattr(faq, field, val)

    db.commit()
    db.refresh(faq)
    return APIResponse(
        success=True,
        message="FAQ updated successfully",
        data=FAQResponse.model_validate(faq)
    )


@router.delete(
    "/{faq_id}",
    response_model=APIResponse[bool],
    summary="Delete FAQ",
)
def delete_faq(
    faq_id: int,
    current_user: User = Depends(require_roles(["Admin", "Manager"])),
    db: Session = Depends(get_db),
):
    faq = db.query(FAQ).filter(FAQ.id == faq_id).first()
    if not faq:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="FAQ not found")

    db.delete(faq)
    db.commit()
    return APIResponse(success=True, message="FAQ deleted successfully", data=True)
