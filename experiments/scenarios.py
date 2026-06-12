"""Scenario experiment: full vehicle x occupant matrix on 4 days."""

from __future__ import annotations

import json
import time
from pathlib import Path

import numpy as np

from hotcarwatch import (
    VEHICLE_ARCHETYPES, OCCUPANT_ARCHETYPES,
    simulate_cabin, hyperthermia_timeline,
    mild_spring_day, summer_phoenix, southern_humid_day, cloudy_warm_day,
)


HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
RESULTS = ROOT / "results"
RESULTS.mkdir(exist_ok=True)


SCENARIOS = [mild_spring_day, summer_phoenix, southern_humid_day, cloudy_warm_day]


def main(out_path: Path = RESULTS / "scenarios.json"):
    results = []
    overall = time.time()
    for sc_fn in SCENARIOS:
        sc = sc_fn(hours=3.0)
        print(f"\n=== {sc.name} ===")
        print(f"  notes: {sc.notes}")
        for vk, veh in VEHICLE_ARCHETYPES.items():
            for ok, occ in OCCUPANT_ARCHETYPES.items():
                sim = simulate_cabin(veh, sc.T_outdoor_C, sc.solar_W_per_m2,
                                       hours=float(sc.times_h[-1]) + 0.025)
                hot = hyperthermia_timeline(occ, sim)
                t_thresh = hot.time_to_threshold_h
                t40      = hot.time_to_40C_h
                t_crit   = hot.time_to_critical_h
                results.append({
                    "scenario":  sc.name,
                    "vehicle":   vk,
                    "occupant":  ok,
                    "peak_cabin_C": float(sim.peak_T_C),
                    "tau_h":        float(sim.tau_h),
                    "time_to_threshold_h": t_thresh,
                    "time_to_40C_h":       t40,
                    "time_to_critical_h":  t_crit,
                    "peak_core_C":   float(hot.peak_T_core_C),
                })
        # pretty per-scenario summary
        print(f"  Peak cabin temps:")
        for vk, veh in list(VEHICLE_ARCHETYPES.items())[:4]:
            sim = simulate_cabin(veh, sc.T_outdoor_C, sc.solar_W_per_m2,
                                   hours=float(sc.times_h[-1]) + 0.025)
            print(f"    {vk:35s}: peak {sim.peak_T_C:5.1f} C")
        print(f"  Time-to-40C for toddler:")
        for vk, veh in list(VEHICLE_ARCHETYPES.items())[:4]:
            sim = simulate_cabin(veh, sc.T_outdoor_C, sc.solar_W_per_m2,
                                   hours=float(sc.times_h[-1]) + 0.025)
            hot = hyperthermia_timeline(OCCUPANT_ARCHETYPES["toddler_2y"], sim)
            t = "n/a (>3h)" if hot.time_to_40C_h is None else f"{hot.time_to_40C_h*60:5.1f} min"
            print(f"    {vk:35s}: {t}")

    print(f"\nTotal: {time.time() - overall:.2f}s")
    out_path.write_text(json.dumps({"per_case": results}, indent=2))
    print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()
