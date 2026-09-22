"""Mentor applications: submitting and deciding. Views call these; they hold the rules."""

import logging

from django.core.mail import send_mail
from django.db import IntegrityError, transaction
from django.template.loader import render_to_string
from django.utils import timezone

from .models import MentorApplication, MentorProfile

log = logging.getLogger(__name__)


class ApplicationError(Exception):
    """A rule was broken; the message is safe to show to the user."""


def submit_application(user, form) -> MentorApplication:
    application = form.save(commit=False)
    application.user = user
    try:
        with transaction.atomic():
            application.save()
    except IntegrityError:
        # The partial unique index on (user) WHERE status = 'pending'.
        raise ApplicationError("You already have an application waiting for review.") from None
    log.info("mentor application %s submitted by user %s", application.pk, user.pk)
    return application


def decide_application(application_id, *, reviewer, accept: bool, note: str = ""):
    """Accept or reject a pending application, exactly once.

    The row lock makes two admins clicking at the same moment safe: the second one sees the
    decided status and gets an error instead of a second decision.
    """
    with transaction.atomic():
        application = (
            MentorApplication.objects.select_for_update()
            .select_related("user", "subject")
            .get(pk=application_id)
        )
        if not application.is_pending:
            raise ApplicationError("This application has already been decided.")
        Status = MentorApplication.Status
        application.status = Status.ACCEPTED if accept else Status.REJECTED
        application.reviewed_at = timezone.now()
        application.reviewed_by = reviewer
        application.decision_note = note
        application.save(update_fields=["status", "reviewed_at", "reviewed_by", "decision_note"])
        if accept:
            profile, _ = MentorProfile.objects.get_or_create(
                user=application.user, defaults={"bio": application.bio}
            )
            profile.subjects.add(application.subject)
        transaction.on_commit(lambda: _notify_applicant(application))
    log.info("mentor application %s %s by user %s", application.pk, application.status, reviewer.pk)
    return application


def _notify_applicant(application):
    context = {"application": application}
    send_mail(
        subject=f"Your APElevate mentor application: {application.get_status_display()}",
        message=render_to_string("accounts/email/application_decided.txt", context),
        from_email=None,
        recipient_list=[application.user.email],
    )
