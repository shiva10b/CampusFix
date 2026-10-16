from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from complaints.models import CampusLocation, ComplaintCategory


CATEGORIES = {
    "Electrical": "Lighting, wiring, power supply, switches, and electrical equipment.",
    "Water and Plumbing": "Leaks, blocked drains, water supply, washrooms, and plumbing fixtures.",
    "Cleanliness": "Cleaning, waste disposal, hygiene, and sanitation concerns.",
    "Wi-Fi and Network": "Campus internet, Wi-Fi coverage, and network connectivity.",
    "Furniture and Equipment": "Damaged furniture, classroom fixtures, and shared equipment.",
    "Safety and Security": "Hazards, access concerns, and campus safety issues.",
    "Other": "Campus maintenance issues that do not fit another category.",
}

LOCATIONS = (
    ("Main Academic Block", "Academic Zone", ""),
    ("Computer Lab 1", "Main Academic Block", "First floor"),
    ("Library", "Learning Resources Block", ""),
    ("Hostel Block A", "Student Residences", ""),
    ("Canteen", "Student Activity Area", ""),
    ("Sports Ground", "Outdoor Campus", ""),
    ("Parking Area", "Main Entrance", ""),
)


class Command(BaseCommand):
    help = "Create or refresh complaint categories and campus locations."

    def add_arguments(self, parser):
        parser.add_argument(
            "--production",
            action="store_true",
            help="Allow reference data initialization when DEBUG=False.",
        )

    def handle(self, *args, **options):
        if not settings.DEBUG and not options["production"]:
            raise CommandError(
                "Production reference data requires the explicit --production flag."
            )
        created_categories = created_locations = 0
        for name, description in CATEGORIES.items():
            _, created = ComplaintCategory.objects.update_or_create(
                name=name, defaults={"description": description, "is_active": True}
            )
            created_categories += int(created)
        for name, area, detail in LOCATIONS:
            _, created = CampusLocation.objects.update_or_create(
                name=name, building_or_area=area,
                defaults={"detail": detail, "is_active": True},
            )
            created_locations += int(created)
        self.stdout.write(self.style.SUCCESS(
            f"Reference data ready: {len(CATEGORIES)} categories ({created_categories} created), "
            f"{len(LOCATIONS)} locations ({created_locations} created)."
        ))
