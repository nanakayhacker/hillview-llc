"""
Module B (shared grade core) + Module D — Plant Simulation & Recovery MCP
server (docs/AMOP_MCP_SPEC.md §4.2, §4.4). The grade engine lives here
because plant and geology must share one grade core, per the spec.
"""
from __future__ import annotations

from fastmcp import FastMCP

from alluvial_mcp.core import grade as grade_core
from alluvial_mcp.core import plant as plant_core
from alluvial_mcp.mcp_utils import MUTATING, READ_ONLY, to_jsonable

mcp = FastMCP("alluvial-plant")


# --- Module B: grade engine --------------------------------------------------


@mcp.tool(annotations=READ_ONLY)
def parse_pan_entry(raw: str | int | float | None) -> dict:
    """E -> exact | Q -> raw/f | S -> S-scale | A -> 0 (NIL) | L -> limit x empirical factor | X -> excluded."""
    r = grade_core.parse_pan_entry(raw)
    return {"code": r.code, "count": r.count, "limit_capped": r.limit_capped}


@mcp.tool(annotations=READ_ONLY)
def compute_horizon_grade(horizon_id: str, pit_id: str, from_m: float, to_m: float, material: str,
                           min_zone: str, description: str | None, pans: list[dict],
                           bulk_density_t_m3: float = 1.35) -> dict:
    """Full horizon grade formula (pooled pan counts -> decay-weighted class shares ->
    natural-log modifiers -> grade/CI/Z). Verified bit-for-bit against Refined_Au_Grade_
    Model.xlsx!HorizonGrade (PRN093/PRN094)."""
    h = grade_core.HorizonInput(
        horizon_id=horizon_id, pit_id=pit_id, from_m=from_m, to_m=to_m, material=material,
        min_zone=min_zone, description=description,
        pans=[grade_core.PanEntryInput(**p) for p in pans], bulk_density_t_m3=bulk_density_t_m3,
    )
    return to_jsonable(grade_core.compute_horizon_grade(h))


@mcp.tool(annotations=READ_ONLY)
def build_pit_composite(pit_id: str, horizons: list[dict], bulk_density_t_m3: float = 1.35) -> dict:
    """Thickness-weighted pit composite grade over panned ore horizons. Verified bit-for-bit
    against Refined_Au_Grade_Model.xlsx!PitComposite for PRN093 and PRN094."""
    parsed = [
        grade_core.HorizonInput(
            horizon_id=h["horizon_id"], pit_id=h["pit_id"], from_m=h["from_m"], to_m=h["to_m"],
            material=h["material"], min_zone=h["min_zone"], description=h.get("description"),
            pans=[grade_core.PanEntryInput(**p) for p in h["pans"]],
            bulk_density_t_m3=h.get("bulk_density_t_m3", bulk_density_t_m3),
        )
        for h in horizons
    ]
    return to_jsonable(grade_core.build_pit_composite(pit_id, parsed, bulk_density_t_m3=bulk_density_t_m3))


@mcp.tool(annotations=READ_ONLY)
def get_adjudicated_pit_grade(pit_id: str, horizons: list[dict]) -> dict:
    """Point grade estimate + credibility class (LOW/MEDIUM/HIGH) + blocking flag."""
    parsed = [
        grade_core.HorizonInput(
            horizon_id=h["horizon_id"], pit_id=h["pit_id"], from_m=h["from_m"], to_m=h["to_m"],
            material=h["material"], min_zone=h["min_zone"], description=h.get("description"),
            pans=[grade_core.PanEntryInput(**p) for p in h["pans"]],
        )
        for h in horizons
    ]
    composite = grade_core.build_pit_composite(pit_id, parsed)
    return to_jsonable(grade_core.get_adjudicated_pit_grade(composite))


@mcp.tool(annotations=READ_ONLY)
def validate_against_feed_grades(model_grades: list[float], feed_grades: list[float]) -> dict:
    return to_jsonable(grade_core.validate_against_feed_grades(model_grades, feed_grades))


# --- Module D: plant simulation & recovery -----------------------------------


