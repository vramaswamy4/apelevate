"""Buying tokens. The server, not the browser, decides whether a payment happened.

In 2022, GET /payment-complete/<price> added tokens to whoever visited it.
"""

import json

import httpx
import pytest
from django.urls import reverse

from payments.bundles import BUNDLES, get_bundle
from payments.models import TokenEntry, TokenPurchase
from payments.providers import Capture, FakeProvider, PaymentProviderError, PayPalProvider
from payments.services import PaymentVerificationError, complete_purchase, start_purchase
from payments.wallet import credit_purchase, ledger_balance


def test_the_2022_exploit_is_gone(client, student):
    client.force_login(student)
    assert client.get("/payment-complete/180").status_code == 404
    assert client.get(reverse("payments:capture", args=[1])).status_code == 405
    student.refresh_from_db()
    assert student.token_balance == 0


def test_bundles_keep_the_2022_prices():
    assert [(b.tokens, b.price_cents) for b in BUNDLES] == [
        (1, 2000),
        (5, 8000),
        (10, 12000),
        (20, 18000),
    ]


def test_unknown_bundle_is_a_404(client, student):
    client.force_login(student)
    assert client.post(reverse("payments:checkout", args=["free"])).status_code == 404


def test_price_comes_from_the_server_not_the_request(client, student):
    client.force_login(student)
    client.post(reverse("payments:checkout", args=["twenty"]), {"amount": "1"})
    purchase = TokenPurchase.objects.get()
    assert (purchase.tokens, purchase.amount_cents) == (20, 18000)


def test_capturing_twice_credits_once(client, student):
    client.force_login(student)
    client.post(reverse("payments:checkout", args=["five"]))
    purchase = TokenPurchase.objects.get()
    for _ in range(3):
        client.post(reverse("payments:capture", args=[purchase.pk]))
    student.refresh_from_db()
    assert student.token_balance == 5
    assert TokenEntry.objects.filter(purchase=purchase).count() == 1


def test_cannot_capture_someone_elses_purchase(client, student, make_user):
    other = make_user()
    purchase = start_purchase(other, get_bundle("ten"))
    client.force_login(student)
    assert client.post(reverse("payments:capture", args=[purchase.pk])).status_code == 404
    assert client.get(reverse("payments:receipt", args=[purchase.pk])).status_code == 404
    assert client.get(reverse("payments:test_pay", args=[purchase.pk])).status_code == 404


def test_json_checkout_for_paypal_buttons(client, student):
    client.force_login(student)
    response = client.post(
        reverse("payments:checkout", args=["single"]), headers={"Accept": "application/json"}
    )
    body = response.json()
    assert body["orderID"].startswith("FAKE-")
    response = client.post(
        reverse("payments:capture", args=[body["purchaseId"]]),
        headers={"Accept": "application/json"},
    )
    assert response.json()["redirect"] == reverse("payments:receipt", args=[body["purchaseId"]])


class LyingProvider(FakeProvider):
    """Reports a capture that doesn't match the purchase."""

    def __init__(self, **changes):
        self.changes = changes

    def capture(self, purchase):
        honest = super().capture(purchase)
        return Capture(**{**honest.__dict__, **self.changes})


@pytest.mark.parametrize(
    "changes",
    [
        {"amount_cents": 100},
        {"currency": "EUR"},
        {"status": "PENDING"},
        {"reference": "999"},
        {"order_id": "SOMEONE-ELSES"},
    ],
    ids=["underpaid", "wrong-currency", "not-completed", "wrong-reference", "wrong-order"],
)
def test_unverified_capture_credits_nothing(student, changes):
    purchase = start_purchase(student, get_bundle("ten"), provider=FakeProvider())
    with pytest.raises(PaymentVerificationError):
        complete_purchase(purchase, provider=LyingProvider(**changes))
    purchase.refresh_from_db()
    student.refresh_from_db()
    assert purchase.status == TokenPurchase.Status.FAILED
    assert purchase.failure_reason
    assert student.token_balance == 0
    assert not TokenEntry.objects.exists()


def test_failed_capture_shows_a_message(client, student, monkeypatch):
    client.force_login(student)
    client.post(reverse("payments:checkout", args=["five"]))
    purchase = TokenPurchase.objects.get()
    monkeypatch.setattr("payments.services.get_provider", lambda: LyingProvider(status="DECLINED"))
    response = client.post(reverse("payments:capture", args=[purchase.pk]), follow=True)
    assert b"no tokens were added" in response.content


# --- PayPal over HTTP, with the network replaced by httpx.MockTransport ------------------------


class FakePayPal:
    """Just enough of the Orders v2 API to test our client against."""

    def __init__(self, capture_status="COMPLETED", amount=None, already_captured=False):
        self.capture_status = capture_status
        self.amount = amount
        self.already_captured = already_captured
        self.requests: list[httpx.Request] = []
        self.orders: dict[str, dict] = {}

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        path = request.url.path
        if path == "/v1/oauth2/token":
            return httpx.Response(200, json={"access_token": "tok", "expires_in": 3600})
        assert request.headers["Authorization"] == "Bearer tok"
        if path == "/v2/checkout/orders" and request.method == "POST":
            body = json.loads(request.content)
            order_id = f"ORDER{len(self.orders) + 1}"
            self.orders[order_id] = body["purchase_units"][0]
            return httpx.Response(201, json={"id": order_id, "status": "CREATED"})
        order_id = path.split("/")[4]
        unit = self.orders[order_id]
        amount = self.amount or unit["amount"]
        order = {
            "id": order_id,
            "status": "COMPLETED",
            "purchase_units": [
                {
                    "reference_id": unit["reference_id"],
                    "amount": unit["amount"],
                    "payments": {
                        "captures": [
                            {
                                "status": self.capture_status,
                                "amount": amount,
                                "custom_id": unit["custom_id"],
                            }
                        ]
                    },
                }
            ],
        }
        if path.endswith("/capture"):
            if self.already_captured:
                return httpx.Response(422, json={"details": [{"issue": "ORDER_ALREADY_CAPTURED"}]})
            return httpx.Response(201, json=order)
        return httpx.Response(200, json=order)


