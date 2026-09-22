"""Enrolment: the one place a student spends a token on a class."""

import logging

from django.db import IntegrityError, transaction
from django.utils import timezone

from payments.wallet import InsufficientTokens, debit_for_enrolment

from .models import Enrolment

log = logging.getLogger(__name__)

ENROLMENT_COST = 1


class EnrolmentError(Exception):
    """A rule was broken; the message is safe to show to the user."""


def enrol(student, tutoring_class, *, now=None) -> Enrolment:
    """Enrol ``student`` in ``tutoring_class`` and charge one token, atomically.

    Either both the enrolment row and the ledger debit are written, or neither is. Double
    enrolment and overdraft are prevented by database constraints (a unique index and a check
    constraint on the balance), not by reading first and writing second, so two requests racing
    can't get past them.
    """
    if tutoring_class.has_started(now or timezone.now()):
        raise EnrolmentError("This class has already started.")
    if tutoring_class.mentor.user_id == student.pk:
        raise EnrolmentError("You can't enrol in your own class.")
    try:
        with transaction.atomic():
            try:
                with transaction.atomic():
                    enrolment = Enrolment.objects.create(
                        tutoring_class=tutoring_class, student=student, tokens_spent=ENROLMENT_COST
                    )
            except IntegrityError:
                raise EnrolmentError("You're already enrolled in this class.") from None
            debit_for_enrolment(enrolment)
    except InsufficientTokens:
        raise EnrolmentError(
            f"Enrolling costs {ENROLMENT_COST} token and your balance is empty. Buy tokens first."
        ) from None
    log.info("user %s enrolled in class %s", student.pk, tutoring_class.pk)
    return enrolment
