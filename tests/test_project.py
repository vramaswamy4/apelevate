"""Project-level guarantees: settings, system checks, migrations, commands."""

import io

import pytest
from django.core.management import call_command
from django.test import override_settings


def test_migrations_match_models():
    call_command("makemigrations", "--check", "--dry-run", stdout=io.StringIO())


def test_deploy_check_flags_fake_payments():
    from payments.checks import payments_backend_check

    with override_settings(PAYMENTS_BACKEND="fake"):
        assert [m.id for m in payments_backend_check(None)] == ["payments.W001"]
    with override_settings(PAYMENTS_BACKEND="paypal", PAYPAL_CLIENT_ID="", PAYPAL_CLIENT_SECRET=""):
        assert [m.id for m in payments_backend_check(None)] == ["payments.E001"]
    with override_settings(
        PAYMENTS_BACKEND="paypal", PAYPAL_CLIENT_ID="a", PAYPAL_CLIENT_SECRET="b"
    ):
        assert payments_backend_check(None) == []


def test_production_settings_refuse_to_start_without_a_secret(monkeypatch):
    import importlib

    from django.core.exceptions import ImproperlyConfigured

    import config.settings as settings_module

    monkeypatch.setenv("DJANGO_DEBUG", "0")
    monkeypatch.setenv("DJANGO_SECRET_KEY", "")
    with pytest.raises(ImproperlyConfigured, match="DJANGO_SECRET_KEY"):
        importlib.reload(settings_module)
    monkeypatch.setenv("DJANGO_SECRET_KEY", "x" * 50)
    importlib.reload(settings_module)


def test_seed_demo_refuses_outside_debug():
    from django.core.management import CommandError

    with pytest.raises(CommandError, match="DJANGO_DEBUG"):
        call_command("seed_demo")


@override_settings(DEBUG=True)
def test_seed_demo_builds_a_consistent_dataset():
    call_command("seed_curriculum", stdout=io.StringIO())
    call_command("seed_demo", stdout=io.StringIO())
    call_command("audit_wallets", stdout=io.StringIO())
    call_command("seed_demo", stdout=io.StringIO())  # second run is a no-op


def test_error_pages_render(client):
    response = client.get("/no-such-page/")
    assert response.status_code == 404
    assert b"Page not found" in response.content
