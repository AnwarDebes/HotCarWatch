"""Figures for the HotCarWatch paper.

    fig_mclaren_replication.pdf  - cabin rise vs time, ours vs McLaren 2005
    fig_validation.pdf           - tau by vehicle vs published bands
    fig_scenarios.pdf            - cabin + core for 4 scenarios x toddler
    fig_interventions.pdf        - minutes bought + still-dangerous %
    fig_frontend_mock.pdf        - mock of the web frontend
"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from hotcarwatch import (
    VEHICLE_ARCHETYPES, OCCUPANT_ARCHETYPES,
    simulate_cabin, hyperthermia_timeline, cabin_time_constant_h,
    mild_spring_day, summer_phoenix, southern_humid_day, cloudy_warm_day,
)


HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
RESULTS = ROOT / "results"
FIG_DIR = ROOT / "paper" / "figures"
FIG_DIR.mkdir(parents=True, exist_ok=True)

plt.rcParams.update({
    "figure.dpi": 110, "savefig.dpi": 200, "font.size": 10,
    "axes.titlesize": 11, "axes.labelsize": 10, "legend.fontsize": 8,
    "figure.constrained_layout.use": True,
    "axes.spines.top": False, "axes.spines.right": False,
})

CABIN = "#d24a14"; OUTDOOR = "#d9b300"; CORE = "#6d4ec5"; RED = "#cc2222"
GOOD = "#1f8a3f"; GREY = "#5b6566"


def fig_mclaren():
    veh = VEHICLE_ARCHETYPES["midsize_sedan_light"]
    times_min = np.array([0, 10, 20, 30, 60])
    # McLaren 2005 measured rise above ambient, in deg C (approx from Fig 2)
    mclaren_22  = np.array([0,  6.0, 13.5, 16.5, 22.0])
    mclaren_32  = np.array([0,  7.5, 14.0, 17.5, 22.0])

    fig, ax = plt.subplots(figsize=(7, 3.4))
    for T_amb, color, mc, label in [(22, "#1e6fb8", mclaren_22, "22 °C ambient"),
                                       (32, "#cc2222", mclaren_32, "32 °C ambient")]:
        sim = simulate_cabin(veh, T_amb, 900.0, hours=1.1, dt_h=0.0167)
        rise = sim.T_cabin_C - T_amb
        ax.plot(sim.times_h * 60, rise, color=color, lw=2, label=f"PipeGuard ({label})".replace("PipeGuard","HotCarWatch"))
        ax.plot(times_min, mc, "o", color=color, markersize=8,
                  markerfacecolor="none", markeredgewidth=2,
                  label=f"McLaren 2005 ({label})")
    ax.set_xlabel("Minutes since parking")
    ax.set_ylabel("Cabin rise above ambient (°C)")
    ax.set_xlim(0, 65); ax.set_ylim(0, 28)
    ax.legend(loc="lower right", fontsize=8)
    ax.set_title("McLaren et al. 2005 cabin-heating replication\n(midsize sedan, 900 W/m² solar)")
    fig.savefig(FIG_DIR / "fig_mclaren_replication.pdf")
    plt.close(fig)


def fig_validation():
    data = json.loads((RESULTS / "validation.json").read_text())
    # plot tau vs archetype
    rows = [r for r in data["per_case"] if r.get("check") == "tau_min"]
    fig, ax = plt.subplots(figsize=(7, 3.6))
    y = np.arange(len(rows))
    for i, r in enumerate(rows):
        lo, hi = r["tau_min_published_range"]
        ax.barh(i, hi - lo, left=lo, color="lightgrey", edgecolor="grey",
                label="Published range" if i == 0 else None)
        ax.plot([r["tau_min_predicted"]], [i], "o", color=CABIN, markersize=10,
                label="HotCarWatch tau" if i == 0 else None)
    ax.set_yticks(y); ax.set_yticklabels([r["archetype"].replace("_", " ") for r in rows])
    ax.invert_yaxis()
    ax.set_xlabel("Time constant tau (minutes)")
    ax.set_xlim(0, 40)
    ax.legend(loc="lower right")
    ax.set_title("Validation: thermal time constant vs published range (NIA / ASHRAE)")
    fig.savefig(FIG_DIR / "fig_validation.pdf")
    plt.close(fig)


def fig_scenarios():
    scenarios = [mild_spring_day(hours=2.0),
                 summer_phoenix(hours=2.0),
                 southern_humid_day(hours=2.0),
                 cloudy_warm_day(hours=2.0)]
    fig, axes = plt.subplots(2, 2, figsize=(10, 5.6))
    for ax, sc in zip(axes.flat, scenarios):
        veh = VEHICLE_ARCHETYPES["midsize_sedan_dark"]
        sim = simulate_cabin(veh, sc.T_outdoor_C, sc.solar_W_per_m2,
                                hours=float(sc.times_h[-1]) + 0.025)
        occ = OCCUPANT_ARCHETYPES["toddler_2y"]
        hot = hyperthermia_timeline(occ, sim)
        ax.plot(sim.times_h * 60, sim.T_outdoor_C, color=OUTDOOR, lw=2, label="outdoor")
        ax.plot(sim.times_h * 60, sim.T_cabin_C, color=CABIN, lw=2.4, label="cabin")
        ax.plot(sim.times_h * 60, hot.T_core_C, color=CORE, lw=2.0, label="toddler core")
        ax.axhline(40, color=RED, lw=0.8, ls="--", label="40 °C")
        ax.set_xlabel("minutes")
        ax.set_ylabel("T (°C)")
        ax.set_title(sc.name, fontsize=9)
        if hot.time_to_40C_h is not None:
            ax.axvline(hot.time_to_40C_h * 60, color=RED, lw=0.8, ls=":")
            ax.text(hot.time_to_40C_h * 60 + 2, 27, f"40°C @\n{hot.time_to_40C_h*60:.0f}min",
                      color=RED, fontsize=7)
        ax.legend(fontsize=7, loc="lower right", framealpha=0.85)
    fig.savefig(FIG_DIR / "fig_scenarios.pdf")
    plt.close(fig)


def fig_interventions():
    data = json.loads((RESULTS / "interventions.json").read_text())
    summary = data["summary"]
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(9, 3.6))
    names = [s["intervention"].replace("_", " ") for s in summary]
    mins = [s["median_minutes_bought"] if s["median_minutes_bought"] < 5000 else 120
             for s in summary]
    danger_pct = [100.0 * s["n_cases_still_dangerous"] / s["n_cases_total"]
                    for s in summary]
    y = np.arange(len(names))
    colors = [GOOD if n == "do not leave occupant" else CABIN for n in names]
    ax1.barh(y, mins, color=colors, alpha=0.85)
    ax1.set_yticks(y); ax1.set_yticklabels(names)
    ax1.invert_yaxis()
    ax1.set_xlabel("Median minutes bought (vs baseline)")
    ax1.set_title("Minutes the intervention delays\n40 °C core (occupant)")
    for i, m in enumerate(mins):
        lbl = "always" if m >= 120 else f"+{m:.0f} min"
        ax1.text(m + 2, i, lbl, va="center", fontsize=9)
    ax2.barh(y, danger_pct, color=[GOOD if d == 0 else RED for d in danger_pct], alpha=0.85)
    ax2.set_yticks(y); ax2.set_yticklabels(["" for _ in names])
    ax2.invert_yaxis()
    ax2.set_xlabel("% of scenarios still dangerous")
    ax2.set_xlim(0, 110)
    ax2.set_title("Coverage of intervention\n(% of scenarios where occupant still hits 40 °C)")
    for i, d in enumerate(danger_pct):
        ax2.text(d + 1.5, i, f"{d:.0f}%", va="center", fontsize=9)
    fig.savefig(FIG_DIR / "fig_interventions.pdf")
    plt.close(fig)


def fig_frontend_mock():
    fig, ax = plt.subplots(figsize=(8.3, 5.5))
    ax.set_xlim(0, 10); ax.set_ylim(0, 6); ax.axis("off")
    ax.add_patch(plt.Rectangle((0.0, 5.4), 10.0, 0.6, color="white",
                                 ec="#bcbcbc", lw=0.6))
    ax.text(0.25, 5.7, "HotCarWatch", color=RED, weight="bold", fontsize=14)
    ax.text(2.2, 5.7, "never leave them in the car", color=GREY, fontsize=8)
    ax.text(9.7, 5.7, "no login, no tracking", color=GREY, fontsize=7, ha="right")
    # Input card
    ax.add_patch(plt.Rectangle((0.2, 0.3), 3.8, 5.0, color="white",
                                 ec="#bcbcbc", lw=0.6))
    ax.text(0.4, 5.05, "1. Conditions", weight="bold")
    ax.text(0.4, 4.75, "Outdoor: 27 °C  Sun: bright (900 W/m²)", fontsize=8,
              bbox=dict(boxstyle="round", facecolor="#fbfaf6"))
    ax.text(0.4, 4.20, "2. The vehicle", weight="bold")
    ax.text(0.4, 3.90, "Midsize sedan, light color ▾", fontsize=8,
              bbox=dict(boxstyle="round", facecolor="#fbfaf6"))
    ax.text(0.4, 3.55, "Windows closed / no sunshade", fontsize=8, color=GREY)
    ax.text(0.4, 3.10, "3. Who's in the car?", weight="bold")
    ax.text(0.4, 2.80, "Toddler ~2 y (12 kg) ▾", fontsize=8,
              bbox=dict(boxstyle="round", facecolor="#fbfaf6"))
    ax.text(0.4, 2.45, "Away for: 15 min", fontsize=8, color=GREY)
    ax.text(0.4, 1.6, "[ Forecast cabin + occupant ]", fontsize=8,
              color="white", bbox=dict(boxstyle="round", facecolor=RED))

    # Output card
    ax.add_patch(plt.Rectangle((4.2, 0.3), 5.6, 5.0, color="white",
                                 ec="#bcbcbc", lw=0.6))
    ax.text(4.4, 5.05, "What happens in the cabin", weight="bold")
    ax.text(9.55, 5.05, "38.3 °C", weight="bold", fontsize=16, color="#d97600", ha="right")
    ax.text(9.55, 4.72, "cabin at planned return", color=GREY, fontsize=7, ha="right")
    ax.text(9.55, 4.55, "core 37.6 °C (fever incipient)", color=GREY, fontsize=7, ha="right")

    # Mini chart
    veh = VEHICLE_ARCHETYPES["midsize_sedan_light"]
    sim = simulate_cabin(veh, 27.0, 900, hours=2.0)
    occ = OCCUPANT_ARCHETYPES["toddler_2y"]
    hot = hyperthermia_timeline(occ, sim)
    ax2 = fig.add_axes([0.46, 0.45, 0.45, 0.32])
    ax2.plot(sim.times_h * 60, sim.T_outdoor_C, color=OUTDOOR, lw=2)
    ax2.plot(sim.times_h * 60, sim.T_cabin_C, color=CABIN, lw=2.4)
    ax2.plot(sim.times_h * 60, hot.T_core_C, color=CORE, lw=2)
    ax2.axhline(40, color=RED, lw=0.7, ls="--")
    ax2.set_xlabel("min", fontsize=7); ax2.set_ylabel("°C", fontsize=7)
    ax2.tick_params(labelsize=6)
    ax2.spines["top"].set_visible(False); ax2.spines["right"].set_visible(False)

    ax.text(4.4, 2.1, "Time to critical milestones", weight="bold")
    ax.text(4.4, 1.85, "Heat stroke (40 °C core):", fontsize=8)
    ax.text(9.7, 1.85, "56 min", ha="right", fontsize=9, color=RED, weight="bold")
    ax.text(4.4, 1.55, "Critical (42 °C core):", fontsize=8)
    ax.text(9.7, 1.55, "1.4 h", ha="right", fontsize=9, color=RED, weight="bold")
    ax.text(4.4, 1.25, "If you parked in deep shade:", fontsize=8)
    ax.text(9.7, 1.25, "+45 min bought", ha="right", fontsize=8, color=GOOD)
    ax.text(4.4, 0.95, "DO NOT leave the toddler in the car. Take them with you.",
              fontsize=8, color=RED)

    fig.savefig(FIG_DIR / "fig_frontend_mock.pdf")
    plt.close(fig)


def main():
    fig_mclaren()
    fig_validation()
    fig_scenarios()
    fig_interventions()
    fig_frontend_mock()
    print(f"Wrote figures to {FIG_DIR}")
    for f in sorted(FIG_DIR.glob("*.pdf")):
        print(f"  {f.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
