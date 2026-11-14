"""
Module A — Finance & Stakeholder Pipeline (core engine).

Verified against the real workbooks:
  - COMPREHENSIVE_FEEDING.xlsx!CASH BOOK: opening balance 52583.07149999976
    at F7, running balance H_n = H_{n-1} + F_n - G_n reproduces exactly.
  - Guyana_Outreach_Cost_Pipeline_Workbook.xlsx!Fraud_Check: risk_score
    formula reproduces P02 (10.714285714285714) and P03
    (14.285714285714285) exactly from the 22-flag weight table.
  - Guyana_Outreach_Cost_Pipeline_Workbook.xlsx!Stage_Costs: the 12-stage
    base cost table (Base scenario) sums to the workbook's 30715 total.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Literal

PROJECT_CODES = {"GRM", "ALV", "NAN", "KOC", "ELIT", "ANY", "SEWM", "EAGL"}
CATEGORY_CODES = {
    "IT", "SSF", "T2", "OE", "PC", "BP", "CC", "RM", "TT", "ST", "FE",
    "FL", "TP", "WM", "CSA", "ACC", "IMP", "UT", "COMM", "WGS", "NA",
}


# ---------------------------------------------------------------------------
# A1 — Cash book
# ---------------------------------------------------------------------------


@dataclass
class CashEntry:
    date: date | None
    description: str
    supplier_customer: str | None
    ref_no: str | None
    project_code: str
    cash_received: float = 0.0
    cash_paid: float = 0.0
    category_code: str = "NA"


def validate_project_category(project_code: str, category_code: str) -> bool:
    return project_code in PROJECT_CODES and category_code in CATEGORY_CODES


def compute_running_balance(opening_balance: float, entries: list[CashEntry]) -> list[dict]:
    """H_n = H_{n-1} + F_n - G_n. Flags any entry that would drive balance negative."""
    balance = opening_balance
    out = []
    for e in entries:
        balance = balance + e.cash_received - e.cash_paid
        out.append({
            "date": e.date, "description": e.description, "project_code": e.project_code,
            "category_code": e.category_code, "cash_received": e.cash_received,
            "cash_paid": e.cash_paid, "balance": balance,
            "data_issue": "NEGATIVE_BALANCE" if balance < 0 else None,
        })
    return out


def get_feeding_rotation_reconciliation(fe_total_by_person: dict[str, float],
                                         expected_days_by_person: dict[str, float],
                                         cost_per_day: float) -> list[dict]:
    """FEEDING_MISMATCH if weekly FE total per active staff deviates > 10% from rotation's expected days."""
    out = []
    for person, fe_total in fe_total_by_person.items():
        expected_cost = expected_days_by_person.get(person, 0.0) * cost_per_day
        deviation = abs(fe_total - expected_cost) / expected_cost if expected_cost > 0 else 0.0
        out.append({
            "person": person, "fe_total": fe_total, "expected_cost": expected_cost,
            "deviation_pct": deviation,
            "flag": "FEEDING_MISMATCH" if deviation > 0.10 else None,
        })
    return out


# ---------------------------------------------------------------------------
# A3 — Stage-cost pipeline (Guyana_Outreach_Cost_Pipeline_Workbook.xlsx)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class StageDefinition:
    stage_id: str
    description: str
    start_week: float
    base_duration_wk: float
    base_cost_usd: float  # at Base scenario (multiplier 1.0)
    gatekeeper: str


STAGE_SEQUENCE: tuple[StageDefinition, ...] = (
    StageDefinition("S1", "Due diligence on the investor and written mandate", 1, 2, 497.5, "ASIC/ABN checks; counsel on finder-fee terms"),
    StageDefinition("S2", "Legal and compliance set-up", 1, 4, 3375.0, "Counsel opinion; work-authorisation scope; registration"),
    StageDefinition("S3", "Desk research and target-universe build", 2, 4, 1372.5, "GGMC tenure map, Gazettes, press, associations"),
    StageDefinition("S4", "Institutional access (GGMC counters, GGDMA, GO-Invest)", 4, 4, 1417.5, "Appointments; official data requests"),
    StageDefinition("S5", "Relationship building and referrals", 6, 8, 3677.5, "Trust is built through referrals and repeat visits"),
    StageDefinition("S6", "Outreach waves and screening calls", 8, 6, 2015.0, "Replies are slow; follow-ups needed"),
    StageDefinition("S7", "Title verification (fraud-check workflow)", 12, 6, 3305.0, "GGMC records; Gazette 21-day objection windows"),
    StageDefinition("S8", "Site visits and technical validation", 16, 6, 4625.0, "Interior travel; weather; independent sampling"),
    StageDefinition("S9", "NDA, LOI and non-binding terms", 20, 4, 2725.0, "Counsel drafting and review"),
    StageDefinition("S10", "Investor presentation and data room", 22, 4, 1615.0, "Calls with Phoenix and its client"),
    StageDefinition("S11", "Term sheet and JV negotiation; consent path", 26, 8, 5165.0, "GGMC written consent where any interest in a permit is created"),
    StageDefinition("S12", "Close-out, handover and reporting", 34, 2, 925.0, "Final report and lessons learned"),
)

