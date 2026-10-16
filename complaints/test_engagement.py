from io import BytesIO
from tempfile import TemporaryDirectory

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase
from django.test import override_settings
from django.urls import reverse
from PIL import Image

from .models import CampusLocation, Complaint, ComplaintCategory, ComplaintFeedback, Notification
from .notifications import notify_once
from .priority import CATEGORY_POINTS, URGENCY_POINTS
from .services import administrator_action, staff_action

User = get_user_model()
PASSWORD = "StrongPass123!"


def make_user(username, role):
    return User.objects.create_user(username=username, email=f"{username}@example.com", password=PASSWORD, department="Campus", role=role)


class EngagementBase(TestCase):
    def setUp(self):
        self.student = make_user("engagement-student", User.Role.STUDENT)
        self.other_student = make_user("engagement-other", User.Role.STUDENT)
        self.staff = make_user("engagement-staff", User.Role.STAFF)
        self.admin = make_user("engagement-admin", User.Role.ADMIN)
        self.admin2 = make_user("engagement-admin2", User.Role.ADMIN)
        self.location = CampusLocation.objects.create(name="Library", building_or_area="Learning Block")
        self.category = ComplaintCategory.objects.create(name="Electrical")

    def complaint(self, **kwargs):
        values = {"student": self.student, "category": self.category, "location": self.location, "title": "Electrical maintenance issue requiring attention", "description": "A detailed description of the campus issue requiring maintenance attention.", "urgency": Complaint.Urgency.MEDIUM}
        values.update(kwargs)
        return Complaint.objects.create(**values)


class PriorityTests(EngagementBase):
    def test_every_urgency_category_combination(self):
        for category_name, category_points in CATEGORY_POINTS.items():
            category = ComplaintCategory.objects.create(name=category_name) if category_name != "Electrical" else self.category
            for urgency, urgency_points in URGENCY_POINTS.items():
                complaint = self.complaint(category=category, urgency=urgency, title=f"{category_name} {urgency} issue")
                expected = urgency_points + category_points
                self.assertEqual(complaint.priority_score, expected)
                expected_level = "CRITICAL" if expected >= 70 else "HIGH" if expected >= 50 else "MEDIUM" if expected >= 30 else "LOW"
                self.assertEqual(complaint.priority_level, expected_level)

    def test_evidence_adds_five_points(self):
        content = BytesIO(); Image.new("RGB", (5, 5), "red").save(content, "PNG")
        image = SimpleUploadedFile("proof.png", content.getvalue(), content_type="image/png")
        with TemporaryDirectory() as media_root, override_settings(MEDIA_ROOT=media_root):
            complaint = self.complaint(evidence_image=image)
        self.assertEqual(complaint.priority_score, 60)
        self.assertIn("5 evidence points", complaint.priority_explanation)

    def test_student_cannot_forge_priority(self):
        self.client.force_login(self.student)
        response = self.client.post(reverse("complaints:create"), {"category": self.category.pk, "location": self.location.pk, "title": "Unsafe electrical socket near reading area", "description": "The socket is loose and should be inspected by the maintenance team.", "urgency": "LOW", "priority_score": 999, "priority_level": "CRITICAL"})
        complaint = Complaint.objects.get(title__startswith="Unsafe")
        self.assertEqual(response.status_code, 302)
        self.assertEqual(complaint.priority_score, 40)
        self.assertEqual(complaint.priority_level, Complaint.Priority.MEDIUM)

    def test_admin_and_staff_priority_filter_and_sort(self):
        low_category = ComplaintCategory.objects.create(name="Cleanliness")
        low = self.complaint(category=low_category, urgency="LOW", title="Low priority cleaning issue")
        high = self.complaint(urgency="HIGH", title="High priority electrical issue")
        administrator_action(complaint_id=low.pk, actor=self.admin, action="assign", staff=self.staff)
        administrator_action(complaint_id=high.pk, actor=self.admin, action="assign", staff=self.staff)
        self.client.force_login(self.admin)
        response = self.client.get(reverse("complaints:admin_queue"), {"priority": high.priority_level, "order": "priority"})
        self.assertIn(high, response.context["page_obj"])
        self.client.force_login(self.staff)
        response = self.client.get(reverse("complaints:staff_queue"), {"priority": low.priority_level})
        self.assertEqual(list(response.context["page_obj"]), [low])


