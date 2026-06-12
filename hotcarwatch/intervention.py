"""Intervention recommendation.

Given a baseline Vehicle + Occupant + scenario, evaluate each
candidate intervention and rank by the change in time-to-threshold
(longer is better).

The only intervention that GUARANTEES safety is
``do_not_leave_occupant``.  This is communicated explicitly.

Other interventions can buy minutes but do not make hot cars safe.
"""

from __future__ import annotations

import copy
import math
from dataclasses import dataclass
from typing import List, Optional

from .vehicle import Vehicle
from .occupant import Occupant
from .thermal import simulate_cabin
from .hyperthermia import hyperthermia_timeline


@dataclass
class Intervention:
    key:               str
    label:             str
    description:       str
    one_time_cost_usd: float = 0.0
    daily_cost_usd:    float = 0.0


INTERVENTIONS = {
    "do_not_leave_occupant": Intervention(
        "do_not_leave_occupant",
        "DO NOT leave the occupant in the vehicle (only safe option)",
        "Leaving any human or animal in any parked vehicle in any sun is "
        "unsafe.  This is the only intervention that prevents heat injury "
        "with certainty.",
    ),
    "crack_windows": Intervention(
        "crack_windows",
        "Crack windows ~1.5 inches",
        "Commonly believed protective; McLaren 2005 measured 0-3 C "
        "reduction in peak cabin temperature.  Inadequate.",
    ),
    "open_windows_halfway": Intervention(
        "open_windows_halfway",
        "Open windows halfway",
        "Adds substantial ventilation -- bigger reduction than cracking, "
        "but still inadequate in direct sun.  Vehicle theft risk.",
    ),
    "use_windshield_sunshade": Intervention(
        "use_windshield_sunshade",
        "Deploy a reflective windshield sunshade",
        "Blocks ~50% of solar gain through the windshield (Vanos 2018).  "
        "Reduces peak cabin temperature by ~5-8 C but does not eliminate it.",
    ),
    "park_in_shade": Intervention(
        "park_in_shade",
        "Park in deep shade or covered garage",
        "Reduces solar load to ~10-20% of full-sun.  Most effective "
        "intervention short of not leaving the occupant.",
    ),
    "leave_engine_ac_on": Intervention(
        "leave_engine_ac_on",
        "Leave the engine + A/C running",
        "Tempting but: (a) child may turn off the engine, (b) A/C may "
        "fail, (c) carbon monoxide risk in enclosed garages, (d) vehicle "
        "theft.  Many hot-car deaths occurred with the A/C running.",
    ),
}


def _apply(vehicle: Vehicle, key: str) -> Vehicle:
    """Return a modified Vehicle reflecting the given intervention."""
    v = copy.copy(vehicle)
    if key == "use_windshield_sunshade":
        v = Vehicle(key=v.key + "_shade", label=v.label + " + sunshade",
                      glass_area_m2=v.glass_area_m2,
                      body_area_m2=v.body_area_m2,
                      thermal_mass_J_per_K=v.thermal_mass_J_per_K,
                      glass_transmissivity=v.glass_transmissivity * 0.50,
                      exterior_absorptivity=v.exterior_absorptivity,
                      U_body_W_m2_K=v.U_body_W_m2_K,
                      cabin_volume_m3=v.cabin_volume_m3)
    return v


