import zoneinfo

from django.utils import timezone


class UserTimezoneMiddleware:
    """Render dates in the signed-in user's time zone. Everything is stored in UTC."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, "user", None)
        if user is not None and user.is_authenticated and user.timezone:
            try:
                timezone.activate(zoneinfo.ZoneInfo(user.timezone))
            except zoneinfo.ZoneInfoNotFoundError:
                timezone.deactivate()
        else:
            timezone.deactivate()
        return self.get_response(request)
