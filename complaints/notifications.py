from django.urls import reverse

from accounts.models import User
from .models import Notification


def notify_once(*, recipient, title, message, destination, notification_type, key):
    return Notification.objects.get_or_create(dedupe_key=f"{key}:user:{recipient.pk}", defaults={"recipient": recipient, "title": title, "message": message, "destination": destination, "notification_type": notification_type})[0]


def notify_active_admins(*, title, message, complaint, key, notification_type=Notification.Type.COMPLAINT):
    destination = reverse("complaints:admin_detail", args=[complaint.ticket_number])
    for admin in User.objects.filter(role=User.Role.ADMIN, is_active=True):
        notify_once(recipient=admin, title=title, message=message, destination=destination, notification_type=notification_type, key=key)


def notify_student(*, complaint, title, message, key, notification_type=Notification.Type.COMPLAINT):
    notify_once(recipient=complaint.student, title=title, message=message, destination=reverse("complaints:detail", args=[complaint.ticket_number]), notification_type=notification_type, key=key)


def notify_staff(*, complaint, title, message, key):
    if complaint.assigned_to:
        notify_once(recipient=complaint.assigned_to, title=title, message=message, destination=reverse("complaints:staff_detail", args=[complaint.ticket_number]), notification_type=Notification.Type.ASSIGNMENT, key=key)
