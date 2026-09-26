from django import forms
from django.contrib.auth.forms import AuthenticationForm, PasswordChangeForm, UserCreationForm

from .models import User


class StyledFormMixin:
    def apply_styles(self):
        for field in self.fields.values():
            css_class = "form-select" if isinstance(field.widget, forms.Select) else "form-control"
            field.widget.attrs["class"] = css_class


class StudentRegistrationForm(StyledFormMixin, UserCreationForm):
    class Meta:
        model = User
        fields = (
            "first_name", "last_name", "username", "email", "student_id",
            "department", "phone_number", "password1", "password2",
        )
        labels = {"phone_number": "Phone number (optional)", "student_id": "Student ID"}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.apply_styles()
        self.fields["first_name"].required = True
        self.fields["last_name"].required = True
        self.fields["email"].required = True
        self.fields["student_id"].required = True
        self.fields["department"].required = True
        self.fields["username"].help_text = "Use letters, numbers, and @/./+/-/_ only."
        self.fields["password1"].help_text = (
            "Use at least 8 characters. Avoid common passwords and personal details."
        )

    def _clean_trimmed(self, field_name):
        return self.cleaned_data.get(field_name, "").strip()

    clean_first_name = lambda self: self._clean_trimmed("first_name")
    clean_last_name = lambda self: self._clean_trimmed("last_name")
    clean_department = lambda self: self._clean_trimmed("department")
    clean_phone_number = lambda self: self._clean_trimmed("phone_number")

    def clean_username(self):
        return self._clean_trimmed("username")

    def clean_email(self):
        email = User.objects.normalize_email(self._clean_trimmed("email"))
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("An account with this email address already exists.")
        return email

    def clean_student_id(self):
        student_id = self._clean_trimmed("student_id").upper()
        if User.objects.filter(student_id__iexact=student_id).exists():
            raise forms.ValidationError("An account with this student ID already exists.")
        return student_id

    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = User.Role.STUDENT
        user.employee_id = None
        if commit:
            user.save()
        return user


class CampusFixAuthenticationForm(StyledFormMixin, AuthenticationForm):
    error_messages = {
        "invalid_login": "The username or password is incorrect.",
        "inactive": "This account is inactive.",
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.apply_styles()


class ProfileUpdateForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = User
        fields = ("first_name", "last_name", "phone_number", "department")
        labels = {"phone_number": "Phone number (optional)"}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.apply_styles()
        self.fields["first_name"].required = True
        self.fields["last_name"].required = True
        self.fields["department"].required = True

    def clean(self):
        cleaned = super().clean()
        for name in self.fields:
            value = cleaned.get(name)
            if isinstance(value, str):
                cleaned[name] = value.strip()
        return cleaned


class StyledPasswordChangeForm(StyledFormMixin, PasswordChangeForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.apply_styles()
