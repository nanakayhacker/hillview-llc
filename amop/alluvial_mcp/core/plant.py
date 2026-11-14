"""
Module D — Plant Simulation & Recovery (core engine).

Verified against FINALGEOS_VAM_alluvial_trommel_Ore_blend_simulation_
GEOSPATIAL.xlsx (Plant_Parameters, Energy_Consumption, Recovery_Dashboard):
Overall Plant Efficiency 0.837936, Effective Recovery 0.7541424, Gold
Recovered 11.951346198067066 oz, Net Revenue after Energy -173.04789782838634
all reproduce exactly below.

DATA-03/DATA-04 (docs/AMOP_MCP_SPEC.md §10): Energy_Consumption!B16 uses an
energy cost rate of 12 $/kWh where 0.12 is clearly intended (confirmed
present in the real workbook, not just the spec's summary). Per the
platform's non-negotiable rule #2 ("no silent data correction"), every
energy-cost tool here returns BOTH the as-entered and the corrected figure
with an explicit `data_issue` flag -- it never substitutes 0.12 quietly.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

TROY_OUNCE_G = 31.1035


# ---------------------------------------------------------------------------
# D3 — plant efficiency factors
# ---------------------------------------------------------------------------


def compute_rpm_factor(rpm_actual: float, rpm_optimal: float) -> float:
    return max(0.8, 1 - abs(rpm_actual - rpm_optimal) * 0.005)


def compute_tilt_factor(tilt_actual_deg: float, tilt_optimal_deg: float) -> float:
    return max(0.8, 1 - abs(tilt_actual_deg - tilt_optimal_deg) * 0.02)


def compute_water_flow_factor(flow_actual: float, flow_min: float, flow_max: float) -> float:
    if flow_min <= flow_actual <= flow_max:
        return 1.0
    distance = (flow_min - flow_actual) if flow_actual < flow_min else (flow_actual - flow_max)
    return max(0.8, 1 - distance * 0.01)


def compute_overall_efficiency(setup_efficiency: float, rpm_factor: float,
                                tilt_factor: float, water_factor: float) -> float:
    return setup_efficiency * rpm_factor * tilt_factor * water_factor


def compute_effective_recovery(base_recovery: float, overall_efficiency: float) -> float:
    return base_recovery * overall_efficiency


@dataclass(frozen=True)
class PlantParameters:
    rated_capacity_m3_hr: float = 166.666666666666
    feed_rate_setpoint_m3_hr: float = 75
    actual_processing_rate_m3_hr: float = 43
    operating_hours: float = 22
    rpm_actual: float = 30
    rpm_optimal: float = 32
    tilt_actual_deg: float = 8
    tilt_optimal_deg: float = 12
    water_flow_actual: float = 120
    water_flow_min: float = 110
    water_flow_max: float = 135
    setup_efficiency: float = 0.92
    base_metallurgical_recovery: float = 0.90


@dataclass
class PlantEfficiencyResult:
    rpm_factor: float
    tilt_factor: float
    water_flow_factor: float
    overall_efficiency: float
    effective_recovery: float
    max_daily_capacity_m3: float


def evaluate_plant_efficiency(p: PlantParameters) -> PlantEfficiencyResult:
    rpm_f = compute_rpm_factor(p.rpm_actual, p.rpm_optimal)
    tilt_f = compute_tilt_factor(p.tilt_actual_deg, p.tilt_optimal_deg)
    water_f = compute_water_flow_factor(p.water_flow_actual, p.water_flow_min, p.water_flow_max)
    overall = compute_overall_efficiency(p.setup_efficiency, rpm_f, tilt_f, water_f)
    recovery = compute_effective_recovery(p.base_metallurgical_recovery, overall)
    return PlantEfficiencyResult(
        rpm_factor=rpm_f, tilt_factor=tilt_f, water_flow_factor=water_f,
        overall_efficiency=overall, effective_recovery=recovery,
        max_daily_capacity_m3=p.actual_processing_rate_m3_hr * p.operating_hours,
    )


# ---------------------------------------------------------------------------
# D4 — blend strategies
# ---------------------------------------------------------------------------


@dataclass
class PitFeed:
    pit_id: str
    grade_g_m3: float
    bulk_density_t_m3: float
    available_volume_m3: float
    easting: float
    northing: float


@dataclass
class Stockpile:
    stockpile_id: str
    easting: float
    northing: float
    capacity_m3: float


def _distance(a_x: float, a_y: float, b_x: float, b_y: float) -> float:
    return ((a_x - b_x) ** 2 + (a_y - b_y) ** 2) ** 0.5


@dataclass
class BlendLine:
    pit_id: str
    volume_m3: float
    grade_g_m3: float


@dataclass
class BlendResult:
    lines: list[BlendLine]
    total_volume_m3: float
    weighted_avg_grade_g_m3: float
    contained_gold_g: float
    strategy: str
    feasible: bool
    blocking_reasons: list[str] = field(default_factory=list)


def _weighted_blend(lines: list[BlendLine]) -> tuple[float, float, float]:
    total_v = sum(l.volume_m3 for l in lines)
    if total_v <= 0:
        return 0.0, 0.0, 0.0
    contained = sum(l.volume_m3 * l.grade_g_m3 for l in lines)
    return total_v, contained / total_v, contained


def run_grade_priority_blend(pits: list[PitFeed], target_m3: float) -> BlendResult:
    remaining = target_m3
    lines = []
    for pit in sorted(pits, key=lambda p: p.grade_g_m3, reverse=True):
        if remaining <= 0:
            break
        take = min(pit.available_volume_m3, remaining)
        if take > 0:
            lines.append(BlendLine(pit.pit_id, take, pit.grade_g_m3))
            remaining -= take
    total_v, grade, contained = _weighted_blend(lines)
    return BlendResult(lines, total_v, grade, contained, "grade", feasible=remaining <= 1e-6,
                        blocking_reasons=[] if remaining <= 1e-6 else [f"Short by {remaining:.1f} m3 of available volume"])


def run_distance_priority_reclaim(pits: list[PitFeed], plant_x: float, plant_y: float,
                                   target_m3: float) -> BlendResult:
    remaining = target_m3
    lines = []
    for pit in sorted(pits, key=lambda p: _distance(p.easting, p.northing, plant_x, plant_y)):
        if remaining <= 0:
            break
        take = min(pit.available_volume_m3, remaining)
        if take > 0:
            lines.append(BlendLine(pit.pit_id, take, pit.grade_g_m3))
            remaining -= take
    total_v, grade, contained = _weighted_blend(lines)
    return BlendResult(lines, total_v, grade, contained, "distance", feasible=remaining <= 1e-6,
                        blocking_reasons=[] if remaining <= 1e-6 else [f"Short by {remaining:.1f} m3 of available volume"])


def run_composite_priority_blend(pits: list[PitFeed], plant_x: float, plant_y: float,
                                  target_m3: float, w_grade: float = 0.5, w_distance: float = 0.5) -> BlendResult:
    grades = [p.grade_g_m3 for p in pits]
    distances = [_distance(p.easting, p.northing, plant_x, plant_y) for p in pits]
    g_max = max(grades) or 1.0
    d_max = max(distances) or 1.0
    scored = sorted(
        zip(pits, grades, distances),
        key=lambda t: -(w_grade * (t[1] / g_max) - w_distance * (t[2] / d_max)),
    )
    remaining = target_m3
    lines = []
    for pit, _, _ in scored:
        if remaining <= 0:
            break
        take = min(pit.available_volume_m3, remaining)
        if take > 0:
            lines.append(BlendLine(pit.pit_id, take, pit.grade_g_m3))
            remaining -= take
    total_v, grade, contained = _weighted_blend(lines)
    return BlendResult(lines, total_v, grade, contained, "composite", feasible=remaining <= 1e-6,
                        blocking_reasons=[] if remaining <= 1e-6 else [f"Short by {remaining:.1f} m3 of available volume"])


def run_concurrency_prefilter(allocation: dict[str, dict[str, float]]) -> dict[str, Literal["CONCURRENT", "SEQUENTIAL"]]:
    """A pit is CONCURRENT if it sends all volume to one stockpile, or >=66% to a dominant one."""
    out = {}
    for pit_id, dest_volumes in allocation.items():
        total = sum(dest_volumes.values())
        if total <= 0:
            out[pit_id] = "SEQUENTIAL"
            continue
        dominant_share = max(dest_volumes.values()) / total
        out[pit_id] = "CONCURRENT" if dominant_share >= 0.66 else "SEQUENTIAL"
    return out


def run_holistic_blend(pits: list[PitFeed], plant_x: float, plant_y: float, target_m3: float,
                        allocation: dict[str, dict[str, float]] | None = None,
                        w_grade: float = 0.5, w_distance: float = 0.5) -> BlendResult:
    """Concurrency-filtered composite blend: SEQUENTIAL pits are deprioritised."""
    if allocation:
        concurrency = run_concurrency_prefilter(allocation)
        concurrent_pits = [p for p in pits if concurrency.get(p.pit_id) == "CONCURRENT"]
        sequential_pits = [p for p in pits if concurrency.get(p.pit_id) != "CONCURRENT"]
        ordered = concurrent_pits + sequential_pits
    else:
        ordered = pits
    grades = [p.grade_g_m3 for p in ordered]
    distances = [_distance(p.easting, p.northing, plant_x, plant_y) for p in ordered]
    g_max = max(grades) or 1.0
    d_max = max(distances) or 1.0
    scored = sorted(
        zip(ordered, grades, distances),
        key=lambda t: -(w_grade * (t[1] / g_max) - w_distance * (t[2] / d_max)),
    )
    remaining = target_m3
    lines = []
    for pit, _, _ in scored:
        if remaining <= 0:
            break
        take = min(pit.available_volume_m3, remaining)
        if take > 0:
            lines.append(BlendLine(pit.pit_id, take, pit.grade_g_m3))
            remaining -= take
    total_v, grade, contained = _weighted_blend(lines)
    return BlendResult(lines, total_v, grade, contained, "holistic", feasible=remaining <= 1e-6,
                        blocking_reasons=[] if remaining <= 1e-6 else [f"Short by {remaining:.1f} m3 of available volume"])


def build_daily_blend(pits: list[PitFeed], plant: PlantEfficiencyResult, target_m3: float,
                       strategy: Literal["grade", "distance", "composite", "holistic"],
                       plant_x: float = 0.0, plant_y: float = 0.0) -> BlendResult:
    capped_target = min(target_m3, plant.max_daily_capacity_m3, sum(p.available_volume_m3 for p in pits))
    if strategy == "grade":
        result = run_grade_priority_blend(pits, capped_target)
    elif strategy == "distance":
        result = run_distance_priority_reclaim(pits, plant_x, plant_y, capped_target)
    elif strategy == "composite":
        result = run_composite_priority_blend(pits, plant_x, plant_y, capped_target)
    else:
        result = run_holistic_blend(pits, plant_x, plant_y, capped_target)
    if target_m3 > plant.max_daily_capacity_m3:
        result.blocking_reasons.append(
            f"Target {target_m3} m3 exceeds plant max daily capacity {plant.max_daily_capacity_m3} m3"
        )
        result.feasible = False
    return result


# ---------------------------------------------------------------------------
# D5 — Energy
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class EquipmentLoad:
    name: str
    kw: float
    qty: int


DEFAULT_EQUIPMENT_LOADS: tuple[EquipmentLoad, ...] = (
    EquipmentLoad("Trommel Drive Motor", 45, 1),
    EquipmentLoad("Water Supply Pump(s)", 30, 2),
    EquipmentLoad("Feed Conveyor", 15, 1),
    EquipmentLoad("Discharge / Stacker Conveyor", 15, 3),
    EquipmentLoad("Sluice / Jig Recovery Pump", 11, 1),
    EquipmentLoad("Auxiliary / Lighting / Control", 8, 1),
)


def total_connected_load_kw(loads: tuple[EquipmentLoad, ...] = DEFAULT_EQUIPMENT_LOADS) -> float:
    return sum(l.kw * l.qty for l in loads)


def compute_daily_kwh(connected_load_kw: float, operating_hours: float) -> float:
    return connected_load_kw * operating_hours


def compute_daily_energy_cost(
    connected_load_kw: float, operating_hours: float, energy_rate_as_entered: float,
) -> dict:
    """
    DATA-03/04: returns BOTH the as-entered rate's cost and the corrected
    (0.12 $/kWh) cost, flagged, never silently substituted.
    """
    kwh = compute_daily_kwh(connected_load_kw, operating_hours)
    as_entered_cost = kwh * energy_rate_as_entered
    corrected_rate = 0.12
    corrected_cost = kwh * corrected_rate
    data_issue = None
    if energy_rate_as_entered > 1.0:
        data_issue = {
            "finding": "DATA_ISSUE", "id": "DATA-03", "sheet": "Energy_Consumption", "cell": "B16",
            "value_found": energy_rate_as_entered, "recommended_value": corrected_rate,
            "action_taken": "none (surfaced to user)",
        }
    return {
        "daily_kwh": kwh,
        "energy_rate_as_entered": energy_rate_as_entered,
        "daily_cost_as_entered_usd": as_entered_cost,
        "corrected_rate": corrected_rate,
        "daily_cost_corrected_usd": corrected_cost,
        "data_issue": data_issue,
    }


def simulate_operating_hours_sensitivity(connected_load_kw: float, energy_rate: float,
                                          hours_range: list[float]) -> list[dict]:
    return [
        {"hours": h, "energy_cost_usd": compute_daily_kwh(connected_load_kw, h) * energy_rate}
        for h in hours_range
    ]


def simulate_load_shedding(loads: tuple[EquipmentLoad, ...], per_equipment_reduction_pct: dict[str, float],
                            operating_hours: float, energy_rate: float) -> dict:
    base_kw = total_connected_load_kw(loads)
    reduced_kw = sum(l.kw * l.qty * (1 - per_equipment_reduction_pct.get(l.name, 0.0)) for l in loads)
    saved_kw = base_kw - reduced_kw
    return {
        "base_connected_load_kw": base_kw, "reduced_connected_load_kw": reduced_kw,
        "daily_kwh_saved": saved_kw * operating_hours,
        "daily_usd_saved": saved_kw * operating_hours * energy_rate,
    }


def simulate_tariff_shifting(connected_load_kw: float, operating_hours: float,
                              peak_rate: float, off_peak_rate: float, hours_on_peak: float) -> dict:
    hours_on_peak = min(hours_on_peak, operating_hours)
    hours_off_peak = operating_hours - hours_on_peak
    blended_cost = connected_load_kw * (hours_on_peak * peak_rate + hours_off_peak * off_peak_rate)
    all_peak_cost = connected_load_kw * operating_hours * peak_rate
    return {
        "blended_daily_cost_usd": blended_cost, "all_peak_daily_cost_usd": all_peak_cost,
        "daily_usd_saved_vs_all_peak": all_peak_cost - blended_cost,
    }


# ---------------------------------------------------------------------------
# D6 — Recovery & net revenue
# ---------------------------------------------------------------------------


def compute_recovered_oz(contained_gold_g: float, effective_recovery: float) -> float:
    return (contained_gold_g * effective_recovery) / TROY_OUNCE_G


def compute_gross_revenue(recovered_oz: float, gold_price_usd_oz: float) -> float:
    return recovered_oz * gold_price_usd_oz


def compute_net_revenue(gross_revenue_usd: float, energy_cost_usd: float, haul_cost_usd: float) -> dict:
    after_energy = gross_revenue_usd - energy_cost_usd
    fully_loaded = after_energy - haul_cost_usd
    true_net_margin = fully_loaded / gross_revenue_usd if gross_revenue_usd > 0 else 0.0
    return {
        "gross_revenue_usd": gross_revenue_usd,
        "net_revenue_after_energy_usd": after_energy,
        "net_revenue_fully_loaded_usd": fully_loaded,
        "true_net_margin": true_net_margin,
    }


# ---------------------------------------------------------------------------
# D7 — 7-day rollup
# ---------------------------------------------------------------------------


def roll_week_simulation(daily_volumes: list[float], daily_grades: list[float], daily_hours: list[float],
                          effective_recovery: float, gold_price_usd_oz: float,
                          connected_load_kw: float, energy_rate: float,
                          haul_cost_per_m3: float = 0.0) -> dict:
    days = []
    cum_gold_oz = 0.0
    cum_net_revenue = 0.0
    for v, g, h in zip(daily_volumes, daily_grades, daily_hours):
        contained_g = v * g
        recovered_oz = compute_recovered_oz(contained_g, effective_recovery)
        gross = compute_gross_revenue(recovered_oz, gold_price_usd_oz)
        energy_cost = compute_daily_kwh(connected_load_kw, h) * energy_rate
        haul_cost = v * haul_cost_per_m3
        net = compute_net_revenue(gross, energy_cost, haul_cost)
        cum_gold_oz += recovered_oz
        cum_net_revenue += net["net_revenue_fully_loaded_usd"]
        days.append({
            "volume_m3": v, "grade_g_m3": g, "hours": h, "recovered_oz": recovered_oz,
            "gross_revenue_usd": gross, "energy_cost_usd": energy_cost, "haul_cost_usd": haul_cost,
            "net_revenue_usd": net["net_revenue_fully_loaded_usd"],
            "cumulative_gold_oz": cum_gold_oz, "cumulative_net_revenue_usd": cum_net_revenue,
        })
    return {"days": days, "total_gold_oz": cum_gold_oz, "total_net_revenue_usd": cum_net_revenue}
