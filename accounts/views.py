from django.contrib import messages
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView, PasswordChangeView
from django.db.models import Avg, Count, Q
from django.http import HttpResponseNotAllowed
from django.shortcuts import redirect, render
from django.urls import reverse, reverse_lazy
from django.utils.http import url_has_allowed_host_and_scheme

from .decorators import management_roles
from .decorators import role_required
from .forms import (
    CampusFixAuthenticationForm,
    ProfileUpdateForm,
    StudentRegistrationForm,
    StyledPasswordChangeForm,
)
from .models import User


def _safe_next_url(request):
    target = request.POST.get("next") or request.GET.get("next")
    if target and url_has_allowed_host_and_scheme(
        target, allowed_hosts={request.get_host()}, require_https=request.is_secure()
    ):
        return target
    return None


def register(request):
    if request.user.is_authenticated:
        return redirect("accounts:dashboard")
    form = StudentRegistrationForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Your student account has been created. You can now log in.")
        return redirect("accounts:login")
    return render(request, "accounts/register.html", {"form": form})


class CampusFixLoginView(LoginView):
    template_name = "accounts/login.html"
    authentication_form = CampusFixAuthenticationForm
    redirect_authenticated_user = True

    def form_valid(self, form):
        messages.success(self.request, f"Welcome back, {form.get_user().display_name}.")
        return super().form_valid(form)

    def get_success_url(self):
        return _safe_next_url(self.request) or reverse("accounts:dashboard")


def logout_view(request):
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    logout(request)
    messages.success(request, "You have been logged out safely.")
    return redirect("core:landing")


@login_required
def dashboard_router(request):
    destinations = {
        User.Role.STUDENT: "accounts:student_dashboard",
        User.Role.STAFF: "accounts:staff_dashboard",
        User.Role.COORDINATOR: "accounts:admin_dashboard",
        User.Role.DEAN: "accounts:admin_dashboard",
        User.Role.ADMIN: "accounts:admin_dashboard",
        User.Role.SUPERADMIN: "accounts:admin_dashboard",
    }
    return redirect(destinations[request.user.role])


@role_required(User.Role.STUDENT)
def student_dashboard(request):
    from complaints.models import Complaint

    complaints = Complaint.objects.filter(student=request.user)
    active_statuses = (
        Complaint.Status.SUBMITTED, Complaint.Status.UNDER_REVIEW,
        Complaint.Status.ASSIGNED, Complaint.Status.IN_PROGRESS,
    )
    resolved_statuses = (Complaint.Status.RESOLVED, Complaint.Status.CLOSED)
    context = {
        "total_complaints": complaints.count(),
        "active_complaints": complaints.filter(status__in=active_statuses).count(),
        "resolved_complaints": complaints.filter(status__in=resolved_statuses).count(),
        "recent_complaints": complaints.select_related("category", "location")[:5],
    }
    return render(request, "accounts/dashboard_student.html", context)


@role_required(User.Role.STAFF)
def staff_dashboard(request):
    from complaints.models import Complaint

    work = Complaint.objects.filter(assigned_to=request.user)
    context = {
        "assigned_work": work.filter(status=Complaint.Status.ASSIGNED).count(),
        "in_progress_work": work.filter(status=Complaint.Status.IN_PROGRESS).count(),
        "resolved_work": work.filter(status__in=(Complaint.Status.RESOLVED, Complaint.Status.CLOSED)).count(),
        "recent_work": work.select_related("student", "category", "location").order_by("-priority_score", "-assigned_at")[:5],
    }
    return render(request, "accounts/dashboard_staff.html", context)


@role_required(*management_roles())
def admin_dashboard(request):
    from complaints.models import Complaint

    counts = User.objects.aggregate(
        total=Count("id"),
        students=Count("id", filter=Q(role=User.Role.STUDENT)),
        staff=Count("id", filter=Q(role=User.Role.STAFF)),
        administrators=Count("id", filter=Q(role=User.Role.ADMIN)),
    )
    complaint_counts = Complaint.objects.aggregate(
        total=Count("id"),
        awaiting=Count("id", filter=Q(status__in=(Complaint.Status.SUBMITTED, Complaint.Status.UNDER_REVIEW))),
        active_work=Count("id", filter=Q(status__in=(Complaint.Status.ASSIGNED, Complaint.Status.IN_PROGRESS))),
        resolved=Count("id", filter=Q(status=Complaint.Status.RESOLVED)),
        closed=Count("id", filter=Q(status=Complaint.Status.CLOSED)),
        rejected=Count("id", filter=Q(status=Complaint.Status.REJECTED)),
    )
    if request.user.role == User.Role.COORDINATOR:
        complaints = Complaint.objects.filter(student__department__iexact=request.user.department)
        complaint_counts = {
            "total": complaints.count(),
            "awaiting": complaints.filter(status__in=("SUBMITTED", "UNDER_REVIEW")).count(),
            "active_work": complaints.filter(status__in=("ASSIGNED", "IN_PROGRESS")).count(),
            "resolved": complaints.filter(status="RESOLVED").count(),
            "closed": complaints.filter(status="CLOSED").count(),
            "rejected": complaints.filter(status="REJECTED").count(),
        }
    priority_summary = Complaint.objects.aggregate(
        low=Count("id", filter=Q(priority_level=Complaint.Priority.LOW)),
        medium=Count("id", filter=Q(priority_level=Complaint.Priority.MEDIUM)),
        high=Count("id", filter=Q(priority_level=Complaint.Priority.HIGH)),
        critical=Count("id", filter=Q(priority_level=Complaint.Priority.CRITICAL)),
    )
    from complaints.models import ComplaintFeedback
    feedback_summary = ComplaintFeedback.objects.aggregate(total=Count("id"), average=Avg("rating"))
    return render(request, "accounts/dashboard_admin.html", {"counts": counts, "complaint_counts": complaint_counts, "priority_summary": priority_summary, "feedback_summary": feedback_summary})



@login_required
def profile(request):
    form = ProfileUpdateForm(request.POST or None, instance=request.user)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Your profile has been updated.")
        return redirect("accounts:profile")
    return render(request, "accounts/profile.html", {"form": form})


class CampusFixPasswordChangeView(PasswordChangeView):
    template_name = "accounts/password_change.html"
    form_class = StyledPasswordChangeForm
    success_url = reverse_lazy("accounts:profile")

    def form_valid(self, form):
        messages.success(self.request, "Your password has been changed securely.")
        return super().form_valid(form)
