"""
Cross-module adjudication layer (docs/AMOP_MCP_SPEC.md §5).

Composite rules read outputs from grade.py, vam.py, plant.py and finance.py
and return a verdict tree -- never raw arithmetic. The LLM explains this
JSON; it does not recompute or reinterpret the thresholds (non-negotiable
rule #1, §8.4).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Literal


class Severity(str, Enum):
    HARD = "HARD"
    SOFT = "SOFT"
    WARN = "WARN"


@dataclass
class RuleResult:
    rule_id: str
    name: str
    passed: bool
    actual: dict
    expected: dict
    severity: Severity
    blocking_reason: str | None = None


# ---------------------------------------------------------------------------
# R-1.1 blend_grade_credibility
# ---------------------------------------------------------------------------


def adjudicate_blend_against_grade_credibility(pit_shares_and_z: dict[str, tuple[float, float]]) -> RuleResult:
    """A pit may contribute > 30% of blend volume only if Z >= 0.6; else cap at 20%."""
    violations = []
    adjusted_shares = {}
    for pit_id, (share, z) in pit_shares_and_z.items():
        cap = 0.30 if z >= 0.6 else 0.20
        adjusted_shares[f"{pit_id}_share"] = share
        adjusted_shares[f"{pit_id}_Z"] = z
        if share > cap:
            violations.append(f"{pit_id}: share {share:.3f} exceeds cap {cap:.2f} at Z={z:.3f}")
    passed = not violations
    return RuleResult(
        rule_id="R-1.1", name="blend_grade_credibility", passed=passed,
        actual=adjusted_shares, expected={"max_share_when_Z_below_0_6": 0.20, "threshold_Z": 0.6},
        severity=Severity.HARD,
        blocking_reason="; ".join(violations) if violations else None,
    )


# ---------------------------------------------------------------------------
# R-1.2 stockpile_compatibility
# ---------------------------------------------------------------------------


def adjudicate_haul_against_stockpile_compatibility(
    stockpile_deficits: dict[str, float], compatibility: dict[str, float]
) -> RuleResult:
    """No allocation to a stockpile whose target-grade deficit > 2x pit grade unless compatibility > 0.8."""
    violations = []
    reroutes = []
    for sp_id, deficit_multiple in stockpile_deficits.items():
        compat = compatibility.get(sp_id, 0.0)
        if deficit_multiple > 2.0 and compat <= 0.8:
            violations.append(f"{sp_id}: deficit multiple {deficit_multiple:.2f} with compatibility {compat:.2f}")
            reroutes.append(f"Reroute volume away from {sp_id}")
    return RuleResult(
        rule_id="R-1.2", name="stockpile_compatibility", passed=not violations,
        actual={"deficits": stockpile_deficits, "compatibility": compatibility},
        expected={"max_deficit_multiple": 2.0}, severity=Severity.SOFT,
        blocking_reason="; ".join(violations) if violations else None,
    )


# ---------------------------------------------------------------------------
# R-1.3 energy_budget
# ---------------------------------------------------------------------------


def adjudicate_plant_feed_against_energy_budget(daily_energy_cost_usd: float, gross_revenue_usd: float) -> RuleResult:
    """Daily energy cost <= 15% of gross gold revenue."""
    ratio = (daily_energy_cost_usd / gross_revenue_usd) if gross_revenue_usd > 0 else float("inf")
    passed = ratio <= 0.15
    return RuleResult(
        rule_id="R-1.3", name="energy_budget", passed=passed,
        actual={"energy_ratio": ratio}, expected={"max_ratio": 0.15}, severity=Severity.HARD,
        blocking_reason=(f"Energy cost {ratio*100:.1f}% of gross gold revenue exceeds 15% budget"
                          if not passed else None),
    )


# ---------------------------------------------------------------------------
# R-1.4 cash_runway
# ---------------------------------------------------------------------------


def adjudicate_prospect_against_cash_runway(runway_weeks: float, min_weeks: float = 2.0) -> RuleResult:
    passed = runway_weeks >= min_weeks
    return RuleResult(
        rule_id="R-1.4", name="cash_runway", passed=passed,
        actual={"runway_weeks": runway_weeks}, expected={"min_weeks": min_weeks}, severity=Severity.HARD,
        blocking_reason=(f"Runway {runway_weeks:.1f} weeks is below the {min_weeks} week minimum"
                          if not passed else None),
    )


# ---------------------------------------------------------------------------
# R-2.1 prospect_clearance / R-2.2 vam_feasibility / R-3.x plant / R-4.1 feeding / R-5.1 data integrity
# ---------------------------------------------------------------------------


def adjudicate_prospect_clearance(risk_class: str, verification_completion: float, fail_count: int) -> RuleResult:
    passed = risk_class == "GREEN" and verification_completion >= 0.75 and fail_count == 0
    return RuleResult(
        rule_id="R-2.1", name="prospect_clearance", passed=passed,
        actual={"risk_class": risk_class, "verification_completion": verification_completion, "fail_count": fail_count},
        expected={"risk_class": "GREEN", "min_completion": 0.75, "max_fails": 0}, severity=Severity.HARD,
        blocking_reason=None if passed else "Prospect not cleared for introduction",
    )


def adjudicate_vam_feasibility(vam_verdict: dict) -> RuleResult:
    passed = vam_verdict.get("verdict") == "VAM_ACCEPTED"
    return RuleResult(
        rule_id="R-2.2", name="vam_feasibility", passed=passed, actual=vam_verdict,
        expected={"verdict": "VAM_ACCEPTED"}, severity=Severity.HARD,
        blocking_reason=None if passed else f"VAM rejected: {vam_verdict.get('failing_constraints')}",
    )


def adjudicate_plant_efficiency_floor(overall_efficiency: float, base_efficiency: float = 1.0) -> RuleResult:
    passed = overall_efficiency >= 0.8 * base_efficiency
    return RuleResult(
        rule_id="R-3.1", name="plant_efficiency_floor", passed=passed,
        actual={"overall_efficiency": overall_efficiency}, expected={"min_ratio_of_base": 0.8},
        severity=Severity.SOFT, blocking_reason=None if passed else "Plant efficiency below 80% of baseline",
    )


def adjudicate_recovery_bounds(effective_recovery: float, base_recovery: float) -> RuleResult:
    lo, hi = 0.8 * base_recovery, base_recovery
    passed = lo <= effective_recovery <= hi
    return RuleResult(
        rule_id="R-3.2", name="recovery_bounds", passed=passed,
        actual={"effective_recovery": effective_recovery}, expected={"range": [lo, hi]},
        severity=Severity.HARD, blocking_reason=None if passed else "Effective recovery outside expected bounds",
    )


def adjudicate_blend_volume_feasibility(blend_volume_m3: float, plant_daily_capacity_m3: float,
                                         available_volume_m3: float) -> RuleResult:
    passed = blend_volume_m3 <= plant_daily_capacity_m3 and blend_volume_m3 <= available_volume_m3
    return RuleResult(
        rule_id="R-3.3", name="blend_volume_feasibility", passed=passed,
        actual={"blend_volume_m3": blend_volume_m3},
        expected={"plant_daily_capacity_m3": plant_daily_capacity_m3, "available_volume_m3": available_volume_m3},
        severity=Severity.HARD,
        blocking_reason=None if passed else "Blend target exceeds plant capacity or available volume",
    )


def adjudicate_feeding_reconciliation(deviation_pct: float) -> RuleResult:
    passed = deviation_pct <= 0.10
    return RuleResult(
        rule_id="R-4.1", name="feeding_reconciliation", passed=passed,
        actual={"deviation_pct": deviation_pct}, expected={"max_deviation_pct": 0.10}, severity=Severity.SOFT,
        blocking_reason=None if passed else "Feeding rotation deviates >10% from cash-book FE total",
    )


def adjudicate_data_integrity(issues: list[dict]) -> RuleResult:
    return RuleResult(
        rule_id="R-5.1", name="data_integrity", passed=len(issues) == 0,
        actual={"issue_count": len(issues), "issues": issues},
        expected={"issue_count": 0}, severity=Severity.WARN,
        blocking_reason=None,
    )


# ---------------------------------------------------------------------------
# Full chain
# ---------------------------------------------------------------------------


@dataclass
class FullChainVerdict:
    verdict: Literal["PASS", "FAIL", "CONDITIONAL"]
    timestamp: str
    inputs: dict
    tree: list[RuleResult] = field(default_factory=list)
    blocking_reasons: list[str] = field(default_factory=list)
    recommended_actions: list[str] = field(default_factory=list)


def adjudicate_full_chain(
    pit_shares_and_z: dict[str, tuple[float, float]],
    stockpile_deficits: dict[str, float],
    compatibility: dict[str, float],
    daily_energy_cost_usd: float,
    gross_revenue_usd: float,
    runway_weeks: float,
    blend_target_m3: float,
    include_pipeline: bool = True,
) -> FullChainVerdict:
    tree = [
        adjudicate_blend_against_grade_credibility(pit_shares_and_z),
        adjudicate_haul_against_stockpile_compatibility(stockpile_deficits, compatibility),
        adjudicate_plant_feed_against_energy_budget(daily_energy_cost_usd, gross_revenue_usd),
    ]
    if include_pipeline:
        tree.append(adjudicate_prospect_against_cash_runway(runway_weeks))

    blocking = [r.blocking_reason for r in tree if not r.passed and r.severity == Severity.HARD and r.blocking_reason]
    soft_fails = [r for r in tree if not r.passed and r.severity == Severity.SOFT]

    if blocking:
        verdict: Literal["PASS", "FAIL", "CONDITIONAL"] = "FAIL"
    elif soft_fails:
        verdict = "CONDITIONAL"
    else:
        verdict = "PASS"

    recommendations = []
    for r in tree:
        if not r.passed and r.name == "energy_budget":
            recommendations.append(f"Reduce blend target from {blend_target_m3} m3, or shift hours from peak to off-peak tariff")
        if not r.passed and r.name == "blend_grade_credibility":
            recommendations.append("Cap the low-credibility pit's share and reroute the balance to a higher-Z pit")
        if not r.passed and r.name == "cash_runway":
            recommendations.append("Reduce weekly outreach-hour allocation to extend runway above 2 weeks")

    return FullChainVerdict(
        verdict=verdict, timestamp=datetime.now(timezone.utc).isoformat(),
        inputs={"blend_target_m3": blend_target_m3, "include_pipeline": include_pipeline},
        tree=tree, blocking_reasons=[b for b in blocking if b], recommended_actions=recommendations,
    )
