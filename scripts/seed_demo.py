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
    Identification,
    Organization,
    Photo,
    Recommendation,
    Scout,
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

            # ─── sample completed scout ────────────────────────────────
            # Materialize one realistic completed scout so a visitor to
            # demo@whorl.app sees a populated dashboard, not an empty one.
            existing_scout = (await session.execute(
                select(Scout).where(Scout.field_id == field.id)
                .where(Scout.summary == "Helicoverpa zea")
            )).scalar_one_or_none()
            if existing_scout is None:
                started = datetime.now(UTC).replace(tzinfo=None) - timedelta(hours=4)
                completed = started + timedelta(seconds=9)
                scout = Scout(
                    field_id=field.id, user_id=user.id,
                    started_at=started, completed_at=completed,
                    status="complete", summary="Helicoverpa zea",
                    notes="Seed scout — a real recommendation generated against the live KB.",
                )
                session.add(scout)
                await session.flush()

                # Placeholder photo row pointing at a path the seed user can
                # later replace by uploading a real photo through the UI.
                photo = Photo(
                    scout_id=scout.id,
                    storage_path="seed/demo-corn-earworm.jpg",
                    thumb_path="seed/demo-corn-earworm_thumb.jpg",
                    sha256="0" * 64,
                    width=960, height=960, bytes=95358,
                )
                session.add(photo)
                await session.flush()

                session.add(Identification(
                    photo_id=photo.id, rank=1,
                    taxon_scientific="Helicoverpa zea",
                    taxon_common="corn earworm",
                    lifecycle_stage="larva",
                    confidence=0.95,
                    features=[
                        "caterpillar on corn kernels",
                        "feeding damage",
                        "brownish body",
                    ],
                    evidence="organism",
                    image_quality="good",
                    notes="Seed identification — corn earworm larva on a fresh ear.",
                    model_used="qwen/qwen3-vl-30b-a3b-instruct",
                ))

                session.add(Recommendation(
                    scout_id=scout.id,
                    action="treat",
                    pest_focus="Helicoverpa zea",
                    threshold_context=(
                        "Confirmed corn earworm larvae at silking-to-dough stage. "
                        "Economic threshold is 1 larva/ear or 5% infested ears, "
                        "currently met at this sampling intensity [1]."
                    ),
                    confidence="high",
                    plain_english=(
                        "Treat. Avoid IRAC 3A — bifenthrin (Brigade 2EC) was "
                        "applied 14 days ago and pyrethroid resistance is "
                        "documented in southern KS H. zea populations. Rotate "
                        "to spinosad (IRAC 5): REI 4 h, PHI 1 d. Spray window "
                        "looks marginal today (winds 14 mph, Manhattan obs); "
                        "the next clean window opens later in the week. Bt-k "
                        "is a strong biological alternative for L1–L2 larvae "
                        "if you prefer to skip the chemical."
                    ),
                    chemical={
                        "product": "Conserve SC",
                        "active_ingredient": "spinosad",
                        "moa_class": "IRAC",
                        "moa_group": "5",
                        "rotation_rationale": (
                            "Field had IRAC 3A bifenthrin 14 days ago; rotate "
                            "off pyrethroids per regional resistance status."
                        ),
                        "rei_hours": 4,
                        "phi_days": 1,
                    },
                    spray_window={
                        "open": (datetime.now(UTC).replace(tzinfo=None) + timedelta(days=3)).date().isoformat(),
                        "close": (datetime.now(UTC).replace(tzinfo=None) + timedelta(days=4)).date().isoformat(),
                        "reason": "winds drop below 10 mph through midday — drift risk clears",
                    },
                    alternatives=[
                        {
                            "category": "biological",
                            "name": "Bacillus thuringiensis var. kurstaki",
                            "summary": "Selective for Lepidoptera; best on L1–L2 larvae; apply in the evening to reduce UV degradation.",
                            "kb_link": "alt-controls/biological/bt-kurstaki",
                        },
                        {
                            "category": "cultural",
                            "name": "Early planting",
                            "summary": "Earlier planting escapes peak adult flight in KS by ~2 weeks; relevant for next season.",
                            "kb_link": "alt-controls/cultural/early-planting",
                        },
                    ],
                    citations=[
                        {"chunk_id": 1, "quote": "treat at 1 larva/ear or 5% infested ears sampled across the field"},
                        {"chunk_id": 2, "quote": "Pyrethroid (IRAC 3A) tolerance has been documented in H. zea populations across the Southern Plains."},
                        {"chunk_id": 3, "quote": "Spinosad — IRAC 5 — REI 4 h, PHI 1 d. Excellent efficacy on L1–L3 larvae."},
                    ],
                    model_used="qwen/qwen3-vl-30b-a3b-instruct",
                    prompt_version="v1.0",
                    latency_ms=9000,
                ))
                print(f"  + sample scout (corn earworm → spinosad rec) {scout.id}")

            await session.commit()
            print(f"demo seeded — sign in as {DEMO_EMAIL}")
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(seed())
