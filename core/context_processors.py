def nav(request):
    """Values the nav bar needs on every page. ``is_mentor`` costs at most one query per request."""
    user = request.user
    if not user.is_authenticated:
        return {}
    return {"nav_is_mentor": user.is_mentor, "nav_token_balance": user.token_balance}
