"""SSE message helper for `sse-starlette.EventSourceResponse`."""

from __future__ import annotations

import json


def sse_message(event: str, data: dict) -> dict:
    """Shape a payload for sse-starlette's EventSourceResponse."""
    return {"event": event, "data": json.dumps(data)}
