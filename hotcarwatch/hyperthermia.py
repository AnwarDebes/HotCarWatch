"""Occupant core-body-temperature ODE driven by cabin air temperature.

We model the core body temperature with a simplified heat balance:

    m_body * c_body * dT_core/dt
        = Q_metabolic
          + h_eff * A_body * (T_cabin - T_core)        [convective ; only when T_cabin > T_core]
          - Q_sweat                                      [evaporative cooling, capped]

where c_body ~ 3470 J/(kg K) (Burton 1935).

In hot conditions (T_cabin > T_core) heat flows INTO the body.
Below T_cabin ~ 35 C the body can dissipate via sweating (humans);
above ~ 40 C sweating is overwhelmed and core temperature climbs.

Pets without sweat glands (dogs, cats) have sweat_capacity_W = 0, so
they cannot evaporatively cool through their skin.  Dogs can cool by
panting BUT only when T_cabin < ~ 40 C; we model this by capping the
panting contribution to a small fraction of the convective-loss
budget that disappears once T_cabin exceeds 40 C.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Optional

import numpy as np

from .occupant import Occupant, OccupantClass
from .thermal import CabinSimulation


CORE_NEUTRAL_C = 37.0
CORE_HEAT_STROKE_C = 40.0     # adult; child threshold lower (clinically)
CORE_CRITICAL_C = 42.0
C_BODY_J_PER_KG_K = 3470.0    # Burton 1935 specific heat of human tissue
H_EFF_W_PER_M2_K = 8.0        # effective coupling between skin and cabin air


def _panting_cooling_W(occ: Occupant, T_cabin_C: float, T_core_C: float
                          ) -> float:
    """For dogs: panting provides a partial evaporative cooling but
    only while T_cabin < body temperature."""
    if occ.occ_class is not OccupantClass.DOG:
        return 0.0
    if T_cabin_C >= T_core_C - 0.5:
        return 0.0
    # Healthy dogs can dissipate ~ 1.0 W/kg by panting in moderate heat.
    # Brachycephalic breeds are derated via their sweat_capacity_W (0
    # already) and lower T_core_threshold.
    return max(0.0, 1.0 * occ.mass_kg * (1 - max(0, T_cabin_C - 32) / 8))


@dataclass
class HyperthermiaTimeline:
    times_h:           np.ndarray
    T_core_C:          np.ndarray
    time_to_threshold_h: Optional[float]
    time_to_40C_h:     Optional[float]
    time_to_critical_h:Optional[float]
    peak_T_core_C:     float
    final_T_core_C:    float


def hyperthermia_timeline(occ: Occupant,
                            cabin: CabinSimulation,
                            T_core_initial_C: Optional[float] = None
                            ) -> HyperthermiaTimeline:
    """Compute the time evolution of the occupant's core body temperature
    given a CabinSimulation.  Identifies time-to-threshold/critical.
    """
    if T_core_initial_C is None:
        T_core_initial_C = occ.T_core_neutral_C
    n = len(cabin.times_h)
    T_core = np.zeros(n)
    T_core[0] = T_core_initial_C
    m_c_body = occ.mass_kg * C_BODY_J_PER_KG_K

    t_thresh_idx = -1
    t_40_idx = -1
    t_crit_idx = -1

    for k in range(n - 1):
        dt_s = (cabin.times_h[k + 1] - cabin.times_h[k]) * 3600.0
        T_cab = cabin.T_cabin_C[k]
        T_core_k = T_core[k]
        # Convective coupling (always); h * A * (T_cab - T_core)
        Q_conv = H_EFF_W_PER_M2_K * occ.surface_area_m2 * (T_cab - T_core_k)
        # Metabolic always present
        Q_met = occ.metabolic_W
        # Evaporative cooling (sweat or panting); only when not overwhelmed
        Q_evap = 0.0
        if T_cab > 31.0:
            # Sweat is effective up to T_cab ~ 38 C, then derated above
            sweat_eff = occ.sweat_capacity_W * max(0.0, 1.0 - max(0, T_cab - 38) / 6)
            Q_evap += sweat_eff
        Q_evap += _panting_cooling_W(occ, T_cab, T_core_k)
        # Net heating
        Q_net = Q_conv + Q_met - Q_evap
        T_core[k + 1] = T_core_k + Q_net * dt_s / m_c_body
        # Latch milestone indices
        if T_core[k + 1] >= occ.T_core_threshold_C and t_thresh_idx < 0:
            t_thresh_idx = k + 1
        if T_core[k + 1] >= 40.0 and t_40_idx < 0:
            t_40_idx = k + 1
        if T_core[k + 1] >= occ.T_core_critical_C and t_crit_idx < 0:
            t_crit_idx = k + 1

    def _idx_to_h(idx: int) -> Optional[float]:
        return float(cabin.times_h[idx]) if idx >= 0 else None

    return HyperthermiaTimeline(
        times_h=cabin.times_h,
        T_core_C=T_core,
        time_to_threshold_h=_idx_to_h(t_thresh_idx),
        time_to_40C_h=_idx_to_h(t_40_idx),
        time_to_critical_h=_idx_to_h(t_crit_idx),
        peak_T_core_C=float(T_core.max()),
        final_T_core_C=float(T_core[-1]),
    )
