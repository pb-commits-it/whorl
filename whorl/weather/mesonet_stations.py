"""Kansas Mesonet station catalog (KSRE network).

Hand-curated subset of the K-State Mesonet (mesonet.k-state.edu). ~30 stations
covers Kansas at roughly 50 km spacing; that's well below the 25 km Mesonet-
preference radius for any farm field in a settled-agriculture county.

Coordinates from the public station-info page on mesonet.k-state.edu. If a
station is renamed or relocated, the API still accepts the name token used
here (Mesonet's URL-builder treats names case-insensitively).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MesonetStation:
    name: str        # the station token accepted by the REST API (`stn=` param)
    lat: float
    lon: float
    label: str       # human-readable label for UI


STATIONS: tuple[MesonetStation, ...] = (
    MesonetStation("Manhattan",     39.2050, -96.5847, "Manhattan"),
    MesonetStation("Topeka",        39.0473, -95.6890, "Topeka"),
    MesonetStation("Wichita",       37.6577, -97.4302, "Wichita"),
    MesonetStation("GardenCity",    37.9755, -100.872, "Garden City"),
    MesonetStation("Hays",          38.8542, -99.3367, "Hays"),
    MesonetStation("Colby",         39.3920, -101.063, "Colby"),
    MesonetStation("DodgeCity",     37.7660, -100.025, "Dodge City"),
    MesonetStation("Hutchinson",    38.0670, -97.9290, "Hutchinson"),
    MesonetStation("Salina",        38.8400, -97.6200, "Salina"),
    MesonetStation("Pittsburg",     37.4108, -94.7050, "Pittsburg"),
    MesonetStation("Parsons",       37.3408, -95.2627, "Parsons"),
    MesonetStation("Olathe",        38.8814, -94.8191, "Olathe"),
    MesonetStation("Tribune",       38.4661, -101.756, "Tribune"),
    MesonetStation("Ottawa",        38.6300, -95.2700, "Ottawa"),
    MesonetStation("Independence",  37.2240, -95.7080, "Independence"),
    MesonetStation("ScottCity",     38.4828, -100.907, "Scott City"),
    MesonetStation("Wakeeney",      39.0250, -99.8830, "WaKeeney"),
    MesonetStation("Russell",       38.8950, -98.8600, "Russell"),
    MesonetStation("Belleville",    39.8244, -97.6386, "Belleville"),
    MesonetStation("Concordia",     39.5510, -97.6620, "Concordia"),
    MesonetStation("Cherokee",      37.3450, -94.8230, "Cherokee"),
    MesonetStation("Sedan",         37.1300, -96.1840, "Sedan"),
    MesonetStation("Hesston",       38.1377, -97.4322, "Hesston"),
    MesonetStation("Rossville",     39.1370, -95.9530, "Rossville"),
    MesonetStation("StJohn",        38.0040, -98.7600, "St. John"),
    MesonetStation("Wellington",    37.2670, -97.3920, "Wellington"),
    MesonetStation("Liberal",       37.0430, -100.917, "Liberal"),
    MesonetStation("Lakin",         37.9400, -101.255, "Lakin"),
    MesonetStation("Phillipsburg",  39.7560, -99.3220, "Phillipsburg"),
    MesonetStation("Atwood",        39.8060, -101.0440, "Atwood"),
)
