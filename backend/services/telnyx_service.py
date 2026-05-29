import hashlib
import hmac
import json
import os
import time
from typing import Optional

import requests

_TELNYX_API_KEY = os.environ.get("TELNYX_API_KEY", "")
_TELNYX_PUBLIC_KEY = os.environ.get("TELNYX_PUBLIC_KEY", "")
_TELNYX_PHONE = os.environ.get("TELNYX_PHONE_NUMBER", "")

_MESSAGES_URL = "https://api.telnyx.com/v2/messages"


def send_sms(to: str, body: str) -> dict:
    resp = requests.post(
        _MESSAGES_URL,
        headers={
            "Authorization": f"Bearer {_TELNYX_API_KEY}",
            "Content-Type": "application/json",
        },
        json={
            "from": _TELNYX_PHONE,
            "to": to,
            "text": body,
        },
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()


def validate_webhook_signature(
    payload: bytes,
    timestamp: str,
    signature: str,
) -> bool:
    """Validate a Telnyx webhook using Ed25519 signature."""
    # Telnyx signs: timestamp + "|" + raw_body
    signed_payload = f"{timestamp}|".encode() + payload
    try:
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
        from cryptography.hazmat.primitives.serialization import load_pem_public_key
        import base64

        public_key_bytes = base64.b64decode(_TELNYX_PUBLIC_KEY)
        public_key = Ed25519PublicKey.from_public_bytes(public_key_bytes)
        sig_bytes = base64.b64decode(signature)
        public_key.verify(sig_bytes, signed_payload)
        return True
    except Exception:
        return False
