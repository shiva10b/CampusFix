from django.contrib.auth.models import AbstractUser, UserManager
from django.db import models


class CampusFixUserManager(UserManager):
    """Keep Django superusers aligned with the CampusFix administrator role."""

    def create_superuser(self, username, email=None, password=None, **extra_fields):
        extra_fields["role"] = self.model.Role.ADMIN
        return super().create_superuser(username, email, password, **extra_fields)


class User(AbstractUser):
    class Role(models.TextChoices):
        STUDENT = "STUDENT", "Student"
        STAFF = "STAFF", "Maintenance Staff"
        ADMIN = "ADMIN", "Administrator"

    role = models.CharField(
        max_length=10,
        choices=Role.choices,
        default=Role.STUDENT,
        db_index=True,
        help_text="Determines the user's CampusFix permissions and dashboard.",
    )
    email = models.EmailField("email address", unique=True)
    phone_number = models.CharField(max_length=20, blank=True)
    department = models.CharField(
        max_length=120,
        default="Not specified",
        help_text="Academic or operational department.",
    )
    student_id = models.CharField(max_length=40, blank=True, null=True, unique=True)
    employee_id = models.CharField(max_length=40, blank=True, null=True, unique=True)
    profile_updated_at = models.DateTimeField(auto_now=True)

    objects = CampusFixUserManager()

    def save(self, *args, **kwargs):
        self.username = self.username.strip()
        self.email = self.__class__.objects.normalize_email(self.email.strip())
        self.first_name = self.first_name.strip()
        self.last_name = self.last_name.strip()
        self.department = self.department.strip()
        self.phone_number = self.phone_number.strip()
        self.student_id = self.student_id.strip() if self.student_id else None
        self.employee_id = self.employee_id.strip() if self.employee_id else None
        if self.is_superuser:
            self.role = self.Role.ADMIN
        super().save(*args, **kwargs)

    @property
    def display_name(self):
        return self.get_full_name() or self.username

    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"