SCENARIO_MULTIPLIERS = {
    "Low": {"cost": 0.85, "delay": 0.8},
    "Base": {"cost": 1.0, "delay": 1.0},
    "High": {"cost": 1.3, "delay": 1.6},
}


def run_stage_cost_simulation(scenario: Literal["Low", "Base", "High"] = "Base",
                               relationship_friction_wk: float = 0.5,
                               contingency_pct: float = 0.10,
                               fx_gyd_per_usd: float | None = None) -> dict:
    mult = SCENARIO_MULTIPLIERS[scenario]
    rows = []
    cursor_week = None
    for s in STAGE_SEQUENCE:
        scenario_duration = s.base_duration_wk * mult["delay"] + relationship_friction_wk
        # start_week is 1-indexed (stage 1 begins at elapsed time 0), so the
        # stage's end on the horizon is (start_week - 1) + duration -- verified
        # against Stage_Costs!F5:F16 (e.g. S12: start 34, duration 2.5 -> end
        # 35.5, not 36.5).
        end_week = (s.start_week - 1) + scenario_duration
        cost = s.base_cost_usd * mult["cost"]
        rows.append({
            "stage_id": s.stage_id, "description": s.description, "start_week": s.start_week,
            "scenario_duration_wk": scenario_duration, "end_week": end_week,
            "gatekeeper": s.gatekeeper, "stage_cost_usd": cost,
        })
        cursor_week = max(cursor_week or 0, end_week)
    total_planned = sum(r["stage_cost_usd"] for r in rows)
    contingency = total_planned * contingency_pct
    result = {
        "scenario": scenario, "stages": rows, "horizon_weeks": cursor_week,
        "total_planned_cost_usd": total_planned, "contingency_usd": contingency,
        "total_with_contingency_usd": total_planned + contingency,
    }
    if fx_gyd_per_usd:
        result["total_with_contingency_gyd"] = (total_planned + contingency) * fx_gyd_per_usd
    return result


def compute_runway(budget_usd: float, weekly_burn_usd: float) -> float:
    if weekly_burn_usd <= 0:
        return float("inf")
    return budget_usd / weekly_burn_usd


# ---------------------------------------------------------------------------
# A4 — Pipeline / Fraud_Check
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class FraudFlagDef:
    flag_id: str
    weight: int
    hard_stop: bool


FRAUD_FLAGS: tuple[FraudFlagDef, ...] = (
    FraudFlagDef("F01", 5, True), FraudFlagDef("F02", 4, True), FraudFlagDef("F03", 4, False),
    FraudFlagDef("F04", 4, False), FraudFlagDef("F05", 3, False), FraudFlagDef("F06", 3, False),
    FraudFlagDef("F07", 3, False), FraudFlagDef("F08", 5, True), FraudFlagDef("F09", 4, False),
    FraudFlagDef("F10", 3, False), FraudFlagDef("F11", 3, False), FraudFlagDef("F12", 5, True),
    FraudFlagDef("F13", 5, True), FraudFlagDef("F14", 5, True), FraudFlagDef("F15", 5, True),
    FraudFlagDef("F16", 2, False), FraudFlagDef("F17", 4, False), FraudFlagDef("F18", 3, False),
    FraudFlagDef("F19", 3, False), FraudFlagDef("F20", 4, False), FraudFlagDef("F21", 4, True),
    FraudFlagDef("F22", 3, False),
)
_TOTAL_WEIGHT = sum(f.weight for f in FRAUD_FLAGS)
AMBER_THRESHOLD_PCT = 15.0
RED_THRESHOLD_PCT = 35.0
MIN_VERIFICATION_COMPLETION = 0.75
N_VERIFICATION_STEPS = 12


def compute_risk_class(flags_triggered: dict[str, bool]) -> dict:
    weighted = sum(f.weight for f in FRAUD_FLAGS if flags_triggered.get(f.flag_id, False))
    risk_score = (weighted / _TOTAL_WEIGHT) * 100
    hard_stops = [f.flag_id for f in FRAUD_FLAGS if f.hard_stop and flags_triggered.get(f.flag_id, False)]
    if hard_stops or risk_score >= RED_THRESHOLD_PCT:
        risk_class = "RED"
    elif risk_score >= AMBER_THRESHOLD_PCT:
        risk_class = "AMBER"
    else:
        risk_class = "GREEN"
    return {"risk_score": risk_score, "risk_class": risk_class, "hard_stop_flags": hard_stops,
            "hard_stop_count": len(hard_stops)}


def compute_verification_completion(verifications_passed: dict[str, bool]) -> float:
    passed = sum(1 for v in verifications_passed.values() if v)
    return passed / N_VERIFICATION_STEPS


