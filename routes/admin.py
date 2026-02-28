from datetime import datetime, timezone

from fastapi import APIRouter, Depends, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from database import get_db
from dependencies import require_role
from models import Complaint, User
from routes.complaints import add_activity
from schemas import APIMessage

router = APIRouter(prefix="/api/admin", tags=["Admin"])


@router.post("/scan-slas", response_model=APIMessage)
def scan_and_escalate_slas(
    db: Session = Depends(get_db), current_user: User = Depends(require_role("admin"))
):
    """
    Scans for all Pending or In Progress complaints that have passed their expected
    resolution date. If breached, auto-escalates them.
    """
    now = datetime.now(timezone.utc)

    breached_complaints = (
        db.query(Complaint)
        .filter(
            Complaint.status != "Resolved",
            Complaint.is_merged.is_(False),
            Complaint.expected_resolution_date < now,
            Complaint.is_sla_breached.is_(False),
        )
        .all()
    )

    escalated_count = 0
    for complaint in breached_complaints:
        complaint.is_sla_breached = True
        complaint.escalation_level = 1

        # Bump priority automatically if needed
        if complaint.priority < 5:
            complaint.priority += 1
            complaint.priority_label = "Escalated"

        add_activity(
            db,
            complaint_id=complaint.id,
            action="SLA Breached",
            details="System automatically escalated priority due to SLA breach.",
            previous_value="Valid",
            new_value="Breached",
            actor="system-ai",
            actor_id=None,
        )
        escalated_count += 1

    db.commit()
    return APIMessage(
        message=f"SLA Scan Complete. {escalated_count} complaints escalated."
    )


@router.get("/analytics")
def get_admin_performance_metrics(
    db: Session = Depends(get_db), current_user: User = Depends(require_role("admin"))
):
    """
    Returns performance metrics per admin (e.g. complaints resolved by admin, average SLA compliance)
    """
    import statistics

    from models import ComplaintActivity

    # Get all "Resolved" actions
    resolution_activities = (
        db.query(ComplaintActivity)
        .filter(
            ComplaintActivity.action == "Status Updated",
            ComplaintActivity.new_value == "Resolved",
        )
        .all()
    )

    admin_stats = {}
    for activity in resolution_activities:
        actor_id = activity.actor_id
        if not actor_id:
            continue

        if actor_id not in admin_stats:
            admin_stats[actor_id] = {
                "actor_name": activity.actor,
                "complaints_resolved": 0,
                "resolutions": [],
            }

        complaint = activity.complaint
        if not complaint:
            continue

        admin_stats[actor_id]["complaints_resolved"] += 1

        # calculate time taken
        time_taken = (
            activity.created_at - complaint.created_at
        ).total_seconds() / 86400
        is_breached = complaint.is_sla_breached
        admin_stats[actor_id]["resolutions"].append(
            {"duration": time_taken, "breached": is_breached}
        )

    # Aggregate
    final_analytics = []
    for aid, st in admin_stats.items():
        resolutions = st["resolutions"]
        total = len(resolutions)
        breaches = sum(1 for r in resolutions if r["breached"])
        durations = [r["duration"] for r in resolutions]

        sla_compliance_pct = (
            round(((total - breaches) / total * 100), 2) if total > 0 else 0.0
        )
        avg_time = round(statistics.mean(durations), 2) if durations else 0.0

        final_analytics.append(
            {
                "admin_id": aid,
                "admin_name": st["actor_name"],
                "total_resolved": total,
                "sla_compliance_rate": f"{sla_compliance_pct}%",
                "avg_resolution_time_days": avg_time,
            }
        )

    return {"admin_performance": final_analytics}
