"""Occupants left in vehicles: children and pets.

We characterise each occupant by:

* class:     human | dog | cat (different thermoregulation)
* mass_kg
* surface_area_m2  (governs convective heat exchange with cabin air)
* metabolic_W      (resting metabolic heat production)
* sweat_capacity_W (maximum evaporative cooling at high ambient)
* T_core_neutral_C (normal core temperature)
* T_core_threshold_C (core temperature at which heat stroke begins)
* T_core_critical_C  (core temperature at which death becomes likely)

For pets we set sweat_capacity_W = 0 because dogs and cats do not
sweat over most of their body (dogs cool by panting -- effective
only when ambient < body temperature; cats are even worse).
The result is that pets reach hyperthermia faster than humans of
the same mass in hot cabin air.

References:
    Bouchama & Knochel 2002 NEJM 346:1978  (heat stroke pathophysiology)
    Bytomski & Squire 2003 Curr Sports Med Rep 2:320  (pediatric)
    Vanos 2018 Temperature 5:276 (modelled 2-yr-old core rise rate)
    PetMD / AVMA / ASPCA heat-stroke guidelines for dogs and cats
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Dict


class OccupantClass(str, Enum):
    HUMAN = "human"
    DOG   = "dog"
    CAT   = "cat"


@dataclass(frozen=True)
class Occupant:
    key:                  str
    label:                str
    occ_class:            OccupantClass
    mass_kg:              float
    surface_area_m2:      float
    metabolic_W:          float
    sweat_capacity_W:     float
    T_core_neutral_C:     float = 37.0
    T_core_threshold_C:   float = 40.0   # heat stroke onset
    T_core_critical_C:    float = 42.0   # cell death, often fatal


# A 50% under-2 mortality fraction motivates archetype selection
# (Null NoHeatstroke.org dataset).
OCCUPANT_ARCHETYPES: Dict[str, Occupant] = {
    "infant_6mo":  Occupant(
        "infant_6mo",   "Infant, ~6 months (7.5 kg)",
        OccupantClass.HUMAN, mass_kg=7.5,  surface_area_m2=0.36,
        metabolic_W=20.0, sweat_capacity_W=15.0),
    "toddler_2y":  Occupant(
        "toddler_2y",   "Toddler, ~2 years (12 kg)",
        OccupantClass.HUMAN, mass_kg=12.0, surface_area_m2=0.55,
        metabolic_W=30.0, sweat_capacity_W=22.0),
    "child_5y":    Occupant(
        "child_5y",     "Child, ~5 years (18 kg)",
        OccupantClass.HUMAN, mass_kg=18.0, surface_area_m2=0.74,
        metabolic_W=45.0, sweat_capacity_W=35.0),
    "adult":       Occupant(
        "adult",        "Adult (75 kg)",
        OccupantClass.HUMAN, mass_kg=75.0, surface_area_m2=1.85,
        metabolic_W=90.0, sweat_capacity_W=120.0),
    "small_dog_10kg": Occupant(
        "small_dog_10kg", "Small dog (10 kg, e.g. terrier)",
        OccupantClass.DOG, mass_kg=10.0, surface_area_m2=0.5,
        metabolic_W=30.0, sweat_capacity_W=0.0,
        T_core_neutral_C=38.5, T_core_threshold_C=40.5,
        T_core_critical_C=42.0),
    "medium_dog_25kg": Occupant(
        "medium_dog_25kg", "Medium dog (25 kg, e.g. Labrador)",
        OccupantClass.DOG, mass_kg=25.0, surface_area_m2=0.95,
        metabolic_W=70.0, sweat_capacity_W=0.0,
        T_core_neutral_C=38.5, T_core_threshold_C=40.5,
        T_core_critical_C=42.0),
    "brachycephalic_dog_15kg": Occupant(
        "brachycephalic_dog_15kg",
        "Brachycephalic dog (15 kg, e.g. pug / bulldog)",
        OccupantClass.DOG, mass_kg=15.0, surface_area_m2=0.65,
        metabolic_W=45.0, sweat_capacity_W=0.0,
        T_core_neutral_C=38.5, T_core_threshold_C=39.5,    # very impaired panting
        T_core_critical_C=41.5),
    "cat_5kg":     Occupant(
        "cat_5kg",     "Cat (5 kg)",
        OccupantClass.CAT, mass_kg=5.0, surface_area_m2=0.32,
        metabolic_W=18.0, sweat_capacity_W=0.0,
        T_core_neutral_C=38.6, T_core_threshold_C=40.0,
        T_core_critical_C=41.5),
}
