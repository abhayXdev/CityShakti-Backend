from datetime import datetime, timedelta, timezone
from typing import List, Optional

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    HTTPException,
    Query,
    Request,
    status,
)
from sqlalchemy.orm import Session

from database import SessionLocal, get_db
from dependencies import get_current_user, require_role
from models import Complaint, ComplaintActivity, ComplaintUpdate, User
from rate_limiter import limiter
from schemas import (
    APIMessage,
    ComplaintAdminUpdate,
    ComplaintAssign,
    ComplaintCreate,
    ComplaintDetailOut,
    ComplaintMergeRequest,
    ComplaintOut,
    ComplaintProgressUpdateCreate,
    ComplaintProgressUpdateOut,
    ComplaintStatusUpdate,
)
from services.ai import (
    calculate_impact_score,
    cosine_similarity,
    predict_category,
    predict_priority,
)

router = APIRouter(prefix="/api/complaints", tags=["Complaints"])
RESOLVED_STATUS = "Resolved"
DUPLICATE_THRESHOLD = 0.75


def add_activity(
    db: Session,
    complaint_id: int,
    action: str,
    details: Optional[str] = None,
    previous_value: Optional[str] = None,
    new_value: Optional[str] = None,
    actor: Optional[str] = None,
    actor_id: Optional[int] = None,
):
    db.add(
        ComplaintActivity(
            complaint_id=complaint_id,
            action=action,
            details=details,
            previous_value=previous_value,
            new_value=new_value,
            actor=actor,
            actor_id=actor_id,
        )
    )


def complaint_text(complaint: Complaint) -> str:
    return f"{complaint.title} {complaint.description}"


def merge_complaints(
    db: Session,
    source: Complaint,
    target: Complaint,
    actor: Optional[str],
    actor_id: Optional[int],
):
    if source.id == target.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot merge same complaint",
        )
    if source.is_merged:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Source complaint already merged",
        )
    if target.is_merged:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Target complaint already merged",
        )

    source.is_merged = True
    source.merged_into_id = target.id
    source.status = "Resolved"
    source.resolved_at = datetime.now(timezone.utc)

    target.reports_count += 1
    target.impact_score = calculate_impact_score(
        target.reports_count, target.priority, target.upvotes
    )

    add_activity(
        db,
        complaint_id=source.id,
        action="Complaint Merged",
        details=f"Merged into complaint #{target.id}",
        actor=actor,
        actor_id=actor_id,
    )
    add_activity(
        db,
        complaint_id=target.id,
        action="Duplicate Linked",
        details=f"Complaint #{source.id} merged as duplicate",
        actor=actor,
        actor_id=actor_id,
    )


def run_auto_duplicate_detection(complaint_id: int):
    db = SessionLocal()
    try:
        complaint = (
            db.query(Complaint)
            .filter(Complaint.id == complaint_id, Complaint.is_merged.is_(False))
            .first()
        )
        if not complaint:
            return

        candidates = (
            db.query(Complaint)
            .filter(
                Complaint.id != complaint.id,
                Complaint.ward == complaint.ward,
                Complaint.is_merged.is_(False),
            )
            .all()
        )
        base_text = complaint_text(complaint)

        for candidate in candidates:
            similarity = cosine_similarity(base_text, complaint_text(candidate))
            if similarity >= DUPLICATE_THRESHOLD:
                target = (
                    candidate
                    if candidate.created_at <= complaint.created_at
                    else complaint
                )
                source = complaint if target.id == candidate.id else candidate

                source.ai_similarity_score = round(similarity, 2)

                merge_complaints(
                    db,
                    source=source,
                    target=target,
                    actor="system-ai",
                    actor_id=None,
                )
                db.commit()
                break
    finally:
        db.close()


