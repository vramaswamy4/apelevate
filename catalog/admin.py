from django.contrib import admin

from .models import Subject, Subtopic, Unit


class UnitInline(admin.TabularInline):
    model = Unit
    extra = 0


class SubtopicInline(admin.TabularInline):
    model = Subtopic
    extra = 0


@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ["name", "slug"]
    prepopulated_fields = {"slug": ["name"]}
    inlines = [UnitInline]


@admin.register(Unit)
class UnitAdmin(admin.ModelAdmin):
    list_display = ["__str__", "subject"]
    list_filter = ["subject"]
    list_select_related = ["subject"]
    inlines = [SubtopicInline]
