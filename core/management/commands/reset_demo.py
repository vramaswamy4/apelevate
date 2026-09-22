from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Wipe every table and reload the curriculum and demo data. Public demo and dev only."

    def handle(self, *args, **options):
        if not (settings.DEBUG or settings.DEMO_MODE):
            raise CommandError("reset_demo only runs with DJANGO_DEBUG=1 or DEMO_MODE=1.")
        call_command("flush", interactive=False, verbosity=0)
        call_command("seed_curriculum", stdout=self.stdout)
        call_command("seed_demo", stdout=self.stdout)
