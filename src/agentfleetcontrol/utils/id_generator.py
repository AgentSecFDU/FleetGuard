"""ID generation utilities with domain-specific prefixes."""

import secrets
import uuid


def generate_device_id() -> str:
    return f"afc-dev-{uuid.uuid4().hex[:12]}"


def generate_event_id() -> str:
    return f"evt_{uuid.uuid4().hex[:12]}"


def generate_approval_id() -> str:
    return f"appr_{uuid.uuid4().hex[:12]}"


def generate_enrollment_token() -> tuple[str, str, str]:
    """Generate an enrollment token.
    Returns: (raw_token, token_hash_prefix, full_token_hash)
    raw_token is shown to the admin once.
    """
    raw = f"afcet_{secrets.token_urlsafe(32)}"
    return raw, raw[:12], raw


def generate_device_api_token() -> tuple[str, str]:
    """Generate a device API token.
    Returns: (raw_token, token_prefix)
    """
    raw = f"afcdt_{secrets.token_urlsafe(32)}"
    return raw, raw[:12]
