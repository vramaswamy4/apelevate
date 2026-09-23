from django.urls import path

from . import views

app_name = "planner"

urlpatterns = [
    path("", views.plan_list, name="list"),
    path("new/", views.plan_new, name="new"),
    path("units/", views.unit_options, name="unit_options"),
    path("<int:pk>/", views.plan_detail, name="detail"),
]
