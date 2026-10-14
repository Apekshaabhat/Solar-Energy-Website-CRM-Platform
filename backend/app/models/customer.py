from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship
from app.core.database import Base


class Customer(Base):
    __tablename__ = "customers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(150), nullable=False)
    contact = Column(String(100), nullable=False)  # phone or email representation
    email = Column(String(255), nullable=True)
    phone = Column(String(50), nullable=True)
    location = Column(String(150), nullable=False)
    property_type = Column(String(50), default="Residential", nullable=False)  # Residential, Commercial, Industrial
    status = Column(String(50), default="Active", nullable=False)  # Active, Inactive
    customer_since = Column(String(50), nullable=True)
    assigned_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    assigned_user = relationship("User", back_populates="customers", foreign_keys=[assigned_user_id])
    projects = relationship("Project", back_populates="customer")
    site_surveys = relationship("SiteSurvey", back_populates="customer")
    leads = relationship("Lead", back_populates="customer")
    activities = relationship("Activity", back_populates="customer", cascade="all, delete-orphan")
