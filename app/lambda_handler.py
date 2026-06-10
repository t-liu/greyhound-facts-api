"""AWS Lambda handler — wraps the FastAPI app with Mangum.

Early-returns immediately for EventBridge warm-up pings to avoid
unnecessary FastAPI overhead.
"""

from __future__ import annotations

from mangum import Mangum

from main import app

_mangum = Mangum(app, lifespan="off")


def handler(event: dict, context: object) -> dict:
    """Lambda entry point.

    Intercepts warm-up events from EventBridge before they reach FastAPI.
    """
    if isinstance(event, dict) and event.get("source") == "warmup":
        return {"statusCode": 200, "body": '"warmup ok"'}
    return _mangum(event, context)
