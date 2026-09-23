from datetime import timedelta

from django.contrib import messages
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from catalog.models import Subtopic, Unit
from classes.models import TutoringClass
from core.htmx import is_htmx

from .checks import WARNING
from .forms import PlanForm
from .models import StudyPlan
from .services import PlannerError, generate_plan


def plan_new(request):
    form = PlanForm(request.POST or None, initial={"subject": request.GET.get("subject")})
    error = None
    if request.method == "POST" and form.is_valid():
        try:
            plan = generate_plan(request.user, **form.cleaned_data)
        except PlannerError as exc:
            error = str(exc)
        else:
            url = reverse("planner:detail", args=[plan.pk])
            if is_htmx(request):
                response = HttpResponse(status=204)
                response["HX-Redirect"] = url
                return response
            return redirect(url)
    recent = request.user.study_plans.filter(status=StudyPlan.Status.OK).select_related("subject")[
        :5
    ]
    return render(request, "planner/new.html", {"form": form, "error": error, "recent": recent})


def unit_options(request):
    """htmx: the weak-unit checkboxes for the chosen subject."""
    units = Unit.objects.filter(subject_id=request.GET.get("subject") or 0).order_by("number")
    return render(request, "planner/_unit_options.html", {"units": units})


def plan_detail(request, pk):
    plan = get_object_or_404(
        StudyPlan.objects.select_related("subject").prefetch_related("weak_units"),
        pk=pk,
        user=request.user,
        status=StudyPlan.Status.OK,
    )
    data = plan.plan
    codes = {code for w in data["weeks"] for code in w["topics"]}
    class_ids = {cid for w in data["weeks"] for cid in w["classes"]}
    topics = {
        t.code: t
        for t in Subtopic.objects.filter(unit__subject=plan.subject).select_related("unit")
        if t.code in codes
    }
    classes = TutoringClass.objects.with_card_data().with_enrolment_flag(request.user)
    classes = {c.pk: c for c in classes.filter(pk__in=class_ids)}
    weeks = [
        {
            **w,
            "starts": plan.starts_on + timedelta(weeks=w["week"] - 1),
            "topic_objs": [topics[c] for c in w["topics"] if c in topics],
            "class_objs": [classes[c] for c in w["classes"] if c in classes],
        }
        for w in data["weeks"]
    ]
    notes = [p for p in plan.problems if p["severity"] == WARNING]
    return render(
        request,
        "planner/detail.html",
        {"plan": plan, "data": data, "weeks": weeks, "notes": notes},
    )


def plan_list(request):
    plans = request.user.study_plans.filter(status=StudyPlan.Status.OK).select_related("subject")
    if not plans.exists():
        messages.info(request, "No plans yet. Make your first one below.")
        return redirect("planner:new")
    return render(request, "planner/list.html", {"plans": plans})