def categorize_and_update(complaint_id: int):
    db = SessionLocal()
    try:
        complaint = db.query(Complaint).filter(Complaint.id == complaint_id).first()
        if not complaint:
            return

        priority_score, priority_label = predict_priority(
            complaint.title, complaint.description
        )
        manual_priority = complaint.priority if complaint.priority else priority_score

        final_category = complaint.category
        if final_category == "General":
            final_category, confidence = predict_category(
                complaint.title, complaint.description
            )
            complaint.ai_confidence_score = confidence

        resolution_days = {5: 1, 4: 3, 3: 7, 2: 14}.get(manual_priority, 30)
        expected_resolution_date = datetime.now(timezone.utc) + timedelta(
            days=resolution_days
        )

        complaint.priority = manual_priority
        complaint.priority_label = priority_label
        complaint.category = final_category
        complaint.expected_resolution_date = expected_resolution_date
        complaint.impact_score = calculate_impact_score(
            complaint.reports_count, complaint.priority, complaint.upvotes
        )
        db.commit()
    finally:
        db.close()


@router.post("", response_model=ComplaintOut, status_code=status.HTTP_201_CREATED)
@limiter.limit("5/minute")
def create_complaint(
    request: Request,
    payload: ComplaintCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("citizen", "admin")),
):
    complaint = Complaint(
        title=payload.title,
        description=payload.description,
        ward=payload.ward,
        category=payload.category,
        latitude=payload.latitude,
        longitude=payload.longitude,
        priority=payload.priority,
        priority_label="Pending Evaluation",
        citizen_id=current_user.id,
        expected_resolution_date=datetime.now(timezone.utc) + timedelta(days=30),
    )
    complaint.reports_count = 1
    complaint.impact_score = calculate_impact_score(
        complaint.reports_count, complaint.priority, 0
    )

    db.add(complaint)
    db.commit()
    db.refresh(complaint)

    add_activity(
        db,
        complaint_id=complaint.id,
        action="Complaint Created",
        details="Citizen complaint registered in command center",
        actor=current_user.full_name,
        actor_id=current_user.id,
    )
    db.commit()

    background_tasks.add_task(run_auto_duplicate_detection, complaint.id)
    background_tasks.add_task(categorize_and_update, complaint.id)
    return complaint


@router.get("", response_model=List[ComplaintOut])
def list_complaints(
    status: Optional[str] = Query(default=None),
    ward: Optional[str] = Query(default=None),
    priority: Optional[int] = Query(default=None, ge=0, le=5),
    assigned_to: Optional[str] = Query(default=None),
    include_merged: bool = Query(default=False),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("citizen", "admin")),
):
    query = db.query(Complaint)

    if current_user.role == "citizen":
        query = query.filter(Complaint.citizen_id == current_user.id)

    if not include_merged:
        query = query.filter(Complaint.is_merged.is_(False))
    if status:
        query = query.filter(Complaint.status == status)
    if ward:
        query = query.filter(Complaint.ward == ward)
    if priority is not None:
        query = query.filter(Complaint.priority == priority)
    if assigned_to:
        query = query.filter(Complaint.assigned_to == assigned_to)

    return query.order_by(Complaint.created_at.desc()).all()


@router.get("/{complaint_id}", response_model=ComplaintDetailOut)
def get_complaint(
    complaint_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("citizen", "admin")),
):
    complaint = db.query(Complaint).filter(Complaint.id == complaint_id).first()
    if not complaint:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Complaint not found"
        )

    if current_user.role == "citizen" and complaint.citizen_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not allowed to view this complaint",
        )
    return complaint


@router.patch("/{complaint_id}", response_model=ComplaintOut)
def admin_update_complaint(
    complaint_id: int,
    payload: ComplaintAdminUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    complaint = db.query(Complaint).filter(Complaint.id == complaint_id).first()
    if not complaint:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Complaint not found"
        )

    if payload.title is not None:
        complaint.title = payload.title
    if payload.description is not None:
        complaint.description = payload.description
        predicted_priority, predicted_label = predict_priority(
            complaint.title, complaint.description
        )
        complaint.priority = max(complaint.priority, predicted_priority)
        complaint.priority_label = predicted_label
        complaint.impact_score = calculate_impact_score(
            complaint.reports_count, complaint.priority, complaint.upvotes
        )
    if payload.category is not None:
        complaint.category = payload.category
    if payload.ward is not None:
        complaint.ward = payload.ward

    add_activity(
        db,
        complaint_id=complaint.id,
        action="Complaint Updated",
        details=payload.note or "Complaint fields updated by admin",
        actor=payload.actor or current_user.full_name,
        actor_id=current_user.id,
    )
    db.commit()
    db.refresh(complaint)
    return complaint


