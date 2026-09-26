from io import StringIO

from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase, override_settings
from django.urls import reverse

from .models import CampusLocation, Complaint, ComplaintCategory, ComplaintHistory
from .services import administrator_action, staff_action


User = get_user_model()
PASSWORD = "StrongPass123!"


def user(username, role, active=True):
    return User.objects.create_user(
        username=username, email=f"{username}@example.com", password=PASSWORD,
        first_name=username.title(), last_name="Tester", department="Campus",
        role=role, is_active=active,
    )


class WorkflowBase(TestCase):
    def setUp(self):
        self.student = user("student-flow", User.Role.STUDENT)
        self.other_student = user("other-student-flow", User.Role.STUDENT)
        self.staff = user("staff-flow", User.Role.STAFF)
        self.other_staff = user("other-staff-flow", User.Role.STAFF)
        self.admin = user("admin-flow", User.Role.ADMIN)
        self.inactive_staff = user("inactive-flow", User.Role.STAFF, active=False)
        category = ComplaintCategory.objects.create(name="Electrical")
        location = CampusLocation.objects.create(name="Lab", building_or_area="Academic Block")
        self.complaint = Complaint.objects.create(
            student=self.student, category=category, location=location,
            title="Unsafe electrical socket in laboratory",
            description="The electrical socket is loose and produces sparks when equipment is connected.",
            urgency=Complaint.Urgency.HIGH,
        )


