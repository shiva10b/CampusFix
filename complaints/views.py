from datetime import timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db.models import Avg, Count, Q
from django.http import HttpResponseNotAllowed
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone

from accounts.decorators import role_required
from accounts.models import User

from .decorators import student_required
from .forms import ComplaintForm
from .models import Complaint, ComplaintCategory, ComplaintFeedback, Notification
from .notifications import notify_active_admins
from .reports import ReportFilterForm, csv_response, filtered_complaints, report_summary, staff_workload
from .services import administrator_action, staff_action
from .workflow_forms import AdministratorActionForm, ComplaintFeedbackForm, StaffActionForm


@student_required
def complaint_create(request):
    form = ComplaintForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        complaint = form.save(commit=False)
        complaint.student = request.user
        complaint.status = Complaint.Status.SUBMITTED
        complaint.save()
        messages.success(request, f"Your complaint was submitted successfully. Ticket: {complaint.ticket_number}")
        return redirect("complaints:detail", ticket_number=complaint.ticket_number)
    return render(request, "complaints/create.html", {"form": form})


@student_required
def complaint_list(request):
    complaints = Complaint.objects.filter(student=request.user).select_related("category", "location")
    search = request.GET.get("q", "").strip()
    status = request.GET.get("status", "").strip()
    category = request.GET.get("category", "").strip()
    if search:
        complaints = complaints.filter(Q(ticket_number__icontains=search) | Q(title__icontains=search))
    if status in Complaint.Status.values:
        complaints = complaints.filter(status=status)
    if category.isdigit():
        complaints = complaints.filter(category_id=int(category))
    page_obj = Paginator(complaints, 10).get_page(request.GET.get("page"))
    context = {
        "page_obj": page_obj,
        "search": search,
        "selected_status": status,
        "selected_category": category,
        "status_choices": Complaint.Status.choices,
        "categories": ComplaintCategory.objects.filter(complaints__student=request.user).distinct(),
    }
    return render(request, "complaints/list.html", context)


@student_required
def complaint_detail(request, ticket_number):
    complaint = get_object_or_404(
        Complaint.objects.select_related("student", "category", "location"),
        ticket_number=ticket_number,
    )
    if complaint.student_id != request.user.id:
        return render(request, "403.html", status=403)
    return render(request, "complaints/detail.html", {"complaint": complaint, "timeline": complaint.history.select_related("actor")})


@role_required(User.Role.ADMIN)
def administrator_queue(request):
    complaints = Complaint.objects.select_related("student", "category", "location", "assigned_to")
    search = request.GET.get("q", "").strip()
    status = request.GET.get("status", "").strip()
    category = request.GET.get("category", "").strip()
    urgency = request.GET.get("urgency", "").strip()
    staff = request.GET.get("staff", "").strip()
    ordering = request.GET.get("order", "newest")
    priority = request.GET.get("priority", "").strip()
    if search:
        complaints = complaints.filter(
            Q(ticket_number__icontains=search) | Q(title__icontains=search)
            | Q(student__username__icontains=search) | Q(student__first_name__icontains=search)
            | Q(student__last_name__icontains=search)
        )
    if status in Complaint.Status.values:
        complaints = complaints.filter(status=status)
    if category.isdigit():
        complaints = complaints.filter(category_id=int(category))
    if urgency in Complaint.Urgency.values:
        complaints = complaints.filter(urgency=urgency)
    if priority in Complaint.Priority.values:
        complaints = complaints.filter(priority_level=priority)
    if staff == "unassigned":
        complaints = complaints.filter(assigned_to__isnull=True)
    elif staff.isdigit():
        complaints = complaints.filter(assigned_to_id=int(staff))
    order_map = {"oldest": "created_at", "priority": "-priority_score", "newest": "-created_at"}
    complaints = complaints.order_by(order_map.get(ordering, "-created_at"), "-created_at")
    context = {
        "page_obj": Paginator(complaints, 15).get_page(request.GET.get("page")),
        "categories": ComplaintCategory.objects.all(),
        "staff_users": User.objects.filter(role=User.Role.STAFF, is_active=True),
        "status_choices": Complaint.Status.choices,
        "urgency_choices": Complaint.Urgency.choices,
        "priority_choices": Complaint.Priority.choices,
        "filters": {"q": search, "status": status, "category": category, "urgency": urgency, "priority": priority, "staff": staff, "order": ordering},
    }
    return render(request, "complaints/admin_queue.html", context)


