import os
import uuid
import datetime
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.orm import Session
from database import get_db
from models import Incident, ReportEvidence, StatusHistory, Feedback, Notification, User, Zone, Authority, EcoTransaction
from schemas import (
    IncidentOut, IncidentDetailOut, IncidentSubmissionResponse,
    AIPredictRequest, AIPredictResponse, FeedbackCreate
)
from auth import get_current_user, get_optional_current_user, require_role
from config import UPLOAD_DIR
from ml_engine import ml_engine, haversine_distance_meters
from rule_engine import find_nearest_or_containing_zone, route_incident_to_authority
from exif_utils import extract_exif_gps

router = APIRouter(prefix="/api/reports", tags=["reports"])

@router.post("/ai-predict", response_model=AIPredictResponse)
def ai_predict_report(req: AIPredictRequest):
    """
    NLP auto-suggests category, severity, confidence, and key extracted keywords from description text.
    """
    res = ml_engine.predict(req.text)
    return res


@router.post("", response_model=IncidentSubmissionResponse)
async def create_report(
    title: str = Form(...),
    description: str = Form(...),
    category: Optional[str] = Form(None),
    severity: Optional[str] = Form(None),
    latitude: float = Form(...),
    longitude: float = Form(...),
    address: Optional[str] = Form("Tirupati, Andhra Pradesh"),
    notes: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user)
):
    """
    Submits a new environmental incident report with:
    1. Media upload & EXIF GPS extraction
    2. NLP Category and Severity suggestion
    3. Location-based duplicate detection (Haversine < 100m on open incidents)
    4. Automatic routing to authority
    5. In-app notifications
    """
    # 1. NLP fallback if not provided
    ai_prediction = ml_engine.predict(description)
    final_category = category or ai_prediction["category"]
    final_severity = severity or ai_prediction["severity"]

    # 2. File handling and EXIF extraction
    image_url = "/seed_assets/default_dumping.jpg"
    has_exif_gps = False
    exif_lat = None
    exif_lng = None

    if file:
        file_ext = os.path.splitext(file.filename)[1] or ".jpg"
        unique_filename = f"{uuid.uuid4().hex}{file_ext}"
        file_path = os.path.join(UPLOAD_DIR, unique_filename)

        file_bytes = await file.read()
        try:
            with open(file_path, "wb") as f:
                f.write(file_bytes)
            image_url = f"/uploads/{unique_filename}"
        except Exception as e:
            print(f"[reports] Warning: could not write uploaded file {file_path}: {e}")
            image_url = "/seed_assets/default_dumping.jpg"

        # Extract EXIF GPS
        gps_result = extract_exif_gps(file_bytes)
        if gps_result:
            has_exif_gps = True
            exif_lat, exif_lng = gps_result
            # If user coordinates are around default/zero, override with real EXIF GPS
            if latitude == 0.0 and longitude == 0.0:
                latitude = exif_lat
                longitude = exif_lng

    reporter_id = current_user.id if current_user else None
    reporter_name = current_user.full_name if current_user else "Citizen Reporter"
    reporter_contact = current_user.email if current_user else "Anonymous / App Guest"

    # 3. LOCATION-BASED DUPLICATE DETECTION (USP)
    # Search open incidents (submitted, assigned, in_progress) of the same category
    open_incidents = db.query(Incident).filter(
        Incident.category == final_category,
        Incident.status.in_(["submitted", "assigned", "in_progress"])
    ).all()

    matched_incident = None
    min_dist_meters = float("inf")

    for inc in open_incidents:
        if inc.latitude is None or inc.longitude is None:
            continue
        dist_m = haversine_distance_meters(latitude, longitude, inc.latitude, inc.longitude)
        if dist_m <= 100.0 and dist_m < min_dist_meters:
            min_dist_meters = dist_m
            matched_incident = inc

    if matched_incident:
        # ATTACH AS EVIDENCE TO EXISTING INCIDENT (NO DUPLICATE TICKET CREATED)
        evidence = ReportEvidence(
            incident_id=matched_incident.id,
            user_id=reporter_id,
            reporter_name=reporter_name,
            reporter_contact=reporter_contact,
            image_url=image_url,
            latitude=latitude,
            longitude=longitude,
            has_exif_gps=has_exif_gps,
            exif_lat=exif_lat,
            exif_lng=exif_lng,
            notes=notes or f"Merged duplicate submission reported ~{int(min_dist_meters)}m from initial location."
        )
        db.add(evidence)

        # Increment reporters count and bump updated_at
        matched_incident.reporters_count += 1
        matched_incident.updated_at = datetime.datetime.utcnow()

        # Add status history log
        history_entry = StatusHistory(
            incident_id=matched_incident.id,
            old_status=matched_incident.status,
            new_status=matched_incident.status,
            changed_by_user_id=reporter_id,
            changed_by_name=reporter_name,
            notes=f"New citizen evidence attached. Location matched within {int(min_dist_meters)}m. Total citizens reporting: {matched_incident.reporters_count}."
        )
        db.add(history_entry)

        # Notify assigned authority officers
        if matched_incident.assigned_authority_id:
            officers = db.query(User).filter(User.authority_id == matched_incident.assigned_authority_id).all()
            for off in officers:
                notif = Notification(
                    user_id=off.id,
                    title=f"Incident {matched_incident.incident_number} Updated (+1 Citizen)",
                    message=f"Another citizen reported {matched_incident.title}. Total reporters: {matched_incident.reporters_count}. Evidence attached.",
                    type="duplicate_merged",
                    link_id=matched_incident.id
                )
                db.add(notif)

        # Notify reporter & reward EcoCoins if logged in
        if current_user:
            current_user.eco_credits = (current_user.eco_credits or 0) + 20
            current_user.green_score = min(900, (current_user.green_score or 0) + 10)
            tx = EcoTransaction(
                user_id=current_user.id,
                amount=20,
                score_change=10,
                action_type="evidence_merged",
                title=f"Co-Report Evidence: {matched_incident.incident_number}",
                description=f"Verified duplicate violation report within {int(min_dist_meters)}m.",
                reference_id=matched_incident.incident_number
            )
            db.add(tx)

            user_notif = Notification(
                user_id=current_user.id,
                title="Duplicate Violation Merged (+20 EcoCoins)",
                message=f"Your report matched active incident {matched_incident.incident_number}. +20 EcoCredits & +10 Civic Score added to your wallet!",
                type="duplicate_merged",
                link_id=matched_incident.id
            )
            db.add(user_notif)

        db.commit()
        db.refresh(matched_incident)

        return {
            "incident": serialize_incident(matched_incident),
            "is_duplicate": True,
            "reporters_count": matched_incident.reporters_count,
            "message": f"A report for this {final_category.replace('_', ' ')} violation already exists ~{int(min_dist_meters)}m away! Your evidence has been merged into {matched_incident.incident_number}. {matched_incident.reporters_count} citizens have reported this.",
            "linked_evidence_id": evidence.id
        }

    # 4. NEW INCIDENT CREATION & AUTOMATED ROUTING
    # Find Zone
    zone = find_nearest_or_containing_zone(db, latitude, longitude)
    zone_id = zone.id if zone else None

    # Auto-Route to Authority
    authority = route_incident_to_authority(db, final_category, zone)
    authority_id = authority.id if authority else None

    # Generate incident number
    count = db.query(Incident).count() + 1
    incident_number = f"ENV-{datetime.datetime.utcnow().year}-{count:04d}"

    initial_status = "assigned" if authority_id else "submitted"

    new_incident = Incident(
        incident_number=incident_number,
        title=title,
        description=description,
        category=final_category,
        severity=final_severity,
        status=initial_status,
        reporters_count=1,
        latitude=latitude,
        longitude=longitude,
        address=address or (zone.name if zone else "Tirupati, AP"),
        zone_id=zone_id,
        assigned_authority_id=authority_id,
        primary_image_url=image_url,
        ai_predicted_category=ai_prediction["category"],
        ai_predicted_severity=ai_prediction["severity"],
        ai_confidence=ai_prediction["confidence"]
    )
    db.add(new_incident)
    db.commit()
    db.refresh(new_incident)

    # Add initial evidence
    evidence = ReportEvidence(
        incident_id=new_incident.id,
        user_id=reporter_id,
        reporter_name=reporter_name,
        reporter_contact=reporter_contact,
        image_url=image_url,
        latitude=latitude,
        longitude=longitude,
        has_exif_gps=has_exif_gps,
        exif_lat=exif_lat,
        exif_lng=exif_lng,
        notes=notes or "Initial submission with photographic evidence."
    )
    db.add(evidence)

    # Initial Status History
    routed_note = f"Incident reported by {reporter_name}. Automatically routed to {authority.name} based on category rule ({final_category})." if authority else f"Incident reported by {reporter_name}."
    history_entry = StatusHistory(
        incident_id=new_incident.id,
        old_status=None,
        new_status=initial_status,
        changed_by_user_id=reporter_id,
        changed_by_name=reporter_name,
        notes=routed_note
    )
    db.add(history_entry)

    # Notify Authority officers
    if authority_id:
        officers = db.query(User).filter(User.authority_id == authority_id).all()
        for off in officers:
            notif = Notification(
                user_id=off.id,
                title=f"New Assignment: {incident_number}",
                message=f"High priority {final_category} incident reported in {zone.name if zone else 'Tirupati'}. Assigned to your department.",
                type="new_assignment",
                link_id=new_incident.id
            )
            db.add(notif)

    # Notify reporter & reward +50 EcoCoins
    if current_user:
        current_user.eco_credits = (current_user.eco_credits or 0) + 50
        current_user.green_score = min(900, (current_user.green_score or 0) + 15)
        tx = EcoTransaction(
            user_id=current_user.id,
            amount=50,
            score_change=15,
            action_type="report_created",
            title=f"Violation Reported: {new_incident.incident_number}",
            description=f"Citizen environmental incident submitted: {new_incident.title[:45]}...",
            reference_id=new_incident.incident_number
        )
        db.add(tx)

        user_notif = Notification(
            user_id=current_user.id,
            title="Report Submitted (+50 EcoCoins Earned!)",
            message=f"Your complaint {incident_number} has been routed to {authority.name if authority else 'Local Authorities'}. +50 EcoCredits & +15 Green Score added to your profile!",
            type="status_change",
            link_id=new_incident.id
        )
        db.add(user_notif)

    db.commit()
    db.refresh(new_incident)

    return {
        "incident": serialize_incident(new_incident),
        "is_duplicate": False,
        "reporters_count": 1,
        "message": f"Report created as {new_incident.incident_number} and routed to {authority.name if authority else 'Authority'}.",
        "linked_evidence_id": evidence.id
    }