class TimelineAndWorkflowServiceTests(WorkflowBase):
    def test_creation_has_initial_submitted_event(self):
        event = self.complaint.history.get()
        self.assertEqual(event.action, ComplaintHistory.Action.SUBMITTED)
        self.assertEqual(event.new_status, Complaint.Status.SUBMITTED)
        self.assertEqual(event.actor, self.student)

    def test_admin_can_review_and_history_is_accurate(self):
        administrator_action(complaint_id=self.complaint.pk, actor=self.admin, action="review")
        self.complaint.refresh_from_db()
        event = self.complaint.history.latest("created_at")
        self.assertEqual(self.complaint.status, Complaint.Status.UNDER_REVIEW)
        self.assertEqual((event.previous_status, event.new_status), (Complaint.Status.SUBMITTED, Complaint.Status.UNDER_REVIEW))

    def test_admin_assigns_only_active_maintenance_staff(self):
        administrator_action(complaint_id=self.complaint.pk, actor=self.admin, action="assign", staff=self.staff)
        self.complaint.refresh_from_db()
        self.assertEqual(self.complaint.status, Complaint.Status.ASSIGNED)
        self.assertEqual(self.complaint.assigned_to, self.staff)
        self.assertIsNotNone(self.complaint.assigned_at)
        for invalid in (self.student, self.admin, self.inactive_staff):
            fresh = Complaint.objects.create(
                student=self.student, category=self.complaint.category, location=self.complaint.location,
                title=f"Invalid assignment target {invalid.username}",
                description="This complaint exists to verify invalid workflow assignment targets.",
            )
            with self.assertRaises(ValidationError):
                administrator_action(complaint_id=fresh.pk, actor=self.admin, action="assign", staff=invalid)

    def test_rejection_requires_meaningful_reason(self):
        with self.assertRaises(ValidationError):
            administrator_action(complaint_id=self.complaint.pk, actor=self.admin, action="reject", note="short")
        administrator_action(complaint_id=self.complaint.pk, actor=self.admin, action="reject", note="This report duplicates an existing verified ticket.")
        self.complaint.refresh_from_db()
        self.assertEqual(self.complaint.status, Complaint.Status.REJECTED)
        self.assertIn("duplicates", self.complaint.history.latest("created_at").note)

    def test_admin_can_reassign_assigned_or_in_progress_work(self):
        administrator_action(complaint_id=self.complaint.pk, actor=self.admin, action="assign", staff=self.staff)
        staff_action(complaint_id=self.complaint.pk, actor=self.staff, action="start")
        administrator_action(complaint_id=self.complaint.pk, actor=self.admin, action="reassign", staff=self.other_staff, note="Shift coverage changed.")
        self.complaint.refresh_from_db()
        self.assertEqual(self.complaint.assigned_to, self.other_staff)
        self.assertEqual(self.complaint.status, Complaint.Status.IN_PROGRESS)
        self.assertEqual(self.complaint.history.latest("created_at").action, ComplaintHistory.Action.REASSIGNED)

    def test_assigned_staff_can_start_and_resolve_with_note(self):
        administrator_action(complaint_id=self.complaint.pk, actor=self.admin, action="assign", staff=self.staff)
        staff_action(complaint_id=self.complaint.pk, actor=self.staff, action="start")
        with self.assertRaises(ValidationError):
            staff_action(complaint_id=self.complaint.pk, actor=self.staff, action="resolve", note="fixed")
        staff_action(complaint_id=self.complaint.pk, actor=self.staff, action="resolve", note="Replaced the damaged socket and completed a safety test.")
        self.complaint.refresh_from_db()
        self.assertEqual(self.complaint.status, Complaint.Status.RESOLVED)
        self.assertEqual(self.complaint.history.latest("created_at").action, ComplaintHistory.Action.RESOLVED)

    def test_staff_cannot_bypass_transition_or_work_on_another_assignment(self):
        with self.assertRaises(PermissionDenied):
            staff_action(complaint_id=self.complaint.pk, actor=self.staff, action="start")
        administrator_action(complaint_id=self.complaint.pk, actor=self.admin, action="assign", staff=self.staff)
        with self.assertRaises(PermissionDenied):
            staff_action(complaint_id=self.complaint.pk, actor=self.other_staff, action="start")
        with self.assertRaises(ValidationError):
            staff_action(complaint_id=self.complaint.pk, actor=self.staff, action="resolve", note="Long enough but wrong transition")

    def test_admin_can_close_only_resolved_complaint(self):
        with self.assertRaises(ValidationError):
            administrator_action(complaint_id=self.complaint.pk, actor=self.admin, action="close")
        administrator_action(complaint_id=self.complaint.pk, actor=self.admin, action="assign", staff=self.staff)
        staff_action(complaint_id=self.complaint.pk, actor=self.staff, action="start")
        staff_action(complaint_id=self.complaint.pk, actor=self.staff, action="resolve", note="Completed the repair and verified normal operation.")
        administrator_action(complaint_id=self.complaint.pk, actor=self.admin, action="close")
        self.complaint.refresh_from_db()
        self.assertEqual(self.complaint.status, Complaint.Status.CLOSED)

    def test_non_admin_cannot_call_administrator_workflow(self):
        with self.assertRaises(PermissionDenied):
            administrator_action(complaint_id=self.complaint.pk, actor=self.student, action="review")


