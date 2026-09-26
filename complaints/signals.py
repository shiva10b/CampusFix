from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Complaint, ComplaintHistory


@receiver(post_save, sender=Complaint)
def create_initial_history(sender, instance, created, **kwargs):
    if created:
        ComplaintHistory.objects.get_or_create(
            complaint=instance,
            action=ComplaintHistory.Action.SUBMITTED,
            previous_status="",
            new_status=Complaint.Status.SUBMITTED,
            defaults={"actor": instance.student, "note": "Complaint submitted by student."},
        )
