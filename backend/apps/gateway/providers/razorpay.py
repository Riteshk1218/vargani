"""Razorpay: orders, checkout signature and webhook signature. Uses the standard library only."""

import base64
import hashlib
import hmac
import json
import urllib.error
import urllib.request

API = "https://api.razorpay.com/v1"


class GatewayError(Exception):
    pass


def _hmac(secret: str, message: bytes) -> str:
    return hmac.new(secret.encode(), message, hashlib.sha256).hexdigest()


class RazorpayClient:
    def __init__(self, config):
        self.config = config

    def create_order(self, *, amount_paise: int, currency: str, receipt: str, notes: dict) -> dict:
        body = json.dumps({"amount": amount_paise, "currency": currency, "receipt": receipt[:40], "notes": notes})
        auth = base64.b64encode(f"{self.config.key_id}:{self.config.key_secret}".encode()).decode()
        request = urllib.request.Request(
            f"{API}/orders",
            data=body.encode(),
            headers={"Content-Type": "application/json", "Authorization": f"Basic {auth}"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=15) as response:  # noqa: S310 - fixed https URL
                return json.loads(response.read())
        except (urllib.error.URLError, TimeoutError, ValueError) as exc:
            raise GatewayError(str(exc)) from exc

    def checkout_signature_valid(self, *, order_id: str, payment_id: str, signature: str) -> bool:
        expected = _hmac(self.config.key_secret, f"{order_id}|{payment_id}".encode())
        return hmac.compare_digest(expected, signature or "")

    def webhook_signature_valid(self, body: bytes, signature: str) -> bool:
        secret = self.config.webhook_secret
        if not secret:
            return False
        return hmac.compare_digest(_hmac(secret, body), signature or "")

    @staticmethod
    def parse_webhook(payload: dict) -> dict:
        """→ {"type", "order_id", "payment_id", "amount", "status"} for the events we act on."""
        entity = (payload.get("payload", {}).get("payment") or {}).get("entity") or {}
        return {
            "type": payload.get("event", ""),
            "order_id": entity.get("order_id"),
            "payment_id": entity.get("id"),
            "amount": entity.get("amount"),
            "status": entity.get("status"),
        }
