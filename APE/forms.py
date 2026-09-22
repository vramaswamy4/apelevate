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

class ClassFormSubject(forms.Form):
    qs = list(Subjects.objects.values_list('sub_name', flat=True))
    # qs = list(Subjects.objects.all())
    qsfinal = []
    for item in qs:
        qsfinal.append((item, item))
    subject = forms.ChoiceField(choices = qsfinal)
    subjectform = forms.BooleanField(widget=forms.HiddenInput, initial=True)

class ClassFormUnit(forms.Form):
    qs = list(Units.objects.values_list('unit_name', flat=True))
    qsfinal = []
    for item in qs:
        qsfinal.append((item, item))
    unit = forms.ChoiceField(choices = qsfinal)
    unitform = forms.BooleanField(widget=forms.HiddenInput, initial=True)

class MenAppForm(forms.ModelForm):
    class Meta:
        model = MentorApplications
        fields = ['mentor_desc', 'q1', 'q2', 'q3', 'cred_proof', 'cv']


# qs = Subtopics.objects.values_list('st_name', flat=True)
