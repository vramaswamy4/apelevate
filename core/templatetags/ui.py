from django import template
from django.utils.safestring import mark_safe

register = template.Library()


@register.filter
def minutes(value):
    """60 -> '1 hr', 90 -> '1 hr 30 min', 45 -> '45 min'."""
    hours, mins = divmod(int(value or 0), 60)
    parts = []
    if hours:
        parts.append(f"{hours} hr")
    if mins or not hours:
        parts.append(f"{mins} min")
    return " ".join(parts)


@register.filter
def cents(value):
    """8000 -> '$80', 12050 -> '$120.50'."""
    dollars, rem = divmod(int(value or 0), 100)
    return f"${dollars:,}" if rem == 0 else f"${dollars:,}.{rem:02d}"


@register.simple_tag(takes_context=True)
def active(context, *url_names):
    """'aria-current="page"' when the current URL name is one of ``url_names``."""
    match = getattr(context.get("request"), "resolver_match", None)
    if match and match.view_name in url_names:
        return mark_safe('aria-current="page"')
    return ""
