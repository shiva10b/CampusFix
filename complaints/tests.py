import shutil
import tempfile
from io import BytesIO, StringIO

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase, override_settings
from django.urls import reverse
from PIL import Image

from .management.commands.create_reference_data import CATEGORIES, LOCATIONS
from .models import CampusLocation, Complaint, ComplaintCategory


User = get_user_model()
PASSWORD = "StrongPass123!"
TEST_MEDIA_ROOT = tempfile.mkdtemp(prefix="campusfix-test-media-")


def make_user(username, role=User.Role.STUDENT):
    return User.objects.create_user(
        username=username,
        email=f"{username}@example.com",
        password=PASSWORD,
        first_name=username.title(),
        last_name="Tester",
        department="CSE",
        role=role,
    )


def make_image(name="evidence.png", image_format="PNG"):
    content = BytesIO()
    Image.new("RGB", (20, 20), "navy").save(content, format=image_format)
    return SimpleUploadedFile(name, content.getvalue(), content_type=f"image/{image_format.lower()}")


@override_settings(MEDIA_ROOT=TEST_MEDIA_ROOT)
class ComplaintTestBase(TestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEST_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.student = make_user("student")
        self.other_student = make_user("other")
        self.staff = make_user("staff", User.Role.STAFF)
        self.admin = make_user("administrator", User.Role.ADMIN)
        self.category = ComplaintCategory.objects.create(name="Electrical", description="Electrical issues")
        self.other_category = ComplaintCategory.objects.create(name="Cleanliness", description="Cleaning issues")
        self.location = CampusLocation.objects.create(name="Computer Lab 1", building_or_area="Academic Block")
        self.other_location = CampusLocation.objects.create(name="Library", building_or_area="Library Block")

    def complaint_data(self, **overrides):
        data = {
            "category": self.category.pk,
            "location": self.location.pk,
            "title": "Projector power socket is loose",
            "description": "The wall power socket beside the projector is loose and disconnects during use.",
            "urgency": Complaint.Urgency.HIGH,
        }
        data.update(overrides)
        return data

    def make_complaint(self, student=None, **overrides):
        data = {
            "student": student or self.student,
            "category": self.category,
            "location": self.location,
            "title": "Projector power socket is loose",
            "description": "The wall power socket beside the projector is loose and disconnects during use.",
            "urgency": Complaint.Urgency.HIGH,
        }
        data.update(overrides)
        return Complaint.objects.create(**data)


class TicketModelTests(ComplaintTestBase):
    def test_ticket_numbers_are_formatted_unique_and_permanent(self):
        first = self.make_complaint()
        second = self.make_complaint(title="A second distinct campus maintenance problem")
        self.assertRegex(first.ticket_number, r"^CF-\d{4}-\d{5,}$")
        self.assertNotEqual(first.ticket_number, second.ticket_number)
        original = first.ticket_number
        first.title = "Updated descriptive title"
        first.save()
        first.refresh_from_db()
        self.assertEqual(first.ticket_number, original)

    def test_new_complaint_defaults_to_submitted(self):
        self.assertEqual(self.make_complaint().status, Complaint.Status.SUBMITTED)


class ComplaintSubmissionTests(ComplaintTestBase):
    def test_only_students_can_open_creation_page(self):
        self.client.force_login(self.student)
        self.assertEqual(self.client.get(reverse("complaints:create")).status_code, 200)
        for user in (self.staff, self.admin):
            self.client.force_login(user)
            self.assertEqual(self.client.get(reverse("complaints:create")).status_code, 403)

    def test_student_can_submit_complaint_with_server_owned_fields(self):
        self.client.force_login(self.student)
        data = self.complaint_data(student=self.other_student.pk, status=Complaint.Status.CLOSED, ticket_number="FORGED")
        response = self.client.post(reverse("complaints:create"), data)
        complaint = Complaint.objects.get()
        self.assertRedirects(response, reverse("complaints:detail", args=[complaint.ticket_number]))
        self.assertEqual(complaint.student, self.student)
        self.assertEqual(complaint.status, Complaint.Status.SUBMITTED)
        self.assertNotEqual(complaint.ticket_number, "FORGED")

    def test_inactive_reference_choices_are_not_available(self):
        self.category.is_active = False
        self.category.save()
        self.client.force_login(self.student)
        response = self.client.get(reverse("complaints:create"))
        self.assertNotIn(self.category, response.context["form"].fields["category"].queryset)

    def test_invalid_image_is_rejected(self):
        self.client.force_login(self.student)
        invalid = SimpleUploadedFile("fake.jpg", b"this is not an image", content_type="image/jpeg")
        data = self.complaint_data(evidence_image=invalid)
        response = self.client.post(reverse("complaints:create"), data)
        self.assertEqual(response.status_code, 200)
        self.assertIn("genuine", response.context["form"].errors["evidence_image"][0])
        self.assertFalse(Complaint.objects.exists())

    def test_oversized_image_is_rejected(self):
        self.client.force_login(self.student)
        oversized = SimpleUploadedFile("large.png", b"0" * (5 * 1024 * 1024 + 1), content_type="image/png")
        data = self.complaint_data(evidence_image=oversized)
        response = self.client.post(reverse("complaints:create"), data)
        self.assertEqual(response.status_code, 200)
        self.assertIn("5 MB", response.context["form"].errors["evidence_image"][0])

    def test_valid_image_upload_is_stored_with_safe_name(self):
        self.client.force_login(self.student)
        data = self.complaint_data(evidence_image=make_image("unsafe name.PNG"))
        response = self.client.post(reverse("complaints:create"), data)
        complaint = Complaint.objects.get()
        self.assertEqual(response.status_code, 302)
        self.assertTrue(complaint.evidence_image.name.startswith("complaint-evidence/"))
        self.assertNotIn("unsafe", complaint.evidence_image.name)


class ComplaintTrackingTests(ComplaintTestBase):
    def setUp(self):
        super().setUp()
        self.own = self.make_complaint()
        self.other = self.make_complaint(student=self.other_student, title="Complaint belonging to another student")
        self.client.force_login(self.student)

    def test_list_shows_only_logged_in_students_complaints(self):
        response = self.client.get(reverse("complaints:list"))
        self.assertContains(response, self.own.ticket_number)
        self.assertNotContains(response, self.other.ticket_number)

    def test_search_by_ticket_and_title(self):
        by_ticket = self.client.get(reverse("complaints:list"), {"q": self.own.ticket_number})
        self.assertEqual(list(by_ticket.context["page_obj"]), [self.own])
        by_title = self.client.get(reverse("complaints:list"), {"q": "Projector power"})
        self.assertEqual(list(by_title.context["page_obj"]), [self.own])

    def test_status_and_category_filters(self):
        second = self.make_complaint(category=self.other_category, title="Cleaning required beside canteen", status=Complaint.Status.CLOSED)
        status_response = self.client.get(reverse("complaints:list"), {"status": Complaint.Status.CLOSED})
        self.assertEqual(list(status_response.context["page_obj"]), [second])
        category_response = self.client.get(reverse("complaints:list"), {"category": self.category.pk})
        self.assertEqual(list(category_response.context["page_obj"]), [self.own])

    def test_student_can_open_own_detail(self):
        response = self.client.get(reverse("complaints:detail", args=[self.own.ticket_number]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.own.description)

    def test_other_students_ticket_returns_403(self):
        response = self.client.get(reverse("complaints:detail", args=[self.other.ticket_number]))
        self.assertEqual(response.status_code, 403)
        self.assertTemplateUsed(response, "403.html")

    def test_staff_and_admin_receive_403_for_student_pages(self):
        for user in (self.staff, self.admin):
            self.client.force_login(user)
            for url in (reverse("complaints:list"), reverse("complaints:create"), reverse("complaints:detail", args=[self.own.ticket_number])):
                self.assertEqual(self.client.get(url).status_code, 403)

    def test_student_dashboard_uses_real_counts_and_recent_tickets(self):
        self.make_complaint(title="Resolved complaint for dashboard", status=Complaint.Status.RESOLVED)
        response = self.client.get(reverse("accounts:student_dashboard"))
        self.assertEqual(response.context["total_complaints"], 2)
        self.assertEqual(response.context["active_complaints"], 1)
        self.assertEqual(response.context["resolved_complaints"], 1)
        self.assertContains(response, self.own.ticket_number)


class ReferenceDataCommandTests(TestCase):
    @override_settings(DEBUG=True)
    def test_reference_command_is_idempotent(self):
        call_command("create_reference_data", stdout=StringIO())
        call_command("create_reference_data", stdout=StringIO())
        self.assertEqual(ComplaintCategory.objects.count(), len(CATEGORIES))
        self.assertEqual(CampusLocation.objects.count(), len(LOCATIONS))

    @override_settings(DEBUG=False)
    def test_reference_command_is_blocked_without_debug(self):
        with self.assertRaises(CommandError):
            call_command("create_reference_data")

    @override_settings(DEBUG=False)
    def test_reference_command_allows_explicit_production_initialization(self):
        call_command("create_reference_data", production=True, stdout=StringIO())
        self.assertEqual(ComplaintCategory.objects.count(), len(CATEGORIES))
        self.assertEqual(CampusLocation.objects.count(), len(LOCATIONS))


class DemoComplaintCommandTests(TestCase):
    @override_settings(DEBUG=True)
    def test_demo_complaint_command_is_idempotent(self):
        call_command("create_demo_complaints", stdout=StringIO())
        call_command("create_demo_complaints", stdout=StringIO())
        student = User.objects.get(username="student_demo")
        self.assertEqual(Complaint.objects.filter(student=student).count(), 3)
        self.assertFalse(Complaint.objects.exclude(status=Complaint.Status.SUBMITTED).exists())

    @override_settings(DEBUG=False)
    def test_demo_complaint_command_is_blocked_without_debug(self):
        with self.assertRaises(CommandError):
            call_command("create_demo_complaints")
