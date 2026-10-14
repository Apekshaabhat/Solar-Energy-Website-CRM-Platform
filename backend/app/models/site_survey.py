from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship
from app.core.database import Base


class SiteSurvey(Base):
    __tablename__ = "site_surveys"

    id = Column(Integer, primary_key=True, index=True)
    customer_name = Column(String(150), nullable=False)
    location = Column(String(150), nullable=False)
    property_type = Column(String(50), default="Residential", nullable=False)  # Residential, Commercial, Industrial
    survey_date = Column(String(50), nullable=False)  # e.g. "15 Sep 2026" or YYYY-MM-DD
    time_slot = Column(String(50), nullable=False)  # e.g. "10:00 AM"
    assigned_to = Column(String(100), default="Rahul", nullable=False)  # Surveyor name string
    status = Column(String(50), default="Scheduled", nullable=False)  # Scheduled, In Progress, Completed, Cancelled
    customer_id = Column(Integer, ForeignKey("customers.id", ondelete="SET NULL"), nullable=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="SET NULL"), nullable=True)
    lead_id = Column(Integer, ForeignKey("leads.id", ondelete="SET NULL"), nullable=True, index=True)
    assigned_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    roof_information = Column(Text, nullable=True)
    capacity_estimate = Column(String(50), nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    customer = relationship("Customer", back_populates="site_surveys", foreign_keys=[customer_id])
    project = relationship("Project", back_populates="site_surveys", foreign_keys=[project_id])
    lead = relationship("Lead", back_populates="site_surveys", foreign_keys=[lead_id])
    assigned_user = relationship("User", back_populates="site_surveys", foreign_keys=[assigned_user_id])