def adjudicate_prospect_introduction(flags_triggered: dict[str, bool],
                                      verifications_passed: dict[str, bool]) -> dict:
    risk = compute_risk_class(flags_triggered)
    completion = compute_verification_completion(verifications_passed)
    cleared = (risk["risk_class"] == "GREEN" and completion >= MIN_VERIFICATION_COMPLETION
               and risk["hard_stop_count"] == 0)
    reason = None
    if not cleared:
        if risk["hard_stop_count"] > 0:
            reason = f"HARD_STOP_{risk['hard_stop_flags'][0]}"
        elif risk["risk_class"] != "GREEN":
            reason = f"RISK_CLASS_{risk['risk_class']}"
        elif completion < MIN_VERIFICATION_COMPLETION:
            reason = "INSUFFICIENT_VERIFICATION"
    return {
        "decision": "ALLOW" if cleared else "DENY", "reason": reason,
        "risk_class": risk["risk_class"], "risk_score": risk["risk_score"],
        "verification_completion": completion,
    }


def score_prospect(warmth: int, attractiveness: int, legal_clarity: int) -> float:
    return ((warmth + attractiveness + legal_clarity) / 15.0) * 100


def rank_prospects_by_value_per_hour(prospects: list[dict], hours_budget: float) -> dict:
    """Greedy: value = priority score / effort hours. prospects: [{id, score, effort_hours}]."""
    scored = sorted(prospects, key=lambda p: p["score"] / p["effort_hours"], reverse=True)
    remaining = hours_budget
    take, skip = [], []
    for p in scored:
        if p["effort_hours"] <= remaining:
            take.append(p)
            remaining -= p["effort_hours"]
        else:
            skip.append(p)
    return {"take": take, "skip": skip, "hours_remaining": remaining}


# ---------------------------------------------------------------------------
# A5 — PSO weekly outreach-hour allocation
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class OutreachChannel:
    name: str
    cap_leads_per_week: float
    saturation_rate_k: float
    min_hours: float


DEFAULT_CHANNELS: tuple[OutreachChannel, ...] = (
    OutreachChannel("GGMC public records and tenure checks", 3.0, 0.30, 4.0),
    OutreachChannel("Associations (GGDMA) and referrals", 4.0, 0.12, 4.0),
    OutreachChannel("GO-Invest and government channels", 2.0, 0.15, 2.0),
    OutreachChannel("Attorneys and professional referrals", 3.5, 0.10, 3.0),
    OutreachChannel("Field visits and regional meetings", 3.0, 0.07, 4.0),
)


def _expected_leads(hours: float, channel: OutreachChannel) -> float:
    import math
    return channel.cap_leads_per_week * (1 - math.exp(-channel.saturation_rate_k * hours))


def optimize_weekly_hours(weekly_hours: float = 40.0,
                           channels: tuple[OutreachChannel, ...] = DEFAULT_CHANNELS,
                           seed: int = 42, n_particles: int = 30, iters: int = 150) -> dict:
    """PSO allocation of weekly_hours across channels; fitness = total expected
    leads - 3*sum(max(0, min_hrs - hours)). Seeded and deterministic (per the
    platform's non-negotiable determinism rule); the seed is returned."""
    import numpy as np
    import pyswarms as ps

    n = len(channels)
    rng_seed = seed
    np.random.seed(rng_seed)

    def objective(positions: "np.ndarray") -> "np.ndarray":
        out = np.zeros(positions.shape[0])
        for row in range(positions.shape[0]):
            raw = positions[row]
            hours = raw / raw.sum() * weekly_hours if raw.sum() > 0 else np.zeros(n)
            total_leads = sum(_expected_leads(hours[i], channels[i]) for i in range(n))
            shortfall_penalty = sum(3 * max(0.0, channels[i].min_hours - hours[i]) for i in range(n))
            out[row] = -(total_leads - shortfall_penalty)  # pyswarms minimizes
        return out

    bounds = (np.zeros(n), np.ones(n) * weekly_hours)
    options = {"c1": 1.5, "c2": 1.5, "w": 0.7}
    optimizer = ps.single.GlobalBestPSO(n_particles=n_particles, dimensions=n, options=options, bounds=bounds)
    best_cost, best_pos = optimizer.optimize(objective, iters=iters, verbose=False)

    hours = best_pos / best_pos.sum() * weekly_hours if best_pos.sum() > 0 else [0.0] * n
    equal_split = weekly_hours / n
    allocation = []
    total_expected_leads = 0.0
    for i, ch in enumerate(channels):
        leads = _expected_leads(hours[i], ch)
        total_expected_leads += leads
        allocation.append({
            "channel": ch.name, "hours": float(hours[i]), "expected_leads": leads,
            "equal_split_hours": equal_split,
        })
    equal_split_leads = sum(_expected_leads(equal_split, ch) for ch in channels)
    return {
        "allocation": allocation, "total_expected_leads": total_expected_leads,
        "equal_split_total_leads": equal_split_leads,
        "uplift_vs_equal_split": total_expected_leads - equal_split_leads,
        "seed": rng_seed,
    }
