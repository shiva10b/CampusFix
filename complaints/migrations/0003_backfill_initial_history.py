from django.db import migrations


BACKFILL_NOTE = "Initial Submitted event backfilled for an existing Batch 3 complaint."


def backfill_history(apps, schema_editor):
    Complaint = apps.get_model("complaints", "Complaint")
    ComplaintHistory = apps.get_model("complaints", "ComplaintHistory")
    existing_ids = set(ComplaintHistory.objects.values_list("complaint_id", flat=True))
    records = []
    for complaint in Complaint.objects.exclude(pk__in=existing_ids).iterator():
        records.append(ComplaintHistory(
            complaint_id=complaint.pk,
            action="SUBMITTED",
            previous_status="",
            new_status="SUBMITTED",
            actor_id=complaint.student_id,
            note=BACKFILL_NOTE,
            created_at=complaint.created_at,
        ))
    ComplaintHistory.objects.bulk_create(records)


def remove_backfill(apps, schema_editor):
    ComplaintHistory = apps.get_model("complaints", "ComplaintHistory")
    ComplaintHistory.objects.filter(action="SUBMITTED", note=BACKFILL_NOTE).delete()


class Migration(migrations.Migration):
    dependencies = [("complaints", "0002_complaint_assigned_at_complaint_assigned_to_and_more")]

    operations = [migrations.RunPython(backfill_history, remove_backfill)]
