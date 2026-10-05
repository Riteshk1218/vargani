"""SMS delivery backends. A real provider (DLT-registered templates in India) is added in Phase 5."""

import logging

from django.conf import settings
from django.utils.module_loading import import_string

logger = logging.getLogger(__name__)


class BaseSMSBackend:
    def send(self, to: str, message: str) -> None:
        raise NotImplementedError


class ConsoleSMSBackend(BaseSMSBackend):
    """Development backend: prints the message to the server log."""

    def send(self, to, message):
        logger.warning("SMS to %s: %s", to, message)


class MemorySMSBackend(BaseSMSBackend):
    """Test backend: keeps messages in memory."""

    outbox: list[tuple[str, str]] = []

    def send(self, to, message):
        MemorySMSBackend.outbox.append((to, message))


def get_sms_backend() -> BaseSMSBackend:
    return import_string(settings.SMS_BACKEND)()
