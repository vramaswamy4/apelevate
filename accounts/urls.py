from django.contrib.auth import views as auth_views
from django.urls import path, reverse_lazy

from core.demo import DEMO_ACCOUNTS, DEMO_PASSWORD

from . import views
from .forms import LoginForm

app_name = "accounts"

urlpatterns = [
    path("signup/", views.signup, name="signup"),
    path(
        "login/",
        auth_views.LoginView.as_view(
            template_name="accounts/login.html",
            authentication_form=LoginForm,
            redirect_authenticated_user=True,
            extra_context={"demo_accounts": DEMO_ACCOUNTS, "demo_password": DEMO_PASSWORD},
        ),
        name="login",
    ),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("profile/", views.profile, name="profile"),
    path("password/", views.password_change, name="password_change"),
    path(
        "password/reset/",
        auth_views.PasswordResetView.as_view(
            template_name="accounts/password_reset.html",
            email_template_name="accounts/email/password_reset.txt",
            subject_template_name="accounts/email/password_reset_subject.txt",
            success_url=reverse_lazy("accounts:password_reset_done"),
        ),
        name="password_reset",
    ),
    path(
        "password/reset/sent/",
        auth_views.PasswordResetDoneView.as_view(template_name="accounts/password_reset_done.html"),
        name="password_reset_done",
    ),
    path(
        "password/reset/<uidb64>/<token>/",
        auth_views.PasswordResetConfirmView.as_view(
            template_name="accounts/password_reset_confirm.html",
            success_url=reverse_lazy("accounts:login"),
        ),
        name="password_reset_confirm",
    ),
    path("apply/", views.apply, name="apply"),
    path("review/", views.review_list, name="review_list"),
    path("review/<int:pk>/", views.review_detail, name="review_detail"),
    path("review/<int:pk>/decide/", views.review_decide, name="review_decide"),
    path("review/<int:pk>/files/<str:kind>/", views.review_file, name="review_file"),
]
