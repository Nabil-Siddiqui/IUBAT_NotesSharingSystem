import re

from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.db import models


class Department(models.Model):
    name = models.CharField(max_length=100, unique=True)
    code = models.CharField(max_length=10, unique=True)

    def __str__(self):
        return self.name


class InterestArea(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name


class User(AbstractUser):
    class Role(models.TextChoices):
        STUDENT = "student", "Student"
        FACULTY = "faculty", "Faculty"
        ADMIN = "admin", "Admin"

    role = models.CharField(max_length=10, choices=Role.choices, default=Role.STUDENT)
    full_name = models.CharField(max_length=150)
    department = models.ForeignKey(
        Department, null=True, blank=True, on_delete=models.SET_NULL
    )
    # Students: true once the email code is confirmed.
    # Faculty: true once admin approves them.
    is_verified = models.BooleanField(default=False)
    is_banned = models.BooleanField(default=False)
    interests = models.ManyToManyField(InterestArea, blank=True)

    def clean(self):
        super().clean()
        domain = settings.UNIVERSITY_EMAIL_DOMAIN
        if self.role == self.Role.STUDENT:
            if not re.fullmatch(r"[0-9]{8}", self.username):
                raise ValidationError("A student's username must be an 8-digit student ID.")
        elif self.role == self.Role.FACULTY:
            if self.username != self.email:
                raise ValidationError("A faculty member's username must be their university email.")
            if not self.email.lower().endswith("@" + domain):
                raise ValidationError(f"Faculty must use an @{domain} email address.")

    def save(self, *args, **kwargs):
        if self.is_superuser:
            self.role = self.Role.ADMIN
        elif self.role == self.Role.STUDENT:
            self.email = f"{self.username}@{settings.UNIVERSITY_EMAIL_DOMAIN}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.username} ({self.role})"

class EmailOTP(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="email_codes")
    code_hash = models.CharField(max_length=128)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    attempts = models.PositiveSmallIntegerField(default=0)
    is_used = models.BooleanField(default=False)

    def __str__(self):
        return f"Code for {self.user.username}"