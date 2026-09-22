"""Public-demo rules (DEMO_MODE=1). See docs in README, "Live demo"."""

from django.conf import settings

DEMO_ACCOUNTS = [
    ("student@apelevate.test", "Student", "Has tokens and a class booked"),
    ("mentor@apelevate.test", "Mentor", "Teaches Chemistry and Calculus; has analytics"),
    ("admin@apelevate.test", "Staff", "Reviews mentor applications"),
    ("applicant@apelevate.test", "Applicant", "Has an application waiting for review"),
]
DEMO_PASSWORD = "apelevate-demo"  # noqa: S105 (published on the sign-in page on purpose)


def is_demo_account(user) -> bool:
    """A shared demo login whose identity visitors mustn't be able to change."""
    return (
        settings.DEMO_MODE
        and user.is_authenticated
        and user.email.endswith("@" + settings.DEMO_EMAIL_DOMAIN)
    )
