from django import forms

from accounts.models import User
from .models import ComplaintFeedback


class AdministratorActionForm(forms.Form):
    action = forms.ChoiceField(choices=(
        ("review", "Move to Under Review"),
        ("assign", "Assign"),
        ("reassign", "Reassign"),
        ("reject", "Reject"),
        ("close", "Close"),
    ), widget=forms.HiddenInput)
    staff = forms.ModelChoiceField(
        queryset=User.objects.none(), required=False, label="Maintenance Staff"
    )
    note = forms.CharField(required=False, widget=forms.Textarea(attrs={"rows": 3}), label="Action note")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["staff"].queryset = User.objects.filter(role=User.Role.STAFF, is_active=True).order_by("first_name", "username")
        self.fields["staff"].widget.attrs["class"] = "form-select"
        self.fields["note"].widget.attrs["class"] = "form-control"


class StaffActionForm(forms.Form):
    action = forms.ChoiceField(choices=(("start", "Start work"), ("resolve", "Mark resolved")), widget=forms.HiddenInput)
    note = forms.CharField(required=False, widget=forms.Textarea(attrs={"rows": 4}), label="Resolution note")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["note"].widget.attrs["class"] = "form-control"


class ComplaintFeedbackForm(forms.ModelForm):
    class Meta:
        model = ComplaintFeedback
        fields = ("rating", "comment")
        widgets = {
            "rating": forms.Select(choices=[(value, f"{value} star{'s' if value != 1 else ''}") for value in range(1, 6)]),
            "comment": forms.Textarea(attrs={"rows": 4, "placeholder": "Optional comments about the completed work"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["rating"].widget.attrs["class"] = "form-select"
        self.fields["comment"].widget.attrs["class"] = "form-control"
