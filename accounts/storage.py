from django.conf import settings
from django.core.files.storage import FileSystemStorage


class PrivateStorage(FileSystemStorage):
    """Uploads that must never be publicly reachable (mentor CVs, score reports).

    Files live outside MEDIA_ROOT and have no URL: ``FileSystemStorage(base_url=None)`` would
    silently fall back to MEDIA_URL, so ``url()`` refuses outright. Staff download these through
    a view that checks permissions.
    """

    def url(self, name):
        raise ValueError("Private files have no public URL; serve them through a view.")


def private_storage():
    """A callable, so migrations don't capture a path and tests can use a temp dir."""
    return PrivateStorage(location=settings.PRIVATE_MEDIA_ROOT)
