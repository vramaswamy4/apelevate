import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.forms import ValidationError
from django.urls import reverse
from django.utils import timezone

from accounts.models import User
from accounts.validators import MAX_UPLOAD_BYTES, validate_document

from .conftest import PASSWORD, PDF_BYTES


def test_sign_in_with_email_in_any_case(client, student):
    response = client.post(
        reverse("accounts:login"), {"username": "STUDENT@example.com", "password": PASSWORD}
    )
    assert response.status_code == 302
    assert response.url == reverse("dashboard")


def test_wrong_password_is_rejected(client, student):
    response = client.post(reverse("accounts:login"), {"username": student.email, "password": "x"})
    assert response.status_code == 200
    assert b"alert--error" in response.content


def test_email_is_unique_ignoring_case(client, student):
    response = client.post(
        reverse("accounts:signup"),
        {
            "first_name": "A",
            "last_name": "B",
            "email": "Student@Example.com",
            "password1": "a-long-enough-password",
            "password2": "a-long-enough-password",
        },
    )
    assert response.status_code == 200
    assert b"already exists" in response.content
    assert User.objects.count() == 1


def test_signup_requires_names(client):
    response = client.post(
        reverse("accounts:signup"),
        {
            "email": "x@example.com",
            "password1": "a-long-password-1",
            "password2": "a-long-password-1",
        },
    )
    assert response.status_code == 200
    assert not User.objects.exists()


def test_superusers_work_without_extra_setup(client):
    """createsuperuser users crashed most pages in 2022 (no Students row)."""
    admin = User.objects.create_superuser("root@example.com", PASSWORD)
    client.force_login(admin)
    assert client.get(reverse("dashboard")).status_code == 200
    assert client.get(reverse("accounts:review_list")).status_code == 200


def test_logout_is_post_only(client, student):
    client.force_login(student)
    assert client.get(reverse("accounts:logout")).status_code == 405
    client.post(reverse("accounts:logout"))
    assert client.get(reverse("dashboard")).status_code == 302


def test_profile_timezone_changes_how_times_render(client, student, make_class):
    tutoring_class = make_class()
    client.force_login(student)
    client.post(
        reverse("accounts:profile"),
        {
            "first_name": "Sam",
            "last_name": "Carter",
            "email": student.email,
            "timezone": "Asia/Dubai",
        },
    )
    student.refresh_from_db()
    assert student.timezone == "Asia/Dubai"
    local = timezone.localtime(
        tutoring_class.starts_at, timezone=__import__("zoneinfo").ZoneInfo("Asia/Dubai")
    )
    page = client.get(tutoring_class.get_absolute_url()).content.decode()
    assert local.strftime("%-I:%M") in page
    assert "+04" in page or "Asia/Dubai" in page or "+0400" in page


def test_password_reset_sends_a_link(client, student, mailoutbox):
    client.post(reverse("accounts:password_reset"), {"email": student.email})
    assert len(mailoutbox) == 1
    assert "/accounts/password/reset/" in mailoutbox[0].body


class TestDocumentValidation:
    def test_pdf_is_accepted(self):
        validate_document(SimpleUploadedFile("cv.pdf", PDF_BYTES))

    @pytest.mark.parametrize("name", ["cv.exe", "cv.html", "cv.docx", "cv"])
    def test_other_types_are_refused(self, name):
        with pytest.raises(ValidationError, match="PDF, PNG or JPEG"):
            validate_document(SimpleUploadedFile(name, PDF_BYTES))

    def test_renamed_file_is_refused(self):
        with pytest.raises(ValidationError, match="don't match"):
            validate_document(SimpleUploadedFile("cv.pdf", b"<script>alert(1)</script>"))

    def test_large_file_is_refused(self):
        big = SimpleUploadedFile("cv.pdf", PDF_BYTES + b"0" * MAX_UPLOAD_BYTES)
        with pytest.raises(ValidationError, match="5 MB"):
            validate_document(big)
