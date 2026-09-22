from django.contrib.auth.decorators import login_not_required
from django.shortcuts import redirect, render
from django.utils import timezone

from accounts.models import MentorApplication
from catalog.models import Subject
from classes.models import Enrolment, TutoringClass


@login_not_required
def home(request):
    if request.user.is_authenticated:
        return redirect("dashboard")
    subjects = Subject.objects.with_counts()
    upcoming = TutoringClass.objects.upcoming().with_card_data()[:3]
    return render(request, "core/home.html", {"subjects": subjects, "upcoming": upcoming})


def dashboard(request):
    now = timezone.now()
    user = request.user
    next_classes = (
        Enrolment.objects.filter(student=user, tutoring_class__starts_at__gte=now)
        .select_related("tutoring_class__subject", "tutoring_class__mentor__user")
        .order_by("tutoring_class__starts_at")[:5]
    )
    suggestions = (
        TutoringClass.objects.upcoming(now)
        .exclude(enrolments__student=user)
        .exclude(mentor__user=user)
        .with_card_data()[:3]
    )
    application = MentorApplication.objects.filter(user=user).select_related("subject").first()
    return render(
        request,
        "core/dashboard.html",
        {"next_classes": next_classes, "suggestions": suggestions, "application": application},
    )
