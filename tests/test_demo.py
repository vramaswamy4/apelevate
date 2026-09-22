"""Public-demo rules: visitors use shared accounts and can't take them over."""

import io

import pytest
from django.core.management import CommandError, call_command
from django.test import override_settings
from django.urls import reverse

from accounts.models import User
from core.demo import DEMO_PASSWORD

pytestmark = pytest.mark.usefixtures("demo_data")


@pytest.fixture
def demo_data(settings):
    settings.DEMO_MODE = True
    call_command("seed_curriculum", stdout=io.StringIO())
    call_command("seed_demo", stdout=io.StringIO())


def test_sign_in_page_lists_the_demo_accounts(client):
    body = client.get(reverse("accounts:login")).content.decode()
    assert "student@apelevate.test" in body
    assert DEMO_PASSWORD in body
    assert "demo-banner" in body


def test_sign_up_is_off(client):
    client.post(
        reverse("accounts:signup"),
        {
            "first_name": "A",
            "last_name": "B",
            "email": "real@example.com",
            "password1": "a-long-password-1",
            "password2": "a-long-password-1",
        },
    )
    assert not User.objects.filter(email="real@example.com").exists()


def test_demo_accounts_cant_change_password(client):
    user = User.objects.get(email="student@apelevate.test")
    client.force_login(user)
    response = client.post(
        reverse("accounts:password_change"),
        {
            "old_password": DEMO_PASSWORD,
            "new_password1": "taken-over-123",
            "new_password2": "taken-over-123",
        },
    )
    assert response.status_code == 302
    user.refresh_from_db()
    assert user.check_password(DEMO_PASSWORD)


def test_demo_accounts_cant_be_renamed(client):
    user = User.objects.get(email="mentor@apelevate.test")
    client.force_login(user)
    client.post(
        reverse("accounts:profile"),
        {
            "first_name": "Hacked",
            "last_name": "X",
            "email": "me@evil.example",
            "timezone": "Europe/London",
        },
    )
    user.refresh_from_db()
    assert (user.first_name, user.email) == ("Priya", "mentor@apelevate.test")
    assert user.timezone == "Europe/London"  # the harmless setting still works


def test_demo_staff_has_a_read_only_admin(client):
    admin = User.objects.get(email="admin@apelevate.test")
    assert admin.is_staff and not admin.is_superuser
    client.force_login(admin)
    assert client.get(reverse("admin:accounts_user_changelist")).status_code == 200
    assert client.get(reverse("admin:accounts_user_add")).status_code == 403


def test_reset_restores_the_demo(client):
    User.objects.filter(email="mentor@apelevate.test").update(first_name="Vandal")
    call_command("reset_demo", stdout=io.StringIO())
    assert User.objects.get(email="mentor@apelevate.test").first_name == "Priya"
    call_command("audit_wallets", stdout=io.StringIO())


@override_settings(DEMO_MODE=False)
def test_reset_refuses_outside_demo_and_debug():
    with pytest.raises(CommandError):
        call_command("reset_demo")
