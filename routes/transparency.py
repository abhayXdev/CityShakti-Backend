import statistics
from datetime import timezone

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from database import get_db
from models import Complaint

router = APIRouter(prefix="/api/transparency", tags=["Transparency"])


@router.get("/metrics")
def get_public_metrics(db: Session = Depends(get_db)):
    """
    Public unstructured endpoint providing municipal-level civic metrics.
    No authentication required.
    """
    total_complaints = db.query(Complaint).count()
    resolved_complaints = (
        db.query(Complaint).filter(Complaint.status == "Resolved").count()
    )

    resolution_rate = round(
        (resolved_complaints / total_complaints * 100) if total_complaints > 0 else 0, 2
    )

    # Average Resolution Time (in days)
    resolved_records = (
        db.query(Complaint.created_at, Complaint.resolved_at)
        .filter(Complaint.status == "Resolved")
        .all()
    )
    if resolved_records:
        durations = [
            (r.resolved_at - r.created_at).total_seconds() / 86400
            for r in resolved_records
            if r.resolved_at and r.created_at
        ]
        avg_resolution_days = round(statistics.mean(durations), 2) if durations else 0
    else:
        avg_resolution_days = 0

    # Top recurring issues (Categories)
    categories = (
        db.query(Complaint.category, func.count(Complaint.id).label("count"))
        .group_by(Complaint.category)
        .order_by(func.count(Complaint.id).desc())
        .limit(5)
        .all()
    )
    top_categories = [{"category": c.category, "reports": c.count} for c in categories]

    # SLA Breaches Total
    sla_breaches = (
        db.query(Complaint).filter(Complaint.is_sla_breached.is_(True)).count()
    )

    return {
        "civic_pulse": {
            "total_complaints_received": total_complaints,
            "total_complaints_resolved": resolved_complaints,
            "city_resolution_rate": f"{resolution_rate}%",
            "average_resolution_time_days": avg_resolution_days,
            "total_sla_breaches": sla_breaches,
            "top_recurring_issues": top_categories,
        }
    }
