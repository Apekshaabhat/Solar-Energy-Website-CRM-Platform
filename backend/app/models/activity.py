from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship
from app.core.database import Base


class Activity(Base):
    __tablename__ = "activities"

    id = Column(Integer, primary_key=True, index=True)
    entity_type = Column(String(50), nullable=False, index=True)  # lead, customer, site_survey, project
    entity_id = Column(Integer, nullable=False, index=True)
    action = Column(String(50), nullable=False)  # created, contacted, scheduled, completed, converted, status_changed, updated
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    customer_id = Column(Integer, ForeignKey("customers.id", ondelete="SET NULL"), nullable=True, index=True)
    customer_name = Column(String(150), nullable=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    status = Column(String(50), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)

    # Relationships
    customer = relationship("Customer", back_populates="activities", foreign_keys=[customer_id])
    user = relationship("User", foreign_keys=[user_id])
