from django.contrib import admin

from .models import CampusLocation, Complaint, ComplaintCategory, ComplaintFeedback, ComplaintHistory, Notification


@admin.register(ComplaintCategory)
class ComplaintCategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "is_active", "created_at", "updated_at")
    list_filter = ("is_active",)
    search_fields = ("name", "description")
    ordering = ("name",)


@admin.register(CampusLocation)
class CampusLocationAdmin(admin.ModelAdmin):
    list_display = ("name", "building_or_area", "detail", "is_active", "updated_at")
    list_filter = ("is_active", "building_or_area")
    search_fields = ("name", "building_or_area", "detail")
    ordering = ("building_or_area", "name")


@admin.register(Complaint)
class ComplaintAdmin(admin.ModelAdmin):
    list_display = ("ticket_number", "title", "student", "priority_level", "priority_score", "status", "assigned_to", "created_at")
    list_filter = ("status", "priority_level", "urgency", "category", "location", "assigned_to", "created_at")
    search_fields = ("ticket_number", "title", "description", "student__username", "student__email")
    ordering = ("-created_at",)
    readonly_fields = (
        "ticket_number", "student", "category", "location", "title", "description",
        "urgency", "priority_score", "priority_level", "priority_explanation", "status", "assigned_to", "assigned_at", "evidence_image",
        "created_at", "updated_at",
    )
    fieldsets = (
        ("Ticket", {"fields": ("ticket_number", "student", "status", "assigned_to", "assigned_at")}),
        ("Issue details (read-only; use CampusFix workflow pages)", {"fields": ("category", "location", "title", "description", "urgency", "priority_score", "priority_level", "priority_explanation", "evidence_image")}),
        ("Timestamps", {"fields": ("created_at", "updated_at")}),
    )

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("recipient", "title", "notification_type", "is_read", "created_at")
    list_filter = ("notification_type", "is_read", "created_at")
    search_fields = ("recipient__username", "recipient__email", "title", "message")
    readonly_fields = ("recipient", "title", "message", "destination", "notification_type", "is_read", "created_at", "dedupe_key")

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(ComplaintFeedback)
class ComplaintFeedbackAdmin(admin.ModelAdmin):
    list_display = ("complaint", "student", "rating", "created_at")
    list_filter = ("rating", "created_at")
    search_fields = ("complaint__ticket_number", "student__username", "comment")
    readonly_fields = ("complaint", "student", "rating", "comment", "created_at")

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(ComplaintHistory)
class ComplaintHistoryAdmin(admin.ModelAdmin):
    list_display = ("complaint", "action", "previous_status", "new_status", "actor", "created_at")
    list_filter = ("action", "previous_status", "new_status", "created_at")
    search_fields = ("complaint__ticket_number", "complaint__title", "actor__username", "note")
    ordering = ("-created_at",)
    readonly_fields = ("complaint", "action", "previous_status", "new_status", "actor", "note", "created_at")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return request.user.is_active and request.user.is_staff and obj is not None

    def has_delete_permission(self, request, obj=None):
        return False
