from collections import defaultdict
from datetime import timezone

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database import get_db
from dependencies import require_role
from models import Complaint, User
from schemas import DashboardSummary, WardStat

router = APIRouter(prefix="/api/dashboard", tags=["Dashboard"])


@router.get("/summary", response_model=DashboardSummary)
def dashboard_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    total = db.query(Complaint).count()
    pending = (
        db.query(Complaint)
        .filter(Complaint.status == "Pending", Complaint.is_merged.is_(False))
        .count()
    )
    in_progress = (
        db.query(Complaint)
        .filter(Complaint.status == "In Progress", Complaint.is_merged.is_(False))
        .count()
    )
    resolved = db.query(Complaint).filter(Complaint.status == "Resolved").count()
    high_priority = (
        db.query(Complaint)
        .filter(Complaint.priority >= 4, Complaint.is_merged.is_(False))
        .count()
    )

    resolved_rows = (
        db.query(Complaint)
        .filter(Complaint.resolved_at.isnot(None), Complaint.is_merged.is_(False))
        .all()
    )
    if resolved_rows:
        total_seconds = 0.0
        for row in resolved_rows:
            created = row.created_at
            resolved_at = row.resolved_at
            if created.tzinfo is None:
                created = created.replace(tzinfo=timezone.utc)
            if resolved_at.tzinfo is None:
                resolved_at = resolved_at.replace(tzinfo=timezone.utc)
            total_seconds += (resolved_at - created).total_seconds()
        avg_hours = round((total_seconds / len(resolved_rows)) / 3600, 2)
    else:
        avg_hours = None

    ward_counters = defaultdict(lambda: {"total": 0, "resolved": 0, "pending": 0})
    all_open = db.query(Complaint).filter(Complaint.is_merged.is_(False)).all()
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

    return DashboardSummary(
        total_complaints=total,
        pending_complaints=pending,
        in_progress_complaints=in_progress,
        resolved_complaints=resolved,
        high_priority_complaints=high_priority,
        avg_resolution_hours=avg_hours,
        ward_stats=ward_stats,
    )
