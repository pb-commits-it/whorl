"""Nightly weather pre-fetch for every field with a centroid recorded.

Invoked by `whorl weather sync` (the production systemd timer fires at 04:00
local). Fields with no centroid are skipped so we don't burn API quota on
fall-back-to-central-Kansas placeholder coordinates.
"""

from __future__ import annotations

import logging

from sqlalchemy import select

from whorl.config import get_settings
from whorl.db import make_engine, make_session_factory
from whorl.models import Field
from whorl.weather.service import forecast_for_field

log = logging.getLogger("whorl.weather.sync")


async def sync_all_fields() -> int:
    """Refresh weather for every field with a real centroid. Returns the count."""
    settings = get_settings()
    engine = make_engine(settings.database_url)
    factory = make_session_factory(engine)
    refreshed = 0
    try:
        async with factory() as session:
            fields = (await session.execute(
                select(Field).where(
                    Field.centroid_lat.is_not(None),
                    Field.centroid_lon.is_not(None),
                )
            )).scalars().all()
            log.info("syncing weather for %d fields", len(fields))
            for f in fields:
                try:
                    await forecast_for_field(session, f, force=True, days=7)
                    refreshed += 1
                except Exception as exc:   # noqa: BLE001
                    log.warning("field %s sync failed: %s", f.id, exc)
    finally:
        await engine.dispose()
    log.info("weather sync done — refreshed=%d", refreshed)
    return refreshed
