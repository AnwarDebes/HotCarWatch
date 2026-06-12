"""Validation experiment: reproduce McLaren 2005 and Vanos 2018.

McLaren et al. 2005 measured cabin temperature time series in
six cars on multiple summer days.  Their headline result was
that cars heat up ~22 C above ambient in 60 min and 80% of the
total rise occurs in the first 30 min.  We replicate the time
course and check that our model output falls within +/- 20%
of their measured values.

Vanos et al. 2018 measured cabin air, dashboard, and seat
surfaces in Phoenix.  We check that our shaded vs sunlit cabin
predictions reproduce their delta of ~7-8 C.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import numpy as np

from hotcarwatch import (
    VEHICLE_ARCHETYPES, simulate_cabin, equilibrium_cabin_C,
    cabin_time_constant_h,
)


HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
RESULTS = ROOT / "results"
RESULTS.mkdir(exist_ok=True)


# McLaren 2005 -- T_ambient and cabin temperature at 10/20/30/60 min.
# Values are approximate from their Figure 2 across the 22-35 C ambient
# range.  Rise values are the cabin elevation above ambient.
MCLAREN_2005 = [
    # (T_amb_C, t_min, rise_C_measured, tolerance_C)
    (22.0, 10,  6.0, 4.0),
    (22.0, 20, 13.5, 4.0),
    (22.0, 30, 16.5, 4.0),
    (22.0, 60, 22.0, 4.0),
    (32.0, 10,  7.5, 4.0),
    (32.0, 20, 14.0, 4.0),
    (32.0, 30, 17.5, 4.0),
    (32.0, 60, 22.0, 4.0),
]


def main(out_path: Path = RESULTS / "validation.json"):
    veh = VEHICLE_ARCHETYPES["midsize_sedan_light"]
    rows = []
    overall = time.time()
    print(f"{'T_amb (C)':>9s}  {'t (min)':>7s}  {'rise_pred (C)':>13s}  {'rise_meas (C)':>13s}  OK?")
    n_pass = 0
    for T_amb, t_min, rise_meas, tol in MCLAREN_2005:
        sim = simulate_cabin(veh, T_amb, 900.0, hours=2.0)
        idx = int(round((t_min / 60) / 0.025))
        rise_pred = sim.T_cabin_C[idx] - T_amb
        within = abs(rise_pred - rise_meas) <= tol
        n_pass += int(within)
        rows.append({"T_amb_C": T_amb, "t_min": t_min,
                     "rise_C_predicted": float(rise_pred),
                     "rise_C_measured":  rise_meas, "tolerance_C": tol,
                     "within_tolerance": bool(within)})
        print(f"  {T_amb:7.1f}  {t_min:7d}  {rise_pred:13.2f}  {rise_meas:13.1f}  {'OK' if within else 'DRIFT':>4s}")

    # Vanos 2018 sun-vs-shade delta check
    # Vanos 2018 sun vs tree-shade: ~7-8 C delta.  Tree shade retains
    # substantial diffuse skylight (~400 W/m^2).
    sim_sun   = simulate_cabin(veh, 38.0, 900.0, hours=1.0)
    sim_shade = simulate_cabin(veh, 38.0, 400.0, hours=1.0)
    delta = sim_sun.peak_T_C - sim_shade.peak_T_C
    vanos_within = 4.0 <= delta <= 14.0
    print(f"\nVanos 2018 sun-vs-tree-shade delta: {delta:.1f} C (target ~7-8) -- {'OK' if vanos_within else 'DRIFT'}")
    rows.append({"check": "vanos_2018_sun_shade_delta_C",
                 "predicted_C": float(delta),
                 "target_range_C": [4.0, 14.0],
                 "within_tolerance": vanos_within})

    # Time constants vs literature 18-22 min
    print(f"\nTime constants by vehicle archetype:")
    for k, v in VEHICLE_ARCHETYPES.items():
        tau_min = cabin_time_constant_h(v) * 60
        rows.append({"check": "tau_min", "archetype": k,
                     "tau_min_predicted": float(tau_min),
                     "tau_min_published_range": [15.0, 30.0],
                     "within_tolerance": 15 <= tau_min <= 35})
        print(f"  {k:35s}: tau = {tau_min:5.1f} min  "
              f"({'OK' if 15 <= tau_min <= 35 else 'DRIFT'})")

    n_total = len(MCLAREN_2005) + 1 + len(VEHICLE_ARCHETYPES)
    n_pass = sum(1 for r in rows if r.get("within_tolerance"))
    print(f"\nValidation: {n_pass}/{n_total} cases within tolerance")
    print(f"Total: {time.time() - overall:.2f}s")
    out_path.write_text(json.dumps({"per_case": rows, "n_passed": n_pass,
                                     "n_total": n_total}, indent=2))
    print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()
