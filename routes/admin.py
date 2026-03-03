from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, Depends, status, HTTPException
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
    db: Session = Depends(get_db), current_user: User = Depends(require_role("officer", "sudo"))
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
    db: Session = Depends(get_db), current_user: User = Depends(require_role("officer", "sudo"))
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


@router.get("/directory")
def get_admin_directory(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("citizen", "officer", "sudo")),
):
    """
    Returns a public directory of all administrators for the 'Contact Us' page.
    Filters out sensitive information like passwords.
    """
    # Find all active users with the "officer" role
    admins = db.query(User).filter(User.role == "officer", User.is_active == True).all()

    directory = []
    for admin in admins:
        directory.append(
            {
                "id": admin.id,
                "full_name": admin.full_name,
                "email": admin.email,
                "department": getattr(admin, "department", None)
                or "General Administration",
                "ward": admin.ward or "City-Wide",
                "phone": getattr(admin, "phone", None),
                "is_suspended": getattr(admin, "is_suspended", False),
            }
        )

    return directory

def get_super_admin(current_user: User = Depends(require_role("sudo"))):
    """Dependency to ensure the user is the Sudo user (role=='sudo')."""
    return current_user

@router.get("/pending-officers")
def get_pending_officers(
    db: Session = Depends(get_db),
    admin_user: User = Depends(get_super_admin)
):
    """Fetch all officers who are waiting for approval."""
    # We serialize manually because User model isn't implicitly converted natively without UserOut schema
    officers = db.query(User).filter(User.role == "officer", User.is_active.is_(False)).all()
    return officers

@router.post("/approve-officer/{user_id}")
def approve_officer(
    user_id: int,
    db: Session = Depends(get_db),
    admin_user: User = Depends(get_super_admin)
):
    """Approve a pending officer, granting them login access."""
    officer = db.query(User).filter(User.id == user_id, User.role == "officer").first()
    
    if not officer:
        raise HTTPException(status_code=404, detail="Officer not found")
        
    if officer.is_active:
        raise HTTPException(status_code=400, detail="Officer is already approved")
        
    officer.is_active = True
    db.commit()
    
    # Simulate sending an approval email
    print(f"\n[{'='*40}]")
    print(f"📧 MOCK NOTIFICATION SYSTEM")
    print(f"To: {officer.email}")
    print(f"Subject: Application Approved - CityShakti Officer")
    print(f"Body: Hello {officer.full_name}, your application to be the {officer.department} Officer for PIN {officer.ward} has been approved by the Sudo User.")
    print(f"Link: You may now log in to the officer portal.")
    print(f"[{'='*40}]\n")
    
    return {"message": "Officer successfully approved", "officer_email": officer.email}

@router.delete("/reject-officer/{user_id}")
def reject_officer(
    user_id: int,
    db: Session = Depends(get_db),
    admin_user: User = Depends(get_super_admin)
):
    """Reject a pending officer (deletes the pending account)."""
    officer = db.query(User).filter(User.id == user_id, User.role == "officer", User.is_active == False).first()
    if not officer:
        raise HTTPException(status_code=404, detail="Pending Officer not found")
        
    db.delete(officer)
    db.commit()
    return {"message": "Pending officer request rejected and account deleted."}

@router.delete("/delete-officer/{user_id}")
def delete_officer(
    user_id: int,
    db: Session = Depends(get_db),
    admin_user: User = Depends(get_super_admin)
):
    """Delete an existing officer account."""
    officer = db.query(User).filter(User.id == user_id, User.role == "officer").first()
    if not officer:
        raise HTTPException(status_code=404, detail="Officer not found")
        
    db.delete(officer)
    db.commit()
    return {"message": "Officer account deleted from the system."}

@router.post("/suspend-officer/{user_id}")
def suspend_officer(
    user_id: int,
    db: Session = Depends(get_db),
    admin_user: User = Depends(get_super_admin)
):
    """Suspend an existing officer account."""
    officer = db.query(User).filter(User.id == user_id, User.role == "officer").first()
    if not officer:
        raise HTTPException(status_code=404, detail="Officer not found")
        
    officer.is_suspended = True
    db.commit()
    return {"message": "Officer account suspended."}

@router.post("/unsuspend-officer/{user_id}")
def unsuspend_officer(
    user_id: int,
    db: Session = Depends(get_db),
    admin_user: User = Depends(get_super_admin)
):
    """Unsuspend an existing officer account."""
    officer = db.query(User).filter(User.id == user_id, User.role == "officer").first()
    if not officer:
        raise HTTPException(status_code=404, detail="Officer not found")
        
    officer.is_suspended = False
    db.commit()
    return {"message": "Officer account unsuspended."}
