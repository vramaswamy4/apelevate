from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db.models import F, Sum
from django.db.models.functions import Coalesce


class Command(BaseCommand):
    help = "Check every user's token balance against their ledger. Exits non-zero on a mismatch."

    def handle(self, *args, **options):
        mismatched = (
            get_user_model()
            .objects.annotate(ledger=Coalesce(Sum("token_entries__delta"), 0))
            .exclude(token_balance=F("ledger"))
            .values_list("pk", "token_balance", "ledger")
        )
        rows = list(mismatched)
        for pk, balance, ledger in rows:
            self.stderr.write(f"user {pk}: balance {balance}, ledger {ledger}")
        if rows:
            raise CommandError(f"{len(rows)} wallet(s) disagree with the ledger.")
        self.stdout.write("All balances match the ledger.")
