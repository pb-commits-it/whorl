"""Server-sent events stream of per-scout live progress.

The pattern: every event published on `app.state.hub` is a tuple `(event, data)`
with a `scout_id` field in `data`. A subscriber to GET /api/stream/scouts/{id}
filters server-side and only forwards events for that scout.

Why filter server-side rather than per-scout hubs: keeps the producer side
(photos / recommend routes) ignorant of whether anyone is listening, and lets
the dashboard mount a single connection per active scout.
"""

from __future__ import annotations

import asyncio
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sse_starlette.sse import EventSourceResponse

from whorl.auth import current_user
from whorl.db import get_session
from whorl.models import Farm, Field, Scout, User
from whorl.stream.hub import LiveHub
from whorl.stream.sse import sse_message

router = APIRouter()


# Heartbeat cadence — keeps proxies (Caddy, nginx) from dropping idle
# connections and lets the client distinguish "alive but quiet" from "dead".
HEARTBEAT_S = 15.0


async def _scout_in_org(
    session: AsyncSession, scout_id: UUID, org_id: UUID,
) -> Scout | None:
    return (await session.execute(
        select(Scout).join(Field, Scout.field_id == Field.id)
        .join(Farm, Field.farm_id == Farm.id)
        .where(Scout.id == scout_id, Farm.org_id == org_id)
    )).scalar_one_or_none()


@router.get("/api/stream/scouts/{scout_id}")
async def stream_scout(
    scout_id: UUID,
    request: Request,
    user: Annotated[User, Depends(current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
):
    scout = await _scout_in_org(session, scout_id, user.org_id)
    if scout is None:
        raise HTTPException(status_code=404, detail="scout not found")

    hub: LiveHub = request.app.state.hub
    queue = hub.subscribe()
    scout_id_str = str(scout_id)

    async def gen():
        # Tell the client we're connected and what the current scout state is —
        # avoids a "loading" flash if it reconnects mid-flow.
        yield sse_message("connected", {
            "scout_id": scout_id_str,
            "scout_status": scout.status,
        })
        try:
            while True:
                try:
                    event, data = await asyncio.wait_for(
                        queue.get(), timeout=HEARTBEAT_S,
                    )
                except asyncio.TimeoutError:
                    # Comment-line keep-alive — EventSourceResponse handles
                    # the SSE-level ping automatically when we yield a dict
                    # with `comment` set, but a typed heartbeat is friendlier
                    # to the client debugger.
                    yield sse_message("heartbeat", {"t": "ping"})
                    continue
                if await request.is_disconnected():
                    break
                if data.get("scout_id") != scout_id_str:
                    continue
                yield sse_message(event, data)
                if event == "scout_complete":
                    break
        finally:
            hub.unsubscribe(queue)

    return EventSourceResponse(gen())
