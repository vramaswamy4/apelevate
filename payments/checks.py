from django.conf import settings
from django.core.checks import Error, Tags, Warning, register


@register(Tags.security, deploy=True)
def payments_backend_check(app_configs, **kwargs):
    """Part of `manage.py check --deploy`: production must take real payments."""
    backend = settings.PAYMENTS_BACKEND
    if backend == "fake":
        return [
            Warning(
                "PAYMENTS_BACKEND is 'fake': anyone can add tokens without paying.",
                hint="Set PAYMENTS_BACKEND=paypal with PayPal credentials in production.",
                id="payments.W001",
            )
        ]
    if backend == "paypal" and not (settings.PAYPAL_CLIENT_ID and settings.PAYPAL_CLIENT_SECRET):
        return [
            Error(
                "PAYMENTS_BACKEND is 'paypal' but PayPal credentials are missing.",
                hint="Set PAYPAL_CLIENT_ID and PAYPAL_CLIENT_SECRET.",
                id="payments.E001",
            )
        ]
    return []
