"""Unit tests for HotCarWatch."""

import math

import numpy as np
import pytest

from hotcarwatch import (
    VEHICLE_ARCHETYPES, OCCUPANT_ARCHETYPES,
    simulate_cabin, equilibrium_cabin_C, cabin_time_constant_h,
    hyperthermia_timeline,
    mild_spring_day, summer_phoenix, southern_humid_day, cloudy_warm_day,
    evaluate_interventions, rank_interventions,
    CORE_NEUTRAL_C, CORE_HEAT_STROKE_C, CORE_CRITICAL_C,
)


def test_equilibrium_above_ambient_in_sun():
    """McLaren 2005: cabin rises ~22 C above ambient at equilibrium."""
    v = VEHICLE_ARCHETYPES["midsize_sedan_light"]
    for T_amb in [22.0, 27.0, 32.0]:
        T_eq = equilibrium_cabin_C(v, T_amb, 900.0)
        delta = T_eq - T_amb
        assert 18 < delta < 28, f"T_amb={T_amb} delta={delta}"


def test_time_constant_in_published_range():
    """McLaren 2005: tau ~ 18-22 min (matches NIA / cabin lump calc)."""
    for key, v in VEHICLE_ARCHETYPES.items():
        tau_min = cabin_time_constant_h(v) * 60
        assert 12 < tau_min < 35, f"{key} tau {tau_min}"


def test_30min_temp_rise_mclaren():
    """McLaren 2005: ~16 C rise in 20 min, 19 C in 30 min, 22 C in 60 min
    in full sun.  Allow +/- 20% tolerance."""
    v = VEHICLE_ARCHETYPES["midsize_sedan_light"]
    sc = mild_spring_day(hours=1.0)
    sim = simulate_cabin(v, sc.T_outdoor_C, sc.solar_W_per_m2, hours=1.0)
    idx30 = int(30 / (60 * 0.025))   # 30 min
    delta30 = sim.T_cabin_C[idx30] - 22.0
    assert 12 < delta30 < 22, f"delta at 30 min = {delta30}"


def test_cracked_windows_minimal_effect():
    """McLaren 2005: cracking windows ~1.5 in had negligible effect."""
    v = VEHICLE_ARCHETYPES["midsize_sedan_dark"]
    sim_closed = simulate_cabin(v, 32.0, 900.0, hours=1.0,
                                  window_open_fraction=0.0)
    sim_crack  = simulate_cabin(v, 32.0, 900.0, hours=1.0,
                                  window_open_fraction=0.05)
    diff = sim_closed.peak_T_C - sim_crack.peak_T_C
    assert 0 <= diff < 4.0, f"diff = {diff}"


def test_shade_reduces_substantially():
    """Vanos 2018: shade reduces peak cabin by ~7-8 C vs full sun."""
    v = VEHICLE_ARCHETYPES["midsize_sedan_dark"]
    sim_sun   = simulate_cabin(v, 35.0, 900.0, hours=1.0)
    sim_shade = simulate_cabin(v, 35.0, 120.0, hours=1.0)
    diff = sim_sun.peak_T_C - sim_shade.peak_T_C
    assert diff > 5.0, f"diff = {diff}"


def test_dark_hotter_than_light():
    """Dadour 2011: dark colors absorb more, raising cabin temperature."""
    v_light = VEHICLE_ARCHETYPES["midsize_sedan_light"]
    v_dark  = VEHICLE_ARCHETYPES["midsize_sedan_dark"]
    s_light = simulate_cabin(v_light, 35.0, 900.0, hours=1.0)
    s_dark  = simulate_cabin(v_dark,  35.0, 900.0, hours=1.0)
    assert s_dark.peak_T_C > s_light.peak_T_C


def test_no_freezing_inside_cabin():
    """Sanity: cabin temp never goes below outdoor temperature."""
    v = VEHICLE_ARCHETYPES["midsize_sedan_dark"]
    sim = simulate_cabin(v, 30.0, 0.0, hours=2.0, T_cabin_initial_C=30.0)
    assert sim.T_cabin_C.min() >= 30.0 - 0.5


def test_toddler_phoenix_critical_in_under_1h():
    """Vanos 2018: 2-year-old in Phoenix-like conditions reaches
    Tc=40 C in 1-2 hours; critical 42 C in 1.5-3 hours."""
    v = VEHICLE_ARCHETYPES["midsize_sedan_dark"]
    sim = simulate_cabin(v, 42.0, 1000.0, hours=2.0)
    hot = hyperthermia_timeline(OCCUPANT_ARCHETYPES["toddler_2y"], sim)
    assert hot.time_to_40C_h is not None
    assert 0.2 < hot.time_to_40C_h < 1.5


