from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import Department, InterestArea, User


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        ("Notes platform", {"fields": (
            "full_name", "role", "batch", "department",
            "is_verified", "is_banned", "interests",
        )}),
    )
    list_display = ("username", "full_name", "role", "is_verified", "is_banned")
    list_filter = ("role", "is_verified", "is_banned", "department")
    search_fields = ("username", "full_name")


admin.site.register(Department)
admin.site.register(InterestArea)