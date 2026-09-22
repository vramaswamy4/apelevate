from django.forms.renderers import TemplatesSetting


class FormRenderer(TemplatesSetting):
    """Renders every form field through templates/forms/field.html (one markup for all forms)."""

    field_template_name = "forms/field.html"
