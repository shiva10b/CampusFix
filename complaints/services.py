from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone

from accounts.models import User

from .models import Complaint, ComplaintHistory
from .notifications import notify_active_admins, notify_staff, notify_student


MIN_NOTE_LENGTH = 10


def _require_admin(actor):
    if not actor.is_authenticated or actor.role != User.Role.ADMIN:
        raise PermissionDenied


def _require_assigned_staff(actor, complaint):
    if not actor.is_authenticated or actor.role != User.Role.STAFF or complaint.assigned_to_id != actor.id:
        raise PermissionDenied


def _meaningful_note(note, label):
    cleaned = (note or "").strip()
    if len(cleaned) < MIN_NOTE_LENGTH:
        raise ValidationError(f"{label} must contain at least {MIN_NOTE_LENGTH} characters.")
    return cleaned


def _history(complaint, action, previous, new, actor, note=""):
    return ComplaintHistory.objects.create(
        complaint=complaint,
        action=action,
        previous_status=previous,
        new_status=new,
        actor=actor,
        note=note.strip(),
    )


@transaction.atomic
def administrator_action(*, complaint_id, actor, action, staff=None, note=""):
    _require_admin(actor)
    complaint = Complaint.objects.select_for_update().get(pk=complaint_id)
    previous = complaint.status

    if action == "review" and previous == Complaint.Status.SUBMITTED:
        complaint.status = Complaint.Status.UNDER_REVIEW
        history_action = ComplaintHistory.Action.STATUS_CHANGED
    elif action == "reject" and previous in {Complaint.Status.SUBMITTED, Complaint.Status.UNDER_REVIEW}:
        note = _meaningful_note(note, "Rejection reason")
        complaint.status = Complaint.Status.REJECTED
        history_action = ComplaintHistory.Action.REJECTED
    elif action == "close" and previous == Complaint.Status.RESOLVED:
        complaint.status = Complaint.Status.CLOSED
        history_action = ComplaintHistory.Action.CLOSED
    elif action in {"assign", "reassign"}:
        if not staff or staff.role != User.Role.STAFF or not staff.is_active:
            raise ValidationError("Choose an active Maintenance Staff account.")
        if action == "assign" and previous not in {Complaint.Status.SUBMITTED, Complaint.Status.UNDER_REVIEW}:
            raise ValidationError("This complaint cannot be assigned from its current status.")
        if action == "reassign" and previous not in {Complaint.Status.ASSIGNED, Complaint.Status.IN_PROGRESS}:
            raise ValidationError("Only Assigned or In Progress complaints can be reassigned.")
        if action == "reassign" and complaint.assigned_to_id == staff.id:
            raise ValidationError("Choose a different Maintenance Staff member for reassignment.")
        complaint.assigned_to = staff
        complaint.assigned_at = timezone.now()
        if action == "assign":
            complaint.status = Complaint.Status.ASSIGNED
            history_action = ComplaintHistory.Action.ASSIGNED
        else:
            history_action = ComplaintHistory.Action.REASSIGNED
    else:
        raise ValidationError("That workflow action is not permitted for the current status.")

    complaint.save(update_fields=("status", "assigned_to", "assigned_at", "updated_at"))
    assignment_note = note
    if action in {"assign", "reassign"}:
        assignment_note = f"Assigned to {staff.display_name}." + (f" {note.strip()}" if note.strip() else "")
    history = _history(complaint, history_action, previous, complaint.status, actor, assignment_note)
    key = f"history:{history.pk}"
    if action == "review":
        notify_student(complaint=complaint, title="Complaint under review", message=f"Your complaint {complaint.ticket_number} is now under review.", key=key)
    elif action in {"assign", "reassign"}:
        notify_staff(complaint=complaint, title="Maintenance work assigned", message=f"Complaint {complaint.ticket_number} has been assigned to you.", key=key)
        notify_student(complaint=complaint, title="Maintenance team assigned", message=f"A maintenance team member has been assigned to {complaint.ticket_number}.", key=key)
    elif action == "reject":
        notify_student(complaint=complaint, title="Complaint rejected", message=f"Complaint {complaint.ticket_number} was rejected: {note}", key=key)
    elif action == "close":
        notify_student(complaint=complaint, title="Complaint closed", message=f"Complaint {complaint.ticket_number} has been closed.", key=key)
    return complaint


@transaction.atomic
def staff_action(*, complaint_id, actor, action, note=""):
    complaint = Complaint.objects.select_for_update().get(pk=complaint_id)
    _require_assigned_staff(actor, complaint)
    previous = complaint.status
    if action == "start" and previous == Complaint.Status.ASSIGNED:
        complaint.status = Complaint.Status.IN_PROGRESS
        history_action = ComplaintHistory.Action.STATUS_CHANGED
    elif action == "resolve" and previous == Complaint.Status.IN_PROGRESS:
        note = _meaningful_note(note, "Resolution note")
        complaint.status = Complaint.Status.RESOLVED
        history_action = ComplaintHistory.Action.RESOLVED
    else:
        raise ValidationError("That workflow action is not permitted for the current status.")
    complaint.save(update_fields=("status", "updated_at"))
    history = _history(complaint, history_action, previous, complaint.status, actor, note)
    key = f"history:{history.pk}"
    if action == "start":
        notify_student(complaint=complaint, title="Work started", message=f"Maintenance work has started on {complaint.ticket_number}.", key=key)
    else:
        notify_student(complaint=complaint, title="Complaint resolved", message=f"Complaint {complaint.ticket_number} has been marked resolved.", key=key, notification_type="RESOLUTION")
        notify_active_admins(title="Complaint resolved", message=f"Complaint {complaint.ticket_number} is ready for closure review.", complaint=complaint, key=key, notification_type="RESOLUTION")
    return complaint