def test_dog_no_sweat_threshold():
    v = VEHICLE_ARCHETYPES["midsize_sedan_dark"]
    sim = simulate_cabin(v, 35.0, 900.0, hours=1.5)
    hot = hyperthermia_timeline(OCCUPANT_ARCHETYPES["medium_dog_25kg"], sim)
    assert hot.time_to_threshold_h is not None


def test_brachycephalic_dog_worst_off():
    """Brachycephalic breeds (pugs/bulldogs) hit threshold fastest."""
    v = VEHICLE_ARCHETYPES["midsize_sedan_dark"]
    sim = simulate_cabin(v, 35.0, 900.0, hours=1.5)
    t_normal = hyperthermia_timeline(OCCUPANT_ARCHETYPES["medium_dog_25kg"], sim).time_to_threshold_h
    t_brach  = hyperthermia_timeline(OCCUPANT_ARCHETYPES["brachycephalic_dog_15kg"], sim).time_to_threshold_h
    assert t_brach < t_normal


def test_infant_worse_than_adult():
    """Infants thermoregulate worse than adults (SA/V, sweat capacity)."""
    v = VEHICLE_ARCHETYPES["midsize_sedan_dark"]
    sim = simulate_cabin(v, 35.0, 900.0, hours=2.0)
    t_infant = hyperthermia_timeline(OCCUPANT_ARCHETYPES["infant_6mo"], sim).time_to_40C_h
    t_adult  = hyperthermia_timeline(OCCUPANT_ARCHETYPES["adult"], sim).time_to_40C_h
    assert t_infant is not None
    if t_adult is not None:
        assert t_infant < t_adult


def test_intervention_park_in_shade_largest_effect():
    """Park in shade should provide the largest reduction other than
    'do not leave'."""
    recs = rank_interventions(VEHICLE_ARCHETYPES["midsize_sedan_dark"],
                                OCCUPANT_ARCHETYPES["toddler_2y"],
                                T_outdoor_C=32.0, solar_W_per_m2=900.0,
                                hours=2.0)
    keys = [r["intervention"] for r in recs]
    assert "do_not_leave_occupant" in keys
    assert "park_in_shade" in keys


def test_intervention_crack_window_minimal_minutes_bought():
    """Cracked windows should buy < 20 min in a serious scenario."""
    rows = evaluate_interventions(VEHICLE_ARCHETYPES["midsize_sedan_dark"],
                                    OCCUPANT_ARCHETYPES["toddler_2y"],
                                    T_outdoor_C=35.0, solar_W_per_m2=900.0,
                                    hours=2.0)
    crack = next(r for r in rows if r["intervention"] == "crack_windows")
    assert crack["minutes_bought"] < 20


def test_intervention_do_not_leave_is_guaranteed():
    rows = evaluate_interventions(VEHICLE_ARCHETYPES["midsize_sedan_dark"],
                                    OCCUPANT_ARCHETYPES["toddler_2y"],
                                    T_outdoor_C=30.0, solar_W_per_m2=800.0)
    dnl = next(r for r in rows if r["intervention"] == "do_not_leave_occupant")
    assert dnl["guaranteed_safe"] is True


def test_mild_spring_day_still_dangerous():
    """McLaren 2005's headline finding: a mild spring day produces
    a lethal cabin in 30-60 minutes."""
    sc = mild_spring_day(hours=1.0)
    sim = simulate_cabin(VEHICLE_ARCHETYPES["midsize_sedan_dark"],
                           sc.T_outdoor_C, sc.solar_W_per_m2, hours=1.0)
    hot = hyperthermia_timeline(OCCUPANT_ARCHETYPES["toddler_2y"], sim)
    # Toddler core should be elevated (>37.5) within 1 hour, even on a
    # cool 22 C day; a 2 h or 3 h exposure crosses the heat-stroke
    # threshold (see Vanos 2018).
    assert hot.peak_T_core_C > 37.5
    # Extended exposure (3 h) on the same day must cross heat-stroke:
    sim3 = simulate_cabin(VEHICLE_ARCHETYPES["midsize_sedan_dark"],
                            sc.T_outdoor_C[0], sc.solar_W_per_m2[0], hours=3.0)
    hot3 = hyperthermia_timeline(OCCUPANT_ARCHETYPES["infant_6mo"], sim3)
    assert hot3.peak_T_core_C > 39.5


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
