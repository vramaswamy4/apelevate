from django.conf import settings


def nav(request):
    """Values the nav bar needs on every page. ``is_mentor`` costs at most one query per request."""
    user = request.user
    context = {"demo_mode": settings.DEMO_MODE}
    if user.is_authenticated:
        context.update(nav_is_mentor=user.is_mentor, nav_token_balance=user.token_balance)
    return context