def evaluate_interventions(vehicle: Vehicle, occupant: Occupant,
                              T_outdoor_C: float,
                              solar_W_per_m2: float,
                              hours: float = 2.0,
                              dt_h: float = 0.025,
                              park_in_shade_solar_W_per_m2: float = 120.0
                              ) -> List[dict]:
    """For each intervention return (label, time_to_40C_h_after,
    time_to_40C_h_baseline, peak_cabin_C_baseline,
    peak_cabin_C_after)."""
    # baseline
    base_sim = simulate_cabin(vehicle, T_outdoor_C, solar_W_per_m2,
                                hours=hours, dt_h=dt_h)
    base_hot = hyperthermia_timeline(occupant, base_sim)
    rows = []
    for key, intv in INTERVENTIONS.items():
        if key == "do_not_leave_occupant":
            rows.append({"intervention": key, "label": intv.label,
                         "description": intv.description,
                         "time_to_40C_after_h":   None,
                         "time_to_40C_baseline_h": base_hot.time_to_40C_h,
                         "peak_cabin_after_C":    None,
                         "peak_cabin_baseline_C": float(base_sim.peak_T_C),
                         "minutes_bought":        math.inf,
                         "guaranteed_safe":       True,
                         "one_time_cost_usd":     0.0,
                         "daily_cost_usd":        0.0})
            continue
        if key == "crack_windows":
            sim2 = simulate_cabin(vehicle, T_outdoor_C, solar_W_per_m2,
                                    hours=hours, dt_h=dt_h,
                                    window_open_fraction=0.05)
        elif key == "open_windows_halfway":
            sim2 = simulate_cabin(vehicle, T_outdoor_C, solar_W_per_m2,
                                    hours=hours, dt_h=dt_h,
                                    window_open_fraction=0.45)
        elif key == "use_windshield_sunshade":
            v2 = _apply(vehicle, key)
            sim2 = simulate_cabin(v2, T_outdoor_C, solar_W_per_m2,
                                    hours=hours, dt_h=dt_h)
        elif key == "park_in_shade":
            sim2 = simulate_cabin(vehicle, T_outdoor_C,
                                    park_in_shade_solar_W_per_m2,
                                    hours=hours, dt_h=dt_h)
        elif key == "leave_engine_ac_on":
            # A/C target ~22 C; clip cabin temperature trajectory at 22 C
            sim2 = simulate_cabin(vehicle, 22.0, 0.0, hours=hours,
                                    dt_h=dt_h, T_cabin_initial_C=22.0)
        else:
            sim2 = base_sim

        hot2 = hyperthermia_timeline(occupant, sim2)
        # Minutes bought relative to baseline
        if base_hot.time_to_40C_h is None:
            minutes_bought = 0
        elif hot2.time_to_40C_h is None:
            minutes_bought = math.inf
        else:
            minutes_bought = 60.0 * (hot2.time_to_40C_h - base_hot.time_to_40C_h)
        rows.append({
            "intervention": key, "label": intv.label,
            "description":  intv.description,
            "time_to_40C_after_h":   hot2.time_to_40C_h,
            "time_to_40C_baseline_h": base_hot.time_to_40C_h,
            "peak_cabin_after_C":    float(sim2.peak_T_C),
            "peak_cabin_baseline_C": float(base_sim.peak_T_C),
            "minutes_bought":        float(minutes_bought)
                                        if math.isfinite(minutes_bought) else math.inf,
            "guaranteed_safe":       False,
            "one_time_cost_usd":     intv.one_time_cost_usd,
            "daily_cost_usd":        intv.daily_cost_usd,
        })
    return rows


def rank_interventions(vehicle: Vehicle, occupant: Occupant,
                          T_outdoor_C: float,
                          solar_W_per_m2: float,
                          hours: float = 2.0,
                          max_recommendations: int = 4) -> List[dict]:
    """Top-K interventions; ``do_not_leave_occupant`` is always first."""
    rows = evaluate_interventions(vehicle, occupant, T_outdoor_C,
                                    solar_W_per_m2, hours=hours)
    # The 'do_not_leave_occupant' row is always the headline; rank the
    # rest by minutes bought.
    head = [r for r in rows if r["intervention"] == "do_not_leave_occupant"]
    tail = [r for r in rows if r["intervention"] != "do_not_leave_occupant"]
    tail.sort(key=lambda r: -r["minutes_bought"])
    return head + tail[:max_recommendations - 1]