class WorkflowPagePermissionTests(WorkflowBase):
    def test_administrator_queue_access(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse("complaints:admin_queue"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.complaint.ticket_number)
        for blocked in (self.student, self.staff):
            self.client.force_login(blocked)
            self.assertEqual(self.client.get(reverse("complaints:admin_queue")).status_code, 403)

    def test_admin_post_review_updates_complaint(self):
        self.client.force_login(self.admin)
        response = self.client.post(reverse("complaints:admin_detail", args=[self.complaint.ticket_number]), {"action": "review"})
        self.assertRedirects(response, reverse("complaints:admin_detail", args=[self.complaint.ticket_number]))
        self.complaint.refresh_from_db()
        self.assertEqual(self.complaint.status, Complaint.Status.UNDER_REVIEW)

    def test_manipulated_invalid_assignment_is_rejected(self):
        self.client.force_login(self.admin)
        response = self.client.post(reverse("complaints:admin_detail", args=[self.complaint.ticket_number]), {"action": "assign", "staff": self.student.pk})
        self.assertEqual(response.status_code, 200)
        self.complaint.refresh_from_db()
        self.assertEqual(self.complaint.status, Complaint.Status.SUBMITTED)

    def test_staff_queue_and_detail_show_only_assigned_work(self):
        administrator_action(complaint_id=self.complaint.pk, actor=self.admin, action="assign", staff=self.staff)
        other = Complaint.objects.create(
            student=self.other_student, category=self.complaint.category, location=self.complaint.location,
            title="Work assigned to another maintenance user",
            description="This complaint verifies that staff work queues do not expose another user's assignments.",
        )
        administrator_action(complaint_id=other.pk, actor=self.admin, action="assign", staff=self.other_staff)
        self.client.force_login(self.staff)
        queue = self.client.get(reverse("complaints:staff_queue"))
        self.assertContains(queue, self.complaint.ticket_number)
        self.assertNotContains(queue, other.ticket_number)
        self.assertEqual(self.client.get(reverse("complaints:staff_detail", args=[self.complaint.ticket_number])).status_code, 200)
        self.assertEqual(self.client.get(reverse("complaints:staff_detail", args=[other.ticket_number])).status_code, 403)

    def test_student_sees_own_timeline_but_not_another_ticket(self):
        administrator_action(complaint_id=self.complaint.pk, actor=self.admin, action="review")
        other = Complaint.objects.create(
            student=self.other_student, category=self.complaint.category, location=self.complaint.location,
            title="A private ticket for the other student",
            description="This is long enough to be a valid complaint that belongs to another student.",
        )
        self.client.force_login(self.student)
        own = self.client.get(reverse("complaints:detail", args=[self.complaint.ticket_number]))
        self.assertContains(own, "Under Review")
        self.assertContains(own, "Ticket timeline")
        self.assertEqual(self.client.get(reverse("complaints:detail", args=[other.ticket_number])).status_code, 403)


class DashboardWorkflowCountTests(WorkflowBase):
    def setUp(self):
        super().setUp()
        administrator_action(complaint_id=self.complaint.pk, actor=self.admin, action="assign", staff=self.staff)
        self.in_progress = Complaint.objects.create(
            student=self.student, category=self.complaint.category, location=self.complaint.location,
            title="Second complaint currently in progress",
            description="This complaint provides a second real workflow state for dashboard counts.",
        )
        administrator_action(complaint_id=self.in_progress.pk, actor=self.admin, action="assign", staff=self.staff)
        staff_action(complaint_id=self.in_progress.pk, actor=self.staff, action="start")

    def test_all_role_dashboards_use_real_workflow_counts(self):
        self.client.force_login(self.student)
        student_page = self.client.get(reverse("accounts:student_dashboard"))
        self.assertEqual(student_page.context["total_complaints"], 2)
        self.assertEqual(student_page.context["active_complaints"], 2)
        self.client.force_login(self.staff)
        staff_page = self.client.get(reverse("accounts:staff_dashboard"))
        self.assertEqual(staff_page.context["assigned_work"], 1)
        self.assertEqual(staff_page.context["in_progress_work"], 1)
        self.client.force_login(self.admin)
        admin_page = self.client.get(reverse("accounts:admin_dashboard"))
        self.assertEqual(admin_page.context["complaint_counts"]["total"], 2)
        self.assertEqual(admin_page.context["complaint_counts"]["active_work"], 2)


class DemoWorkflowCommandTests(TestCase):
    @override_settings(DEBUG=True)
    def test_demo_workflow_is_idempotent(self):
        call_command("create_demo_workflow", stdout=StringIO())
        first_history_count = ComplaintHistory.objects.count()
        call_command("create_demo_workflow", stdout=StringIO())
        self.assertEqual(Complaint.objects.filter(student__username="student_demo").count(), 3)
        self.assertEqual(ComplaintHistory.objects.count(), first_history_count)
        self.assertSetEqual(
            set(Complaint.objects.filter(student__username="student_demo").values_list("status", flat=True)),
            {Complaint.Status.SUBMITTED, Complaint.Status.ASSIGNED, Complaint.Status.IN_PROGRESS},
        )

    @override_settings(DEBUG=False)
    def test_demo_workflow_is_blocked_without_debug(self):
        with self.assertRaises(CommandError):
            call_command("create_demo_workflow")
