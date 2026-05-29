"""Seed a demo organization for the launch.

Creates `demo@whorl.app` (farmer org) with one farm, one corn field at
Manhattan, KS coordinates, one logged IRAC 3A bifenthrin application 14 days
ago — exactly the setup the README hero scout uses.

Idempotent: re-running just no-ops or repairs the same rows.

  python scripts/seed_demo.py
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from whorl.config import get_settings
from whorl.db import make_engine, make_session_factory
from whorl.models import (
    Application,
    Farm,
    Field,
    Organization,
    User,
)

DEMO_EMAIL = "demo@whorl.app"
DEMO_ORG = "Demo Farm — whorl.app"
DEMO_FARM = "Hartman Family Farm"
DEMO_FIELD = "North 80"
DEMO_LAT = 39.2050     # Manhattan, KS — in range of the KSU Mesonet station
DEMO_LON = -96.5847


async def seed():
    settings = get_settings()
    engine = make_engine(settings.database_url)
    factory = make_session_factory(engine)
    try:
        async with factory() as session:
            org = (await session.execute(
                select(Organization).where(Organization.name == DEMO_ORG)
            )).scalar_one_or_none()
            if org is None:
                org = Organization(name=DEMO_ORG, type="farmer")
                session.add(org)
                await session.flush()
                print(f"  + org {org.id}")

            user = (await session.execute(
                select(User).where(User.email == DEMO_EMAIL)
            )).scalar_one_or_none()
            if user is None:
                user = User(
                    org_id=org.id, email=DEMO_EMAIL, name="Demo Scout", role="owner",
                )
                session.add(user)
                await session.flush()
                print(f"  + user {user.email}")

            farm = (await session.execute(
                select(Farm).where(Farm.org_id == org.id, Farm.name == DEMO_FARM)
            )).scalar_one_or_none()
            if farm is None:
                farm = Farm(org_id=org.id, name=DEMO_FARM, notes="Demo farm seeded by scripts/seed_demo.py")
                session.add(farm)
                await session.flush()
                print(f"  + farm {farm.id}")

            field = (await session.execute(
                select(Field).where(Field.farm_id == farm.id, Field.name == DEMO_FIELD)
            )).scalar_one_or_none()
            if field is None:
                field = Field(
                    farm_id=farm.id, name=DEMO_FIELD, crop="corn",
                    centroid_lat=DEMO_LAT, centroid_lon=DEMO_LON, acres=80,
                )
                session.add(field)
                await session.flush()
                print(f"  + field {field.id}")
            else:
                # Repair coords on existing rows so the demo always has Mesonet.
                field.centroid_lat = DEMO_LAT
                field.centroid_lon = DEMO_LON

            # IRAC 3A application — 14 days back. Only seed if absent (we don't
            # want to keep stacking duplicates each time someone re-runs this).
            existing_app = (await session.execute(
                select(Application).where(
                    Application.field_id == field.id,
                    Application.product_name == "Brigade 2EC",
                )
            )).scalar_one_or_none()
            if existing_app is None:
                applied = datetime.now(UTC).replace(tzinfo=None) - timedelta(days=14)
                session.add(Application(
                    field_id=field.id, applied_at=applied,
                    product_name="Brigade 2EC", active_ingredient="bifenthrin",
                    moa_class="IRAC", moa_group="3A",
                    pest_target="Helicoverpa zea",
                    rate="6.4 oz/ac", rei_hours=12, phi_days=1,
                    recorded_by=user.id,
                    notes="Seeded by scripts/seed_demo.py — forces MOA rotation in the recommender.",
                ))
                print("  + application (IRAC 3A bifenthrin, 14d ago)")

            await session.commit()
            print(f"demo seeded — sign in as {DEMO_EMAIL}")
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(seed())
