from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from payments.models import TokenPurchase
from payments.providers import PaymentProviderError, get_provider
from payments.services import PaymentVerificationError, complete_purchase


class Command(BaseCommand):
    help = (
        "Retry the capture of purchases left 'awaiting payment' (for example, the buyer's browser "
        "closed after approving). Captures are idempotent, so this is safe to run on a schedule."
    )

    def add_arguments(self, parser):
        parser.add_argument("--older-than-minutes", type=int, default=10)

    def handle(self, *args, older_than_minutes, **options):
        cutoff = timezone.now() - timedelta(minutes=older_than_minutes)
        stuck = TokenPurchase.objects.filter(
            status=TokenPurchase.Status.CREATED,
            provider_order_id__isnull=False,
            created_at__lt=cutoff,
        )
        provider = get_provider()
        completed = failed = 0
        for purchase in stuck.filter(provider=provider.name):
            try:
                complete_purchase(purchase, provider=provider)
                completed += 1
            except (PaymentProviderError, PaymentVerificationError) as exc:
                failed += 1
                self.stderr.write(f"purchase {purchase.pk}: {exc}")
        self.stdout.write(f"Reconciled: {completed} completed, {failed} not payable.")
