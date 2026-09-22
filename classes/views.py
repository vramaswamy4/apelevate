from django.contrib import messages
from django.contrib.auth.decorators import login_not_required
from django.core.paginator import Paginator
from django.db.models import Count
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from catalog.models import Subtopic
from core.htmx import is_htmx
from core.permissions import mentor_required

from .forms import ClassFilterForm, ClassRequestForm, TutoringClassForm
from .models import ClassRequest, Enrolment, TutoringClass
from .services import ENROLMENT_COST, EnrolmentError, enrol
from .stats import mentor_by_subject, mentor_monthly, mentor_summary

# --- Students -----------------------------------------------------------------------------------


@login_not_required
def class_list(request):
    form = ClassFilterForm(request.GET or None)
    classes = TutoringClass.objects.upcoming().with_card_data().with_enrolment_flag(request.user)
    if form.is_valid():
        if form.cleaned_data["subject"]:
            classes = classes.filter(subject=form.cleaned_data["subject"])
        if form.cleaned_data["mentor"]:
            classes = classes.filter(mentor=form.cleaned_data["mentor"])
    page = Paginator(classes, 12).get_page(request.GET.get("page"))
    context = {"form": form, "page": page}
    template = "classes/_class_results.html" if is_htmx(request) else "classes/class_list.html"
    return render(request, template, context)


@login_not_required
def class_detail(request, pk):
    tutoring_class = get_object_or_404(
        TutoringClass.objects.with_card_data().with_enrolment_flag(request.user), pk=pk
    )
    return render(request, "classes/class_detail.html", _detail_context(request, tutoring_class))


def _detail_context(request, tutoring_class, error=None):
    user = request.user
    is_owner = user.is_authenticated and tutoring_class.mentor.user_id == user.pk
    roster = None
    if is_owner or user.is_staff:
        roster = tutoring_class.enrolments.select_related("student").order_by("student__first_name")
    return {
        "class": tutoring_class,
        "can_see_meeting": tutoring_class.can_see_meeting(user),
        "is_owner": is_owner,
        "roster": roster,
        "enrolment_cost": ENROLMENT_COST,
        "error": error,
    }


@require_POST
def enrol_view(request, pk):
    tutoring_class = get_object_or_404(TutoringClass.objects.with_card_data(), pk=pk)
    error = None
    try:
        enrol(request.user, tutoring_class)
    except EnrolmentError as exc:
        error = str(exc)
    request.user.refresh_from_db(fields=["token_balance"])
    tutoring_class = (
        TutoringClass.objects.with_card_data().with_enrolment_flag(request.user).get(pk=pk)
    )
    if is_htmx(request):
        context = _detail_context(request, tutoring_class, error=error)
        return render(request, "classes/_enrol_panel.html", context)
    if error:
        messages.error(request, error)
    else:
        messages.success(request, f"You're enrolled in {tutoring_class.title}.")
    return redirect(tutoring_class)


def my_classes(request):
    now = timezone.now()
    enrolments = Enrolment.objects.filter(student=request.user).select_related(
        "tutoring_class__subject", "tutoring_class__mentor__user"
    )
    upcoming = enrolments.filter(tutoring_class__starts_at__gte=now).order_by(
        "tutoring_class__starts_at"
    )
    past = enrolments.filter(tutoring_class__starts_at__lt=now).order_by(
        "-tutoring_class__starts_at"
    )[:20]
    return render(request, "classes/my_classes.html", {"upcoming": upcoming, "past": past})


def requests_view(request):
    initial = {"unit": request.GET.get("unit")} if request.GET.get("unit") else None
    form = ClassRequestForm(request.POST or None, initial=initial)
    if request.method == "POST" and form.is_valid():
        class_request = form.save(commit=False)
        class_request.student = request.user
        class_request.save()
        messages.success(request, "Request sent. Mentors for that subject will see it.")
        return redirect("classes:requests")
    mine = request.user.class_requests.select_related("unit__subject")
    return render(request, "classes/requests.html", {"form": form, "requests": mine})


@require_POST
def close_request(request, pk):
    class_request = get_object_or_404(ClassRequest, pk=pk, student=request.user)
    class_request.is_open = False
    class_request.save(update_fields=["is_open"])
    return redirect("classes:requests")


# --- Mentors ------------------------------------------------------------------------------------


@mentor_required
def teach_dashboard(request):
    mentor = request.user.mentor
    now = timezone.now()
    upcoming = TutoringClass.objects.filter(mentor=mentor).upcoming(now).with_card_data()[:10]
    open_requests = (
        ClassRequest.objects.filter(is_open=True, unit__subject__in=mentor.subjects.all())
        .select_related("unit__subject", "student")
        .order_by("-created_at")[:10]
    )
    return render(
        request,
        "classes/teach_dashboard.html",
        {
            "summary": mentor_summary(mentor, now),
            "upcoming": upcoming,
            "open_requests": open_requests,
            "subjects": mentor.subjects.all(),
        },
    )


@mentor_required
def class_create(request):
    mentor = request.user.mentor
    initial = {}
    if request.GET.get("subject"):
        initial["subject"] = request.GET["subject"]
    form = TutoringClassForm(request.POST or None, mentor=mentor, initial=initial)
    if request.method == "POST" and form.is_valid():
        tutoring_class = form.save()
        messages.success(request, f"{tutoring_class.title} is scheduled and open for enrolment.")
        return redirect(tutoring_class)
    return render(request, "classes/class_form.html", {"form": form})


@mentor_required
def subtopic_options(request):
    """htmx: the topic checkboxes for the subject picked in the class form."""
    mentor = request.user.mentor
    subject_id = request.GET.get("subject")
    subtopics = Subtopic.objects.none()
    if subject_id and mentor.subjects.filter(pk=subject_id).exists():
        subtopics = Subtopic.objects.filter(unit__subject_id=subject_id).select_related("unit")
    return render(request, "classes/_subtopic_options.html", {"subtopics": subtopics})


@mentor_required
def teach_analytics(request):
    mentor = request.user.mentor
    now = timezone.now()
    classes = (
        TutoringClass.objects.filter(mentor=mentor)
        .past(now)
        .select_related("subject")
        .annotate(enrolment_count=Count("enrolments"))
        .order_by("-starts_at")[:25]
    )
    return render(
        request,
        "classes/teach_analytics.html",
        {
            "summary": mentor_summary(mentor, now),
            "monthly": mentor_monthly(mentor, now),
            "by_subject": mentor_by_subject(mentor),
            "recent": classes,
        },
    )


@mentor_required
def teach_classes(request):
    mentor = request.user.mentor
    now = timezone.now()
    scope = request.GET.get("when", "upcoming")
    classes = TutoringClass.objects.filter(mentor=mentor).with_card_data()
    classes = classes.past(now).order_by("-starts_at") if scope == "past" else classes.upcoming(now)
    page = Paginator(classes, 20).get_page(request.GET.get("page"))
    return render(request, "classes/teach_classes.html", {"page": page, "when": scope})
