from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import MentorApplication, MentorProfile, User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    ordering = ["email"]
    list_display = ["email", "first_name", "last_name", "token_balance", "is_staff", "date_joined"]
    search_fields = ["email", "first_name", "last_name"]
    readonly_fields = ["token_balance", "last_login", "date_joined"]
    fieldsets = [
        (None, {"fields": ["email", "password"]}),
        ("Profile", {"fields": ["first_name", "last_name", "timezone", "token_balance"]}),
        (
            "Permissions",
            {"fields": ["is_active", "is_staff", "is_superuser", "groups", "user_permissions"]},
        ),
        ("Dates", {"fields": ["last_login", "date_joined"]}),
    ]
    add_fieldsets = [
        (
            None,
            {
                "classes": ["wide"],
                "fields": ["email", "first_name", "last_name", "password1", "password2"],
            },
        )
    ]


@admin.register(MentorProfile)
class MentorProfileAdmin(admin.ModelAdmin):
    list_display = ["user", "approved_at"]
    filter_horizontal = ["subjects"]
    search_fields = ["user__email", "user__first_name", "user__last_name"]
    list_select_related = ["user"]


@admin.register(MentorApplication)
class MentorApplicationAdmin(admin.ModelAdmin):
    """Read-only: decisions go through the review screen so the rules in services.py apply."""

    list_display = ["user", "subject", "status", "submitted_at", "reviewed_by"]
    list_filter = ["status", "subject"]
    search_fields = ["user__email", "user__last_name"]
    list_select_related = ["user", "subject", "reviewed_by"]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
