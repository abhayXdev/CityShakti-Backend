from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    role = Column(String, nullable=False, default="citizen", index=True)
    ward = Column(String, nullable=True, index=True)
    points = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    complaints = relationship(
        "Complaint", back_populates="citizen", foreign_keys="Complaint.citizen_id"
    )
    activities = relationship("ComplaintActivity", back_populates="actor_user")


class Complaint(Base):
    __tablename__ = "complaints"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    description = Column(String)
    ward = Column(String, index=True)
    citizen_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    merged_into_id = Column(
        Integer, ForeignKey("complaints.id"), nullable=True, index=True
    )
    is_merged = Column(Boolean, default=False, index=True)
    category = Column(String, default="General", index=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    priority = Column(Integer, default=0)
    priority_label = Column(String, default="Low", index=True)
    reports_count = Column(Integer, default=1)
    upvotes = Column(Integer, default=0)
    impact_score = Column(Float, default=0)
    status = Column(String, default="Pending")
    assigned_to = Column(String, nullable=True, index=True)
    assigned_department = Column(String, nullable=True, index=True)

    # AI Metadata
    ai_confidence_score = Column(Float, nullable=True)
    ai_similarity_score = Column(Float, nullable=True)

    # SLA Tracking
    is_sla_breached = Column(Boolean, default=False, index=True)
    escalation_level = Column(Integer, default=0, index=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    expected_resolution_date = Column(DateTime(timezone=True), nullable=True)
    resolved_at = Column(DateTime(timezone=True), nullable=True)

    citizen = relationship(
        "User", back_populates="complaints", foreign_keys=[citizen_id]
    )
    activities = relationship(
        "ComplaintActivity", back_populates="complaint", cascade="all, delete-orphan"
    )
    updates = relationship(
        "ComplaintUpdate", back_populates="complaint", cascade="all, delete-orphan"
    )
    merged_into = relationship("Complaint", remote_side=[id])


class ComplaintActivity(Base):
    __tablename__ = "complaint_activities"

    id = Column(Integer, primary_key=True, index=True)
    complaint_id = Column(
        Integer, ForeignKey("complaints.id"), index=True, nullable=False
    )
    action = Column(String, nullable=False)
    details = Column(String, nullable=True)
    previous_value = Column(String, nullable=True)
    new_value = Column(String, nullable=True)
    actor = Column(String, nullable=True)
    actor_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    complaint = relationship("Complaint", back_populates="activities")
    actor_user = relationship("User", back_populates="activities")


class ComplaintUpdate(Base):
    __tablename__ = "complaint_updates"

    id = Column(Integer, primary_key=True, index=True)
    complaint_id = Column(
        Integer, ForeignKey("complaints.id"), index=True, nullable=False
    )
    phase = Column(String, nullable=False, default="after")
    note = Column(String, nullable=True)
    photo_url = Column(String, nullable=True)
    created_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    complaint = relationship("Complaint", back_populates="updates")
