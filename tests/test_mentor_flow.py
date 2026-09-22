"""A student applies to mentor, staff accept, the new mentor schedules a class.

In 2022 the application was saved without its user (so Accept crashed), classes were saved
without their mentor (so they never appeared under My classes), and the create-class wizard
threw away the subject and topics the mentor picked.
"""

from datetime import timedelta

import pytest
from django.core import mail
from django.urls import reverse
from django.utils import timezone

from accounts.forms import MentorApplicationForm
from accounts.models import MentorApplication, MentorProfile
from accounts.services import ApplicationError, decide_application
from classes.models import TutoringClass


def apply(client, subject, pdf, png):
    return client.post(
        reverse("accounts:apply"),
        {
            "subject": subject.pk,
            "bio": "IB senior in Dubai.",
            "ap_experience": "Scored a 5 in May.",
            "teaching_experience": "Peer tutor for two years.",
            "motivation": "I know where people get stuck.",
            "score_report": png("score.png"),
            "cv": pdf("cv.pdf"),
        },
    )


def class_form_data(subject, **overrides):
    topics = list(subject.units.first().subtopics.values_list("pk", flat=True)[:2])
    starts = timezone.localtime() + timedelta(days=2)
    data = {
        "subject": subject.pk,
        "subtopics": topics,
        "title": "Equilibrium: Q versus K",
        "description": "Bring the practice set.",
        "starts_at": starts.strftime("%Y-%m-%dT%H:%M"),
        "duration_minutes": 60,
        "meeting_url": "https://us02web.zoom.us/j/81234567890?pwd=abcdefghijklmnop",
        "meeting_id": "812 3456 7890",
        "meeting_passcode": "ape001",
    }
    data.update(overrides)
    return data


def test_full_mentor_journey(
    client, student, staff, chemistry, pdf, png, django_capture_on_commit_callbacks
):
    # Apply.
    client.force_login(student)
    assert apply(client, chemistry, pdf, png).status_code == 302
    application = MentorApplication.objects.get()
    assert application.user == student  # never set in 2022
    assert application.subject == chemistry  # hardcoded to pk=1 in 2022
    assert application.is_pending
    assert not student.is_mentor
    assert client.get(reverse("classes:teach")).status_code == 403

    # Staff accept (POST, not a GET link); the applicant is emailed after commit.
    client.force_login(staff)
    with django_capture_on_commit_callbacks(execute=True):
        response = client.post(
            reverse("accounts:review_decide", args=[application.pk]),
            {"decision": "accept", "note": "Welcome aboard"},
        )
    assert response.status_code == 302
    application.refresh_from_db()
    assert application.status == MentorApplication.Status.ACCEPTED
    assert application.reviewed_by == staff
    assert len(mail.outbox) == 1
    assert "accepted" in mail.outbox[0].body
    assert "Welcome aboard" in mail.outbox[0].body

    # The student is now a mentor for that subject, and still a student.
    profile = MentorProfile.objects.get(user=student)
    assert list(profile.subjects.all()) == [chemistry]
    client.force_login(student)
    assert client.get(reverse("classes:teach")).status_code == 200
    assert client.get(reverse("dashboard")).status_code == 200

    # Schedule a class: it belongs to them and shows up in their portal.
    response = client.post(reverse("classes:create"), class_form_data(chemistry))
    assert response.status_code == 302
    created = TutoringClass.objects.get()
    assert created.mentor == profile  # NULL for every class in 2022
    assert created.subject == chemistry
    assert created.subtopics.count() == 2
    assert b"Equilibrium" in client.get(reverse("classes:teach")).content


def test_reject(client, student, staff, chemistry, pdf, png, django_capture_on_commit_callbacks):
    client.force_login(student)
    apply(client, chemistry, pdf, png)
    application = MentorApplication.objects.get()
    client.force_login(staff)
    with django_capture_on_commit_callbacks(execute=True):
        client.post(
            reverse("accounts:review_decide", args=[application.pk]), {"decision": "reject"}
        )
    application.refresh_from_db()
    assert application.status == MentorApplication.Status.REJECTED
    assert not MentorProfile.objects.filter(user=student).exists()
    assert "aren't able to accept" in mail.outbox[0].body


def test_a_decision_is_final(student, staff, chemistry, make_application):
    application = make_application(student, chemistry)
    decide_application(application.pk, reviewer=staff, accept=False)
    with pytest.raises(ApplicationError, match="already been decided"):
        decide_application(application.pk, reviewer=staff, accept=True)
    assert not MentorProfile.objects.filter(user=student).exists()


