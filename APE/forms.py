from django.contrib.auth.forms import UserCreationForm
from django import forms
from django.contrib.auth.models import User
from.models import Classes, Subtopics, Units, Subjects, MentorApplications


class SignUpForm(UserCreationForm):
    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email', 'password1', 'password2']


class ClassForm(forms.ModelForm):
    class Meta:
        model = Classes
        fields = ['class_desc', 'zoom_ID', 'zoom_password', 'zoom_link', 'date', 'time']

def _subject_choices():
    return [(name, name) for name in Subjects.objects.values_list('sub_name', flat=True)]


def _unit_choices():
    return [(name, name) for name in Units.objects.values_list('unit_name', flat=True)]


class ClassFormSubject(forms.Form):
    subject = forms.ChoiceField(choices=_subject_choices)
    subjectform = forms.BooleanField(widget=forms.HiddenInput, initial=True)

class ClassFormUnit(forms.Form):
    unit = forms.ChoiceField(choices=_unit_choices)
    unitform = forms.BooleanField(widget=forms.HiddenInput, initial=True)

class MenAppForm(forms.ModelForm):
    class Meta:
        model = MentorApplications
        fields = ['mentor_desc', 'q1', 'q2', 'q3', 'cred_proof', 'cv']


# qs = Subtopics.objects.values_list('st_name', flat=True)
