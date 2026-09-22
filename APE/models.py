from django.db import models
from django.conf import settings
from django.contrib.auth.models import User
import datetime
# Create your models here.

# User= settings.AUTH_USER_MODEL


class Subjects(models.Model):
    sub_name = models.TextField()
    sub_desc = models.TextField()
    sub_outline = models.FileField()

class Units(models.Model):
    subject = models.ForeignKey(Subjects, null=True, on_delete=models.SET_NULL)
    unit_number = models.IntegerField()
    unit_name = models.TextField()

class Subtopics(models.Model):
    unit = models.ForeignKey(Units, null=True, on_delete=models.SET_NULL)
    st_number = models.FloatField()
    st_name = models.TextField()

class Students(models.Model):
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    profile_pic = models.FileField(blank=True)
    Tokens = models.IntegerField(default=0)

class Mentors(models.Model):
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    subjects = models.ManyToManyField(Subjects)
    mentor_desc = models.TextField()
    hrs_taught = models.FloatField(default = 0.0)
    no_students = models.IntegerField(default = 0)
    revenue = models.FloatField(default = 0.0)
    paypal = models.TextField()
    referral_code = models.TextField()

class MentorApplications(models.Model):
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    mentor_desc = models.TextField()
    subject = models.ForeignKey(Subjects, on_delete=models.SET_NULL, null=True)
    q1 = models.TextField()
    q2 = models.TextField()
    q3 = models.TextField()
    cred_proof = models.FileField()
    cv = models.FileField()
    decided = models.BooleanField(default=False)

class Classes(models.Model):
    subtopics = models.ManyToManyField(Subtopics)
    class_desc = models.TextField()
    mentor = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    students = models.ManyToManyField(Students, blank=True)
    zoom_ID = models.CharField(max_length=30)
    zoom_password = models.CharField(max_length=30)
    zoom_link = models.CharField(max_length=30)
    date = models.DateField(blank=True)
    time = models.TimeField(blank=True)


class ClassRequests(models.Model):
    unit = models.ForeignKey(Units, on_delete=models.SET_NULL, null=True)
    notes = models.TextField()
    active = models.BooleanField()

# class StudentClasses(models.Model):
#     sc_id = models.AutoField(primary_key=True, unique=True)
#     user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
#     class_field = models.ForeignKey(Classes, on_delete=models.SET_NULL, null=True)
#
#
# class MentorSubjects(models.Model):
#     ms_id = models.AutoField(primary_key=True, unique=True)
#     user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
#     subject = models.ForeignKey(Subjects, on_delete=models.SET_NULL, null=True)


