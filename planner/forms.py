from datetime import timedelta

from django import forms
from django.utils import timezone

from catalog.models import Subject, Unit


class UnitChoiceField(forms.ModelMultipleChoiceField):
    def label_from_instance(self, obj):
        return f"Unit {obj.number}: {obj.name}"


class PlanForm(forms.Form):
    subject = forms.ModelChoiceField(queryset=Subject.objects.all(), empty_label="Choose a subject")
    exam_date = forms.DateField(
        widget=forms.DateInput(attrs={"type": "date"}),
        help_text="Plans cover up to the last 16 weeks before it. The College Board publishes "
        "the exam schedule each year.",
    )
    hours_per_week = forms.IntegerField(
        min_value=1, max_value=20, initial=5, label="Hours you can study each week"
    )
    weak_units = UnitChoiceField(
        queryset=Unit.objects.none(),
        required=False,
        widget=forms.CheckboxSelectMultiple,
        label="Units you find hardest",
        help_text="They'll be scheduled early and revisited before the exam.",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        subject_id = self.data.get("subject") or self.initial.get("subject")
        if subject_id:
            self.fields["weak_units"].queryset = Unit.objects.filter(
                subject_id=subject_id
            ).order_by("number")

    def clean_exam_date(self):
        exam_date = self.cleaned_data["exam_date"]
        today = timezone.localdate()
        if exam_date <= today:
            raise forms.ValidationError("Pick a date in the future.")
        if exam_date > today + timedelta(days=366):
            raise forms.ValidationError("Pick a date within the next year.")
        return exam_date
