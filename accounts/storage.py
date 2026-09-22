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
    """A callable, so migrations don't capture a path and tests can use a temp dir.

    With PRIVATE_STORAGE_BUCKET set (production on Cloud Run, whose disk doesn't survive a
    restart) the files go to a private Google Cloud Storage bucket instead, with the same rule:
    no URLs, only reads through the permission-checked view.
    """
    if settings.PRIVATE_STORAGE_BUCKET:
        from storages.backends.gcloud import GoogleCloudStorage

        class PrivateBucketStorage(GoogleCloudStorage):
            def url(self, name, parameters=None, expire=None, http_method=None):
                raise ValueError("Private files have no public URL; serve them through a view.")

        return PrivateBucketStorage(
            bucket_name=settings.PRIVATE_STORAGE_BUCKET, default_acl=None, querystring_auth=True
        )
    return PrivateStorage(location=settings.PRIVATE_MEDIA_ROOT)
