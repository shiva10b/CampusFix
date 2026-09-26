from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from accounts.models import User
from complaints.management.commands.create_demo_complaints import DEMO_COMPLAINTS
from complaints.models import Complaint, ComplaintHistory


class Command(BaseCommand):
    help = "Prepare local Submitted, Assigned, and In Progress workflow examples."

    def handle(self, *args, **options):
        if not settings.DEBUG:
            raise CommandError("Demo workflow data can only be created when DEBUG=True.")
        call_command("create_demo_complaints", verbosity=0)
        student = User.objects.get(username="student_demo")
        staff = User.objects.get(username="staff_demo")
        desired = (
            (DEMO_COMPLAINTS[0][0], Complaint.Status.SUBMITTED),
            (DEMO_COMPLAINTS[1][0], Complaint.Status.ASSIGNED),
            (DEMO_COMPLAINTS[2][0], Complaint.Status.IN_PROGRESS),
        )
        prepared = []
        for title, status in desired:
            complaint = Complaint.objects.get(student=student, title=title)
            if status == Complaint.Status.SUBMITTED:
                complaint.status = status
                complaint.assigned_to = None
                complaint.assigned_at = None
                complaint.save(update_fields=("status", "assigned_to", "assigned_at", "updated_at"))
            else:
                complaint.status = status
                complaint.assigned_to = staff
                complaint.assigned_at = complaint.assigned_at or timezone.now()
                complaint.save(update_fields=("status", "assigned_to", "assigned_at", "updated_at"))
                ComplaintHistory.objects.get_or_create(
                    complaint=complaint,
                    action=ComplaintHistory.Action.ASSIGNED,
                    previous_status=Complaint.Status.SUBMITTED,
                    new_status=Complaint.Status.ASSIGNED,
                    note="Demo workflow assignment to staff_demo.",
                    defaults={"actor": User.objects.get(username="admin_demo")},
                )
                if status == Complaint.Status.IN_PROGRESS:
                    ComplaintHistory.objects.get_or_create(
                        complaint=complaint,
                        action=ComplaintHistory.Action.STATUS_CHANGED,
                        previous_status=Complaint.Status.ASSIGNED,
                        new_status=Complaint.Status.IN_PROGRESS,
                        note="Demo maintenance work started.",
                        defaults={"actor": staff},
                    )
            prepared.append(
                f"{complaint.ticket_number}: {complaint.get_status_display()}"
                + (f" - {staff.username}" if complaint.assigned_to_id else " - unassigned")
            )
        self.stdout.write(self.style.SUCCESS("Demo workflow ready:\n" + "\n".join(prepared)))
