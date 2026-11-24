from django import forms
from django.contrib.auth.password_validation import validate_password

from .models import Department, User


class StudentRegistrationForm(forms.ModelForm):
    username = forms.CharField(
        label="Student ID",
        help_text="Your 8-digit student ID. Digits only.",
        error_messages={"required": "Enter your student ID."},
        widget=forms.TextInput(attrs={"maxlength": "8", "inputmode": "numeric"}),
    )
    password1 = forms.CharField(label="Password", widget=forms.PasswordInput)
    password2 = forms.CharField(label="Confirm password", widget=forms.PasswordInput)

    class Meta:
        model = User
        fields = ["username", "full_name", "department"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        department = self.fields["department"]
        department.queryset = Department.objects.order_by("name")
        department.empty_label = None
        department.required = True
        for name, field in self.fields.items():
            field.widget.attrs["class"] = "form-select" if name == "department" else "form-control"

    def clean_username(self):
        username = self.cleaned_data["username"]
        if not (username.isascii() and username.isdigit()):
            raise forms.ValidationError("Student ID must contain digits only (0 to 9).")
        if len(username) != 8:
            raise forms.ValidationError(
                f"Student ID must be exactly 8 digits. You entered {len(username)}."
            )
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError("This student ID is already registered.")
        return username

    def clean(self):
        cleaned = super().clean()
        password1 = cleaned.get("password1")
        password2 = cleaned.get("password2")
        if password1 and password2:
            if password1 != password2:
                self.add_error("password2", "The two passwords do not match.")
            else:
                try:
                    validate_password(password1)
                except forms.ValidationError as error:
                    self.add_error("password1", error)
        return cleaned

    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = User.Role.STUDENT
        user.is_active = False  # becomes active after the email code (Module 6)
        user.set_password(self.cleaned_data["password1"])
        if commit:
            user.save()
        return user