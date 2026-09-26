from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from accounts.models import User


DEMO_USERS = (
    {"username": "student_demo", "password": "CampusFixStudent@2026", "defaults": {"email": "student.demo@campusfix.local", "first_name": "Aarav", "last_name": "Student", "role": User.Role.STUDENT, "department": "Computer Science and Engineering", "student_id": "CF-DEMO-STUDENT", "employee_id": None, "is_staff": False, "is_superuser": False, "is_active": True}},
    {"username": "staff_demo", "password": "CampusFixStaff@2026", "defaults": {"email": "staff.demo@campusfix.local", "first_name": "Meera", "last_name": "Maintenance", "role": User.Role.STAFF, "department": "Campus Maintenance", "student_id": None, "employee_id": "CF-DEMO-STAFF", "is_staff": False, "is_superuser": False, "is_active": True}},
    {"username": "admin_demo", "password": "CampusFixAdmin@2026", "defaults": {"email": "admin.demo@campusfix.local", "first_name": "Devika", "last_name": "Administrator", "role": User.Role.ADMIN, "department": "Administration", "student_id": None, "employee_id": "CF-DEMO-ADMIN", "is_staff": True, "is_superuser": True, "is_active": True}},
)


class Command(BaseCommand):
    help = "Create or refresh the three local-only CampusFix demonstration users."

    def handle(self, *args, **options):
        if not settings.DEBUG:
            raise CommandError("Demo users can only be created when DEBUG=True.")

        self.stdout.write(self.style.WARNING("Local development accounts only - never use in production."))
        for definition in DEMO_USERS:
            user, created = User.objects.update_or_create(
                username=definition["username"], defaults=definition["defaults"]
            )
            user.set_password(definition["password"])
            user.save()
            action = "Created" if created else "Refreshed"
            self.stdout.write(self.style.SUCCESS(
                f"{action}: {user.username} / {definition['password']} ({user.get_role_display()})"
            ))
