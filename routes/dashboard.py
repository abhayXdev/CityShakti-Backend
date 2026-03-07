from collections import defaultdict
from datetime import timezone

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func, or_
import re

from database import get_db
from dependencies import require_role
from models import Complaint, User
from schemas import DashboardSummary, WardStat

router = APIRouter(prefix="/api/dashboard", tags=["Dashboard"])


@router.get("/summary", response_model=DashboardSummary)
def dashboard_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("officer", "sudo")),
):
    query = db.query(Complaint)
    
    if current_user.role == "officer":
        if current_user.ward:
            tw = current_user.ward.replace(' ', '').lower()
            query = query.filter(
                func.replace(func.coalesce(func.nullif(func.lower(Complaint.incident_ward), ''), func.lower(Complaint.ward)), ' ', '') == tw
            )
        
        dept = current_user.department
        if dept:
            # Loosen word length from 3 to 2 to catch "Water", "Roads", etc if split
            words = [w for w in re.split(r'[^a-zA-Z0-9]', dept) if len(w) >= 2]
            if words:
                conds = []
                for w in words:
                    conds.append(func.coalesce(Complaint.assigned_department, '').ilike(f"%{w}%"))
                    conds.append(func.coalesce(Complaint.category, '').ilike(f"%{w}%"))
                query = query.filter(or_(*conds))

    total = query.count()
    # Corrected statuses: Include Submitted and Assigned in Pending counts
    pending = query.filter(Complaint.status.in_(["Submitted", "Assigned", "Pending"]), Complaint.is_merged.is_(False)).count()
    in_progress = query.filter(Complaint.status == "In Progress", Complaint.is_merged.is_(False)).count()
    resolved = query.filter(Complaint.status.in_(["Resolved", "Closed"])).count()
    high_priority = query.filter(Complaint.priority >= 4, Complaint.is_merged.is_(False)).count()
    # Add escalated count: SLA breached and not resolved/closed
    escalated = query.filter(Complaint.is_sla_breached.is_(True), ~Complaint.status.in_(["Resolved", "Closed"])).count()

    resolved_rows = query.filter(Complaint.resolved_at.isnot(None), Complaint.is_merged.is_(False)).all()
    if resolved_rows:
        total_seconds = 0.0
        total_assigned_seconds = 0.0
        assigned_count = 0

        for row in resolved_rows:
            created = row.created_at
            resolved_at = row.resolved_at
            if created.tzinfo is None:
                created = created.replace(tzinfo=timezone.utc)
            if resolved_at.tzinfo is None:
                resolved_at = resolved_at.replace(tzinfo=timezone.utc)
            total_seconds += (resolved_at - created).total_seconds()

            if row.assigned_at:
                assigned = row.assigned_at
                if assigned.tzinfo is None:
                    assigned = assigned.replace(tzinfo=timezone.utc)
                if resolved_at > assigned:
                    total_assigned_seconds += (resolved_at - assigned).total_seconds()
                    assigned_count += 1

        avg_hours = round((total_seconds / len(resolved_rows)) / 3600, 2)
        avg_assignment_to_resolution_hours = (
            round((total_assigned_seconds / assigned_count) / 3600, 2)
            if assigned_count > 0
            else None
        )
    else:
        avg_hours = None
        avg_assignment_to_resolution_hours = None

    ward_counters = defaultdict(lambda: {"total": 0, "resolved": 0, "pending": 0})
    all_open = query.filter(Complaint.is_merged.is_(False)).all()
    for complaint in all_open:
        ward_info = ward_counters[complaint.ward]
        ward_info["total"] += 1
        if complaint.status == "Resolved":
            ward_info["resolved"] += 1
        else:
            ward_info["pending"] += 1

    ward_stats = [
        WardStat(
            ward=ward,
            total=data["total"],
            resolved=data["resolved"],
            pending=data["pending"],
        )
        for ward, data in sorted(ward_counters.items(), key=lambda item: item[0])
    ]

    category_counters = defaultdict(int)
    for complaint in all_open:
        category_counters[complaint.category] += 1

    category_stats = [
        {"category": cat, "total": count}
        for cat, count in sorted(
            category_counters.items(), key=lambda i: i[1], reverse=True
        )
    ]

    return DashboardSummary(
        total_complaints=total,
        pending_complaints=pending,
        in_progress_complaints=in_progress,
        resolved_complaints=resolved,
        high_priority_complaints=high_priority,
        escalated_complaints=escalated,
        avg_resolution_hours=avg_hours,
        avg_assignment_to_resolution_hours=avg_assignment_to_resolution_hours,
        ward_stats=ward_stats,
        category_stats=category_stats,
    )
