def is_htmx(request) -> bool:
    """True when the request came from htmx and expects an HTML fragment back."""
    return request.headers.get("HX-Request") == "true"
