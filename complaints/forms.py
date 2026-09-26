from pathlib import Path

from django import forms
from PIL import Image, UnidentifiedImageError

from .models import CampusLocation, Complaint, ComplaintCategory


MAX_IMAGE_SIZE = 5 * 1024 * 1024
ALLOWED_IMAGE_FORMATS = {"JPEG", "PNG", "WEBP"}


class ComplaintForm(forms.ModelForm):
    evidence_image = forms.FileField(
        required=False,
        label="Evidence image (optional)",
        help_text="Optional genuine JPEG, PNG, or WebP image, maximum 5 MB.",
    )

    class Meta:
        model = Complaint
        fields = ("category", "location", "title", "description", "urgency", "evidence_image")
        labels = {"evidence_image": "Evidence image (optional)", "location": "Campus location"}
        help_texts = {
            "title": "Summarise the issue in 5 to 140 characters.",
            "description": "Describe what happened, where it is, and any safety impact (at least 20 characters).",
            "urgency": "Choose High only when the issue needs prompt attention or affects safety/access.",
            "evidence_image": "Optional genuine JPEG, PNG, or WebP image, maximum 5 MB.",
        }
        widgets = {"description": forms.Textarea(attrs={"rows": 6})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["category"].queryset = ComplaintCategory.objects.filter(is_active=True)
        self.fields["location"].queryset = CampusLocation.objects.filter(is_active=True)
        for field in self.fields.values():
            field.widget.attrs["class"] = "form-select" if isinstance(field.widget, forms.Select) else "form-control"
        self.fields["evidence_image"].widget.attrs["accept"] = "image/jpeg,image/png,image/webp"

    def clean_title(self):
        return self.cleaned_data["title"].strip()

    def clean_description(self):
        return self.cleaned_data["description"].strip()

    def clean_evidence_image(self):
        upload = self.cleaned_data.get("evidence_image")
        if not upload:
            return upload
        if upload.size > MAX_IMAGE_SIZE:
            raise forms.ValidationError("The image must be 5 MB or smaller.")
        try:
            image = Image.open(upload)
            detected_format = image.format
            image.verify()
            upload.seek(0)
        except (UnidentifiedImageError, OSError, ValueError):
            raise forms.ValidationError("Upload a genuine JPEG, PNG, or WebP image.")
        if detected_format not in ALLOWED_IMAGE_FORMATS:
            raise forms.ValidationError("Only JPEG, PNG, and WebP images are allowed.")
        safe_extension = {"JPEG": ".jpg", "PNG": ".png", "WEBP": ".webp"}[detected_format]
        upload.name = f"evidence{safe_extension}"
        return upload
