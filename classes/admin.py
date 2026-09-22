from django.contrib import admin

from .models import ClassRequest, Enrolment, TutoringClass


class EnrolmentInline(admin.TabularInline):
    model = Enrolment
    extra = 0
    readonly_fields = ["student", "tokens_spent", "created_at"]
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False  # enrolments move tokens; they're made through classes.services.enrol


@admin.register(TutoringClass)
class TutoringClassAdmin(admin.ModelAdmin):
    list_display = ["title", "subject", "mentor", "starts_at", "duration_minutes"]
    list_filter = ["subject"]
    search_fields = ["title", "mentor__user__email"]
    date_hierarchy = "starts_at"
    list_select_related = ["subject", "mentor__user"]
    filter_horizontal = ["subtopics"]
    inlines = [EnrolmentInline]


@admin.register(ClassRequest)
class ClassRequestAdmin(admin.ModelAdmin):
    list_display = ["student", "unit", "is_open", "created_at"]
    list_filter = ["is_open", "unit__subject"]
    list_select_related = ["student", "unit__subject"]
