"""Who can open what. One table, every page, every role.

The 2022 app checked roles with a decorator that only looked at a user's first auth group and
answered "not authorized" with HTTP 200. Here a signed-out visitor is redirected to sign in, and a
signed-in user without the role gets a real 403.
"""

import pytest
from django.urls import reverse

PUBLIC, LOGIN, FORBIDDEN, OK = "public", "login", "forbidden", "ok"

# (url name, kwargs builder) -> expected outcome for anon / student / mentor / staff
MATRIX = [
    ("home", None, [PUBLIC, "redirect", "redirect", "redirect"]),
    ("catalog:subject_list", None, [PUBLIC, OK, OK, OK]),
    ("catalog:subject_detail", "subject", [PUBLIC, OK, OK, OK]),
    ("classes:list", None, [PUBLIC, OK, OK, OK]),
    ("classes:detail", "class", [PUBLIC, OK, OK, OK]),
    ("accounts:login", None, [PUBLIC, "redirect", "redirect", "redirect"]),
    ("accounts:signup", None, [PUBLIC, "redirect", "redirect", "redirect"]),
    ("dashboard", None, [LOGIN, OK, OK, OK]),
    ("classes:mine", None, [LOGIN, OK, OK, OK]),
    ("classes:requests", None, [LOGIN, OK, OK, OK]),
    ("accounts:profile", None, [LOGIN, OK, OK, OK]),
    ("accounts:apply", None, [LOGIN, OK, OK, OK]),
    ("payments:buy", None, [LOGIN, OK, OK, OK]),
    ("classes:teach", None, [LOGIN, FORBIDDEN, OK, FORBIDDEN]),
    ("classes:teach_classes", None, [LOGIN, FORBIDDEN, OK, FORBIDDEN]),
    ("classes:create", None, [LOGIN, FORBIDDEN, OK, FORBIDDEN]),
    ("classes:analytics", None, [LOGIN, FORBIDDEN, OK, FORBIDDEN]),
    ("accounts:review_list", None, [LOGIN, FORBIDDEN, FORBIDDEN, OK]),
    ("accounts:review_detail", "application", [LOGIN, FORBIDDEN, FORBIDDEN, OK]),
]
ROLES = ["anon", "student", "mentor", "staff"]


@pytest.fixture
def objects(chemistry, make_class, student, make_application):
    application = make_application(student, chemistry)
    return {
        "subject": {"slug": chemistry.slug},
        "class": {"pk": make_class().pk},
        "application": {"pk": application.pk},
    }


@pytest.mark.parametrize(("url_name", "kwargs_key", "expected"), MATRIX)
@pytest.mark.parametrize("role_index", range(4), ids=ROLES)
def test_access(
    client, objects, student, mentor, staff, url_name, kwargs_key, expected, role_index
):
    user = [None, student, mentor, staff][role_index]
    if user:
        client.force_login(user)
    url = reverse(url_name, kwargs=objects[kwargs_key] if kwargs_key else None)
    response = client.get(url)
    outcome = expected[role_index]
    if outcome in (PUBLIC, OK):
        assert response.status_code == 200
    elif outcome == LOGIN:
        assert response.status_code == 302
        assert response.url.startswith(reverse("accounts:login"))
    elif outcome == FORBIDDEN:
        assert response.status_code == 403
    else:
        assert response.status_code == 302


def test_every_url_is_covered_by_the_matrix():
    """A new page must be added to MATRIX (or to the list of POST-only / file routes below)."""
    from django.urls import get_resolver

    covered = {name for name, _, _ in MATRIX}
    not_pages = {
        "accounts:logout",
        "accounts:password_change",
        "accounts:password_reset",
        "accounts:password_reset_done",
        "accounts:password_reset_confirm",
        "accounts:review_decide",
        "accounts:review_file",
        "classes:enrol",
        "classes:close_request",
        "classes:subtopic_options",
        "payments:checkout",
        "payments:capture",
        "payments:test_pay",
        "payments:receipt",
    }
    names = set()
    for pattern in get_resolver().url_patterns:
        namespace = getattr(pattern, "namespace", None)
        for sub in getattr(pattern, "url_patterns", [pattern]):
            if getattr(sub, "name", None):
                names.add(f"{namespace}:{sub.name}" if namespace else sub.name)
    ours = {n for n in names if not n.startswith("admin")}
    assert ours - covered - not_pages == set()


@pytest.mark.parametrize(
    ("url_name", "kwargs_key"),
    [("accounts:review_decide", "application"), ("classes:enrol", "class")],
)
def test_state_changing_urls_refuse_get(client, objects, staff, url_name, kwargs_key):
    """Accept/reject were GET links in 2022, so a forged <img> tag could trigger them."""
    client.force_login(staff)
    response = client.get(reverse(url_name, kwargs=objects[kwargs_key]))
    assert response.status_code == 405


def test_student_cannot_download_application_files(client, objects, student):
    client.force_login(student)
    url = reverse("accounts:review_file", kwargs={**objects["application"], "kind": "cv"})
    assert client.get(url).status_code == 403