@router.get("", response_model=List[IncidentOut])
def list_reports(
    status: Optional[str] = None,
    category: Optional[str] = None,
    severity: Optional[str] = None,
    zone_id: Optional[int] = None,
    authority_id: Optional[int] = None,
    search: Optional[str] = None,
    reporter_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    query = db.query(Incident)

    if status and status != "all":
        query = query.filter(Incident.status == status)
    if category and category != "all":
        query = query.filter(Incident.category == category)
    if severity and severity != "all":
        query = query.filter(Incident.severity == severity)
    if zone_id:
        query = query.filter(Incident.zone_id == zone_id)
    if authority_id:
        query = query.filter(Incident.assigned_authority_id == authority_id)
    if search:
        search_filter = f"%{search}%"
        query = query.filter(
            (Incident.title.ilike(search_filter)) |
            (Incident.description.ilike(search_filter)) |
            (Incident.incident_number.ilike(search_filter)) |
            (Incident.address.ilike(search_filter))
        )
    if reporter_id:
        # Match incidents where user submitted any evidence
        incident_ids = [e.incident_id for e in db.query(ReportEvidence.incident_id).filter(ReportEvidence.user_id == reporter_id).all()]
        query = query.filter(Incident.id.in_(incident_ids))

    incidents = query.order_by(Incident.created_at.desc()).all()
    return [serialize_incident(inc) for inc in incidents]


@router.get("/{id}", response_model=IncidentDetailOut)
def get_report_detail(id: int, db: Session = Depends(get_db)):
    incident = db.query(Incident).filter(Incident.id == id).first()
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")

    detail = serialize_incident(incident)
    detail["evidences"] = incident.evidences
    detail["history"] = incident.history
    detail["feedbacks"] = incident.feedbacks
    return detail


@router.patch("/{id}/status")
async def update_report_status(
    id: int,
    new_status: str = Form(...),
    notes: Optional[str] = Form(None),
    after_file: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Authority dashboard action to update status:
    Submitted -> Assigned -> In Progress -> Resolved.
    When resolving, accepts resolution note and proof 'after' photo.
    """
    incident = db.query(Incident).filter(Incident.id == id).first()
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")

    old_status = incident.status
    incident.status = new_status
    incident.updated_at = datetime.datetime.utcnow()

    # Handle resolution details
    if new_status in ["resolved", "closed"]:
        incident.resolved_at = incident.resolved_at or datetime.datetime.utcnow()
        if new_status == "closed":
            incident.closed_at = incident.closed_at or datetime.datetime.utcnow()
        if notes:
            incident.resolution_notes = notes

        if after_file:
            file_ext = os.path.splitext(after_file.filename)[1] or ".jpg"
            unique_filename = f"resolved_{uuid.uuid4().hex}{file_ext}"
            file_path = os.path.join(UPLOAD_DIR, unique_filename)
            file_bytes = await after_file.read()
            try:
                with open(file_path, "wb") as f:
                    f.write(file_bytes)
                incident.after_image_url = f"/uploads/{unique_filename}"
            except Exception as e:
                print(f"[reports] Warning: could not write resolved file {file_path}: {e}")
                category_after_map = {
                    "illegal_dumping": "/seed_assets/dumping_after.jpg",
                    "water_pollution": "/seed_assets/water_after.jpg",
                    "air_pollution": "/seed_assets/air_after.jpg",
                    "deforestation": "/seed_assets/tree_after.jpg",
                    "noise": "/seed_assets/noise_after.jpg",
                    "other": "/seed_assets/dumping_after.jpg"
                }
                incident.after_image_url = category_after_map.get(incident.category, "/seed_assets/dumping_after.jpg")
        elif not incident.after_image_url:
            category_after_map = {
                "illegal_dumping": "/seed_assets/dumping_after.jpg",
                "water_pollution": "/seed_assets/water_after.jpg",
                "air_pollution": "/seed_assets/air_after.jpg",
                "deforestation": "/seed_assets/tree_after.jpg",
                "noise": "/seed_assets/noise_after.jpg",
                "other": "/seed_assets/dumping_after.jpg"
            }
            incident.after_image_url = category_after_map.get(incident.category, "/seed_assets/dumping_after.jpg")

    # Log in Status History
    history_entry = StatusHistory(
        incident_id=incident.id,
        old_status=old_status,
        new_status=new_status,
        changed_by_user_id=current_user.id,
        changed_by_name=f"{current_user.full_name} ({current_user.role.capitalize()})",
        notes=notes or f"Status changed from {old_status} to {new_status}."
    )
    db.add(history_entry)

    # Notify all citizens who reported this incident
    reporter_user_ids = {e.user_id for e in incident.evidences if e.user_id}
    for uid in reporter_user_ids:
        msg = f"Your report {incident.incident_number} has been updated to '{new_status.replace('_', ' ').capitalize()}'."
        if new_status == "resolved":
            msg = f"Authority resolved {incident.incident_number}! Please inspect the proof photo and confirm if it was actually fixed."
        notif = Notification(
            user_id=uid,
            title=f"Status Update: {incident.incident_number}",
            message=msg,
            type="status_change",
            link_id=incident.id
        )
        db.add(notif)

    db.commit()
    db.refresh(incident)
    return serialize_incident(incident)


@router.post("/{id}/feedback")
def submit_citizen_feedback(
    id: int,
    feedback_in: FeedbackCreate,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user)
):
    """
    Citizen Feedback & Transparency (USP):
    Prompt: "Was this actually fixed?"
    Yes -> Closed with proof
    No -> Reopened and escalated to CRITICAL with escalation counter incremented!
    """
    incident = db.query(Incident).filter(Incident.id == id).first()
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")

    citizen_name = current_user.full_name if current_user else "Citizen Verifier"
    user_id = current_user.id if current_user else None

    # Save Feedback
    fb = Feedback(
        incident_id=incident.id,
        user_id=user_id,
        citizen_name=citizen_name,
        was_fixed=feedback_in.was_fixed,
        rating=feedback_in.rating or (5 if feedback_in.was_fixed else 1),
        comments=feedback_in.comments
    )
    db.add(fb)

    if feedback_in.was_fixed:
        # Citizen confirms: Close with proof
        old_status = incident.status
        incident.status = "closed"
        incident.closed_at = datetime.datetime.utcnow()
        if not incident.after_image_url:
            category_after_map = {
                "illegal_dumping": "/seed_assets/dumping_after.jpg",
                "water_pollution": "/seed_assets/water_after.jpg",
                "air_pollution": "/seed_assets/air_after.jpg",
                "deforestation": "/seed_assets/tree_after.jpg",
                "noise": "/seed_assets/noise_after.jpg",
                "other": "/seed_assets/dumping_after.jpg"
            }
            incident.after_image_url = category_after_map.get(incident.category, "/seed_assets/dumping_after.jpg")

        history_entry = StatusHistory(
            incident_id=incident.id,
            old_status=old_status,
            new_status="closed",
            changed_by_user_id=user_id,
            changed_by_name=citizen_name,
            notes=f"Citizen confirmed fix with {feedback_in.rating}★ rating. Verified and officially closed."
        )
        db.add(history_entry)

        # Notify assigned authority
        if incident.assigned_authority_id:
            officers = db.query(User).filter(User.authority_id == incident.assigned_authority_id).all()
            for off in officers:
                notif = Notification(
                    user_id=off.id,
                    title=f"Citizen Verified Fix: {incident.incident_number}",
                    message=f"Citizen verified resolution with {feedback_in.rating} stars! Case officially closed.",
                    type="feedback",
                    link_id=incident.id
                )
                db.add(notif)

        # Reward EcoCoins for civic audit participation
        if current_user:
            current_user.eco_credits = (current_user.eco_credits or 0) + 30
            current_user.green_score = min(900, (current_user.green_score or 0) + 12)
            tx = EcoTransaction(
                user_id=current_user.id,
                amount=30,
                score_change=12,
                action_type="feedback_audit",
                title=f"Resolution Audit Verified: {incident.incident_number}",
                description=f"Confirmed satisfactory resolution with {feedback_in.rating}★ rating.",
                reference_id=incident.incident_number
            )
            db.add(tx)

        db.commit()
        return {"status": "closed", "message": "Thank you! Your verification has officially closed the case with proof. +30 EcoCredits added to your wallet!"}

    else:
        # CITIZEN REPORTS NOT FIXED: REOPEN & ESCALATE (USP)
        old_status = incident.status
        incident.status = "in_progress"
        incident.is_escalated = True
        incident.escalation_count += 1
        incident.severity = "critical"  # Escalated automatically to critical!

        escalation_note = f"CITIZEN VERIFICATION FAILED: 'Not actually fixed' reported by citizen. Reopened and ESCALATED to CRITICAL (Escalation Level #{incident.escalation_count}). Reason: {feedback_in.comments or 'Inadequate resolution'}."

        history_entry = StatusHistory(
            incident_id=incident.id,
            old_status=old_status,
            new_status="in_progress",
            changed_by_user_id=user_id,
            changed_by_name=citizen_name,
            notes=escalation_note
        )
        db.add(history_entry)

        # High priority notification to Authority and Admin
        recipients = db.query(User).filter(
            (User.authority_id == incident.assigned_authority_id) | (User.role == "admin")
        ).all()

        for rec in recipients:
            notif = Notification(
                user_id=rec.id,
                title=f"ESCALATION ALERT: {incident.incident_number}",
                message=f"Citizen reported problem NOT FIXED! Escalated to CRITICAL (#{incident.escalation_count}). Immediate re-inspection required.",
                type="escalation",
                link_id=incident.id
            )
            db.add(notif)

        db.commit()
        return {
            "status": "reopened_escalated",
            "escalation_count": incident.escalation_count,
            "message": f"Report has been reopened and escalated to CRITICAL priority (Level #{incident.escalation_count}). Senior authority officers have been notified for immediate action."
        }


def serialize_incident(inc: Incident) -> dict:
    category_after_map = {
        "illegal_dumping": "/seed_assets/dumping_after.jpg",
        "water_pollution": "/seed_assets/water_after.jpg",
        "air_pollution": "/seed_assets/air_after.jpg",
        "deforestation": "/seed_assets/tree_after.jpg",
        "noise": "/seed_assets/noise_after.jpg",
        "other": "/seed_assets/dumping_after.jpg"
    }
    after_url = inc.after_image_url
    if not after_url and inc.status in ["resolved", "closed"]:
        after_url = category_after_map.get(inc.category, "/seed_assets/dumping_after.jpg")

    return {
        "id": inc.id,
        "incident_number": inc.incident_number,
        "title": inc.title,
        "description": inc.description,
        "category": inc.category,
        "severity": inc.severity,
        "status": inc.status,
        "reporters_count": inc.reporters_count,
        "latitude": inc.latitude,
        "longitude": inc.longitude,
        "address": inc.address,
        "zone_id": inc.zone_id,
        "assigned_authority_id": inc.assigned_authority_id,
        "primary_image_url": inc.primary_image_url or "/seed_assets/default_dumping.jpg",
        "after_image_url": after_url,
        "resolution_notes": inc.resolution_notes or ("Official remediation completed by assigned authority." if inc.status in ["resolved", "closed"] else None),
        "resolved_at": inc.resolved_at or (inc.updated_at if inc.status in ["resolved", "closed"] else None),
        "closed_at": inc.closed_at or (inc.updated_at if inc.status == "closed" else None),
        "is_escalated": inc.is_escalated,
        "escalation_count": inc.escalation_count,
        "ai_predicted_category": inc.ai_predicted_category,
        "ai_predicted_severity": inc.ai_predicted_severity,
        "ai_confidence": inc.ai_confidence,
        "created_at": inc.created_at,
        "updated_at": inc.updated_at,
        "authority_name": inc.authority.name if inc.authority else "Pending Assignment",
        "zone_name": inc.zone.name if inc.zone else "Tirupati Region"
    }
