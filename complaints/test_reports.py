import csv
from datetime import timedelta
from io import StringIO

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import User
from .models import CampusLocation, Complaint, ComplaintCategory, ComplaintFeedback

PASSWORD = "StrongPass123!"


class ReportTests(TestCase):
    def setUp(self):
        self.student = User.objects.create_user("student-r", "student-r@example.com", PASSWORD, role=User.Role.STUDENT)
        self.staff = User.objects.create_user("staff-r", "staff-r@example.com", PASSWORD, role=User.Role.STAFF, employee_id="EMP-R")
        self.admin = User.objects.create_user("admin-r", "admin-r@example.com", PASSWORD, role=User.Role.ADMIN)
        self.category = ComplaintCategory.objects.create(name="Electrical")
        self.other_category = ComplaintCategory.objects.create(name="Cleanliness")
        self.location = CampusLocation.objects.create(name="Lab", building_or_area="Block A")
        self.first = self.make_complaint(title="=FORMULA dangerous title", status=Complaint.Status.ASSIGNED, assigned_to=self.staff)
        self.second = self.make_complaint(title="Washroom cleaning required", category=self.other_category, status=Complaint.Status.RESOLVED, assigned_to=self.staff)
        ComplaintFeedback.objects.create(complaint=self.second, student=self.student, rating=4, comment="+formula comment")

    def make_complaint(self, **overrides):
        values = {"student": self.student, "category": self.category, "location": self.location, "title": "A valid maintenance issue", "description": "This is a detailed maintenance complaint for reporting tests.", "urgency": Complaint.Urgency.HIGH}
        values.update(overrides)
        return Complaint.objects.create(**values)

    def test_reports_and_exports_are_admin_only(self):
        names = ("reports", "report_print", "complaint_csv", "workload_csv", "feedback_csv")
        for user in (self.student, self.staff):
            self.client.force_login(user)
            for name in names:
                self.assertEqual(self.client.get(reverse(f"complaints:{name}")).status_code, 403)
        self.client.force_login(self.admin)
        self.assertEqual(self.client.get(reverse("complaints:reports")).status_code, 200)

    def test_filters_totals_and_custom_dates(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse("complaints:reports"), {"status": Complaint.Status.RESOLVED})
        self.assertEqual(response.context["summary"]["total"], 1)
        self.assertContains(response, self.second.ticket_number)
        self.assertNotContains(response, self.first.ticket_number)
        today = timezone.localdate()
        custom = self.client.get(reverse("complaints:reports"), {"period": "custom", "start_date": today, "end_date": today})
        self.assertEqual(custom.context["summary"]["total"], 2)
        invalid = self.client.get(reverse("complaints:reports"), {"period": "custom", "start_date": today, "end_date": today - timedelta(days=1)})
        self.assertContains(invalid, "start date cannot be after")

    def read_csv(self, name, data=None):
        response = self.client.get(reverse(f"complaints:{name}"), data or {})
        self.assertEqual(response["Content-Type"], "text/csv; charset=utf-8")
        self.assertIn("attachment", response["Content-Disposition"])
        return list(csv.reader(StringIO(response.content.decode("utf-8-sig"))))

    def test_csv_exports_headers_filters_and_formula_safety(self):
        self.client.force_login(self.admin)
        rows = self.read_csv("complaint_csv", {"status": Complaint.Status.ASSIGNED})
        self.assertEqual(rows[0][:3], ["Ticket", "Title", "Student"])
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[1][1], "'=FORMULA dangerous title")
        workload = self.read_csv("workload_csv")
        self.assertEqual(workload[0][0], "Staff")
        feedback = self.read_csv("feedback_csv")
        self.assertEqual(feedback[0], ["Ticket", "Student", "Rating", "Comment", "Submitted"])
        self.assertEqual(feedback[1][3], "'+formula comment")

    def test_print_pagination_long_and_empty_rendering(self):
        self.client.force_login(self.admin)
        printed = self.client.get(reverse("complaints:report_print"), {"status": Complaint.Status.RESOLVED})
        self.assertContains(printed, "status RESOLVED")
        for number in range(21):
            self.make_complaint(title=f"Long issue {number} " + "x" * 120)
        response = self.client.get(reverse("complaints:reports"), {"status": Complaint.Status.SUBMITTED})
        self.assertContains(response, "status=SUBMITTED&page=2")
        empty = self.client.get(reverse("complaints:reports"), {"q": "no-such-ticket"})
        self.assertContains(empty, "No matching complaints")
