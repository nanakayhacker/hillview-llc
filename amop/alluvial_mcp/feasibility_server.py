"""
Alluvial Project Feasibility Reporting & Cost-Tracking MCP server (NEW --
not in the original 4-server topology, added for the feasibility/JORC-style
reporting module and the exploration-through-HSE expenditure tracker).
"""
from __future__ import annotations

from fastmcp import FastMCP

from alluvial_mcp.core import cost_tracking as cost_core
from alluvial_mcp.core import feasibility as feas_core
from alluvial_mcp.mcp_utils import DESTRUCTIVE, MUTATING, READ_ONLY, to_jsonable

mcp = FastMCP("alluvial-feasibility")


# --- Cost tracking ------------------------------------------------------------


@mcp.tool(annotations=READ_ONLY)
def list_cost_code_taxonomy() -> dict:
    """The full EXPLORATION/MINING_OPERATIONS/PLANT_PROCESSING/CAMP_DEVELOPMENT/
    HSE_ADMIN/CONTINGENCY cost-code taxonomy."""
    return {"categories": [to_jsonable(c) for c in cost_core.COST_CODE_TAXONOMY]}


@mcp.tool(annotations=READ_ONLY)
def rollup_budget_by_phase(lines: list[dict]) -> dict:
    """Budget BAC/EV/AC/variance/%consumed rollup by phase. lines: [{cost_code, planned_bac_usd,
    earned_value_usd, actual_validated_usd, vouchers_on_hold_usd}]."""
    parsed = [cost_core.BudgetLine(**l) for l in lines]
    return to_jsonable(cost_core.rollup_budget_by_phase(parsed))


@mcp.tool(annotations=READ_ONLY)
def validate_voucher(voucher_id: str, cost_code: str, payee: str, description: str, amount_usd: float,
                      has_invoice: bool, has_contract_or_po: bool, has_receipt_or_acceptance: bool,
                      has_tax_ref: bool, approval_level_given: int, voucher_date: str | None = None) -> dict:
    """A voucher counts as actual spend only when VALID: invoice, contract/PO, receipt/
    acceptance, tax ref, a known cost code, and sufficient approval level for its amount."""
    v = cost_core.Voucher(voucher_id, None, cost_code, payee, description, amount_usd, has_invoice,
                           has_contract_or_po, has_receipt_or_acceptance, has_tax_ref, approval_level_given)
    return to_jsonable(cost_core.validate_voucher(v))


@mcp.tool(annotations=READ_ONLY)
def summarize_vouchers(vouchers: list[dict]) -> dict:
    parsed = [cost_core.Voucher(
        v["voucher_id"], None, v["cost_code"], v["payee"], v["description"], v["amount_usd"],
        v["has_invoice"], v["has_contract_or_po"], v["has_receipt_or_acceptance"], v["has_tax_ref"],
        v["approval_level_given"],
    ) for v in vouchers]
    return to_jsonable(cost_core.summarize_vouchers(parsed))


@mcp.tool(annotations=READ_ONLY)
def rollup_bom_total(lines: list[dict]) -> dict:
    """Trommel/plant bill-of-materials costing. lines: [{component_id, assembly, component,
    cost_code, qty, unit, unit_cost_usd, criticality, lead_time_wk, status}]."""
    parsed = [cost_core.BOMLine(**l) for l in lines]
    return to_jsonable(cost_core.rollup_bom_total(parsed))


@mcp.tool(annotations=READ_ONLY)
def estimate_camp_requirements(headcount: int = 140, m2_per_bed_prefab: float = 6.0,
                                beds_per_room: float = 4.0, office_m2_per_admin_staff: float = 8.0,
                                admin_staff_fraction: float = 0.15, power_kw_per_person: float = 0.6,
                                generator_oversize_factor: float = 1.3) -> dict:
    """Structured placeholder sizing for camp development (prefab housing, offices, power
    plant) -- NOT an engineering design; every figure must be replaced with a quoted BOQ."""
    a = cost_core.CampSizingAssumptions(headcount, m2_per_bed_prefab, beds_per_room,
                                         office_m2_per_admin_staff, admin_staff_fraction,
                                         power_kw_per_person, generator_oversize_factor)
    return to_jsonable(cost_core.estimate_camp_requirements(a))


@mcp.tool(annotations=READ_ONLY)
def evaluate_tranche_release(gates_passed: dict[str, bool]) -> dict:
    """T0 (baseline approved) / T1 (Gate A) / T2 (Gate B) / T3 (Gate C) release conditions."""
    return {"tranches": cost_core.evaluate_tranche_release(gates_passed)}


# --- Feasibility ---------------------------------------------------------------


@mcp.tool(annotations=READ_ONLY)
def classify_resource_prototype(pit_id: str, z_credibility: float, qaqc_pass: bool,
                                 class_vs_cutoff: str) -> dict:
    """PROTOTYPE confidence classification (Measured/Indicated/Inferred; Proved/Probable).
    NOT a JORC Code or NI 43-101 compliant statement -- see feasibility.SCOPE_DISCLAIMER."""
    return to_jsonable(feas_core.classify_resource_prototype(pit_id, z_credibility, qaqc_pass, class_vs_cutoff))


@mcp.tool(annotations=READ_ONLY)
def run_feasibility_model(
    gold_price_usd_oz: float = 4500.0, royalty_rate: float = 0.05, head_grade_g_m3: float = 0.2,
    metallurgical_recovery: float = 0.75, feed_rate_m3_hr: float = 43.0,
    operating_hours_per_day: float = 22.0, operating_days_per_year: float = 240.0,
    availability_factor: float = 0.85, operating_cost_usd_m3: float = 12.0,
    fixed_overhead_usd_yr: float = 400000.0, plant_capex_usd: float = 1200000.0,
    civil_capex_usd: float = 250000.0, preproduction_capex_usd: float = 120000.0,
    capex_contingency_pct: float = 0.10, corporation_tax_rate: float = 0.40,
    discount_rate: float = 0.12, project_life_years: int = 6, depreciation_period_years: int = 5,
) -> dict:
    """Full DCF: material processed, EBITDA, break-even grades, 0..project_life cash-flow
    schedule, NPV, IRR, payback. Verified bit-for-bit against Alluvial_Campaign_Control_
    Workbook_Guyana.xlsx!Feasibility. Not a resource/reserve statement -- planning only."""
    a = feas_core.FeasibilityAssumptions(
        gold_price_usd_oz, royalty_rate, head_grade_g_m3, metallurgical_recovery, feed_rate_m3_hr,
        operating_hours_per_day, operating_days_per_year, availability_factor, operating_cost_usd_m3,
        fixed_overhead_usd_yr, plant_capex_usd, civil_capex_usd, preproduction_capex_usd,
        capex_contingency_pct, corporation_tax_rate, discount_rate, project_life_years,
        depreciation_period_years,
    )
    return to_jsonable(feas_core.run_feasibility_model(a))


@mcp.tool(annotations=READ_ONLY)
def build_sensitivity_grid(grades: list[float], prices: list[float],
                            feasibility_assumptions: dict | None = None) -> dict:
    """NPV sensitivity grid over head grade (rows) x gold price (columns)."""
    a = feas_core.FeasibilityAssumptions(**(feasibility_assumptions or {}))
    return to_jsonable(feas_core.build_sensitivity_grid(a, grades, prices))


if __name__ == "__main__":
    mcp.run()
