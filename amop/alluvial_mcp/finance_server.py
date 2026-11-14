"""Module A — Finance & Stakeholder Pipeline MCP server (docs/AMOP_MCP_SPEC.md §4.1)."""
from __future__ import annotations

from fastmcp import FastMCP

from alluvial_mcp.core import finance as core
from alluvial_mcp.mcp_utils import MUTATING, READ_ONLY, to_jsonable

mcp = FastMCP("alluvial-finance")


@mcp.tool(annotations=READ_ONLY)
def compute_running_balance(opening_balance: float, entries: list[dict]) -> dict:
    """Cash-book running balance: H_n = H_{n-1} + F_n - G_n. Flags NEGATIVE_BALANCE."""
    parsed = [core.CashEntry(**e) for e in entries]
    return {"ledger": to_jsonable(core.compute_running_balance(opening_balance, parsed))}


@mcp.tool(annotations=READ_ONLY)
def validate_project_category(project_code: str, category_code: str) -> dict:
    return {"valid": core.validate_project_category(project_code, category_code)}


@mcp.tool(annotations=READ_ONLY)
def run_stage_cost_simulation(scenario: str = "Base", relationship_friction_wk: float = 0.5,
                               contingency_pct: float = 0.10, fx_gyd_per_usd: float | None = None) -> dict:
    """12-stage (S1-S12) outreach cost/duration schedule. scenario in {Low, Base, High}."""
    return to_jsonable(core.run_stage_cost_simulation(scenario, relationship_friction_wk, contingency_pct, fx_gyd_per_usd))


@mcp.tool(annotations=READ_ONLY)
def compute_runway(budget_usd: float, weekly_burn_usd: float) -> dict:
    return {"runway_weeks": core.compute_runway(budget_usd, weekly_burn_usd)}


@mcp.tool(annotations=READ_ONLY)
def compute_risk_class(flags_triggered: dict[str, bool]) -> dict:
    """Fraud_Check 22-flag scorecard. Any hard-stop (F01,F02,F08,F12,F13,F14,F15,F21) forces RED."""
    return to_jsonable(core.compute_risk_class(flags_triggered))


@mcp.tool(annotations=READ_ONLY)
def compute_verification_completion(verifications_passed: dict[str, bool]) -> dict:
    return {"completion": core.compute_verification_completion(verifications_passed)}


@mcp.tool(annotations=READ_ONLY)
def adjudicate_prospect_introduction(flags_triggered: dict[str, bool],
                                      verifications_passed: dict[str, bool]) -> dict:
    """ALLOW iff GREEN AND verification completion >= 0.75 AND fail_count == 0."""
    return to_jsonable(core.adjudicate_prospect_introduction(flags_triggered, verifications_passed))


@mcp.tool(annotations=READ_ONLY)
def score_prospect(warmth: int, attractiveness: int, legal_clarity: int) -> dict:
    return {"score": core.score_prospect(warmth, attractiveness, legal_clarity)}


@mcp.tool(annotations=READ_ONLY)
def rank_prospects_by_value_per_hour(prospects: list[dict], hours_budget: float) -> dict:
    """Greedy ranking: value = priority score / effort hours."""
    return to_jsonable(core.rank_prospects_by_value_per_hour(prospects, hours_budget))


@mcp.tool(annotations=READ_ONLY)
def optimize_weekly_hours(weekly_hours: float = 40.0, seed: int = 42) -> dict:
    """Seeded pyswarms PSO allocation of weekly outreach hours across the 5 channels."""
    return to_jsonable(core.optimize_weekly_hours(weekly_hours=weekly_hours, seed=seed))


if __name__ == "__main__":
    mcp.run()
