"""Admin studio: how the Collect form looks in one organization, set by its admins without code changes.

Stored in `Organization.settings["form_studio"]`:

    {
        "labels": {"amount": "Rakkam", ...},            # field key -> name shown instead of the default
        "modes": {"cheque": {"label": "", "hidden": true}, ...},   # payment mode dropdown
        "custom_fields": [                               # extra dropdowns asked on every collection
            {"key": "f_1a2b3c", "label": "Ward", "options": ["1", "2"], "required": false, "active": true},
        ],
    }

The value picked in a custom dropdown is saved on the payment (`Payment.custom_fields`, key -> option text)
and frozen into the receipt with the label it had then. A dropdown is switched off rather than deleted, so
older collections keep showing what was picked.
"""

import secrets

from django.utils.translation import gettext_lazy as _
from rest_framework.exceptions import ValidationError

from apps.payments.models import PaymentMode

SETTINGS_KEY = "form_studio"

# Collect form fields whose name an admin may change.
LABEL_FIELDS = (
    "payer",
    "contribution_type",
    "month",
    "amount",
    "received",
    "follow_up_on",
    "mode",
    "paid_on",
    "reference",
    "cheque_number",
    "cheque_bank",
    "cheque_date",
    "notes",
)
# Modes a collector picks by hand (online payments come through the gateway).
MANUAL_MODES = tuple(m for m in PaymentMode.values if m not in ("online", "gateway"))
MAX_LABEL = 60
MAX_FIELDS = 10
MAX_OPTIONS = 50


def default_config() -> dict:
    return {"labels": {}, "modes": {}, "custom_fields": []}


def get_config(org) -> dict:
    stored = (org.settings or {}).get(SETTINGS_KEY) or {}
    return {**default_config(), **stored}


def _text(value, field: str, errors: dict, *, required=False) -> str:
    if not isinstance(value, str):
        errors[field] = [_("Invalid value.")]
        return ""
    value = " ".join(value.split())
    if len(value) > MAX_LABEL:
        errors[field] = [_("Keep it to %(n)s characters.") % {"n": MAX_LABEL}]
    elif required and not value:
        errors[field] = [_("This field is required.")]
    return value


def validate_config(data, previous: dict | None = None) -> dict:
    """Clean what the admin sent. New dropdowns get a key here; keys of existing dropdowns never change."""
    if not isinstance(data, dict):
        raise ValidationError({"non_field_errors": [_("Invalid value.")]})
    errors: dict = {}

    labels = {}
    raw_labels = data.get("labels") or {}
    if not isinstance(raw_labels, dict):
        errors["labels"] = [_("Invalid value.")]
        raw_labels = {}
    for key, value in raw_labels.items():
        if key not in LABEL_FIELDS:
            errors[f"labels.{key}"] = [_("Unknown field.")]
            continue
        value = _text(value, f"labels.{key}", errors)
        if value:
            labels[key] = value

    modes = {}
    raw_modes = data.get("modes") or {}
    if not isinstance(raw_modes, dict):
        errors["modes"] = [_("Invalid value.")]
        raw_modes = {}
    for mode, value in raw_modes.items():
        if mode not in MANUAL_MODES or not isinstance(value, dict):
            errors[f"modes.{mode}"] = [_("Unknown payment mode.")]
            continue
        label = _text(value.get("label", ""), f"modes.{mode}.label", errors)
        hidden = bool(value.get("hidden", False))
        if label or hidden:
            modes[mode] = {"label": label, "hidden": hidden}
    if all(modes.get(m, {}).get("hidden") for m in MANUAL_MODES):
        errors["modes"] = [_("Keep at least one payment mode.")]

    known_keys = {f["key"] for f in (previous or {}).get("custom_fields", [])}
    fields = []
    raw_fields = data.get("custom_fields") or []
    if not isinstance(raw_fields, list):
        errors["custom_fields"] = [_("Invalid value.")]
        raw_fields = []
    if len(raw_fields) > MAX_FIELDS:
        errors["custom_fields"] = [_("At most %(n)s dropdowns.") % {"n": MAX_FIELDS}]
    seen_keys = set()
    for index, raw in enumerate(raw_fields[:MAX_FIELDS]):
        prefix = f"custom_fields.{index}"
        if not isinstance(raw, dict):
            errors[prefix] = [_("Invalid value.")]
            continue
        key = raw.get("key") or ""
        if key and key not in known_keys:
            errors[f"{prefix}.key"] = [_("Unknown field.")]
            continue
        key = key or f"f_{secrets.token_hex(3)}"
        if key in seen_keys:
            errors[f"{prefix}.key"] = [_("Invalid value.")]
            continue
        seen_keys.add(key)
        label = _text(raw.get("label", ""), f"{prefix}.label", errors, required=True)
        raw_options = raw.get("options") or []
        if not isinstance(raw_options, list):
            errors[f"{prefix}.options"] = [_("Invalid value.")]
            raw_options = []
        options = []
        for o, option in enumerate(raw_options):
            option = _text(option, f"{prefix}.options.{o}", errors)
            if option and option not in options:
                options.append(option)
        if not options:
            errors[f"{prefix}.options"] = [_("Add at least one option.")]
        elif len(options) > MAX_OPTIONS:
            errors[f"{prefix}.options"] = [_("At most %(n)s options.") % {"n": MAX_OPTIONS}]
        fields.append(
            {
                "key": key,
                "label": label,
                "options": options,
                "required": bool(raw.get("required", False)),
                "active": bool(raw.get("active", True)),
            }
        )
    # Dropdowns left out are kept switched off, so older collections still show their label.
    for old in (previous or {}).get("custom_fields", []):
        if old["key"] not in seen_keys:
            fields.append({**old, "active": False})

    if errors:
        raise ValidationError(errors)
    return {"labels": labels, "modes": modes, "custom_fields": fields}


def clean_values(org, values) -> dict:
    """Check the custom dropdown answers of one collection against the organization's studio."""
    values = values or {}
    if not isinstance(values, dict):
        raise ValidationError({"custom_fields": [_("Invalid value.")]})
    errors = {}
    cleaned = {}
    active = {f["key"]: f for f in get_config(org)["custom_fields"] if f.get("active", True)}
    for key, value in values.items():
        field = active.get(key)
        if field is None:
            errors[key] = [_("Unknown field.")]
        elif value in (None, ""):
            continue
        elif value not in field["options"]:
            errors[key] = [_("Choose one of the options.")]
        else:
            cleaned[key] = value
    for key, field in active.items():
        if field.get("required") and key not in cleaned and key not in errors:
            errors[key] = [_("This field is required.")]
    if errors:
        raise ValidationError({"custom_fields": errors})
    return cleaned


def describe_values(org, values: dict | None) -> list[dict]:
    """[{key, label, value}] in the order the dropdowns are set up, for display."""
    values = values or {}
    if not values:
        return []
    fields = get_config(org)["custom_fields"]
    out = [{"key": f["key"], "label": f["label"], "value": values[f["key"]]} for f in fields if f["key"] in values]
    known = {f["key"] for f in fields}
    out += [{"key": k, "label": k, "value": v} for k, v in values.items() if k not in known]
    return out


def mode_label(org, mode: str) -> str:
    """The admin's own name for a payment mode, or "" for the standard one."""
    return (get_config(org)["modes"].get(mode) or {}).get("label", "")