@mcp.tool(annotations=READ_ONLY)
def evaluate_plant_efficiency(rpm_actual: float = 30, rpm_optimal: float = 32, tilt_actual_deg: float = 8,
                               tilt_optimal_deg: float = 12, water_flow_actual: float = 120,
                               water_flow_min: float = 110, water_flow_max: float = 135,
                               setup_efficiency: float = 0.92, base_metallurgical_recovery: float = 0.90,
                               actual_processing_rate_m3_hr: float = 43, operating_hours: float = 22) -> dict:
    """RPM/tilt/water penalty factors -> overall efficiency -> effective recovery. Verified
    bit-for-bit against FINALGEOS!Plant_Parameters (overall 0.837936, recovery 0.7541424)."""
    p = plant_core.PlantParameters(
        rpm_actual=rpm_actual, rpm_optimal=rpm_optimal, tilt_actual_deg=tilt_actual_deg,
        tilt_optimal_deg=tilt_optimal_deg, water_flow_actual=water_flow_actual,
        water_flow_min=water_flow_min, water_flow_max=water_flow_max, setup_efficiency=setup_efficiency,
        base_metallurgical_recovery=base_metallurgical_recovery,
        actual_processing_rate_m3_hr=actual_processing_rate_m3_hr, operating_hours=operating_hours,
    )
    return to_jsonable(plant_core.evaluate_plant_efficiency(p))


@mcp.tool(annotations=READ_ONLY)
def build_daily_blend(pits: list[dict], target_m3: float, strategy: str = "holistic",
                       plant_x: float = 0.0, plant_y: float = 0.0,
                       plant_efficiency: dict | None = None) -> dict:
    """strategy in {grade, distance, composite, holistic}. Caps target at plant daily
    capacity and total available pit volume."""
    pit_objs = [plant_core.PitFeed(**p) for p in pits]
    eff = plant_core.evaluate_plant_efficiency(plant_core.PlantParameters(**(plant_efficiency or {})))
    return to_jsonable(plant_core.build_daily_blend(pit_objs, eff, target_m3, strategy, plant_x, plant_y))


@mcp.tool(annotations=READ_ONLY)
def run_concurrency_prefilter(allocation: dict[str, dict[str, float]]) -> dict:
    """CONCURRENT if a pit sends all volume to one stockpile or >=66% to a dominant one."""
    return {"concurrency": plant_core.run_concurrency_prefilter(allocation)}


@mcp.tool(annotations=READ_ONLY)
def compute_daily_energy_cost(connected_load_kw: float = 184, operating_hours: float = 22,
                               energy_rate_as_entered: float = 12.0) -> dict:
    """DATA-03/04: returns both the as-entered rate's cost and the 0.12 $/kWh corrected
    figure, flagged as a DATA_ISSUE -- never silently substituted."""
    return to_jsonable(plant_core.compute_daily_energy_cost(connected_load_kw, operating_hours, energy_rate_as_entered))


@mcp.tool(annotations=READ_ONLY)
def simulate_tariff_shifting(connected_load_kw: float, operating_hours: float, peak_rate: float,
                              off_peak_rate: float, hours_on_peak: float) -> dict:
    return to_jsonable(plant_core.simulate_tariff_shifting(connected_load_kw, operating_hours, peak_rate,
                                                            off_peak_rate, hours_on_peak))


@mcp.tool(annotations=READ_ONLY)
def compute_recovered_oz(contained_gold_g: float, effective_recovery: float) -> dict:
    return {"recovered_oz": plant_core.compute_recovered_oz(contained_gold_g, effective_recovery)}


@mcp.tool(annotations=READ_ONLY)
def compute_net_revenue(gross_revenue_usd: float, energy_cost_usd: float, haul_cost_usd: float) -> dict:
    return to_jsonable(plant_core.compute_net_revenue(gross_revenue_usd, energy_cost_usd, haul_cost_usd))


@mcp.tool(annotations=READ_ONLY)
def roll_week_simulation(daily_volumes: list[float], daily_grades: list[float], daily_hours: list[float],
                          effective_recovery: float, gold_price_usd_oz: float, connected_load_kw: float,
                          energy_rate: float, haul_cost_per_m3: float = 0.0) -> dict:
    return to_jsonable(plant_core.roll_week_simulation(daily_volumes, daily_grades, daily_hours,
                                                        effective_recovery, gold_price_usd_oz,
                                                        connected_load_kw, energy_rate, haul_cost_per_m3))


if __name__ == "__main__":
    mcp.run()
