"""Default contribution types created with every event, in its organization's default language."""

# (English, Marathi, Hindi, kind)
DEFAULT_TYPES = [
    ("Donation", "देणगी", "दान", "one_time"),
    ("Membership Fee", "सभासद शुल्क", "सदस्यता शुल्क", "one_time"),
    ("Monthly Contribution", "मासिक वर्गणी", "मासिक योगदान", "recurring_monthly"),
    ("Other", "इतर", "अन्य", "one_time"),
]
LANGUAGE_INDEX = {"en": 0, "mr": 1, "hi": 2}


def seed_types(event, type_model=None, user=None):
    """Add the default types an event does not have yet, in any language. Existing types are left alone."""
    if type_model is None:
        from .models import ContributionType as type_model
    index = LANGUAGE_INDEX.get(event.organization.default_language, 0)
    existing = set(type_model.objects.filter(event=event).values_list("name", flat=True))
    type_model.objects.bulk_create(
        [
            type_model(
                organization_id=event.organization_id,
                event=event,
                name=row[index],
                kind=row[3],
                created_by=user,
                updated_by=user,
            )
            for row in DEFAULT_TYPES
            if not existing.intersection(row[:3])
        ]
    )
