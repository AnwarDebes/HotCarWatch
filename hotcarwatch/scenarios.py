"""Outdoor weather scenarios for HotCarWatch.

Four reference outdoor scenarios with documented physical parameters:

* mild_spring_day:        22 C ambient, 800 W/m^2 solar
    Replicates the surprising McLaren et al. 2005 finding that a mild
    spring day produces a lethal cabin.
* summer_phoenix:         42 C ambient, 1000 W/m^2 solar
    Worst-case desert summer.
* southern_humid_day:     34 C ambient, 900 W/m^2 solar
    Typical Southern US summer afternoon.
* cloudy_warm_day:        29 C ambient, 350 W/m^2 solar (50% cloud)
    Less obvious but still dangerous.
"""

from __future__ import annotations

from dataclasses import dataclass
import numpy as np


@dataclass
class Scenario:
    name:                  str
    T_outdoor_C:           np.ndarray
    solar_W_per_m2:        np.ndarray
    times_h:               np.ndarray
    notes:                 str


def _const(value: float, hours: float = 2.0, dt_h: float = 0.025) -> np.ndarray:
    n = int(round(hours / dt_h))
    return np.full(n, float(value))


def mild_spring_day(hours: float = 2.0) -> Scenario:
    dt = 0.025
    times = np.arange(int(hours / dt)) * dt
    return Scenario(
        name="Mild spring day (22 C, full sun)",
        T_outdoor_C=_const(22.0, hours), solar_W_per_m2=_const(800.0, hours),
        times_h=times,
        notes="McLaren 2005 surprised the public health community by "
              "showing that a mild outdoor day produces a lethal cabin.",
    )


def summer_phoenix(hours: float = 2.0) -> Scenario:
    dt = 0.025
    times = np.arange(int(hours / dt)) * dt
    return Scenario(
        name="Phoenix summer afternoon (42 C, full sun)",
        T_outdoor_C=_const(42.0, hours), solar_W_per_m2=_const(1000.0, hours),
        times_h=times,
        notes="Worst case continental US; Phoenix routinely reaches 42 C.",
    )


def southern_humid_day(hours: float = 2.0) -> Scenario:
    dt = 0.025
    times = np.arange(int(hours / dt)) * dt
    return Scenario(
        name="Southern humid summer day (34 C, full sun)",
        T_outdoor_C=_const(34.0, hours), solar_W_per_m2=_const(900.0, hours),
        times_h=times,
        notes="Typical Southern US July afternoon.",
    )


def cloudy_warm_day(hours: float = 2.0) -> Scenario:
    dt = 0.025
    times = np.arange(int(hours / dt)) * dt
    return Scenario(
        name="Cloudy warm day (29 C, 50% cloud)",
        T_outdoor_C=_const(29.0, hours), solar_W_per_m2=_const(350.0, hours),
        times_h=times,
        notes="Cloud cover dramatically reduces solar load, but cabins "
              "still warm above ambient.",
    )
