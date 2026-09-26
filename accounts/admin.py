from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User


@admin.register(User)
class CampusFixUserAdmin(UserAdmin):
    list_display = (
        "username", "full_name", "email", "role", "is_active", "is_staff"
    )
    list_filter = ("role", "is_active", "is_staff", "is_superuser")
    search_fields = ("username", "first_name", "last_name", "email")
    ordering = ("username",)
    fieldsets = UserAdmin.fieldsets + (
        (
            "CampusFix profile and access",
            {
                "fields": (
                    "role", "phone_number", "department", "student_id",
                    "employee_id", "profile_updated_at",
                )
            },
        ),
    )
    readonly_fields = ("profile_updated_at",)
    add_fieldsets = UserAdmin.add_fieldsets + (
        (
            "CampusFix profile and access",
            {
                "fields": (
                    "email", "first_name", "last_name", "role", "phone_number",
                    "department", "student_id", "employee_id",
                )
            },
        ),
    )

    @admin.display(description="Name")
    def full_name(self, obj):
        return obj.get_full_name() or "—"
