from sqlalchemy import Column, Integer, String, DateTime, func
from sqlalchemy.orm import relationship
from app.core.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    phone = Column(String(50), nullable=True)
    role = Column(String(50), default="Sales Rep", nullable=False)  # Admin, Manager, Sales Rep, Support, Customer
    status = Column(String(50), default="Active", nullable=False)  # Active, Invited, Pending, Inactive
    failed_attempts = Column(Integer, default=0, nullable=False, server_default="0")
    locked_until = Column(DateTime(timezone=True), nullable=True)
    token_version = Column(Integer, default=0, nullable=False, server_default="0")
    last_login = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    leads = relationship("Lead", back_populates="assigned_user", foreign_keys="Lead.assigned_user_id")
    customers = relationship("Customer", back_populates="assigned_user", foreign_keys="Customer.assigned_user_id")
    projects = relationship("Project", back_populates="assigned_user", foreign_keys="Project.assigned_user_id")
    site_surveys = relationship("SiteSurvey", back_populates="assigned_user", foreign_keys="SiteSurvey.assigned_user_id")
    blogs = relationship("BlogPost", back_populates="author_user", foreign_keys="BlogPost.author_id")
