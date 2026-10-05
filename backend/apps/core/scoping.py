"""Row scopes for money tables: which payments / contributions / receipts a role may see."""

from .tenancy import SCOPE_ALL, SCOPE_OWN, SCOPE_SELF


def scope_money(queryset, context, code, user, *, collector="collector", person="person"):
    """all → everything; own → rows I collected; self → rows of my linked person; anything else → nothing."""
    scope = context.scope(code)
    if scope == SCOPE_ALL:
        return queryset
    if scope == SCOPE_OWN:
        return queryset.filter(**{collector: context.membership})
    if scope == SCOPE_SELF:
        return queryset.filter(**{f"{person}__user": user})
    return queryset.none()
