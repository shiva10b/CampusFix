from dataclasses import dataclass

URGENCY_POINTS = {"LOW": 10, "MEDIUM": 25, "HIGH": 40}
CATEGORY_POINTS = {"Safety and Security": 40, "Electrical": 30, "Water and Plumbing": 30, "Furniture and Equipment": 20, "Wi-Fi and Network": 15, "Cleanliness": 10, "Other": 10}


@dataclass(frozen=True)
class PriorityResult:
    score: int
    level: str
    explanation: str


def calculate_priority(complaint):
    urgency_points = URGENCY_POINTS.get(complaint.urgency, 10)
    category_name = complaint.category.name if getattr(complaint, "category_id", None) else "Other"
    category_points = CATEGORY_POINTS.get(category_name, 10)
    evidence_points = 5 if complaint.evidence_image else 0
    score = urgency_points + category_points + evidence_points
    level = "CRITICAL" if score >= 70 else "HIGH" if score >= 50 else "MEDIUM" if score >= 30 else "LOW"
    explanation = f"{urgency_points} urgency points ({complaint.get_urgency_display()}), {category_points} category points ({category_name}), and {evidence_points} evidence points. Total: {score}."
    return PriorityResult(score, level, explanation)
