"""Payment providers.

The browser never tells the server that a payment succeeded. The server creates the order, the
buyer approves it in PayPal's popup, and then the server captures it and reads the amount,
currency and reference from PayPal's response before crediting anything.

``FakeProvider`` implements the same interface without a network, for development and tests.
"""

import logging
import time
import uuid
from dataclasses import dataclass
from decimal import Decimal

import httpx
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

log = logging.getLogger(__name__)


class PaymentProviderError(Exception):
    """The provider couldn't be reached or returned something unusable."""


@dataclass(frozen=True)
class Capture:
    order_id: str
    status: str  # "COMPLETED" when money has moved
    amount_cents: int
    currency: str
    reference: str  # our TokenPurchase id, echoed back by the provider


def _to_cents(value: str) -> int:
    return int(Decimal(value) * 100)


def _to_decimal_string(cents: int) -> str:
    return f"{Decimal(cents) / 100:.2f}"


class FakeProvider:
    name = "fake"
    is_test = True

    def create_order(self, purchase) -> str:
        return f"FAKE-{uuid.uuid4().hex[:16].upper()}"

    def capture(self, purchase) -> Capture:
        return Capture(
            order_id=purchase.provider_order_id,
            status="COMPLETED",
            amount_cents=purchase.amount_cents,
            currency=purchase.currency,
            reference=str(purchase.pk),
        )


class PayPalProvider:
    """PayPal Orders v2 over REST.

    Both calls send a ``PayPal-Request-Id`` derived from our purchase id, so retrying a request
    (a timeout, a double click, the reconcile command) returns the original result instead of
    creating a second order or capturing twice.
    """

    name = "paypal"
    is_test = False
    BASE_URLS = {
        "sandbox": "https://api-m.sandbox.paypal.com",
        "live": "https://api-m.paypal.com",
    }

    def __init__(self, client_id, client_secret, environment="sandbox", transport=None):
        if environment not in self.BASE_URLS:
            raise ImproperlyConfigured(f"PAYPAL_ENVIRONMENT must be one of {list(self.BASE_URLS)}")
        self.client_id = client_id
        self.client_secret = client_secret
        self.environment = environment
        self._http = httpx.Client(
            base_url=self.BASE_URLS[environment], timeout=15.0, transport=transport
        )
        self._token = None
        self._token_expires = 0.0

    def _access_token(self) -> str:
        if self._token and time.monotonic() < self._token_expires:
            return self._token
        response = self._request(
            "POST",
            "/v1/oauth2/token",
            auth=(self.client_id, self.client_secret),
            data={"grant_type": "client_credentials"},
        )
        body = response.json()
        self._token = body["access_token"]
        self._token_expires = time.monotonic() + int(body.get("expires_in", 300)) - 60
        return self._token

    def _request(self, method, path, **kwargs) -> httpx.Response:
        try:
            response = self._http.request(method, path, **kwargs)
        except httpx.HTTPError as exc:
            raise PaymentProviderError(f"PayPal unreachable: {exc.__class__.__name__}") from exc
        return response

    def _authed(self, method, path, *, request_id=None, **kwargs) -> httpx.Response:
        headers = {"Authorization": f"Bearer {self._access_token()}"}
        if request_id:
            headers["PayPal-Request-Id"] = request_id
        headers["Prefer"] = "return=representation"
        return self._request(method, path, headers=headers, **kwargs)

    def create_order(self, purchase) -> str:
        response = self._authed(
            "POST",
            "/v2/checkout/orders",
            request_id=f"apelevate-order-{purchase.pk}",
            json={
                "intent": "CAPTURE",
                "purchase_units": [
                    {
                        "reference_id": str(purchase.pk),
                        "custom_id": str(purchase.pk),
                        "description": f"APElevate: {purchase.tokens} class tokens",
                        "amount": {
                            "currency_code": purchase.currency,
                            "value": _to_decimal_string(purchase.amount_cents),
                        },
                    }
                ],
            },
        )
        if response.status_code not in (200, 201):
            log.warning("paypal create_order %s: %s", response.status_code, response.text[:500])
            raise PaymentProviderError("PayPal refused to create the order.")
        return response.json()["id"]

    def capture(self, purchase) -> Capture:
        order_id = purchase.provider_order_id
        response = self._authed(
            "POST",
            f"/v2/checkout/orders/{order_id}/capture",
            request_id=f"apelevate-capture-{purchase.pk}",
        )
        if response.status_code == 422 and "ORDER_ALREADY_CAPTURED" in response.text:
            response = self._authed("GET", f"/v2/checkout/orders/{order_id}")
        if response.status_code not in (200, 201):
            log.warning("paypal capture %s: %s", response.status_code, response.text[:500])
            raise PaymentProviderError("PayPal couldn't capture the payment.")
        return self._parse_capture(response.json())

    @staticmethod
    def _parse_capture(order: dict) -> Capture:
        try:
            unit = order["purchase_units"][0]
            captures = unit.get("payments", {}).get("captures", [])
            capture = captures[0] if captures else {}
            amount = capture.get("amount") or unit["amount"]
            return Capture(
                order_id=order["id"],
                status=capture.get("status", order.get("status", "")),
                amount_cents=_to_cents(amount["value"]),
                currency=amount["currency_code"],
                reference=capture.get("custom_id") or unit.get("custom_id", ""),
            )
        except (KeyError, IndexError, TypeError, ArithmeticError) as exc:
            raise PaymentProviderError("Unexpected response from PayPal.") from exc


def get_provider():
    backend = settings.PAYMENTS_BACKEND
    if backend == "fake":
        return FakeProvider()
    if backend == "paypal":
        return PayPalProvider(
            settings.PAYPAL_CLIENT_ID,
            settings.PAYPAL_CLIENT_SECRET,
            settings.PAYPAL_ENVIRONMENT,
        )
    raise ImproperlyConfigured(f"Unknown PAYMENTS_BACKEND {backend!r}")
