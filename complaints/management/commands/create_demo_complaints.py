from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError

from accounts.models import User
from complaints.models import CampusLocation, Complaint, ComplaintCategory


DEMO_COMPLAINTS = (
    ("Flickering lights in computer lab", "Electrical", "Computer Lab 1", Complaint.Urgency.MEDIUM, "Several ceiling lights keep flickering during afternoon practical sessions."),
    ("Water leaking near hostel washroom", "Water and Plumbing", "Hostel Block A", Complaint.Urgency.HIGH, "Water is leaking continuously near the first-floor washroom entrance and making the floor slippery."),
    ("Weak Wi-Fi signal in library", "Wi-Fi and Network", "Library", Complaint.Urgency.LOW, "The Wi-Fi signal frequently disconnects near the rear study tables in the library."),
)


class Command(BaseCommand):
    help = "Create or refresh submitted complaints for the local student demo account."

    def handle(self, *args, **options):
        if not settings.DEBUG:
            raise CommandError("Demo complaints can only be created when DEBUG=True.")
        call_command("create_demo_users", verbosity=0)
        call_command("create_reference_data", verbosity=0)
        student = User.objects.get(username="student_demo")
        created_count = 0
        tickets = []
        for title, category_name, location_name, urgency, description in DEMO_COMPLAINTS:
            complaint, created = Complaint.objects.update_or_create(
                student=student,
                title=title,
                defaults={
                    "category": ComplaintCategory.objects.get(name=category_name),
                    "location": CampusLocation.objects.get(name=location_name),
                    "description": description,
                    "urgency": urgency,
                    "status": Complaint.Status.SUBMITTED,
                },
            )
            created_count += int(created)
            tickets.append(complaint.ticket_number)
        self.stdout.write(self.style.SUCCESS(
            f"Demo complaints ready: {len(DEMO_COMPLAINTS)} total ({created_count} created). "
            f"Tickets: {', '.join(tickets)}"
        ))
