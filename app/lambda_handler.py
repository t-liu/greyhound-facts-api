"""AWS Lambda handler — wraps the FastAPI app with Mangum."""

from __future__ import annotations

import os
import sys
from types import ModuleType

# ── VIRTUAL NAMESPACE PATCH ───────────────────────────────────────────
# Creates a fake 'app' module pointing to the current execution directory
# to prevent 'No module named app' errors during flattened Lambda execution.
if "app" not in sys.modules:
    app_mock = ModuleType("app")
    app_mock.__path__ = [os.path.dirname(__file__)]
    sys.modules["app"] = app_mock
# ───────────────────────────────────────────────────────────────────────

from mangum import Mangum
from main import app  # Now resolves safely

_mangum = Mangum(app, lifespan="off")


def handler(event: dict, context: object) -> dict:
    if isinstance(event, dict) and event.get("source") == "warmup":
        return {"statusCode": 200, "body": '"warmup ok"'}
    return _mangum(event, context)