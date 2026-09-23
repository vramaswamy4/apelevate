from django.contrib import admin

from .models import StudyPlan


@admin.register(StudyPlan)
class StudyPlanAdmin(admin.ModelAdmin):
    list_display = [
        "user",
        "subject",
        "status",
        "model",
        "attempts",
        "input_tokens",
        "output_tokens",
        "latency_ms",
        "created_at",
    ]
    list_filter = ["status", "model", "subject"]
    list_select_related = ["user", "subject"]
    readonly_fields = [f.name for f in StudyPlan._meta.fields]
