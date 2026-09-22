"""Buying tokens: start a checkout, then verify and credit it."""

import logging

from .bundles import CURRENCY
from .models import TokenPurchase
from .providers import PaymentProviderError, get_provider
from .wallet import credit_purchase

log = logging.getLogger(__name__)


class PaymentVerificationError(Exception):
    """The provider says something other than "paid in full, for this purchase"."""


def start_purchase(user, bundle, provider=None) -> TokenPurchase:
    provider = provider or get_provider()
    purchase = TokenPurchase.objects.create(
        user=user,
        bundle=bundle.key,
        tokens=bundle.tokens,
        amount_cents=bundle.price_cents,
        currency=CURRENCY,
        provider=provider.name,
    )
    purchase.provider_order_id = provider.create_order(purchase)
    purchase.save(update_fields=["provider_order_id"])
    log.info("purchase %s created, order %s", purchase.pk, purchase.provider_order_id)
    return purchase


def complete_purchase(purchase, provider=None) -> TokenPurchase:
    """Capture the order and credit tokens if, and only if, the provider confirms full payment.

    Idempotent: completing an already-completed purchase does nothing, and the capture call
    itself is idempotent on the provider side. The network call happens outside any database
    transaction so a slow provider never holds a row lock.
    """
    if purchase.status == TokenPurchase.Status.COMPLETED:
        return purchase
    provider = provider or get_provider()
    capture = provider.capture(purchase)
    problems = []
    if capture.order_id != purchase.provider_order_id:
        problems.append("order id mismatch")
    if capture.status != "COMPLETED":
        problems.append(f"status {capture.status or 'missing'}")
    if capture.amount_cents != purchase.amount_cents or capture.currency != purchase.currency:
        problems.append(f"amount {capture.amount_cents} {capture.currency}")
    if capture.reference != str(purchase.pk):
        problems.append("reference mismatch")
    if problems:
        reason = "; ".join(problems)
        TokenPurchase.objects.filter(pk=purchase.pk).update(
            status=TokenPurchase.Status.FAILED, failure_reason=reason[:200]
        )
        log.warning("purchase %s failed verification: %s", purchase.pk, reason)
        raise PaymentVerificationError(reason)
    credit_purchase(purchase.pk)
    purchase.refresh_from_db()
    log.info("purchase %s completed: %s tokens", purchase.pk, purchase.tokens)
    return purchase


__all__ = [
    "PaymentProviderError",
    "PaymentVerificationError",
    "complete_purchase",
    "start_purchase",
]
