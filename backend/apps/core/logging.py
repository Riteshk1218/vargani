"""One JSON object per log line in production, so log tools (Loki, CloudWatch, Datadog) can filter by field."""

import json
import logging
from datetime import UTC, datetime

from .context import get_request_id

_STANDARD = set(vars(logging.makeLogRecord({}))) | {"message", "asctime"}


class JSONFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "time": datetime.fromtimestamp(record.created, UTC).isoformat(timespec="milliseconds"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        request_id = getattr(record, "request_id", None) or get_request_id()
        if request_id:
            payload["request_id"] = request_id
        for key, value in vars(record).items():
            if key not in _STANDARD and key not in payload and not key.startswith("_"):
                payload[key] = value if isinstance(value, str | int | float | bool | type(None)) else str(value)
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)
