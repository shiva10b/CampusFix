from pathlib import Path
from uuid import uuid4

from django.conf import settings
from django.core.validators import MaxValueValidator, MinLengthValidator, MinValueValidator
from django.db import models


def evidence_upload_path(instance, filename):
    extension = Path(filename).suffix.lower()
    return f"complaint-evidence/{uuid4().hex}{extension}"


class ComplaintCategory(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("name",)
        verbose_name_plural = "complaint categories"

    def __str__(self):
        return self.name


class CampusLocation(models.Model):
    name = models.CharField(max_length=120)
    building_or_area = models.CharField(max_length=120)
    detail = models.CharField(max_length=120, blank=True, help_text="Optional room, floor, or landmark.")
    is_active = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("building_or_area", "name")
        constraints = [
            models.UniqueConstraint(fields=("name", "building_or_area"), name="unique_location_in_area")
        ]

    def __str__(self):
        return f"{self.name} — {self.building_or_area}"


class Complaint(models.Model):
    class Urgency(models.TextChoices):
        LOW = "LOW", "Low"
        MEDIUM = "MEDIUM", "Medium"
        HIGH = "HIGH", "High"

    class Status(models.TextChoices):
        SUBMITTED = "SUBMITTED", "Submitted"
        UNDER_REVIEW = "UNDER_REVIEW", "Under Review"
        ASSIGNED = "ASSIGNED", "Assigned"
        IN_PROGRESS = "IN_PROGRESS", "In Progress"
        RESOLVED = "RESOLVED", "Resolved"
        CLOSED = "CLOSED", "Closed"
        REJECTED = "REJECTED", "Rejected"

    class Priority(models.TextChoices):
        LOW = "LOW", "Low"
        MEDIUM = "MEDIUM", "Medium"
        HIGH = "HIGH", "High"
        CRITICAL = "CRITICAL", "Critical"

    ticket_number = models.CharField(max_length=32, unique=True, null=True, blank=True, editable=False)
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="complaints")
    category = models.ForeignKey(ComplaintCategory, on_delete=models.PROTECT, related_name="complaints")
    location = models.ForeignKey(CampusLocation, on_delete=models.PROTECT, related_name="complaints")
    title = models.CharField(max_length=140, validators=[MinLengthValidator(5)])
    description = models.TextField(validators=[MinLengthValidator(20)])
    urgency = models.CharField(max_length=10, choices=Urgency.choices, default=Urgency.MEDIUM, db_index=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.SUBMITTED, db_index=True, editable=False)
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="assigned_complaints",
        blank=True,
        null=True,
        limit_choices_to={"role": "STAFF", "is_active": True},
    )
    assigned_at = models.DateTimeField(blank=True, null=True)
    evidence_image = models.ImageField(upload_to=evidence_upload_path, blank=True, null=True)
    priority_score = models.PositiveSmallIntegerField(default=0, editable=False, db_index=True)
    priority_level = models.CharField(max_length=10, choices=Priority.choices, default=Priority.LOW, editable=False, db_index=True)
    priority_explanation = models.TextField(blank=True, editable=False)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=("student", "status", "-created_at"), name="complaint_student_status_idx"),
            models.Index(fields=("category", "-created_at"), name="complaint_category_idx"),
        ]

    def save(self, *args, **kwargs):
        from .priority import calculate_priority

        result = calculate_priority(self)
        self.priority_score = result.score
        self.priority_level = result.level
        self.priority_explanation = result.explanation
        update_fields = kwargs.get("update_fields")
        if update_fields and {"urgency", "category", "category_id", "evidence_image"}.intersection(update_fields):
            kwargs["update_fields"] = tuple(set(update_fields) | {"priority_score", "priority_level", "priority_explanation"})
        is_new = self.pk is None
        super().save(*args, **kwargs)
        if is_new and not self.ticket_number:
            ticket = f"CF-{self.created_at.year}-{self.pk:05d}"
            type(self).objects.filter(pk=self.pk, ticket_number__isnull=True).update(ticket_number=ticket)
            self.ticket_number = ticket
            from .notifications import notify_active_admins

            history = self.history.get(action=ComplaintHistory.Action.SUBMITTED)
            notify_active_admins(
                title="New complaint submitted",
                message=f"A new complaint {self.ticket_number} was submitted for review.",
                complaint=self,
                key=f"history:{history.pk}:new-complaint",
            )

    def __str__(self):
        return f"{self.ticket_number or 'Pending ticket'} — {self.title}"


class ComplaintHistory(models.Model):
    class Action(models.TextChoices):
        SUBMITTED = "SUBMITTED", "Submitted"
        STATUS_CHANGED = "STATUS_CHANGED", "Status Changed"
        ASSIGNED = "ASSIGNED", "Assigned"
        REASSIGNED = "REASSIGNED", "Reassigned"
        REJECTED = "REJECTED", "Rejected"
        RESOLVED = "RESOLVED", "Resolved"
        CLOSED = "CLOSED", "Closed"

    complaint = models.ForeignKey(Complaint, on_delete=models.CASCADE, related_name="history")
    action = models.CharField(max_length=20, choices=Action.choices)
    previous_status = models.CharField(max_length=20, choices=Complaint.Status.choices, blank=True)
    new_status = models.CharField(max_length=20, choices=Complaint.Status.choices, blank=True)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="complaint_history_actions",
        blank=True,
        null=True,
    )
    note = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ("created_at", "pk")
        verbose_name_plural = "complaint history"
        indexes = [models.Index(fields=("complaint", "created_at"), name="complaint_history_time_idx")]

    def __str__(self):
        return f"{self.complaint.ticket_number} — {self.get_action_display()}"


class Notification(models.Model):
    class Type(models.TextChoices):
        COMPLAINT = "COMPLAINT", "Complaint Update"
        ASSIGNMENT = "ASSIGNMENT", "Assignment"
        RESOLUTION = "RESOLUTION", "Resolution"
        FEEDBACK = "FEEDBACK", "Feedback"

    recipient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications")
    title = models.CharField(max_length=140)
    message = models.CharField(max_length=300)
    destination = models.CharField(max_length=300, blank=True)
    notification_type = models.CharField(max_length=20, choices=Type.choices)
    is_read = models.BooleanField(default=False, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    dedupe_key = models.CharField(max_length=160, unique=True, blank=True, null=True, editable=False)

    class Meta:
        ordering = ("-created_at", "-pk")
        indexes = [models.Index(fields=("recipient", "is_read", "-created_at"), name="notification_user_unread_idx")]

    def __str__(self):
        return f"{self.recipient.username} — {self.title}"


class ComplaintFeedback(models.Model):
    complaint = models.OneToOneField(Complaint, on_delete=models.CASCADE, related_name="feedback")
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="complaint_feedback")
    rating = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    comment = models.CharField(max_length=1000, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)

    def __str__(self):
        return f"{self.complaint.ticket_number} — {self.rating}/5"
