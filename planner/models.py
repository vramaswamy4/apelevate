from django.conf import settings
from django.db import models


class StudyPlan(models.Model):
    """One generated plan, with everything needed to audit it: inputs, output, model and cost."""

    class Status(models.TextChoices):
        OK = "ok", "Ready"
        FAILED = "failed", "Failed"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="study_plans"
    )
    subject = models.ForeignKey("catalog.Subject", on_delete=models.CASCADE, related_name="+")
    exam_date = models.DateField()
    starts_on = models.DateField(help_text="First day of week 1.")
    hours_per_week = models.PositiveSmallIntegerField()
    weak_units = models.ManyToManyField("catalog.Unit", blank=True, related_name="+")
    # sha256 of the full model input; identical requests within a day reuse the stored plan.
    input_hash = models.CharField(max_length=64, db_index=True)
    status = models.CharField(max_length=10, choices=Status.choices)
    plan = models.JSONField(null=True, blank=True)
    problems = models.JSONField(default=list, blank=True)  # validation findings, if any
    model = models.CharField(max_length=100)
    attempts = models.PositiveSmallIntegerField(default=1)
    input_tokens = models.PositiveIntegerField(default=0)
    output_tokens = models.PositiveIntegerField(default=0)
    latency_ms = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.subject} plan for {self.user} ({self.status})"

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens
