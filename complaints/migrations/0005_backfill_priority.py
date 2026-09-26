from django.db import migrations


URGENCY = {"LOW": 10, "MEDIUM": 25, "HIGH": 40}
CATEGORY = {"Safety and Security": 40, "Electrical": 30, "Water and Plumbing": 30, "Furniture and Equipment": 20, "Wi-Fi and Network": 15, "Cleanliness": 10, "Other": 10}


def backfill_priority(apps, schema_editor):
    Complaint = apps.get_model("complaints", "Complaint")
    for complaint in Complaint.objects.select_related("category").iterator():
        urgency_points = URGENCY.get(complaint.urgency, 10)
        category_points = CATEGORY.get(complaint.category.name, 10)
        evidence_points = 5 if complaint.evidence_image else 0
        score = urgency_points + category_points + evidence_points
        level = "CRITICAL" if score >= 70 else "HIGH" if score >= 50 else "MEDIUM" if score >= 30 else "LOW"
        explanation = f"{urgency_points} urgency points ({complaint.urgency}), {category_points} category points ({complaint.category.name}), and {evidence_points} evidence points. Total: {score}."
        Complaint.objects.filter(pk=complaint.pk).update(priority_score=score, priority_level=level, priority_explanation=explanation)


class Migration(migrations.Migration):
    dependencies = [("complaints", "0004_complaint_priority_explanation_and_more")]
    operations = [migrations.RunPython(backfill_priority, migrations.RunPython.noop)]
