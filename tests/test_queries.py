"""Query budgets: page cost must not grow with the number of classes on it.

In 2022 nested template loops ran a query per class, per topic and per student: 72 queries to
show 12 classes. These tests render each list page with 2 rows and with 10 and require the same
query count.
"""

import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from classes.services import enrol


def count_queries(client, url):
    with CaptureQueriesContext(connection) as ctx:
        response = client.get(url)
    assert response.status_code == 200
    return len(ctx)


@pytest.fixture
def populate(make_class, make_user, give_tokens):
    students = [make_user() for _ in range(3)]
    for s in students:
        give_tokens(s, "twenty")

    def populate(n):
        for i in range(n):
            c = make_class(title=f"Class {i}")
            for s in students:
                enrol(s, c)
        return students[0]

    return populate


@pytest.mark.parametrize(
    "url_name", ["classes:list", "dashboard", "classes:mine", "catalog:subject_list"]
)
def test_student_pages_have_a_flat_query_count(client, populate, url_name):
    student = populate(2)
    client.force_login(student)
    small = count_queries(client, reverse(url_name))
    populate(8)
    large = count_queries(client, reverse(url_name))
    assert large == small, f"{url_name}: {small} queries with 2 classes, {large} with 10"


@pytest.mark.parametrize("url_name", ["classes:teach", "classes:teach_classes"])
def test_mentor_pages_have_a_flat_query_count(client, populate, mentor, url_name):
    populate(2)
    client.force_login(mentor)
    small = count_queries(client, reverse(url_name))
    populate(8)
    assert count_queries(client, reverse(url_name)) == small


def test_class_list_stays_small(client, populate):
    student = populate(10)
    client.force_login(student)
    assert count_queries(client, reverse("classes:list")) <= 8