@router.patch("/{complaint_id}/assign", response_model=ComplaintOut)
def assign_complaint(
    complaint_id: int,
    payload: ComplaintAssign,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    complaint = db.query(Complaint).filter(Complaint.id == complaint_id).first()
    if not complaint:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Complaint not found"
        )

    old_assignee = complaint.assigned_to

    complaint.assigned_to = payload.assigned_to
    complaint.assigned_department = payload.assigned_department
    if complaint.status == "Pending":
        complaint.status = "In Progress"

    add_activity(
        db,
        complaint_id=complaint.id,
        action="Complaint Assigned",
        details=f"Assigned to {payload.assigned_to} in {payload.assigned_department}",
        previous_value=old_assignee or "Unassigned",
        new_value=payload.assigned_to,
        actor=payload.actor or current_user.full_name,
        actor_id=current_user.id,
    )
    db.commit()
    db.refresh(complaint)
    return complaint


@router.patch("/{complaint_id}/status", response_model=ComplaintOut)
def update_complaint_status(
    complaint_id: int,
    payload: ComplaintStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    complaint = db.query(Complaint).filter(Complaint.id == complaint_id).first()
    if not complaint:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Complaint not found"
        )

    old_status = complaint.status
    complaint.status = payload.status
    complaint.resolved_at = (
        datetime.now(timezone.utc) if payload.status == RESOLVED_STATUS else None
    )

    add_activity(
        db,
        complaint_id=complaint.id,
        action="Status Updated",
        details=payload.note or f"Status changed to {payload.status}",
        previous_value=old_status,
        new_value=payload.status,
        actor=payload.actor or current_user.full_name,
        actor_id=current_user.id,
    )
    db.commit()
    db.refresh(complaint)
    return complaint


@router.post(
    "/{complaint_id}/updates",
    response_model=ComplaintProgressUpdateOut,
    status_code=status.HTTP_201_CREATED,
)
def add_progress_update(
    complaint_id: int,
    payload: ComplaintProgressUpdateCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    complaint = db.query(Complaint).filter(Complaint.id == complaint_id).first()
    if not complaint:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Complaint not found"
        )

    progress = ComplaintUpdate(
        complaint_id=complaint_id,
        phase=payload.phase,
        note=payload.note,
        photo_url=payload.photo_url,
        created_by_id=current_user.id,
    )
    db.add(progress)

    add_activity(
        db,
        complaint_id=complaint.id,
        action="Progress Update Added",
        details=f"{payload.phase.title()} update added",
        actor=current_user.full_name,
        actor_id=current_user.id,
    )
    db.commit()
    db.refresh(progress)
    return progress


@router.post("/merge", response_model=APIMessage)
def manual_merge_complaints(
    payload: ComplaintMergeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    source = (
        db.query(Complaint).filter(Complaint.id == payload.source_complaint_id).first()
    )
    target = (
        db.query(Complaint).filter(Complaint.id == payload.target_complaint_id).first()
    )
    if not source or not target:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Source or target complaint not found",
        )
    if source.ward != target.ward:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Complaints must be in same ward to merge",
        )

    merge_complaints(
        db,
        source=source,
        target=target,
        actor=payload.actor or current_user.full_name,
        actor_id=current_user.id,
    )
    db.commit()
    return APIMessage(
        message=f"Complaint #{source.id} merged into complaint #{target.id}"
    )


@router.post("/{complaint_id}/upvote", response_model=APIMessage)
@limiter.limit("10/minute")
def upvote_complaint(
    request: Request,
    complaint_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("citizen", "admin")),
):
    complaint = db.query(Complaint).filter(Complaint.id == complaint_id).first()
    if not complaint:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Complaint not found"
        )

    complaint.upvotes += 1
    complaint.impact_score += 0.5

    # Reward the citizen who reported it
    if complaint.citizen:
        complaint.citizen.points += 5

    add_activity(
        db,
        complaint_id=complaint.id,
        action="Complaint Upvoted",
        details="Community member upvoted this issue",
        actor=current_user.full_name,
        actor_id=current_user.id,
    )
    db.commit()
    return APIMessage(message="Complaint upvoted successfully")