class NotificationTests(EngagementBase):
    def test_new_complaint_notifies_active_admins(self):
        complaint = self.complaint()
        self.assertEqual(Notification.objects.filter(title="New complaint submitted").count(), 2)
        self.assertSetEqual(set(Notification.objects.values_list("recipient", flat=True)), {self.admin.pk, self.admin2.pk})

    def test_workflow_notifications_have_correct_recipients(self):
        complaint = self.complaint()
        Notification.objects.all().delete()
        administrator_action(complaint_id=complaint.pk, actor=self.admin, action="review")
        administrator_action(complaint_id=complaint.pk, actor=self.admin, action="assign", staff=self.staff)
        staff_action(complaint_id=complaint.pk, actor=self.staff, action="start")
        staff_action(complaint_id=complaint.pk, actor=self.staff, action="resolve", note="Repaired the electrical connection and tested it safely.")
        administrator_action(complaint_id=complaint.pk, actor=self.admin, action="close")
        self.assertTrue(Notification.objects.filter(recipient=self.student, title="Complaint under review").exists())
        self.assertTrue(Notification.objects.filter(recipient=self.staff, title="Maintenance work assigned").exists())
        self.assertTrue(Notification.objects.filter(recipient=self.student, title="Work started").exists())
        self.assertEqual(Notification.objects.filter(title="Complaint resolved", recipient__role=User.Role.ADMIN).count(), 2)
        self.assertTrue(Notification.objects.filter(recipient=self.student, title="Complaint closed").exists())

    def test_reassignment_and_rejection_notifications(self):
        other_staff = make_user("engagement-staff2", User.Role.STAFF)
        complaint = self.complaint()
        administrator_action(complaint_id=complaint.pk, actor=self.admin, action="assign", staff=self.staff)
        administrator_action(complaint_id=complaint.pk, actor=self.admin, action="reassign", staff=other_staff)
        self.assertTrue(Notification.objects.filter(recipient=other_staff, title="Maintenance work assigned").exists())
        rejected = self.complaint(title="A separate complaint to reject")
        administrator_action(complaint_id=rejected.pk, actor=self.admin, action="reject", note="This issue is outside the campus maintenance scope.")
        self.assertTrue(Notification.objects.filter(recipient=self.student, title="Complaint rejected", message__contains="outside").exists())

    def test_notification_deduplication_and_privacy(self):
        notify_once(recipient=self.student, title="Test", message="Private", destination="/dashboard/", notification_type="COMPLAINT", key="same")
        notify_once(recipient=self.student, title="Test", message="Private", destination="/dashboard/", notification_type="COMPLAINT", key="same")
        notification = Notification.objects.get(dedupe_key=f"same:user:{self.student.pk}")
        self.assertEqual(Notification.objects.filter(dedupe_key__startswith="same:").count(), 1)
        self.client.force_login(self.other_student)
        self.assertEqual(self.client.get(reverse("complaints:notification_open", args=[notification.pk])).status_code, 403)
        notification.refresh_from_db(); self.assertFalse(notification.is_read)

    def test_mark_one_and_mark_all_read(self):
        first = notify_once(recipient=self.student, title="One", message="First", destination="/dashboard/", notification_type="COMPLAINT", key="one")
        second = notify_once(recipient=self.student, title="Two", message="Second", destination="/dashboard/", notification_type="COMPLAINT", key="two")
        self.client.force_login(self.student)
        self.client.get(reverse("complaints:notification_open", args=[first.pk]))
        first.refresh_from_db(); self.assertTrue(first.is_read)
        self.assertEqual(self.client.get(reverse("complaints:notifications_read_all")).status_code, 405)
        self.client.post(reverse("complaints:notifications_read_all"))
        second.refresh_from_db(); self.assertTrue(second.is_read)


class FeedbackAndAnalyticsTests(EngagementBase):
    def resolved_complaint(self):
        complaint = self.complaint()
        administrator_action(complaint_id=complaint.pk, actor=self.admin, action="assign", staff=self.staff)
        staff_action(complaint_id=complaint.pk, actor=self.staff, action="start")
        staff_action(complaint_id=complaint.pk, actor=self.staff, action="resolve", note="Completed repair and verified the result with a safety check.")
        return complaint

    def test_feedback_only_owner_and_only_after_resolution(self):
        complaint = self.complaint()
        self.client.force_login(self.student)
        self.assertEqual(self.client.get(reverse("complaints:feedback", args=[complaint.ticket_number])).status_code, 403)
        complaint = self.resolved_complaint()
        self.client.force_login(self.other_student)
        self.assertEqual(self.client.get(reverse("complaints:feedback", args=[complaint.ticket_number])).status_code, 403)
        for blocked in (self.staff, self.admin):
            self.client.force_login(blocked)
            self.assertEqual(self.client.get(reverse("complaints:feedback", args=[complaint.ticket_number])).status_code, 403)

    def test_feedback_submission_is_unique_and_notifies_admins(self):
        complaint = self.resolved_complaint()
        self.client.force_login(self.student)
        response = self.client.post(reverse("complaints:feedback", args=[complaint.ticket_number]), {"rating": 5, "comment": "The repair was completed quickly and professionally."})
        self.assertRedirects(response, reverse("complaints:detail", args=[complaint.ticket_number]))
        self.assertEqual(ComplaintFeedback.objects.filter(complaint=complaint).count(), 1)
        self.client.post(reverse("complaints:feedback", args=[complaint.ticket_number]), {"rating": 4})
        self.assertEqual(ComplaintFeedback.objects.filter(complaint=complaint).count(), 1)
        self.assertEqual(Notification.objects.filter(title="Student feedback received").count(), 2)

    def test_analytics_real_data_and_role_protection(self):
        complaint = self.resolved_complaint()
        ComplaintFeedback.objects.create(complaint=complaint, student=self.student, rating=4, comment="Good work")
        self.client.force_login(self.admin)
        response = self.client.get(reverse("complaints:analytics"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["metrics"]["total"], 1)
        self.assertEqual(response.context["metrics"]["feedback_total"], 1)
        self.assertEqual(response.context["metrics"]["feedback_average"], 4)
        for blocked in (self.student, self.staff):
            self.client.force_login(blocked)
            self.assertEqual(self.client.get(reverse("complaints:analytics")).status_code, 403)


class DemoEngagementCommandTests(TestCase):
    @override_settings(DEBUG=True)
    def test_command_is_idempotent(self):
        call_command("create_demo_engagement")
        call_command("create_demo_engagement")
        complaint = Complaint.objects.get(title="Resolved reading room light repair")
        self.assertEqual(complaint.status, Complaint.Status.RESOLVED)
        self.assertEqual(Complaint.objects.filter(title=complaint.title).count(), 1)

    @override_settings(DEBUG=False)
    def test_command_is_blocked_without_debug(self):
        with self.assertRaises(CommandError):
            call_command("create_demo_engagement")
