"""Default expense categories created with every organization, in its default language."""

DEFAULT_CATEGORIES = [
    ("Decoration", "सजावट", "सजावट"),
    ("Sound", "ध्वनी व्यवस्था", "ध्वनि व्यवस्था"),
    ("Lighting", "रोषणाई", "रोशनी"),
    ("Pandal", "मंडप", "पंडाल"),
    ("Prasad / Food", "प्रसाद / भोजन", "प्रसाद / भोजन"),
    ("Electricity", "वीज", "बिजली"),
    ("Advertisement", "जाहिरात", "विज्ञापन"),
    ("Cultural Program", "सांस्कृतिक कार्यक्रम", "सांस्कृतिक कार्यक्रम"),
    ("Transportation", "वाहतूक", "परिवहन"),
    ("Printing", "छपाई", "छपाई"),
    ("Other", "इतर", "अन्य"),
]
LANGUAGE_INDEX = {"en": 0, "mr": 1, "hi": 2}


def seed_categories(org, category_model=None):
    if category_model is None:
        from .models import ExpenseCategory as category_model
    index = LANGUAGE_INDEX.get(org.default_language, 0)
    existing = set(category_model.objects.filter(organization=org).values_list("name", flat=True))
    category_model.objects.bulk_create(
        [
            category_model(organization=org, name=names[index], is_default=True)
            for names in DEFAULT_CATEGORIES
            if names[index] not in existing
        ]
    )