@role_required(User.Role.ADMIN)
def administrator_detail(request, ticket_number):
    complaint = get_object_or_404(Complaint.objects.select_related("student", "category", "location", "assigned_to"), ticket_number=ticket_number)
    form = AdministratorActionForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            administrator_action(
                complaint_id=complaint.pk, actor=request.user,
                action=form.cleaned_data["action"], staff=form.cleaned_data.get("staff"),
                note=form.cleaned_data.get("note", ""),
            )
        except ValidationError as exc:
            form.add_error(None, exc.messages[0])
        else:
            messages.success(request, "Complaint workflow updated successfully.")
            return redirect("complaints:admin_detail", ticket_number=ticket_number)
    return render(request, "complaints/admin_detail.html", {"complaint": complaint, "form": form, "timeline": complaint.history.select_related("actor")})


@role_required(User.Role.STAFF)
def staff_queue(request):
    complaints = Complaint.objects.filter(assigned_to=request.user).select_related("student", "category", "location")
    search = request.GET.get("q", "").strip()
    status = request.GET.get("status", "").strip()
    priority = request.GET.get("priority", "").strip()
    ordering = request.GET.get("order", "priority")
    if search:
        complaints = complaints.filter(Q(ticket_number__icontains=search) | Q(title__icontains=search))
    if status in Complaint.Status.values:
        complaints = complaints.filter(status=status)
    if priority in Complaint.Priority.values:
        complaints = complaints.filter(priority_level=priority)
    complaints = complaints.order_by("-priority_score", "-assigned_at") if ordering == "priority" else complaints.order_by("-assigned_at")
    context = {
        "page_obj": Paginator(complaints, 10).get_page(request.GET.get("page")),
        "status_choices": Complaint.Status.choices,
        "search": search,
        "selected_status": status,
        "selected_priority": priority,
        "priority_choices": Complaint.Priority.choices,
        "ordering": ordering,
    }
    return render(request, "complaints/staff_queue.html", context)


@role_required(User.Role.STAFF)
def staff_detail(request, ticket_number):
    complaint = get_object_or_404(Complaint.objects.select_related("student", "category", "location", "assigned_to"), ticket_number=ticket_number)
    if complaint.assigned_to_id != request.user.id:
        return render(request, "403.html", status=403)
    form = StaffActionForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            staff_action(
                complaint_id=complaint.pk, actor=request.user,
                action=form.cleaned_data["action"], note=form.cleaned_data.get("note", ""),
            )
        except ValidationError as exc:
            form.add_error(None, exc.messages[0])
        else:
            messages.success(request, "Complaint status updated successfully.")
            return redirect("complaints:staff_detail", ticket_number=ticket_number)
    return render(request, "complaints/staff_detail.html", {"complaint": complaint, "form": form, "timeline": complaint.history.select_related("actor")})


@student_required
def submit_feedback(request, ticket_number):
    complaint = get_object_or_404(Complaint, ticket_number=ticket_number)
    if complaint.student_id != request.user.id:
        return render(request, "403.html", status=403)
    if complaint.status not in {Complaint.Status.RESOLVED, Complaint.Status.CLOSED}:
        return render(request, "403.html", status=403)
    if hasattr(complaint, "feedback"):
        messages.info(request, "Feedback has already been submitted for this complaint.")
        return redirect("complaints:detail", ticket_number=ticket_number)
    form = ComplaintFeedbackForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        feedback = form.save(commit=False)
        feedback.complaint = complaint
        feedback.student = request.user
        feedback.save()
        notify_active_admins(
            title="Student feedback received",
            message=f"A {feedback.rating}/5 rating was submitted for {complaint.ticket_number}.",
            complaint=complaint,
            key=f"feedback:{feedback.pk}",
            notification_type=Notification.Type.FEEDBACK,
        )
        messages.success(request, "Thank you. Your feedback has been submitted.")
        return redirect("complaints:detail", ticket_number=ticket_number)
    return render(request, "complaints/feedback.html", {"complaint": complaint, "form": form})


@login_required
def notification_center(request):
    page_obj = Paginator(request.user.notifications.all(), 20).get_page(request.GET.get("page"))
    return render(request, "complaints/notifications.html", {"page_obj": page_obj})


@login_required
def notification_open(request, notification_id):
    notification = get_object_or_404(Notification, pk=notification_id)
    if notification.recipient_id != request.user.id:
        return render(request, "403.html", status=403)
    if not notification.is_read:
        notification.is_read = True
        notification.save(update_fields=("is_read",))
    destination = notification.destination
    if not destination.startswith("/") or destination.startswith("//"):
        destination = reverse("complaints:notifications")
    return redirect(destination)


@login_required
def notifications_mark_all_read(request):
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    request.user.notifications.filter(is_read=False).update(is_read=True)
    messages.success(request, "All notifications marked as read.")
    return redirect("complaints:notifications")


