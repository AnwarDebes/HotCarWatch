"""HotCarWatch: in-vehicle temperature + time-to-hyperthermia for
children and pets left in parked cars.

WARNING.  Leaving any human or animal in a parked vehicle in any
sunny conditions is dangerous.  HotCarWatch is a public-domain
decision-support model.  Do not use it to justify leaving an
occupant behind.

Quick start
-----------

    from hotcarwatch import (
        VEHICLE_ARCHETYPES, OCCUPANT_ARCHETYPES,
        simulate_cabin, hyperthermia_timeline, rank_interventions,
    )

    veh = VEHICLE_ARCHETYPES["midsize_sedan_dark"]
    occ = OCCUPANT_ARCHETYPES["toddler_2y"]
    sim = simulate_cabin(veh, T_outdoor_C=27.0, solar_W_per_m2=900.0,
                          hours=2.0)
    risk = hyperthermia_timeline(occ, sim)
    print(f"Cabin reaches {sim.T_cabin_C.max():.1f} C at {sim.t_h_at_peak:.2f} h")
    print(f"Occupant core reaches 40 C at t = {risk.time_to_40C_h:.2f} h")
"""

from .vehicle import (
    Vehicle, VEHICLE_ARCHETYPES, glass_transmissivity_from_tint,
)
from .occupant import (
    Occupant, OCCUPANT_ARCHETYPES, OccupantClass,
)
from .thermal import (
    CabinSimulation, simulate_cabin, equilibrium_cabin_C,
    cabin_time_constant_h,
)
from .hyperthermia import (
    HyperthermiaTimeline, hyperthermia_timeline,
    CORE_NEUTRAL_C, CORE_HEAT_STROKE_C, CORE_CRITICAL_C,
)
from .scenarios import (
    Scenario, mild_spring_day, summer_phoenix, southern_humid_day,
    cloudy_warm_day,
)
from .intervention import (
    Intervention, INTERVENTIONS, evaluate_interventions, rank_interventions,
)
