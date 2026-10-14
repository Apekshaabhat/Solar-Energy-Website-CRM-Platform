from sqlalchemy import Column, Integer, String, Float, Text, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship
from app.core.database import Base


class Lead(Base):
    __tablename__ = "leads"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(150), nullable=False)
    contact = Column(String(100), nullable=False)
    email = Column(String(255), nullable=True)
    phone = Column(String(50), nullable=True)
    location = Column(String(150), nullable=False)
    property_type = Column(String(50), default="Residential", nullable=False)  # Residential, Commercial, Industrial
    source = Column(String(100), default="Website", nullable=False)  # Website, Calculator, Referral, Cold Call, Ad Campaign, Social Media, Direct Enquiry
    status = Column(String(50), default="New", nullable=False)  # New, Contacted, Site Survey, Quoted, Converted, Lost
    notes = Column(Text, nullable=True)
    estimated_value = Column(Float, nullable=True)
    assigned_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    customer_id = Column(Integer, ForeignKey("customers.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    assigned_user = relationship("User", back_populates="leads", foreign_keys=[assigned_user_id])
    customer = relationship("Customer", back_populates="leads", foreign_keys=[customer_id])
    site_surveys = relationship("SiteSurvey", back_populates="lead")
    projects = relationship("Project", back_populates="source_lead")