@role_required(User.Role.ADMIN)
def analytics(request):
    period = request.GET.get("period", "all")
    complaints = Complaint.objects.all()
    feedback = ComplaintFeedback.objects.all()
    if period in {"30", "90"}:
        since = timezone.now() - timedelta(days=int(period))
        complaints = complaints.filter(created_at__gte=since)
        feedback = feedback.filter(created_at__gte=since)
    status_data = list(complaints.values("status").annotate(total=Count("id")).order_by("status"))
    category_data = list(complaints.values("category__name").annotate(total=Count("id")).order_by("category__name"))
    priority_data = list(complaints.values("priority_level").annotate(total=Count("id")).order_by("priority_level"))
    urgency_data = list(complaints.values("urgency").annotate(total=Count("id")).order_by("urgency"))
    metrics = {
        "total": complaints.count(),
        "awaiting": complaints.filter(status__in=(Complaint.Status.SUBMITTED, Complaint.Status.UNDER_REVIEW)).count(),
        "active": complaints.filter(status__in=(Complaint.Status.ASSIGNED, Complaint.Status.IN_PROGRESS)).count(),
        "resolved_closed": complaints.filter(status__in=(Complaint.Status.RESOLVED, Complaint.Status.CLOSED)).count(),
        "rejected": complaints.filter(status=Complaint.Status.REJECTED).count(),
        "feedback_total": feedback.count(),
        "feedback_average": feedback.aggregate(value=Avg("rating"))["value"],
    }
    return render(request, "complaints/analytics.html", {"metrics": metrics, "status_data": status_data, "category_data": category_data, "priority_data": priority_data, "urgency_data": urgency_data, "period": period})


def _report_data(request):
    # Bind even an empty query string so the default all-time report is valid.
    form = ReportFilterForm(request.GET)
    valid = form.is_valid()
    complaints = filtered_complaints(form.cleaned_data) if valid else Complaint.objects.none()
    return form, complaints, valid


@role_required(User.Role.ADMIN)
def reports(request):
    form, complaints, valid = _report_data(request)
    query = request.GET.copy()
    query.pop("page", None)
    context = {
        "form": form,
        "summary": report_summary(complaints),
        "page_obj": Paginator(complaints, 20).get_page(request.GET.get("page")),
        "workload": staff_workload(complaints),
        "feedback_rows": ComplaintFeedback.objects.filter(complaint__in=complaints).select_related("complaint", "student")[:100],
        "filter_query": query.urlencode(),
        "filters_valid": valid,
    }
    return render(request, "complaints/reports.html", context)


@role_required(User.Role.ADMIN)
def report_print(request):
    form, complaints, valid = _report_data(request)
    return render(request, "complaints/report_print.html", {
        "form": form, "complaints": complaints[:500], "summary": report_summary(complaints),
        "generated_at": timezone.localtime(), "filters_valid": valid,
    })


@role_required(User.Role.ADMIN)
def complaint_csv(request):
    form, complaints, valid = _report_data(request)
    if not valid:
        return reports(request)
    rows = ((c.ticket_number, c.title, c.student.display_name, c.category.name, c.location.name,
             c.get_urgency_display(), c.get_priority_level_display(), c.priority_score,
             c.get_status_display(), c.assigned_to.display_name if c.assigned_to else "",
             timezone.localtime(c.created_at).isoformat(), timezone.localtime(c.updated_at).isoformat(),
             c.feedback.rating if hasattr(c, "feedback") else "") for c in complaints)
    return csv_response("campusfix-complaints.csv", ("Ticket", "Title", "Student", "Category", "Location", "Urgency", "Priority", "Score", "Status", "Assigned staff", "Created", "Updated", "Feedback rating"), rows)


@role_required(User.Role.ADMIN)
def workload_csv(request):
    form, complaints, valid = _report_data(request)
    if not valid:
        return reports(request)
    rows = ((r["staff"].display_name, r["staff"].employee_id, r["assigned"], r["in_progress"], r["resolved"], r["active"], r["feedback_average"]) for r in staff_workload(complaints))
    return csv_response("campusfix-staff-workload.csv", ("Staff", "Employee ID", "Assigned", "In Progress", "Resolved", "Total Active", "Average Feedback"), rows)


@role_required(User.Role.ADMIN)
def feedback_csv(request):
    form, complaints, valid = _report_data(request)
    if not valid:
        return reports(request)
    feedback = ComplaintFeedback.objects.filter(complaint__in=complaints).select_related("complaint", "student")
    rows = ((f.complaint.ticket_number, f.student.display_name, f.rating, f.comment, timezone.localtime(f.created_at).isoformat()) for f in feedback)
    return csv_response("campusfix-feedback.csv", ("Ticket", "Student", "Rating", "Comment", "Submitted"), rows)