def paypal(fake):
    return PayPalProvider("id", "secret", "sandbox", transport=httpx.MockTransport(fake))


def test_paypal_happy_path(student):
    fake = FakePayPal()
    provider = paypal(fake)
    purchase = start_purchase(student, get_bundle("five"), provider=provider)
    create = fake.requests[1]
    assert json.loads(create.content)["purchase_units"][0]["amount"] == {
        "currency_code": "USD",
        "value": "80.00",
    }
    assert create.headers["PayPal-Request-Id"] == f"apelevate-order-{purchase.pk}"

    complete_purchase(purchase, provider=provider)
    capture = fake.requests[-1]
    assert capture.url.path == f"/v2/checkout/orders/{purchase.provider_order_id}/capture"
    assert capture.headers["PayPal-Request-Id"] == f"apelevate-capture-{purchase.pk}"
    student.refresh_from_db()
    assert student.token_balance == 5
    # The OAuth token was fetched once and reused.
    assert sum(r.url.path == "/v1/oauth2/token" for r in fake.requests) == 1


def test_paypal_underpayment_is_refused(student):
    fake = FakePayPal(amount={"currency_code": "USD", "value": "1.00"})
    provider = paypal(fake)
    purchase = start_purchase(student, get_bundle("five"), provider=provider)
    with pytest.raises(PaymentVerificationError, match="amount"):
        complete_purchase(purchase, provider=provider)
    student.refresh_from_db()
    assert student.token_balance == 0


def test_paypal_pending_capture_is_refused(student):
    provider = paypal(FakePayPal(capture_status="PENDING"))
    purchase = start_purchase(student, get_bundle("five"), provider=provider)
    with pytest.raises(PaymentVerificationError, match="PENDING"):
        complete_purchase(purchase, provider=provider)


def test_paypal_already_captured_reads_the_order(student):
    """A retry after a lost response: PayPal says 'already captured', we read the result."""
    fake = FakePayPal(already_captured=True)
    provider = paypal(fake)
    purchase = start_purchase(student, get_bundle("single"), provider=provider)
    complete_purchase(purchase, provider=provider)
    assert fake.requests[-1].method == "GET"
    student.refresh_from_db()
    assert student.token_balance == 1


def test_paypal_unreachable_raises_a_provider_error(student):
    def down(request):
        raise httpx.ConnectError("no route", request=request)

    provider = PayPalProvider("id", "secret", transport=httpx.MockTransport(down))
    purchase = TokenPurchase.objects.create(
        user=student, bundle="five", tokens=5, amount_cents=8000, provider="paypal"
    )
    with pytest.raises(PaymentProviderError, match="unreachable"):
        provider.create_order(purchase)


def test_reconcile_completes_abandoned_captures(student):
    from datetime import timedelta

    from django.core.management import call_command
    from django.utils import timezone

    purchase = start_purchase(student, get_bundle("ten"))
    TokenPurchase.objects.filter(pk=purchase.pk).update(
        created_at=timezone.now() - timedelta(hours=1)
    )
    call_command("reconcile_purchases")
    student.refresh_from_db()
    assert student.token_balance == 10


# --- The ledger ---------------------------------------------------------------------------------


def test_balance_always_equals_the_ledger(student, make_class, give_tokens):
    from classes.services import enrol

    give_tokens(student, "ten")
    give_tokens(student, "single")
    for i in range(4):
        enrol(student, make_class(title=f"Class {i}"))
    student.refresh_from_db()
    assert student.token_balance == ledger_balance(student) == 7


def test_database_refuses_a_negative_balance(student):
    from django.db import IntegrityError, transaction

    from accounts.models import User

    with pytest.raises(IntegrityError), transaction.atomic():
        User.objects.filter(pk=student.pk).update(token_balance=-1)


def test_crediting_a_purchase_is_idempotent(student):
    purchase = start_purchase(student, get_bundle("five"))
    assert credit_purchase(purchase.pk) is True
    assert credit_purchase(purchase.pk) is False
    student.refresh_from_db()
    assert student.token_balance == 5


def test_balance_changes_must_be_in_a_transaction(student):
    from unittest import mock

    from django.db import connection

    from payments.wallet import _move

    # pytest-django wraps each test in a transaction; simulate code running outside one.
    with (
        mock.patch.object(connection, "in_atomic_block", False),
        pytest.raises(RuntimeError, match="transaction"),
    ):
        _move(student.pk, 5, kind="adjustment")


def test_audit_command_detects_drift(student, give_tokens):
    from django.core.management import CommandError, call_command

    from accounts.models import User

    give_tokens(student)
    call_command("audit_wallets")
    User.objects.filter(pk=student.pk).update(token_balance=99)
    with pytest.raises(CommandError, match="1 wallet"):
        call_command("audit_wallets")
