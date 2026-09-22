from django.core.management import call_command
from django.urls import reverse

from catalog.models import Subject, Subtopic, Unit


def test_topic_1_10_sorts_after_1_9_and_is_distinct_from_1_1(chemistry):
    """The 2022 model stored topic numbers as floats, so 1.10 was saved as 1.1."""
    unit = chemistry.units.get(number=1)
    codes = [t.code for t in Subtopic.objects.filter(unit=unit)]
    assert codes == ["1.1", "1.2", "1.3", "1.10"]


def test_seed_curriculum_is_idempotent():
    call_command("seed_curriculum")
    counts = (Subject.objects.count(), Unit.objects.count(), Subtopic.objects.count())
    call_command("seed_curriculum")
    assert (Subject.objects.count(), Unit.objects.count(), Subtopic.objects.count()) == counts
    assert counts[0] == 3


def test_subject_page_lists_units_and_upcoming_classes(client, chemistry, make_class):
    make_class(title="Moles clinic")
    response = client.get(reverse("catalog:subject_detail", args=[chemistry.slug]))
    body = response.content.decode()
    assert "Unit 1" in body
    assert "1.10" in body
    assert "Moles clinic" in body


def test_subject_with_classes_cannot_be_deleted(chemistry, make_class):
    import pytest
    from django.db.models import ProtectedError

    make_class()
    with pytest.raises(ProtectedError):
        chemistry.delete()
