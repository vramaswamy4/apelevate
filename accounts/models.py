import uuid
import zoneinfo
from functools import cached_property
from pathlib import Path

from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from django.db.models import Q

from .storage import private_storage


def timezone_choices():
    return [(name, name.replace("_", " ")) for name in sorted(zoneinfo.available_timezones())]


class UserManager(BaseUserManager):
    """Users sign in with their email address; there is no username."""

    use_in_migrations = True

    def _create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError("An email address is required.")
        user = self.model(email=self.normalize_email(email).lower(), **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        return self._create_user(email, password, **extra_fields)


class User(AbstractUser):
    username = None
    email = models.EmailField("email address", unique=True)
    timezone = models.CharField(max_length=64, default="UTC", choices=timezone_choices)
    # A cache of the ledger total in payments.TokenEntry, written only by payments.wallet in the
    # same transaction as the ledger row. The check constraint makes an overdraft impossible even
    # if two enrolments race.
    token_balance = models.IntegerField(default=0, editable=False)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["first_name", "last_name"]

    objects = UserManager()

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=Q(token_balance__gte=0), name="token_balance_non_negative"
            ),
        ]

    def __str__(self):
        return self.get_full_name() or self.email

    @cached_property
    def mentor(self):
        """The user's ``MentorProfile``, or None. Cached for the life of the instance."""
        try:
            return self.mentor_profile
        except MentorProfile.DoesNotExist:
            return None

    @property
    def is_mentor(self) -> bool:
        return self.mentor is not None


class MentorProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="mentor_profile")
    bio = models.TextField()
    subjects = models.ManyToManyField("catalog.Subject", related_name="mentors")
    approved_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["user__first_name", "user__last_name"]

    def __str__(self):
        return str(self.user)


def application_upload_path(instance, filename):
    # Never keep the uploaded name: it is user-controlled and can collide or leak.
    return f"applications/{uuid.uuid4().hex}{Path(filename).suffix.lower()}"


class MentorApplication(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending review"
        ACCEPTED = "accepted", "Accepted"
        REJECTED = "rejected", "Not accepted"

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="mentor_applications")
    subject = models.ForeignKey(
        "catalog.Subject", on_delete=models.PROTECT, related_name="applications"
    )
    bio = models.TextField("about you")
    ap_experience = models.TextField("your experience with this AP exam")
    teaching_experience = models.TextField("your teaching or tutoring experience")
    motivation = models.TextField("what would make you a good mentor")
    # Private storage: not under MEDIA_ROOT and never served directly. Staff download these
    # through a view that checks permissions.
    score_report = models.FileField(storage=private_storage, upload_to=application_upload_path)
    cv = models.FileField("CV", storage=private_storage, upload_to=application_upload_path)
    status = models.CharField(
        max_length=10, choices=Status.choices, default=Status.PENDING, db_index=True
    )
    submitted_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    decision_note = models.TextField(blank=True)

    class Meta:
        ordering = ["-submitted_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["user"],
                condition=Q(status="pending"),
                name="one_pending_application_per_user",
            ),
        ]

    def __str__(self):
        return f"{self.user} for {self.subject} ({self.get_status_display()})"

    @property
    def is_pending(self) -> bool:
        return self.status == self.Status.PENDING
