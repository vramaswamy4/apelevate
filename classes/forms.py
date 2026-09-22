from django import forms
from django.utils import timezone

from accounts.models import MentorProfile
from catalog.models import Subject, Subtopic, Unit

from .models import ClassRequest, TutoringClass


class SubtopicChoiceField(forms.ModelMultipleChoiceField):
    def label_from_instance(self, obj):
        return f"{obj.code} {obj.name}"


class TutoringClassForm(forms.ModelForm):
    subtopics = SubtopicChoiceField(
        queryset=Subtopic.objects.none(),
        widget=forms.CheckboxSelectMultiple,
        help_text="Pick the topics this class covers.",
    )
    meeting_url = forms.URLField(label="Zoom link", max_length=500, assume_scheme="https")
    starts_at = forms.DateTimeField(
        label="Starts",
        widget=forms.DateTimeInput(attrs={"type": "datetime-local"}, format="%Y-%m-%dT%H:%M"),
        help_text="In your time zone.",
    )

    class Meta:
        model = TutoringClass
        fields = [
            "subject",
            "subtopics",
            "title",
            "description",
            "starts_at",
            "duration_minutes",
            "meeting_url",
            "meeting_id",
            "meeting_passcode",
        ]
        widgets = {"description": forms.Textarea(attrs={"rows": 3})}
        labels = {"duration_minutes": "Length"}

    def __init__(self, *args, mentor: MentorProfile, **kwargs):
        super().__init__(*args, **kwargs)
        self.mentor = mentor
        self.fields["subject"].queryset = mentor.subjects.all()
        self.fields["subject"].empty_label = "Choose a subject"
        subject_id = self.data.get("subject") or self.initial.get("subject")
        if subject_id:
            # Only this subject's topics are valid choices, so a posted topic from another
            # subject fails validation as "not one of the available choices".
            self.fields["subtopics"].queryset = Subtopic.objects.filter(
                unit__subject_id=subject_id
            ).select_related("unit")

    def clean_starts_at(self):
        starts_at = self.cleaned_data["starts_at"]
        if starts_at <= timezone.now():
            raise forms.ValidationError("Pick a time in the future.")
        return starts_at

    def clean_meeting_url(self):
        url = self.cleaned_data["meeting_url"]
        if not url.startswith("https://"):
            raise forms.ValidationError("Use the https:// link Zoom gives you.")
        return url

    def save(self, commit=True):
        self.instance.mentor = self.mentor
        return super().save(commit=commit)


class ClassFilterForm(forms.Form):
    subject = forms.ModelChoiceField(
        queryset=Subject.objects.all(),
        required=False,
        empty_label="All subjects",
        to_field_name="slug",
    )
    mentor = forms.ModelChoiceField(
        queryset=MentorProfile.objects.select_related("user"),
        required=False,
        empty_label="All mentors",
    )


class UnitChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        return f"{obj.subject.name}: Unit {obj.number}, {obj.name}"


class ClassRequestForm(forms.ModelForm):
    unit = UnitChoiceField(
        queryset=Unit.objects.select_related("subject").order_by("subject__name", "number"),
        empty_label="Choose a unit",
    )

    class Meta:
        model = ClassRequest
        fields = ["unit", "notes"]
        widgets = {"notes": forms.Textarea(attrs={"rows": 3})}
        labels = {"notes": "What would help? (optional)"}
