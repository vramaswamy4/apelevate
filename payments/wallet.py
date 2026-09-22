"""The only code that changes a token balance.

Every change writes a ledger row and moves ``User.token_balance`` by the same amount in one
transaction. The balance update is a single ``UPDATE ... SET token_balance = token_balance + n``,
so concurrent updates can't lose each other, and the ``token_balance_non_negative`` check
constraint rejects any debit that would overdraw. There's no read-then-write race to lose.
"""

from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.db.models import F, Sum
from django.utils import timezone

from .models import TokenEntry, TokenPurchase


class InsufficientTokens(Exception):
    pass


def _move(user_id, delta, **entry):
    if not transaction.get_connection().in_atomic_block:
        raise RuntimeError("Token balance changes must run inside transaction.atomic().")
    try:
        with transaction.atomic():
            get_user_model().objects.filter(pk=user_id).update(
                token_balance=F("token_balance") + delta
            )
    except IntegrityError as exc:
        raise InsufficientTokens from exc
    return TokenEntry.objects.create(user_id=user_id, delta=delta, **entry)


def debit_for_enrolment(enrolment) -> TokenEntry:
    return _move(
        enrolment.student_id,
        -enrolment.tokens_spent,
        kind=TokenEntry.Kind.ENROLMENT,
        enrolment=enrolment,
    )


def credit_purchase(purchase_id) -> bool:
    """Credit a verified purchase. Returns False if it was already credited (safe to replay)."""
    with transaction.atomic():
        purchase = TokenPurchase.objects.select_for_update().get(pk=purchase_id)
        if purchase.status == TokenPurchase.Status.COMPLETED:
            return False
        _move(purchase.user_id, purchase.tokens, kind=TokenEntry.Kind.PURCHASE, purchase=purchase)
        purchase.status = TokenPurchase.Status.COMPLETED
        purchase.completed_at = timezone.now()
        purchase.failure_reason = ""
        purchase.save(update_fields=["status", "completed_at", "failure_reason"])
    return True


def ledger_balance(user) -> int:
    return TokenEntry.objects.filter(user=user).aggregate(total=Sum("delta"))["total"] or 0
