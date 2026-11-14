"""Cross-module adjudication layer MCP server (docs/AMOP_MCP_SPEC.md §5)."""
from __future__ import annotations

from fastmcp import FastMCP

from alluvial_mcp.core import adjudication as core
from alluvial_mcp.mcp_utils import READ_ONLY, to_jsonable

mcp = FastMCP("alluvial-adjudication")


@mcp.tool(annotations=READ_ONLY)
def adjudicate_blend_against_grade_credibility(pit_shares_and_z: dict[str, list[float]]) -> dict:
    """A pit may contribute >30% of blend volume only if Z>=0.6; else capped at 20%.
    pit_shares_and_z: {pit_id: [share, z]}."""
    parsed = {k: (v[0], v[1]) for k, v in pit_shares_and_z.items()}
    return to_jsonable(core.adjudicate_blend_against_grade_credibility(parsed))


@mcp.tool(annotations=READ_ONLY)
def adjudicate_haul_against_stockpile_compatibility(stockpile_deficits: dict[str, float],
                                                     compatibility: dict[str, float]) -> dict:
    return to_jsonable(core.adjudicate_haul_against_stockpile_compatibility(stockpile_deficits, compatibility))


@mcp.tool(annotations=READ_ONLY)
def adjudicate_plant_feed_against_energy_budget(daily_energy_cost_usd: float, gross_revenue_usd: float) -> dict:
    """Daily energy cost must be <=15% of gross gold revenue."""
    return to_jsonable(core.adjudicate_plant_feed_against_energy_budget(daily_energy_cost_usd, gross_revenue_usd))


@mcp.tool(annotations=READ_ONLY)
def adjudicate_prospect_against_cash_runway(runway_weeks: float, min_weeks: float = 2.0) -> dict:
    return to_jsonable(core.adjudicate_prospect_against_cash_runway(runway_weeks, min_weeks))


@mcp.tool(annotations=READ_ONLY)
def adjudicate_prospect_clearance(risk_class: str, verification_completion: float, fail_count: int) -> dict:
    return to_jsonable(core.adjudicate_prospect_clearance(risk_class, verification_completion, fail_count))


@mcp.tool(annotations=READ_ONLY)
def adjudicate_vam_feasibility(vam_verdict: dict) -> dict:
    return to_jsonable(core.adjudicate_vam_feasibility(vam_verdict))


@mcp.tool(annotations=READ_ONLY)
def adjudicate_plant_efficiency_floor(overall_efficiency: float, base_efficiency: float = 1.0) -> dict:
    return to_jsonable(core.adjudicate_plant_efficiency_floor(overall_efficiency, base_efficiency))


@mcp.tool(annotations=READ_ONLY)
def adjudicate_recovery_bounds(effective_recovery: float, base_recovery: float) -> dict:
    return to_jsonable(core.adjudicate_recovery_bounds(effective_recovery, base_recovery))


@mcp.tool(annotations=READ_ONLY)
def adjudicate_blend_volume_feasibility(blend_volume_m3: float, plant_daily_capacity_m3: float,
                                         available_volume_m3: float) -> dict:
    return to_jsonable(core.adjudicate_blend_volume_feasibility(blend_volume_m3, plant_daily_capacity_m3,
                                                                 available_volume_m3))


@mcp.tool(annotations=READ_ONLY)
def adjudicate_feeding_reconciliation(deviation_pct: float) -> dict:
    return to_jsonable(core.adjudicate_feeding_reconciliation(deviation_pct))


@mcp.tool(annotations=READ_ONLY)
def adjudicate_data_integrity(issues: list[dict]) -> dict:
    return to_jsonable(core.adjudicate_data_integrity(issues))


@mcp.tool(annotations=READ_ONLY)
def adjudicate_full_chain(pit_shares_and_z: dict[str, list[float]], stockpile_deficits: dict[str, float],
                           compatibility: dict[str, float], daily_energy_cost_usd: float,
                           gross_revenue_usd: float, runway_weeks: float, blend_target_m3: float,
                           include_pipeline: bool = True) -> dict:
    """Runs R-1.1..R-1.4 in order and returns a single PASS/FAIL/CONDITIONAL verdict tree.
    The LLM must explain this JSON verbatim -- never re-derive or paraphrase the thresholds."""
    parsed = {k: (v[0], v[1]) for k, v in pit_shares_and_z.items()}
    return to_jsonable(core.adjudicate_full_chain(parsed, stockpile_deficits, compatibility,
                                                   daily_energy_cost_usd, gross_revenue_usd, runway_weeks,
                                                   blend_target_m3, include_pipeline))


if __name__ == "__main__":
    mcp.run()
