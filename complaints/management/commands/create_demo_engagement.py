from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError

from accounts.models import User
from complaints.models import CampusLocation, Complaint, ComplaintCategory
from complaints.services import administrator_action, staff_action


class Command(BaseCommand):
    help = "Prepare one resolved local demo ticket for Batch 5 feedback and analytics."

    def handle(self, *args, **options):
        if not settings.DEBUG:
            raise CommandError("Demo engagement data can only be created when DEBUG=True.")
        call_command("create_demo_workflow", verbosity=0)
        student = User.objects.get(username="student_demo")
        staff = User.objects.get(username="staff_demo")
        admin = User.objects.get(username="admin_demo")
        complaint, _ = Complaint.objects.get_or_create(
            student=student,
            title="Resolved reading room light repair",
            defaults={"category": ComplaintCategory.objects.get(name="Electrical"), "location": CampusLocation.objects.get(name="Library"), "description": "A failed reading room light was reported for the Batch 5 feedback demonstration.", "urgency": Complaint.Urgency.MEDIUM},
        )
        if complaint.status == Complaint.Status.SUBMITTED:
            administrator_action(complaint_id=complaint.pk, actor=admin, action="assign", staff=staff)
            complaint.refresh_from_db()
        if complaint.status == Complaint.Status.ASSIGNED:
            staff_action(complaint_id=complaint.pk, actor=staff, action="start")
            complaint.refresh_from_db()
        if complaint.status == Complaint.Status.IN_PROGRESS:
            staff_action(complaint_id=complaint.pk, actor=staff, action="resolve", note="Replaced the failed light and confirmed normal operation in the reading room.")
            complaint.refresh_from_db()
        self.stdout.write(self.style.SUCCESS(f"Batch 5 demo ready: {complaint.ticket_number} - {complaint.get_status_display()} - feedback eligible."))
