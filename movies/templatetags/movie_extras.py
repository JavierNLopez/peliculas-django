from django import template

register = template.Library()


@register.filter
def money_us(value):
    if value in (None, ""):
        return "N/D"
    try:
        return f"${value:,.0f}"
    except (ValueError, TypeError):
        return value


@register.filter
def money_mx(value):
    if value in (None, ""):
        return "N/D"
    try:
        formatted = f"{value:,.0f}"
        formatted = formatted.replace(",", "X").replace(".", ",").replace("X", ".")
        return f"${formatted}"
    except (ValueError, TypeError):
        return value
