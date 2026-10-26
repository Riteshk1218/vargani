"""Default contribution types created with every event, in its organization's default language."""

# (English, Marathi, Hindi, kind), in list order: Donation first, so Collect selects it by default.
DEFAULT_TYPES = [
    ("Donation", "देणगी", "दान", "one_time"),
    ("Membership Fee", "सभासद शुल्क", "सदस्यता शुल्क", "one_time"),
    ("Monthly Contribution", "मासिक वर्गणी", "मासिक योगदान", "recurring_monthly"),
    ("Other", "इतर", "अन्य", "one_time"),
]
MONTHLY = DEFAULT_TYPES[2]
LANGUAGE_INDEX = {"en": 0, "mr": 1, "hi": 2}
DEFAULT_POSITION = 100  # ContributionType.position for types the organization added itself


def seed_types(event, type_model=None, user=None):
    """Add the default types an event does not have yet, in any language, and put the defaults in order.

    An event that already has its own monthly type keeps it in the monthly slot instead of getting a second one.
    Types the organization added itself, and their names, are otherwise left alone.
    """
    if type_model is None:
        from .models import ContributionType as type_model
    index = LANGUAGE_INDEX.get(event.organization.default_language, 0)
    types = type_model.objects.filter(event=event)
    own_monthly = (
        types.filter(kind="recurring_monthly", is_active=True)
        .exclude(name__in=MONTHLY[:3])
        .order_by("created_at")
        .first()
    )
    if own_monthly:
        # A seeded "Monthly Contribution" next to the event's own monthly type is a duplicate in Collect.
        types.filter(name__in=MONTHLY[:3], created_by__isnull=True).update(is_active=False)
        if own_monthly.position == DEFAULT_POSITION:
            types.filter(pk=own_monthly.pk).update(position=DEFAULT_TYPES.index(MONTHLY))
    existing = dict(types.values_list("name", "position"))
    # Existing default types (in any language) still left at the default position move to theirs.
    for position, row in enumerate(DEFAULT_TYPES):
        names = [name for name in row[:3] if existing.get(name) == DEFAULT_POSITION]
        if names:
            types.filter(name__in=names).update(position=position)
    type_model.objects.bulk_create(
        [
            type_model(
                organization_id=event.organization_id,
                event=event,
                name=row[index],
                kind=row[3],
                position=position,
                created_by=user,
                updated_by=user,
            )
            for position, row in enumerate(DEFAULT_TYPES)
            if not existing.keys() & set(row[:3]) and not (row is MONTHLY and own_monthly)
        ]
    )
