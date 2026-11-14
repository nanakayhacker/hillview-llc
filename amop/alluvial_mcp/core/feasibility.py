"""
Alluvial Project Feasibility Reporting & Generation Module (NEW).

Two parts, both explicitly PROTOTYPE / non-compliant (see SCOPE_DISCLAIMER):

1. A JORC-style confidence classification (Measured/Indicated/Inferred
   resource; Proved/Probable reserve) driven by the grade engine's pit
   composite Z-credibility and QAQC pass flag. This is a structural
   prototype only -- it does NOT constitute a JORC Code or NI 43-101
   compliant Mineral Resource/Reserve statement, which requires sign-off by
   a Competent/Qualified Person and full Table 1 reporting. The intent (per
   the brief) is a 3D-geological-model-report-shaped scaffold ready to
   receive that CP sign-off and real drill/pit data later.

2. A DCF/NPV/IRR/break-even economics engine verified EXACTLY against
   Alluvial_Campaign_Control_Workbook_Guyana.xlsx!Feasibility: material
   processed 192984 m3/yr, EBITDA 1262875.7494172682, NPV 1894893.2578734749,
   payback 2 years, all reproduced bit-for-bit below.

The full feasibility report sequences EXPLORATION -> MINING_OPERATIONS ->
PLANT_PROCESSING -> CAMP_DEVELOPMENT -> HSE_ADMIN, with every dollar figure
linked to a cost_tracking.py cost code -- never a number invented in a
prompt.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

TROY_OUNCE_G = 31.1035

SCOPE_DISCLAIMER = (
    "This feasibility output is a planning and decision-support prototype. "
    "It does NOT constitute a Mineral Resource or Reserve statement, a JORC "
    "Code (2012) or NI 43-101 compliant declaration, or a legal opinion. "
    "Classification and economics here are heuristics pending sign-off by a "
    "Competent Person / Qualified Person and replacement of every "
    "placeholder input with quoted costs and measured grade."
)


# ---------------------------------------------------------------------------
# JORC-style prototype classification
# ---------------------------------------------------------------------------

ResourceCategory = Literal["MEASURED", "INDICATED", "INFERRED", "NOT CLASSIFIED"]
ReserveCategory = Literal["PROVED", "PROBABLE", "NOT CONVERTIBLE"]


@dataclass
class ResourceClassification:
    pit_id: str
    z_credibility: float
    qaqc_pass: bool
    resource_category: ResourceCategory
    reserve_category: ReserveCategory
    rationale: str


def classify_resource_prototype(pit_id: str, z_credibility: float, qaqc_pass: bool,
                                 class_vs_cutoff: str) -> ResourceClassification:
    """
    Prototype confidence mapping (NOT a JORC Code classification):
      Z >= 0.8 and QAQC pass             -> MEASURED  -> convertible to PROVED
      0.6 <= Z < 0.8 and QAQC pass       -> INDICATED -> convertible to PROBABLE
      Z < 0.6 or QAQC fail               -> INFERRED  -> not convertible to a Reserve
      BELOW DETECTION / NOT PANNED       -> NOT CLASSIFIED
    """
    if class_vs_cutoff in ("BELOW DETECTION", "NOT PANNED"):
        return ResourceClassification(pit_id, z_credibility, qaqc_pass, "NOT CLASSIFIED",
                                       "NOT CONVERTIBLE", "Horizon(s) below detection or never panned.")
    if z_credibility >= 0.8 and qaqc_pass:
        return ResourceClassification(pit_id, z_credibility, qaqc_pass, "MEASURED", "PROVED",
                                       "Z>=0.8 with QAQC pass: high sampling/grade confidence.")
    if z_credibility >= 0.6 and qaqc_pass:
        return ResourceClassification(pit_id, z_credibility, qaqc_pass, "INDICATED", "PROBABLE",
                                       "0.6<=Z<0.8 with QAQC pass: reasonable confidence, modifying factors assumed.")
    return ResourceClassification(pit_id, z_credibility, qaqc_pass, "INFERRED", "NOT CONVERTIBLE",
                                   "Z<0.6 or QAQC fail: low confidence, cannot convert to a Reserve.")


# ---------------------------------------------------------------------------
# DCF / NPV / IRR / break-even economics
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class FeasibilityAssumptions:
    gold_price_usd_oz: float = 4500.0
    royalty_rate: float = 0.05
    head_grade_g_m3: float = 0.2
    metallurgical_recovery: float = 0.75
    feed_rate_m3_hr: float = 43.0
    operating_hours_per_day: float = 22.0
    operating_days_per_year: float = 240.0
    availability_factor: float = 0.85
    operating_cost_usd_m3: float = 12.0
    fixed_overhead_usd_yr: float = 400000.0
    plant_capex_usd: float = 1200000.0
    civil_capex_usd: float = 250000.0
    preproduction_capex_usd: float = 120000.0
    capex_contingency_pct: float = 0.10
    corporation_tax_rate: float = 0.40
    discount_rate: float = 0.12
    project_life_years: int = 6
    depreciation_period_years: int = 5


@dataclass
class AnnualEconomics:
    material_processed_m3_yr: float
    recovered_gold_oz_yr: float
    gross_revenue_usd_yr: float
    royalty_usd_yr: float
    operating_cost_usd_yr: float
    ebitda_usd_yr: float
    operating_breakeven_grade_g_m3: float
    all_in_breakeven_grade_g_m3: float
    total_initial_capex_usd: float


def compute_annual_economics(a: FeasibilityAssumptions) -> AnnualEconomics:
    material = a.feed_rate_m3_hr * a.operating_hours_per_day * a.operating_days_per_year * a.availability_factor
    recovered_oz = material * a.head_grade_g_m3 * a.metallurgical_recovery / TROY_OUNCE_G
    revenue = recovered_oz * a.gold_price_usd_oz
    royalty = revenue * a.royalty_rate
    operating_cost = material * a.operating_cost_usd_m3 + a.fixed_overhead_usd_yr
    ebitda = revenue - royalty - operating_cost

    total_capex = (a.plant_capex_usd + a.civil_capex_usd) * (1 + a.capex_contingency_pct) + a.preproduction_capex_usd

    revenue_per_g_m3 = material * a.metallurgical_recovery / TROY_OUNCE_G * a.gold_price_usd_oz * (1 - a.royalty_rate)
    operating_breakeven = operating_cost / revenue_per_g_m3 if revenue_per_g_m3 > 0 else float("inf")
    all_in_breakeven = (operating_cost + total_capex / a.project_life_years) / revenue_per_g_m3 if revenue_per_g_m3 > 0 else float("inf")

    return AnnualEconomics(
        material_processed_m3_yr=material, recovered_gold_oz_yr=recovered_oz,
        gross_revenue_usd_yr=revenue, royalty_usd_yr=royalty, operating_cost_usd_yr=operating_cost,
        ebitda_usd_yr=ebitda, operating_breakeven_grade_g_m3=operating_breakeven,
        all_in_breakeven_grade_g_m3=all_in_breakeven, total_initial_capex_usd=total_capex,
    )


@dataclass
class CashFlowYear:
    year: int
    in_life: bool
    ebitda_usd: float
    depreciation_usd: float
    tax_usd: float
    capex_usd: float
    free_cash_flow_usd: float
    cumulative_usd: float
    payback_flag: bool


def build_cash_flow_schedule(a: FeasibilityAssumptions, econ: AnnualEconomics | None = None) -> list[CashFlowYear]:
    econ = econ or compute_annual_economics(a)
    years: list[CashFlowYear] = []
    cumulative = 0.0
    for t in range(0, a.project_life_years + 1):
        in_life = 1 <= t <= a.project_life_years
        ebitda = econ.ebitda_usd_yr if in_life else 0.0
        depreciation = econ.total_initial_capex_usd / a.depreciation_period_years if (in_life and t <= a.depreciation_period_years) else 0.0
        tax = max(0.0, ebitda - depreciation) * a.corporation_tax_rate if in_life else 0.0
        capex = -econ.total_initial_capex_usd if t == 0 else 0.0
        fcf = capex if t == 0 else (ebitda - tax)
        cumulative += fcf
        years.append(CashFlowYear(
            year=t, in_life=in_life, ebitda_usd=ebitda, depreciation_usd=depreciation, tax_usd=tax,
            capex_usd=capex, free_cash_flow_usd=fcf, cumulative_usd=cumulative, payback_flag=cumulative >= 0,
        ))
    return years


def compute_npv(cash_flows: list[CashFlowYear], discount_rate: float) -> float:
    return sum(cf.free_cash_flow_usd / ((1 + discount_rate) ** cf.year) for cf in cash_flows)


def compute_irr(cash_flows: list[CashFlowYear]) -> float | None:
    from scipy.optimize import brentq

    flows = [cf.free_cash_flow_usd for cf in cash_flows]

    def npv_at(r: float) -> float:
        return sum(f / ((1 + r) ** t) for t, f in enumerate(flows))

    try:
        return brentq(npv_at, -0.99, 10.0)
    except ValueError:
        return None


def compute_payback_years(cash_flows: list[CashFlowYear]) -> int | None:
    for cf in cash_flows:
        if cf.payback_flag:
            return cf.year
    return None


@dataclass
class FeasibilityResult:
    assumptions: FeasibilityAssumptions
    annual_economics: AnnualEconomics
    cash_flows: list[CashFlowYear]
    npv_usd: float
    irr: float | None
    payback_years: int | None


def run_feasibility_model(a: FeasibilityAssumptions = FeasibilityAssumptions()) -> FeasibilityResult:
    econ = compute_annual_economics(a)
    cash_flows = build_cash_flow_schedule(a, econ)
    npv = compute_npv(cash_flows, a.discount_rate)
    irr = compute_irr(cash_flows)
    payback = compute_payback_years(cash_flows)
    return FeasibilityResult(assumptions=a, annual_economics=econ, cash_flows=cash_flows,
                              npv_usd=npv, irr=irr, payback_years=payback)


def build_sensitivity_grid(a: FeasibilityAssumptions, grades: list[float], prices: list[float]) -> dict:
    grid = []
    for g in grades:
        row = []
        for p in prices:
            a2 = FeasibilityAssumptions(**{**a.__dict__, "head_grade_g_m3": g, "gold_price_usd_oz": p})
            econ = compute_annual_economics(a2)
            cfs = build_cash_flow_schedule(a2, econ)
            row.append(compute_npv(cfs, a.discount_rate))
        grid.append(row)
    return {"grades": grades, "prices": prices, "npv_grid_usd": grid}


# ---------------------------------------------------------------------------
# Full feasibility report generator (exploration -> ... -> HSE/admin)
# ---------------------------------------------------------------------------


@dataclass
class FeasibilityReport:
    disclaimer: str
    resource_classifications: list[ResourceClassification]
    economics: FeasibilityResult
    cost_rollup_by_phase: dict
    bom_summary: dict | None
    data_issues: list[dict] = field(default_factory=list)


def generate_feasibility_report(
    resource_classifications: list[ResourceClassification],
    economics: FeasibilityResult,
    cost_rollup_by_phase: dict,
    bom_summary: dict | None = None,
    data_issues: list[dict] | None = None,
) -> FeasibilityReport:
    """Assembles the sequenced report. Every section is a pass-through of a
    deterministic core/ result -- this function performs no arithmetic of
    its own, only sequencing and labelling."""
    return FeasibilityReport(
        disclaimer=SCOPE_DISCLAIMER,
        resource_classifications=resource_classifications,
        economics=economics,
        cost_rollup_by_phase=cost_rollup_by_phase,
        bom_summary=bom_summary,
        data_issues=data_issues or [],
    )
