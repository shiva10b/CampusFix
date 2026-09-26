import csv
from datetime import timedelta

from django import forms
from django.db.models import Avg, Q
from django.http import HttpResponse
from django.utils import timezone

from accounts.models import User

from .models import Complaint, ComplaintCategory, ComplaintFeedback


class ReportFilterForm(forms.Form):
    PERIOD_CHOICES = (("all", "All time"), ("30", "Last 30 days"), ("90", "Last 90 days"), ("custom", "Custom dates"))

    period = forms.ChoiceField(choices=PERIOD_CHOICES, required=False, initial="all")
    start_date = forms.DateField(required=False, widget=forms.DateInput(attrs={"type": "date"}))
    end_date = forms.DateField(required=False, widget=forms.DateInput(attrs={"type": "date"}))
    status = forms.ChoiceField(required=False)
    category = forms.ModelChoiceField(queryset=ComplaintCategory.objects.all(), required=False, empty_label="All categories")
    priority = forms.ChoiceField(required=False)
    urgency = forms.ChoiceField(required=False)
    staff = forms.ModelChoiceField(queryset=User.objects.none(), required=False, empty_label="All staff")
    q = forms.CharField(required=False, max_length=140, label="Search")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["status"].choices = (("", "All statuses"), *Complaint.Status.choices)
        self.fields["priority"].choices = (("", "All priorities"), *Complaint.Priority.choices)
        self.fields["urgency"].choices = (("", "All urgency levels"), *Complaint.Urgency.choices)
        self.fields["staff"].queryset = User.objects.filter(role=User.Role.STAFF, is_active=True).order_by("first_name", "username")
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "form-select" if isinstance(field.widget, forms.Select) else "form-control")
        self.fields["q"].widget.attrs["placeholder"] = "Ticket, title, or student"

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("period") == "custom":
            if not cleaned.get("start_date") or not cleaned.get("end_date"):
                raise forms.ValidationError("Choose both a start date and an end date for a custom report.")
            if cleaned["start_date"] > cleaned["end_date"]:
                raise forms.ValidationError("The start date cannot be after the end date.")
        return cleaned


def filtered_complaints(cleaned):
    queryset = Complaint.objects.select_related("student", "category", "location", "assigned_to", "feedback")
    period = cleaned.get("period") or "all"
    if period in {"30", "90"}:
        queryset = queryset.filter(created_at__gte=timezone.now() - timedelta(days=int(period)))
    elif period == "custom":
        queryset = queryset.filter(created_at__date__range=(cleaned["start_date"], cleaned["end_date"]))
    if cleaned.get("status"):
        queryset = queryset.filter(status=cleaned["status"])
    if cleaned.get("category"):
        queryset = queryset.filter(category=cleaned["category"])
    if cleaned.get("priority"):
        queryset = queryset.filter(priority_level=cleaned["priority"])
    if cleaned.get("urgency"):
        queryset = queryset.filter(urgency=cleaned["urgency"])
    if cleaned.get("staff"):
        queryset = queryset.filter(assigned_to=cleaned["staff"])
    if cleaned.get("q"):
        search = cleaned["q"].strip()
        queryset = queryset.filter(
            Q(ticket_number__icontains=search) | Q(title__icontains=search)
            | Q(student__username__icontains=search) | Q(student__first_name__icontains=search)
            | Q(student__last_name__icontains=search)
        )
    return queryset.order_by("-created_at", "-pk")


def report_summary(queryset):
    feedback = ComplaintFeedback.objects.filter(complaint__in=queryset)
    return {
        "total": queryset.count(),
        "awaiting": queryset.filter(status__in=(Complaint.Status.SUBMITTED, Complaint.Status.UNDER_REVIEW)).count(),
        "active": queryset.filter(status__in=(Complaint.Status.ASSIGNED, Complaint.Status.IN_PROGRESS)).count(),
        "resolved": queryset.filter(status=Complaint.Status.RESOLVED).count(),
        "closed": queryset.filter(status=Complaint.Status.CLOSED).count(),
        "rejected": queryset.filter(status=Complaint.Status.REJECTED).count(),
        "high_priority": queryset.filter(priority_level__in=(Complaint.Priority.CRITICAL, Complaint.Priority.HIGH)).count(),
        "feedback_count": feedback.count(),
        "feedback_average": feedback.aggregate(value=Avg("rating"))["value"],
    }


def staff_workload(queryset):
    rows = []
    for staff in User.objects.filter(role=User.Role.STAFF, is_active=True).order_by("first_name", "username"):
        assigned = queryset.filter(assigned_to=staff)
        rows.append({
            "staff": staff,
            "assigned": assigned.filter(status=Complaint.Status.ASSIGNED).count(),
            "in_progress": assigned.filter(status=Complaint.Status.IN_PROGRESS).count(),
            "resolved": assigned.filter(status=Complaint.Status.RESOLVED).count(),
            "active": assigned.filter(status__in=(Complaint.Status.ASSIGNED, Complaint.Status.IN_PROGRESS)).count(),
            "feedback_average": ComplaintFeedback.objects.filter(complaint__in=assigned).aggregate(value=Avg("rating"))["value"],
        })
    return rows


def csv_response(filename, headers, rows):
    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    response.write("\ufeff")
    writer = csv.writer(response)
    writer.writerow(headers)
    for row in rows:
        writer.writerow([safe_csv_cell(value) for value in row])
    return response


def safe_csv_cell(value):
    if value is None:
        return ""
    text = str(value)
    if text.startswith(("=", "+", "-", "@")):
        return "'" + text
    return text
