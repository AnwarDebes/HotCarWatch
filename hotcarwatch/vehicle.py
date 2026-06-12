"""Vehicle thermal characteristics for parked-car heating.

Each vehicle archetype is parameterised by the four numbers that
matter for the parked-car heat-balance ODE:

* glass_area_m2:  glass area exposed to direct sun (m^2)
* body_area_m2:   exterior surface area (m^2) -- governs convective loss
* thermal_mass_J_per_K:  total cabin thermal mass (air + interior plastics + steel)
* glass_transmissivity:  fraction of incident solar that reaches interior (0-1)

Plus two surface properties:

* exterior_absorptivity:  fraction of incident solar absorbed by body
  (dark colors ~ 0.85, light colors ~ 0.30)
* U_body_W_m2_K:          effective overall heat transfer coefficient
  through the body shell (typically 5-8 for sheet-metal + thin insulation)

References:
    McLaren, Null & Quinn 2005 Pediatrics 116:e109-e112
    Grundstein, Meentemeyer & Dowd 2009 Int J Biometeorol 53:255
    Vanos et al. 2018 Temperature 5:276-292
    Dadour et al. 2011 (vehicle color thermal effect)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict


@dataclass(frozen=True)
class Vehicle:
    key:                   str
    label:                 str
    glass_area_m2:         float
    body_area_m2:          float
    thermal_mass_J_per_K:  float    # cabin air + interior + steel
    glass_transmissivity:  float    # 0-1
    exterior_absorptivity: float    # 0-1 (dark vs light)
    U_body_W_m2_K:         float
    cabin_volume_m3:       float = 3.0


VEHICLE_ARCHETYPES: Dict[str, Vehicle] = {
    "compact_sedan_light":   Vehicle(
        "compact_sedan_light",   "Compact sedan, light exterior, clear glass",
        glass_area_m2=2.2,  body_area_m2=8.5,  thermal_mass_J_per_K=70_000,
        glass_transmissivity=0.80, exterior_absorptivity=0.35,
        U_body_W_m2_K=6.5, cabin_volume_m3=2.8),
    "compact_sedan_dark":    Vehicle(
        "compact_sedan_dark",    "Compact sedan, dark exterior, clear glass",
        glass_area_m2=2.2,  body_area_m2=8.5,  thermal_mass_J_per_K=70_000,
        glass_transmissivity=0.80, exterior_absorptivity=0.85,
        U_body_W_m2_K=6.5, cabin_volume_m3=2.8),
    "midsize_sedan_light":   Vehicle(
        "midsize_sedan_light",   "Midsize sedan, light exterior",
        glass_area_m2=2.6,  body_area_m2=9.5,  thermal_mass_J_per_K=85_000,
        glass_transmissivity=0.80, exterior_absorptivity=0.35,
        U_body_W_m2_K=6.5, cabin_volume_m3=3.0),
    "midsize_sedan_dark":    Vehicle(
        "midsize_sedan_dark",    "Midsize sedan, dark exterior",
        glass_area_m2=2.6,  body_area_m2=9.5,  thermal_mass_J_per_K=85_000,
        glass_transmissivity=0.80, exterior_absorptivity=0.85,
        U_body_W_m2_K=6.5, cabin_volume_m3=3.0),
    "suv_dark_tinted":       Vehicle(
        "suv_dark_tinted",       "Large SUV, dark exterior, lightly tinted glass",
        glass_area_m2=3.0,  body_area_m2=12.0, thermal_mass_J_per_K=120_000,
        glass_transmissivity=0.65, exterior_absorptivity=0.85,
        U_body_W_m2_K=6.5, cabin_volume_m3=4.2),
    "minivan_light":         Vehicle(
        "minivan_light",         "Minivan, light exterior, large glass area",
        glass_area_m2=3.2,  body_area_m2=12.5, thermal_mass_J_per_K=110_000,
        glass_transmissivity=0.80, exterior_absorptivity=0.35,
        U_body_W_m2_K=6.5, cabin_volume_m3=4.5),
    "midsize_dark_with_sunshade": Vehicle(
        "midsize_dark_with_sunshade", "Midsize dark sedan + windshield sunshade",
        glass_area_m2=2.6,  body_area_m2=9.5,  thermal_mass_J_per_K=85_000,
        glass_transmissivity=0.40,    # sunshade blocks ~50% of windshield gain
        exterior_absorptivity=0.85,
        U_body_W_m2_K=6.5, cabin_volume_m3=3.0),
}


def glass_transmissivity_from_tint(tint_percent: float) -> float:
    """Convert window tint (% light transmission) to transmissivity (0-1).
    'Clear glass' is ~80% (no aftermarket tint); 'limo tint' is ~5%.
    Most US states limit windshield tint to >= 70%."""
    return max(0.05, min(0.85, tint_percent / 100.0))
