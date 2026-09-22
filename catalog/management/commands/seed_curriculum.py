from django.core.management.base import BaseCommand
from django.db import transaction

from catalog.curriculum import CURRICULUM
from catalog.models import Subject, Subtopic, Unit


class Command(BaseCommand):
    help = "Create or update the AP subjects, units and topics. Safe to run repeatedly."

    @transaction.atomic
    def handle(self, *args, **options):
        topics = 0
        for data in CURRICULUM:
            subject, _ = Subject.objects.update_or_create(
                slug=data["slug"],
                defaults={"name": data["name"], "description": data["description"]},
            )
            for number, name, subtopic_names in data["units"]:
                unit, _ = Unit.objects.update_or_create(
                    subject=subject, number=number, defaults={"name": name}
                )
                for i, topic in enumerate(subtopic_names, start=1):
                    Subtopic.objects.update_or_create(unit=unit, number=i, defaults={"name": topic})
                    topics += 1
        self.stdout.write(f"Curriculum ready: {len(CURRICULUM)} subjects, {topics} topics.")
