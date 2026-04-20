"""Custom template tags and filters for HRMS"""
from django import template

register = template.Library()


@register.filter
def get_item(dictionary, key):
    """Get a dict value by key in templates. Usage: {{ my_dict|get_item:key }}"""
    if isinstance(dictionary, dict):
        return dictionary.get(key, [])
    return []


@register.filter
def multiply(value, arg):
    """Multiply a value. Usage: {{ value|multiply:2 }}"""
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return 0


@register.filter
def percentage(value, total):
    """Calculate percentage. Usage: {{ value|percentage:total }}"""
    try:
        if float(total) == 0:
            return 0
        return round((float(value) / float(total)) * 100, 1)
    except (ValueError, TypeError):
        return 0
