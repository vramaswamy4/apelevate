from django.urls import path

from . import views

app_name = "catalog"

urlpatterns = [
    path("", views.subject_list, name="subject_list"),
    path("<slug:slug>/", views.subject_detail, name="subject_detail"),
]
