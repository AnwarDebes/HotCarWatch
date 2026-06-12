"""Intervention experiment: minutes-bought for each intervention
across all scenario x vehicle x occupant combinations."""

from __future__ import annotations

import json
import time
from pathlib import Path

import numpy as np

from hotcarwatch import (
    VEHICLE_ARCHETYPES, OCCUPANT_ARCHETYPES,
    mild_spring_day, summer_phoenix, southern_humid_day,
    evaluate_interventions,
)


HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
RESULTS = ROOT / "results"
RESULTS.mkdir(exist_ok=True)


def main(out_path: Path = RESULTS / "interventions.json"):
    scenarios = [mild_spring_day(hours=2.0),
                 summer_phoenix(hours=2.0),
                 southern_humid_day(hours=2.0)]
    rows = []
    overall = time.time()
    for sc in scenarios:
        for vk, veh in VEHICLE_ARCHETYPES.items():
            for ok, occ in OCCUPANT_ARCHETYPES.items():
                for r in evaluate_interventions(
                            veh, occ,
                            float(sc.T_outdoor_C[0]), float(sc.solar_W_per_m2[0]),
                            hours=2.0):
                    rows.append({
                        "scenario": sc.name, "vehicle": vk, "occupant": ok,
                        "intervention": r["intervention"], "label": r["label"],
                        "peak_cabin_baseline_C": r["peak_cabin_baseline_C"],
                        "peak_cabin_after_C":    r["peak_cabin_after_C"],
                        "time_to_40C_baseline_h": r["time_to_40C_baseline_h"],
                        "time_to_40C_after_h":    r["time_to_40C_after_h"],
                        "minutes_bought": r["minutes_bought"]
                                          if r["minutes_bought"] != float("inf") else 9999,
                        "guaranteed_safe": r["guaranteed_safe"],
                    })

    # Summary by intervention
    by_int = {}
    for r in rows:
        by_int.setdefault(r["intervention"], []).append(r)
    summary = []
    for k, rs in by_int.items():
        finite = [x["minutes_bought"] for x in rs if x["minutes_bought"] < 5000]
        med = float(np.median(finite)) if finite else float("inf")
        n_unsafe = sum(1 for x in rs if x["time_to_40C_after_h"] is not None)
        summary.append({"intervention": k,
                         "median_minutes_bought":      med,
                         "n_cases_still_dangerous":    int(n_unsafe),
                         "n_cases_total":              len(rs)})
    summary.sort(key=lambda r: -r["median_minutes_bought"])
    print("Intervention efficacy (averaged across all archetypes/scenarios):")
    for s in summary:
        print(f"  {s['intervention']:30s}: median +{s['median_minutes_bought']:6.1f} min  "
              f"(still dangerous in {s['n_cases_still_dangerous']}/{s['n_cases_total']} cases)")
    print(f"\nTotal: {time.time() - overall:.2f}s")
    out_path.write_text(json.dumps({"per_case": rows, "summary": summary}, indent=2))
    print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()
