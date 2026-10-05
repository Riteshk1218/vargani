"""Event templates: starting configurations, not hard-coded data. Names and amounts are always user-entered."""

from django.utils.translation import gettext_lazy as _

MODULE_KEYS = ("contributions", "monthly", "expenses", "collectors", "member_portal")

TEMPLATES = {
    "festival": {
        "name": _("Festival"),
        "description": _("Festivals such as Ganesh Chaturthi, Navratri or Dahi Handi."),
        "modules": {
            "contributions": True,
            "monthly": False,
            "expenses": True,
            "collectors": True,
            "member_portal": True,
        },
    },
    "fundraising": {
        "name": _("Fundraising"),
        "description": _("A campaign that collects donations towards a goal."),
        "modules": {
            "contributions": True,
            "monthly": False,
            "expenses": True,
            "collectors": True,
            "member_portal": True,
        },
    },
    "membership": {
        "name": _("Membership"),
        "description": _("Annual or monthly membership and Vargani collection."),
        "modules": {
            "contributions": True,
            "monthly": True,
            "expenses": False,
            "collectors": True,
            "member_portal": True,
        },
    },
    "society": {
        "name": _("Society"),
        "description": _("Housing society maintenance, funds and expenses."),
        "modules": {
            "contributions": True,
            "monthly": True,
            "expenses": True,
            "collectors": True,
            "member_portal": True,
        },
    },
    "custom": {
        "name": _("Custom"),
        "description": _("Start empty and choose the modules yourself."),
        "modules": {
            "contributions": True,
            "monthly": False,
            "expenses": True,
            "collectors": False,
            "member_portal": False,
        },
    },
}
