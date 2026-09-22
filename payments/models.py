from django.conf import settings
from django.db import models
from django.db.models import Q


class TokenPurchase(models.Model):
    """One checkout attempt with the payment provider."""

    class Status(models.TextChoices):
        CREATED = "created", "Awaiting payment"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="token_purchases"
    )
    bundle = models.CharField(max_length=20)
    tokens = models.PositiveSmallIntegerField()
    amount_cents = models.PositiveIntegerField()
    currency = models.CharField(max_length=3, default="USD")
    provider = models.CharField(max_length=20)
    # NULL until the provider returns an id; NULLs don't collide in the unique constraint below.
    provider_order_id = models.CharField(max_length=64, null=True, blank=True)  # noqa: DJ001
    status = models.CharField(
        max_length=10, choices=Status.choices, default=Status.CREATED, db_index=True
    )
    failure_reason = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["provider", "provider_order_id"], name="unique_provider_order"
            ),
        ]

    def __str__(self):
        return f"{self.tokens} tokens for {self.user} ({self.get_status_display()})"


class TokenEntry(models.Model):
    """The token ledger. ``User.token_balance`` always equals the sum of a user's entries.

    Each purchase can credit at most once and each enrolment can debit at most once: the
    one-to-one columns are unique, so replaying a capture or an enrolment can't double-count.
    """

    class Kind(models.TextChoices):
        PURCHASE = "purchase", "Purchase"
        ENROLMENT = "enrolment", "Enrolment"
        ADJUSTMENT = "adjustment", "Adjustment"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="token_entries"
    )
    delta = models.IntegerField()
    kind = models.CharField(max_length=12, choices=Kind.choices)
    purchase = models.OneToOneField(
        TokenPurchase, on_delete=models.PROTECT, null=True, blank=True, related_name="entry"
    )
    enrolment = models.OneToOneField(
        "classes.Enrolment",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="token_entry",
    )
    memo = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-pk"]
        verbose_name_plural = "token entries"
        constraints = [
            models.CheckConstraint(condition=~Q(delta=0), name="token_entry_non_zero"),
        ]

    def __str__(self):
        return f"{self.delta:+d} for {self.user} ({self.kind})"