def test_decision_over_htmx_returns_the_panel(client, student, staff, chemistry, make_application):
    application = make_application(student, chemistry)
    client.force_login(staff)
    response = client.post(
        reverse("accounts:review_decide", args=[application.pk]),
        {"decision": "accept"},
        headers={"HX-Request": "true"},
    )
    assert response.status_code == 200
    assert b'id="decision"' in response.content
    assert b"<html" not in response.content


def test_one_pending_application_at_a_time(client, student, chemistry, physics, pdf, png):
    client.force_login(student)
    apply(client, chemistry, pdf, png)
    response = apply(client, physics, pdf, png)
    assert response.status_code == 200
    assert b"in review" in response.content
    assert MentorApplication.objects.count() == 1


def test_mentor_can_apply_for_another_subject_only(mentor, chemistry, physics):
    form = MentorApplicationForm(user=mentor)
    assert list(form.fields["subject"].queryset) == [physics]


def test_staff_download_application_files(client, staff, student, chemistry, make_application):
    application = make_application(student, chemistry)
    client.force_login(staff)
    response = client.get(reverse("accounts:review_file", args=[application.pk, "cv"]))
    assert response.status_code == 200
    assert response["Content-Disposition"].startswith("attachment")
    assert b"".join(response.streaming_content).startswith(b"%PDF")
    assert (
        client.get(reverse("accounts:review_file", args=[application.pk, "bio"])).status_code == 404
    )


def test_uploads_are_stored_privately_under_random_names(student, chemistry, pdf, settings):
    application = MentorApplication.objects.create(
        user=student,
        subject=chemistry,
        bio="b",
        ap_experience="a",
        teaching_experience="t",
        motivation="m",
        score_report=pdf("my score report.pdf"),
        cv=pdf(),
    )
    assert "my score" not in application.score_report.name
    assert application.score_report.path.startswith(str(settings.PRIVATE_MEDIA_ROOT))
    with pytest.raises(ValueError):
        application.score_report.url  # noqa: B018  (private storage has no URL)


class TestClassForm:
    def test_topic_from_another_subject_is_rejected(self, client, mentor, chemistry, physics):
        client.force_login(mentor)
        foreign = physics.units.first().subtopics.first()
        response = client.post(
            reverse("classes:create"), class_form_data(chemistry, subtopics=[foreign.pk])
        )
        assert response.status_code == 200
        assert not TutoringClass.objects.exists()

    def test_subject_must_be_one_you_mentor(self, client, mentor, physics):
        client.force_login(mentor)
        response = client.post(reverse("classes:create"), class_form_data(physics))
        assert response.status_code == 200
        assert not TutoringClass.objects.exists()

    def test_start_time_must_be_in_the_future(self, client, mentor, chemistry):
        client.force_login(mentor)
        past = (timezone.localtime() - timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M")
        response = client.post(
            reverse("classes:create"), class_form_data(chemistry, starts_at=past)
        )
        assert b"in the future" in response.content

    def test_real_zoom_links_fit(self, client, mentor, chemistry):
        """The 2022 field was 30 characters, shorter than a real Zoom link."""
        client.force_login(mentor)
        long_link = "https://us02web.zoom.us/j/81234567890?pwd=" + "x" * 60
        client.post(reverse("classes:create"), class_form_data(chemistry, meeting_url=long_link))
        assert TutoringClass.objects.get().meeting_url == long_link

    def test_link_must_be_https(self, client, mentor, chemistry):
        client.force_login(mentor)
        response = client.post(
            reverse("classes:create"),
            class_form_data(chemistry, meeting_url="http://zoom.us/j/1"),
        )
        assert b"https://" in response.content
        assert not TutoringClass.objects.exists()

    def test_topic_picker_only_offers_your_subjects(self, client, mentor, chemistry, physics):
        client.force_login(mentor)
        ok = client.get(reverse("classes:subtopic_options"), {"subject": chemistry.pk})
        assert b"Topic 1.1" in ok.content
        other = client.get(reverse("classes:subtopic_options"), {"subject": physics.pk})
        assert b'type="checkbox"' not in other.content


def test_roster_is_visible_to_the_mentor_only(client, mentor, student, make_class, give_tokens):
    from classes.services import enrol

    give_tokens(student)
    tutoring_class = make_class()
    enrol(student, tutoring_class)
    client.force_login(mentor)
    assert b"student@example.com" in client.get(tutoring_class.get_absolute_url()).content
    client.force_login(student)
    assert b"Roster" not in client.get(tutoring_class.get_absolute_url()).content
