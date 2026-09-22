from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm

from catalog.models import Subject

from .models import MentorApplication, User
from .validators import validate_document

LONG_TEXT = {"max_length": 2000, "widget": forms.Textarea(attrs={"rows": 4})}


class EmailNormalizingMixin:
    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        taken = User.objects.filter(email__iexact=email)
        if self.instance.pk:
            taken = taken.exclude(pk=self.instance.pk)
        if taken.exists():
            raise forms.ValidationError("An account with this email already exists.")
        return email


class SignUpForm(EmailNormalizingMixin, UserCreationForm):
    class Meta:
        model = User
        fields = ["first_name", "last_name", "email"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name in ("first_name", "last_name"):
            self.fields[name].required = True
        self.fields["email"].widget.attrs["autocomplete"] = "email"


class LoginForm(AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].widget.input_type = "email"
        self.fields["username"].widget.attrs["autocomplete"] = "email"

    def clean_username(self):
        return self.cleaned_data["username"].strip().lower()


class ProfileForm(EmailNormalizingMixin, forms.ModelForm):
    class Meta:
        model = User
        fields = ["first_name", "last_name", "email", "timezone"]
        help_texts = {"timezone": "Class times are shown in this time zone."}


class MentorApplicationForm(forms.ModelForm):
    bio = forms.CharField(label="About you", **LONG_TEXT)
    ap_experience = forms.CharField(label="Your experience with this AP exam", **LONG_TEXT)
    teaching_experience = forms.CharField(label="Your teaching or tutoring experience", **LONG_TEXT)
    motivation = forms.CharField(label="What would make you a good mentor?", **LONG_TEXT)
    score_report = forms.FileField(
        label="AP score report",
        help_text="A PDF, PNG or JPEG of your score report, 5 MB at most.",
        validators=[validate_document],
    )
    cv = forms.FileField(
        label="CV", help_text="PDF, PNG or JPEG, 5 MB at most.", validators=[validate_document]
    )

    class Meta:
        model = MentorApplication
        fields = [
            "subject",
            "bio",
            "ap_experience",
            "teaching_experience",
            "motivation",
            "score_report",
            "cv",
        ]

    def __init__(self, *args, user, **kwargs):
        super().__init__(*args, **kwargs)
        subjects = Subject.objects.all()
        if user.is_mentor:
            subjects = subjects.exclude(pk__in=user.mentor.subjects.all())
        self.fields["subject"].queryset = subjects
        self.fields["subject"].empty_label = "Choose a subject"


class DecisionForm(forms.Form):
    decision = forms.ChoiceField(choices=[("accept", "Accept"), ("reject", "Reject")])
    note = forms.CharField(
        required=False,
        max_length=1000,
        label="Note to the applicant (optional)",
        widget=forms.Textarea(attrs={"rows": 2}),
    )
