from django.contrib.auth.decorators import login_not_required
from django.db.models import Prefetch
from django.shortcuts import get_object_or_404, render

from classes.models import TutoringClass

from .models import Subject, Subtopic, Unit


@login_not_required
def subject_list(request):
    return render(request, "catalog/subject_list.html", {"subjects": Subject.objects.with_counts()})


@login_not_required
def subject_detail(request, slug):
    subject = get_object_or_404(
        Subject.objects.prefetch_related(
            Prefetch(
                "units",
                queryset=Unit.objects.prefetch_related(
                    Prefetch("subtopics", queryset=Subtopic.objects.select_related("unit"))
                ),
            )
        ),
        slug=slug,
    )
    upcoming = TutoringClass.objects.upcoming().filter(subject=subject).with_card_data()[:6]
    return render(
        request, "catalog/subject_detail.html", {"subject": subject, "upcoming": upcoming}
    )
