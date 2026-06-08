"""UUID-based request ID helpers."""

from __future__ import annotations

import uuid


def generate_request_id() -> str:
    """Return a new RFC-4122 UUID4 as a string."""
    return str(uuid.uuid4())
