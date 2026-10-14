from sqlalchemy import Column, Integer, String, Float, Boolean, Date, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship
from app.core.database import Base


class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    category = Column(String(50), nullable=False)  # Residential, Commercial, Industrial
    location = Column(String(150), nullable=False)
    capacity = Column(String(50), nullable=False)  # e.g. "12 kW", "250 kW"
    capacity_kw = Column(Float, nullable=True)
    status = Column(String(50), default="In Progress", nullable=False)  # Planning, In Progress, Completed, On Hold, Cancelled
    customer_id = Column(Integer, ForeignKey("customers.id", ondelete="SET NULL"), nullable=True)
    source_lead_id = Column(Integer, ForeignKey("leads.id", ondelete="SET NULL"), nullable=True, index=True)
    assigned_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    image_url = Column(String(500), nullable=True)
    is_public = Column(Boolean, default=True, nullable=False)
    estimated_cost = Column(Float, nullable=True)
    actual_cost = Column(Float, nullable=True)
    start_date = Column(Date, nullable=True)
    completion_date = Column(Date, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    customer = relationship("Customer", back_populates="projects", foreign_keys=[customer_id])
    source_lead = relationship("Lead", back_populates="projects", foreign_keys=[source_lead_id])
    assigned_user = relationship("User", back_populates="projects", foreign_keys=[assigned_user_id])
    site_surveys = relationship("SiteSurvey", back_populates="project")
