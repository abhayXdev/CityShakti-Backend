from datetime import datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class APIMessage(BaseModel):
    message: str


class UserRegister(BaseModel):
    full_name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    role: Literal["citizen", "officer", "sudo"] = "citizen"
    ward: Optional[str] = Field(default=None, pattern=r"^\d{6}$", description="6-digit Indian PIN code")
    department: Optional[str] = Field(default=None, max_length=100)


class UserLogin(BaseModel):
    email: EmailStr
    password: str
    role: Optional[Literal["citizen", "officer", "sudo"]] = None


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class UserOut(BaseModel):
    id: int
    full_name: str
    email: EmailStr
    role: str
    ward: Optional[str]
    department: Optional[str] = None
    points: int = 0
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


class ComplaintCreate(BaseModel):
    title: str = Field(min_length=3, max_length=200)
    description: str = Field(min_length=10, max_length=5000)
    ward: str = Field(pattern=r"^\d{6}$", description="6-digit Indian PIN code")
    incident_ward: Optional[str] = Field(default=None, pattern=r"^\d{6}$", description="6-digit Indian PIN code of incident")
    category: str = Field(default="General", max_length=100)
    photo_url: Optional[str] = Field(default=None, max_length=1000)
    latitude: float
    longitude: float
    priority: int = Field(default=0, ge=0, le=5)


class ComplaintAdminUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=3, max_length=200)
    description: Optional[str] = Field(default=None, min_length=10, max_length=5000)
    category: Optional[str] = Field(default=None, max_length=100)
    ward: Optional[str] = Field(default=None, min_length=2, max_length=100)
    note: Optional[str] = Field(default=None, max_length=1000)
    actor: Optional[str] = None


class ComplaintAssign(BaseModel):
    assigned_to: str = Field(min_length=2, max_length=120)
    assigned_department: Optional[str] = None
    actor: Optional[str] = None


class ComplaintStatusUpdate(BaseModel):
    status: Literal["Submitted", "Assigned", "In Progress", "Resolved", "Closed", "Rejected"]
    note: Optional[str] = None
    actor: Optional[str] = None


class ComplaintMergeRequest(BaseModel):
    source_complaint_id: int
    target_complaint_id: int
    actor: Optional[str] = None


class ComplaintProgressUpdateCreate(BaseModel):
    phase: Literal["update", "before", "after"] = "update"
    note: Optional[str] = Field(default=None, max_length=2000)
    photo_url: Optional[str] = Field(default=None, max_length=1000)


class ComplaintActivityOut(BaseModel):
    id: int
    action: str
    details: Optional[str]
    previous_value: Optional[str] = None
    new_value: Optional[str] = None
    actor: Optional[str]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ComplaintProgressUpdateOut(BaseModel):
    id: int
    phase: str
    note: Optional[str]
    photo_url: Optional[str]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ComplaintOut(BaseModel):
    id: int
    title: str
    description: str
    ward: str
    incident_ward: Optional[str] = None
    category: str
    priority: int
    priority_label: str
    reports_count: int
    upvotes: int = 0
    impact_score: float
    status: str
    photo_url: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    citizen_id: Optional[int]
    merged_into_id: Optional[int]
    is_merged: bool
    assigned_to: Optional[str]
    assigned_department: Optional[str]
    assigned_at: Optional[datetime] = None
    ai_confidence_score: Optional[float] = None
    ai_similarity_score: Optional[float] = None
    is_sla_breached: bool = False
    escalation_level: int = 0
    created_at: datetime
    updated_at: Optional[datetime]
    expected_resolution_date: Optional[datetime]
    resolved_at: Optional[datetime]

    model_config = ConfigDict(from_attributes=True)


class ComplaintDetailOut(ComplaintOut):
    activities: List[ComplaintActivityOut] = Field(default_factory=list)
    updates: List[ComplaintProgressUpdateOut] = Field(default_factory=list)


class WardStat(BaseModel):
    ward: str
    total: int
    resolved: int
    pending: int


class CategoryStat(BaseModel):
    category: str
    total: int


class DashboardSummary(BaseModel):
    total_complaints: int
    pending_complaints: int
    in_progress_complaints: int
    resolved_complaints: int
    high_priority_complaints: int
    avg_resolution_hours: Optional[float]
    avg_assignment_to_resolution_hours: Optional[float] = None
    ward_stats: List[WardStat] = Field(default_factory=list)
    category_stats: List[CategoryStat] = Field(default_factory=list)
