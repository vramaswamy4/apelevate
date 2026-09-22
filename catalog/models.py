"""The AP curriculum tree: Subject -> Unit -> Subtopic. Classes are tagged with subtopics."""

from django.db import models
from django.db.models import Count, Q
from django.urls import reverse
from django.utils import timezone


class SubjectQuerySet(models.QuerySet):
    def with_counts(self, now=None):
        now = now or timezone.now()
        return self.annotate(
            unit_count=Count("units", distinct=True),
            upcoming_class_count=Count(
                "classes", filter=Q(classes__starts_at__gte=now), distinct=True
            ),
        )


class Subject(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True)
    description = models.TextField(blank=True)

    objects = SubjectQuerySet.as_manager()

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse("catalog:subject_detail", args=[self.slug])


class Unit(models.Model):
    # CASCADE inside the tree: a unit belongs to its subject. Deleting a subject that has classes
    # is still blocked, by TutoringClass.subject (PROTECT).
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name="units")
    number = models.PositiveSmallIntegerField()
    name = models.CharField(max_length=200)

    class Meta:
        ordering = ["subject__name", "number"]
        constraints = [
            models.UniqueConstraint(fields=["subject", "number"], name="unique_unit_number"),
        ]

    def __str__(self):
        return f"Unit {self.number}: {self.name}"


class Subtopic(models.Model):
    unit = models.ForeignKey(Unit, on_delete=models.CASCADE, related_name="subtopics")
    # The part after the dot: topic 1.10 is unit 1, number 10. Stored as an integer so 1.10
    # sorts after 1.9 and can't collide with 1.1 (the original stored 1.10 as the float 1.1).
    number = models.PositiveSmallIntegerField()
    name = models.CharField(max_length=200)

    class Meta:
        ordering = ["unit__number", "number"]
        constraints = [
            models.UniqueConstraint(fields=["unit", "number"], name="unique_subtopic_number"),
        ]

    def __str__(self):
        return f"{self.code} {self.name}"

    @property
    def code(self) -> str:
        return f"{self.unit.number}.{self.number}"
