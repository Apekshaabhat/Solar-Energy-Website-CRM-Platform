import re
import math
from typing import Optional, List
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import or_, desc

from app.core.database import get_db
from app.dependencies.auth import get_optional_current_user, is_staff_user, require_roles
from app.models.user import User
from app.models.blog import BlogPost
from app.schemas.blog import BlogCreate, BlogUpdate, BlogResponse
from app.schemas.common import APIResponse, PaginatedResponse, PaginationMeta

router = APIRouter(prefix="/blogs", tags=["Blog Management"])
STAFF_ROLES = ["Admin", "Manager", "Sales Rep", "Support"]


def generate_slug(title: str) -> str:
    slug = re.sub(r"[^\w\s-]", "", title.lower()).strip()
    return re.sub(r"[-\s]+", "-", slug)


@router.get(
    "",
    response_model=PaginatedResponse[BlogResponse],
    summary="List blog articles",
)
def list_blogs(
    search: Optional[str] = Query(None, description="Search by title or excerpt"),
    category: Optional[str] = Query(None, description="Filter by category"),
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by Published or Draft"),
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    current_user: Optional[User] = Depends(get_optional_current_user),
    db: Session = Depends(get_db),
):
    query = db.query(BlogPost)
    is_admin = current_user is not None and current_user.role.strip().casefold() == "admin"

    if not is_admin:
        query = query.filter(BlogPost.status == "Published")

    if search:
        s = f"%{search.strip()}%"
        query = query.filter(or_(BlogPost.title.ilike(s), BlogPost.excerpt.ilike(s)))

    if category and category not in ["All", "All Categories"]:
        query = query.filter(BlogPost.category.ilike(category))

    if status_filter and status_filter not in ["All", "All Status", "All Statuses"] and is_admin:
        query = query.filter(BlogPost.status.ilike(status_filter))

    total = query.count()
    total_pages = math.ceil(total / limit) if total > 0 else 1

    posts = (
        query.order_by(desc(BlogPost.created_at))
        .offset((page - 1) * limit)
        .limit(limit)
        .all()
    )

    return PaginatedResponse(
        success=True,
        items=[BlogResponse.model_validate(p) for p in posts],
        meta=PaginationMeta(page=page, limit=limit, total=total, total_pages=total_pages),
    )


@router.post(
    "",
    response_model=APIResponse[BlogResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create a new blog article",
)
def create_blog(
    request: BlogCreate,
    current_user: User = Depends(require_roles(["Admin"])),
    db: Session = Depends(get_db),
):
    base_slug = request.slug or generate_slug(request.title)
    slug = base_slug
    counter = 1
    while db.query(BlogPost).filter(BlogPost.slug == slug).first():
        slug = f"{base_slug}-{counter}"
        counter += 1

    post = BlogPost(
        title=request.title.strip(),
        slug=slug,
        category=request.category,
        status=request.status or "Draft",
        author=request.author or current_user.name or "Admin",
        author_id=current_user.id,
        date=request.date or datetime.now().strftime("%b %d, %Y"),
        excerpt=request.excerpt.strip() if request.excerpt else None,
        content=request.content.strip() if request.content else None,
        cover_image=request.cover_image.strip() if request.cover_image else None,
        read_time=request.read_time or "5 min read",
    )
    db.add(post)
    db.commit()
    db.refresh(post)
    return APIResponse(
        success=True,
        message="Blog post created successfully",
        data=BlogResponse.model_validate(post)
    )


@router.get(
    "/{id_or_slug}",
    response_model=APIResponse[BlogResponse],
    summary="Get blog article by ID or slug",
)
def get_blog(
    id_or_slug: str,
    current_user: Optional[User] = Depends(get_optional_current_user),
    db: Session = Depends(get_db),
):
    if id_or_slug.isdigit():
        post = db.query(BlogPost).filter(BlogPost.id == int(id_or_slug)).first()
    else:
        post = db.query(BlogPost).filter(BlogPost.slug == id_or_slug).first()

    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Blog post not found")
    is_admin = current_user is not None and current_user.role.strip().casefold() == "admin"
    if post.status != "Published" and not is_admin:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Blog post not found")
    return APIResponse(success=True, data=BlogResponse.model_validate(post))


@router.patch(
    "/{post_id}",
    response_model=APIResponse[BlogResponse],
    summary="Update blog article",
)
def update_blog(
    post_id: int,
    request: BlogUpdate,
    current_user: User = Depends(require_roles(["Admin"])),
    db: Session = Depends(get_db),
):
    post = db.query(BlogPost).filter(BlogPost.id == post_id).first()
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Blog post not found")

    update_data = request.model_dump(exclude_unset=True)
    if "slug" in update_data and update_data["slug"]:
        slug_val = update_data["slug"].strip()
        existing = db.query(BlogPost).filter(BlogPost.slug == slug_val, BlogPost.id != post_id).first()
        if existing:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Slug already in use by another article")
        post.slug = slug_val

    for field, val in update_data.items():
        if field != "slug" and val is not None:
            setattr(post, field, val)

    db.commit()
    db.refresh(post)
    return APIResponse(
        success=True,
        message="Blog post updated successfully",
        data=BlogResponse.model_validate(post)
    )


@router.delete(
    "/{post_id}",
    response_model=APIResponse[bool],
    summary="Delete blog article",
)
def delete_blog(
    post_id: int,
    current_user: User = Depends(require_roles(["Admin"])),
    db: Session = Depends(get_db),
):
    post = db.query(BlogPost).filter(BlogPost.id == post_id).first()
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Blog post not found")

    db.delete(post)
    db.commit()
    return APIResponse(success=True, message="Blog post deleted successfully", data=True)
