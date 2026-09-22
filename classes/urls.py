from django.urls import path

from . import views

app_name = "classes"

urlpatterns = [
    path("classes/", views.class_list, name="list"),
    path("classes/mine/", views.my_classes, name="mine"),
    path("classes/requests/", views.requests_view, name="requests"),
    path("classes/requests/<int:pk>/close/", views.close_request, name="close_request"),
    path("classes/<int:pk>/", views.class_detail, name="detail"),
    path("classes/<int:pk>/enrol/", views.enrol_view, name="enrol"),
    path("teach/", views.teach_dashboard, name="teach"),
    path("teach/classes/", views.teach_classes, name="teach_classes"),
    path("teach/classes/new/", views.class_create, name="create"),
    path("teach/subtopics/", views.subtopic_options, name="subtopic_options"),
    path("teach/analytics/", views.teach_analytics, name="analytics"),
]
