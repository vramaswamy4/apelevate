from pathlib import Path

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth import views as auth_views
from django.contrib.auth.decorators import login_not_required
from django.core.paginator import Paginator
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.views.decorators.http import require_POST

from core.demo import is_demo_account
from core.htmx import is_htmx
from core.permissions import staff_required

from .forms import DecisionForm, MentorApplicationForm, ProfileForm, SignUpForm
from .models import MentorApplication
from .services import ApplicationError, decide_application, submit_application


@login_not_required
def signup(request):
    if request.user.is_authenticated:
        return redirect("dashboard")
    if settings.DEMO_MODE:
        # Sign-up is off in the public demo so visitors never put real details where the shared
        # demo staff account could read them.
        return render(request, "accounts/signup_closed.html")
    form = SignUpForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        login(request, user, backend="django.contrib.auth.backends.ModelBackend")
        messages.success(request, f"Welcome to APElevate, {user.first_name}.")
        return redirect("dashboard")
    return render(request, "accounts/signup.html", {"form": form})


_password_change = auth_views.PasswordChangeView.as_view(
    template_name="accounts/password_change.html",
    success_url=reverse_lazy("accounts:profile"),
)


def password_change(request):
    if is_demo_account(request.user):
        messages.info(request, "Demo accounts are shared, so their passwords can't be changed.")
        return redirect("accounts:profile")
    return _password_change(request)


def profile(request):
    form = ProfileForm(request.POST or None, instance=request.user)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Profile saved.")
        return redirect("accounts:profile")
    applications = request.user.mentor_applications.select_related("subject")
    return render(request, "accounts/profile.html", {"form": form, "applications": applications})


def apply(request):
    pending = request.user.mentor_applications.filter(
        status=MentorApplication.Status.PENDING
    ).first()
    form = MentorApplicationForm(request.POST or None, request.FILES or None, user=request.user)
    if pending is None and request.method == "POST" and form.is_valid():
        try:
            submit_application(request.user, form)
        except ApplicationError as exc:
            messages.error(request, str(exc))
        else:
            messages.success(request, "Application sent. We'll email you when it's reviewed.")
            return redirect("dashboard")
    no_subjects_left = not form.fields["subject"].queryset.exists()
    return render(
        request,
        "accounts/apply.html",
        {"form": form, "pending": pending, "no_subjects_left": no_subjects_left},
    )


# --- Staff: application review ----------------------------------------------------------------


@staff_required
def review_list(request):
    status = request.GET.get("status", MentorApplication.Status.PENDING)
    if status not in MentorApplication.Status.values:
        status = MentorApplication.Status.PENDING
    applications = MentorApplication.objects.filter(status=status).select_related(
        "user", "subject", "reviewed_by"
    )
    if status == MentorApplication.Status.PENDING:
        applications = applications.order_by("submitted_at")  # oldest first: a queue
    page = Paginator(applications, 20).get_page(request.GET.get("page"))
    return render(
        request,
        "accounts/review_list.html",
        {"page": page, "status": status, "statuses": MentorApplication.Status.choices},
    )


@staff_required
def review_detail(request, pk):
    application = get_object_or_404(
        MentorApplication.objects.select_related("user", "subject", "reviewed_by"), pk=pk
    )
    return render(
        request,
        "accounts/review_detail.html",
        {"application": application, "form": DecisionForm()},
    )


@staff_required
@require_POST
def review_decide(request, pk):
    application = get_object_or_404(MentorApplication, pk=pk)
    form = DecisionForm(request.POST)
    error = None
    if form.is_valid():
        try:
            application = decide_application(
                application.pk,
                reviewer=request.user,
                accept=form.cleaned_data["decision"] == "accept",
                note=form.cleaned_data["note"],
            )
        except ApplicationError as exc:
            error = str(exc)
            application.refresh_from_db()
    else:
        error = "Choose accept or reject."
    if is_htmx(request):
        return render(
            request,
            "accounts/_decision_panel.html",
            {"application": application, "form": form, "error": error},
        )
    if error:
        messages.error(request, error)
    else:
        messages.success(request, f"Application {application.get_status_display().lower()}.")
    return redirect("accounts:review_detail", pk=application.pk)


@staff_required
def review_file(request, pk, kind):
    if kind not in ("score_report", "cv"):
        raise Http404
    application = get_object_or_404(MentorApplication.objects.select_related("user"), pk=pk)
    field = getattr(application, kind)
    if not field:
        raise Http404
    name = f"{application.user.last_name or 'applicant'}-{kind.replace('_', '-')}"
    return FileResponse(
        field.open("rb"), as_attachment=True, filename=f"{name}{Path(field.name).suffix}"
    )
