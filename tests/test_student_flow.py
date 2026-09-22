"""A student signs up, buys tokens, finds a class, enrols and gets the Zoom link.

In the 2022 app this flow broke in three places: sign-up crashed without hand-made auth groups,
tokens could be added by visiting a URL, and new classes never appeared in the class list.
"""

from datetime import timedelta

import pytest
from django.urls import reverse

from accounts.models import User
from classes.models import Enrolment
from classes.services import EnrolmentError, enrol
from payments.models import TokenEntry


def test_full_student_journey(client, make_class):
    tutoring_class = make_class(title="Rate laws")

    # Sign up: signed in straight away, no groups needed.
    response = client.post(
        reverse("accounts:signup"),
        {
            "first_name": "Maya",
            "last_name": "Singh",
            "email": "Maya@Example.com",
            "password1": "a-long-enough-password",
            "password2": "a-long-enough-password",
        },
    )
    assert response.status_code == 302
    user = User.objects.get(email="maya@example.com")  # stored lowercased
    assert user.token_balance == 0

    # A brand-new class with nobody enrolled is listed (it wasn't in 2022).
    assert b"Rate laws" in client.get(reverse("classes:list")).content

    # Before enrolling, the Zoom details are hidden.
    detail = client.get(tutoring_class.get_absolute_url())
    assert b"s3cret" not in detail.content

    # Buy five tokens through the (fake) provider: checkout, then server-side capture.
    response = client.post(reverse("payments:checkout", args=["five"]))
    assert response.status_code == 302
    purchase = user.token_purchases.get()
    response = client.post(reverse("payments:capture", args=[purchase.pk]))
    assert response.status_code == 302
    user.refresh_from_db()
    assert user.token_balance == 5

    # Enrol: one token spent, Zoom details now visible, class listed under My classes.
    response = client.post(reverse("classes:enrol", args=[tutoring_class.pk]))
    assert response.status_code == 302
    user.refresh_from_db()
    assert user.token_balance == 4
    assert b"s3cret" in client.get(tutoring_class.get_absolute_url()).content
    assert b"Rate laws" in client.get(reverse("classes:mine")).content


def test_enrol_over_htmx_returns_the_panel_and_updated_balance(
    client, student, make_class, give_tokens
):
    give_tokens(student, "single")
    tutoring_class = make_class()
    client.force_login(student)
    response = client.post(
        reverse("classes:enrol", args=[tutoring_class.pk]), headers={"HX-Request": "true"}
    )
    assert response.status_code == 200
    body = response.content.decode()
    assert 'id="enrol-panel"' in body
    assert "You're enrolled" in body
    assert 'hx-swap-oob="true"' in body  # nav balance updates in place
    assert "<html" not in body


class TestEnrolmentRules:
    def test_costs_one_token(self, student, make_class, give_tokens):
        give_tokens(student, "five")
        enrolment = enrol(student, make_class())
        student.refresh_from_db()
        assert student.token_balance == 4
        assert enrolment.token_entry.delta == -1

    def test_needs_a_token(self, student, make_class):
        with pytest.raises(EnrolmentError, match="balance is empty"):
            enrol(student, make_class())
        assert not Enrolment.objects.exists()
        assert not TokenEntry.objects.exists()

    def test_once_per_class(self, student, make_class, give_tokens):
        give_tokens(student, "five")
        tutoring_class = make_class()
        enrol(student, tutoring_class)
        with pytest.raises(EnrolmentError, match="already enrolled"):
            enrol(student, tutoring_class)
        student.refresh_from_db()
        assert student.token_balance == 4  # the second attempt charged nothing

    def test_not_after_the_class_starts(self, student, make_class, give_tokens):
        give_tokens(student)
        with pytest.raises(EnrolmentError, match="already started"):
            enrol(student, make_class(starts_in=-timedelta(minutes=1)))

    def test_not_in_your_own_class(self, mentor, make_class, give_tokens):
        give_tokens(mentor)
        with pytest.raises(EnrolmentError, match="own class"):
            enrol(mentor, make_class())

    def test_last_token_can_only_be_spent_once(self, student, make_class, give_tokens):
        give_tokens(student, "single")
        enrol(student, make_class(title="A"))
        with pytest.raises(EnrolmentError, match="balance is empty"):
            enrol(student, make_class(title="B"))
        assert student.enrolments.count() == 1


def test_failed_enrolment_shows_an_error_not_a_crash(client, student, make_class):
    client.force_login(student)
    tutoring_class = make_class()
    response = client.post(reverse("classes:enrol", args=[tutoring_class.pk]), follow=True)
    assert response.status_code == 200
    assert b"balance is empty" in response.content


def test_filters_narrow_the_class_list(client, make_class, physics, make_user):
    from accounts.models import MentorProfile

    other = make_user(first_name="Omar")
    MentorProfile.objects.create(user=other, bio="b").subjects.add(physics)
    make_class(title="Chem class")
    make_class(title="Physics class", mentor_user=other, subject=physics)
    response = client.get(reverse("classes:list"), {"subject": physics.slug})
    assert b"Physics class" in response.content
    assert b"Chem class" not in response.content


def test_filter_request_from_htmx_returns_only_the_results(client, make_class):
    make_class()
    response = client.get(reverse("classes:list"), headers={"HX-Request": "true"})
    assert b"<html" not in response.content
    assert b"class-card" in response.content


def test_unknown_class_is_a_404(client):
    assert client.get(reverse("classes:detail", args=[999])).status_code == 404


def test_class_requests(client, student, chemistry):
    client.force_login(student)
    unit = chemistry.units.first()
    client.post(reverse("classes:requests"), {"unit": unit.pk, "notes": "Moles please"})
    request = student.class_requests.get()
    assert request.is_open
    client.post(reverse("classes:close_request", args=[request.pk]))
    request.refresh_from_db()
    assert not request.is_open


def test_cannot_close_someone_elses_request(client, student, make_user, chemistry):
    other = make_user()
    request = other.class_requests.create(unit=chemistry.units.first())
    client.force_login(student)
    assert client.post(reverse("classes:close_request", args=[request.pk])).status_code == 404
