from django.contrib import admin
from django.urls import include, path

from core import views as core_views

admin.site.site_header = "APElevate admin"
admin.site.site_title = "APElevate admin"

urlpatterns = [
    path("", core_views.home, name="home"),
    path("dashboard/", core_views.dashboard, name="dashboard"),
    path("accounts/", include("accounts.urls")),
    path("subjects/", include("catalog.urls")),
    path("tokens/", include("payments.urls")),
    path("", include("classes.urls")),
    path("admin/", admin.site.urls),
]
