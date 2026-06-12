"""Cabin air thermal balance.

The cabin is modelled as a single thermal mass M (J/K) -- the sum
of the cabin air, the seats, the dashboard, the steering wheel, and
the interior steel plate.  Three heat-flux terms act on it:

    M dT_c/dt = Q_solar(t) - U_body * A_body * (T_c - T_amb)
                            - vent_W_per_K * (T_c - T_amb)

* Q_solar = abs_int * tau_glass * A_glass * S_solar
  where S_solar is the incident solar irradiance (W/m^2).
  Additional exterior-skin absorption adds
  alpha_ext * S_solar * A_skin_eff, but most of that re-radiates
  outward; we lump it into an effective elevation of the body's
  effective absorptivity so the solar gain term captures both
  interior and re-radiated paths.
* U_body * A_body * (T_c - T_amb) is the conductive loss through
  the body shell.
* vent_W_per_K is an optional ventilation term (windows cracked).
  Empirically (McLaren 2005), cracking the windows ~1.5 in adds
  negligible ventilation -- we model this with a small term that
  shifts equilibrium by only ~1-3 C.

The equilibrium cabin temperature is

    T_c,eq = T_amb + Q_solar / (U_body * A_body + vent_W_per_K)

and the time constant is

    tau = M / (U_body * A_body + vent_W_per_K).

The analytical solution is exponential:

    T_c(t) = T_c,eq + (T_c(0) - T_c,eq) * exp(-t / tau).
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Sequence, Union

import numpy as np

from .vehicle import Vehicle


# Effective interior absorptivity for solar that gets through the glass.
# Cabin interiors absorb ~70-80% of incoming photons (Vanos 2018).
INTERIOR_ABSORPTIVITY = 0.75

# Effective contribution from exterior skin re-radiating inward.  This
# is small but non-negligible for dark colors.  We model it as adding
# alpha_ext * eta_skin to the in-cabin solar gain.
SKIN_INWARD_RERAD_FRACTION = 0.18


def _vent_W_per_K(window_open_fraction: float, body_area_m2: float) -> float:
    """Crude convective venting model: closed -> ~0; small crack -> ~5
    W/K; fully open -> ~50 W/K (relative to a typical body area)."""
    f = max(0.0, min(1.0, window_open_fraction))
    return f * 50.0 * (body_area_m2 / 10.0)


def solar_gain_W(vehicle: Vehicle, solar_W_per_m2: float) -> float:
    """Total in-cabin solar heat gain (W) for the given irradiance."""
    direct = INTERIOR_ABSORPTIVITY * vehicle.glass_transmissivity * \
                vehicle.glass_area_m2 * solar_W_per_m2
    indirect = SKIN_INWARD_RERAD_FRACTION * vehicle.exterior_absorptivity * \
                  vehicle.body_area_m2 * solar_W_per_m2 * 0.10
    # The indirect path goes through the body U-value and the cabin's
    # thermal mass with a substantial attenuation factor (~0.10) before
    # reaching the cabin air -- see Vanos 2018 surface vs air gradient.
    return float(direct + indirect)


def equilibrium_cabin_C(vehicle: Vehicle, T_outdoor_C: float,
                          solar_W_per_m2: float,
                          window_open_fraction: float = 0.0) -> float:
    """Steady-state cabin temperature."""
    Q_sol = solar_gain_W(vehicle, solar_W_per_m2)
    L = vehicle.U_body_W_m2_K * vehicle.body_area_m2 + \
        _vent_W_per_K(window_open_fraction, vehicle.body_area_m2)
    if L <= 0:
        return T_outdoor_C
    return float(T_outdoor_C + Q_sol / L)


def cabin_time_constant_h(vehicle: Vehicle,
                              window_open_fraction: float = 0.0) -> float:
    """Thermal time constant tau (hours) of the cabin lump."""
    L = vehicle.U_body_W_m2_K * vehicle.body_area_m2 + \
        _vent_W_per_K(window_open_fraction, vehicle.body_area_m2)
    if L <= 0:
        return math.inf
    return vehicle.thermal_mass_J_per_K / L / 3600.0


@dataclass
class CabinSimulation:
    times_h:               np.ndarray
    T_cabin_C:             np.ndarray
    T_outdoor_C:           np.ndarray
    solar_W_per_m2:        np.ndarray
    T_cabin_equilibrium_C: float
    tau_h:                 float
    t_h_at_peak:           float
    peak_T_C:              float


def simulate_cabin(vehicle:               Vehicle,
                     T_outdoor_C:          Union[float, Sequence[float]],
                     solar_W_per_m2:       Union[float, Sequence[float]] = 900.0,
                     hours:                float = 2.0,
                     dt_h:                 float = 0.025,
                     T_cabin_initial_C:    float | None = None,
                     window_open_fraction: float = 0.0) -> CabinSimulation:
    """Forward-simulate the cabin temperature ODE on a uniform grid.

    Inputs may be scalar or array-like (same length as time grid).
    """
    n = max(2, int(round(hours / dt_h)))
    times = np.arange(n) * dt_h
    # Coerce inputs
    if np.ndim(T_outdoor_C) == 0:
        T_out_series = np.full(n, float(T_outdoor_C))
    else:
        x = np.asarray(T_outdoor_C, dtype=np.float64)
        T_out_series = (x if x.shape[0] == n
                            else np.interp(times, np.linspace(0, hours, x.shape[0]), x))
    if np.ndim(solar_W_per_m2) == 0:
        S_series = np.full(n, float(solar_W_per_m2))
    else:
        x = np.asarray(solar_W_per_m2, dtype=np.float64)
        S_series = (x if x.shape[0] == n
                       else np.interp(times, np.linspace(0, hours, x.shape[0]), x))

    if T_cabin_initial_C is None:
        T_cabin_initial_C = float(T_out_series[0])

    T_c = np.zeros(n)
    T_c[0] = T_cabin_initial_C
    L = vehicle.U_body_W_m2_K * vehicle.body_area_m2 + \
        _vent_W_per_K(window_open_fraction, vehicle.body_area_m2)
    tau = vehicle.thermal_mass_J_per_K / L / 3600.0   # hours

    for k in range(n - 1):
        dt = times[k + 1] - times[k]
        Q_sol_k = solar_gain_W(vehicle, S_series[k])
        T_eq = T_out_series[k] + Q_sol_k / L
        T_c[k + 1] = T_eq + (T_c[k] - T_eq) * math.exp(-dt / tau)

    peak_idx = int(np.argmax(T_c))
    return CabinSimulation(
        times_h=times,
        T_cabin_C=T_c,
        T_outdoor_C=T_out_series,
        solar_W_per_m2=S_series,
        T_cabin_equilibrium_C=float(T_out_series[0]
                                        + solar_gain_W(vehicle, float(S_series[0])) / L),
        tau_h=float(tau),
        t_h_at_peak=float(times[peak_idx]),
        peak_T_C=float(T_c[peak_idx]),
    )
