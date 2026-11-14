"""
Exploration & Operations Cost Tracking / Expenditure Module (NEW).

Structural placeholder derived from Alluvial_Campaign_Control_Workbook_
Guyana.xlsx (Budget, Vouchers, Trommel_BOM, Compliance sheets -- its 100-800
cost-code ledger, phase-to-tranche map T0-T3, and voucher validation
workflow all reproduce exactly below), extended with the full exploration ->
mining -> plant -> camp -> HSE/admin category breakdown requested for a
medium-scale alluvial mine:

  EXPLORATION        (1xxx): mobilisation, coordination, lodging, field
                      logistics, personnel, jurisdictional permitting,
                      employee contracts/payroll, prospecting equipment,
                      mineral title acquisition & licensing
  MINING_OPERATIONS  (2xxx): haulage, excavation, access/earthworks,
                      stockpiling, fuelling, operational overheads
  PLANT_PROCESSING   (3xxx): sourcing/procurement, retaining wall, trommel
                      fabrication & welding, water pumps, piping, rotor
                      motors, fans, screens, hoppers, conveyors, sluice
                      boards, dump box, reservoir tank
  CAMP_DEVELOPMENT   (4xxx): prefab housing, offices, power plant, wiring &
                      electrification, Starlink/router, for ~140 employees
  HSE_ADMIN          (5xxx): health & safety, kitchen, HR, accounting
  CONTINGENCY        (9xxx)

No arithmetic belongs in an LLM prompt: every rollup here is deterministic
and traceable back to a cost code.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Literal

Phase = Literal["EXPLORATION", "MINING_OPERATIONS", "PLANT_PROCESSING", "CAMP_DEVELOPMENT", "HSE_ADMIN", "CONTINGENCY"]


@dataclass(frozen=True)
class CostCategory:
    code: str
    phase: Phase
    name: str
    default_unit: str = "US$"


COST_CODE_TAXONOMY: tuple[CostCategory, ...] = (
    # EXPLORATION
    CostCategory("1000", "EXPLORATION", "Mobilisation (personnel, equipment, freight to site)"),
    CostCategory("1010", "EXPLORATION", "Coordination (project management, scheduling, liaison)"),
    CostCategory("1020", "EXPLORATION", "Lodging and accommodation (field crew)"),
    CostCategory("1030", "EXPLORATION", "Field logistics (vehicles, fuel, transport of samples/supplies)"),
    CostCategory("1040", "EXPLORATION", "Personnel (geologists, technicians, field crew wages)"),
    CostCategory("1050", "EXPLORATION", "Jurisdictional permitting cost (licences, fees, Gazette notices)"),
    CostCategory("1060", "EXPLORATION", "Employee contractual agreements (salary/payroll contracts)"),
    CostCategory("1070", "EXPLORATION", "Equipment acquisition for prospecting (pitting, panning, survey gear)"),
    CostCategory("1080", "EXPLORATION", "Mineral title acquisition and licensing (claim/permit fees, legal)"),
    CostCategory("1090", "EXPLORATION", "Laboratory, assay and QAQC"),
    # MINING_OPERATIONS
    CostCategory("2000", "MINING_OPERATIONS", "Haulage (pit to stockpile/plant transport)"),
    CostCategory("2010", "MINING_OPERATIONS", "Excavation (pit digging, overburden removal)"),
    CostCategory("2020", "MINING_OPERATIONS", "Access creation and earthworks (roads, pads, drainage)"),
    CostCategory("2030", "MINING_OPERATIONS", "Stockpiling (pad construction, handling, reclaim)"),
    CostCategory("2040", "MINING_OPERATIONS", "Fuelling (diesel/petrol for mining fleet)"),
    CostCategory("2050", "MINING_OPERATIONS", "Mining operations overheads (supervision, consumables, hire)"),
    # PLANT_PROCESSING
    CostCategory("3000", "PLANT_PROCESSING", "Sourcing and procurement (plant components, freight)"),
    CostCategory("3010", "PLANT_PROCESSING", "Retaining wall construction"),
    CostCategory("3020", "PLANT_PROCESSING", "Trommel fabrication, metalwork and welding (drum, frame, liners)"),
    CostCategory("3030", "PLANT_PROCESSING", "Water pump installation"),
    CostCategory("3040", "PLANT_PROCESSING", "Piping"),
    CostCategory("3050", "PLANT_PROCESSING", "Trommel drive: rotor motors, gearboxes, couplings"),
    CostCategory("3060", "PLANT_PROCESSING", "Fans"),
    CostCategory("3070", "PLANT_PROCESSING", "Screens (trommel panels, grizzly, classification)"),
    CostCategory("3080", "PLANT_PROCESSING", "Hoppers (feed hopper, grizzly oversize)"),
    CostCategory("3090", "PLANT_PROCESSING", "Conveyor belts (feed, discharge/stacker)"),
    CostCategory("3100", "PLANT_PROCESSING", "Sluice boards"),
    CostCategory("3110", "PLANT_PROCESSING", "Dump box"),
    CostCategory("3120", "PLANT_PROCESSING", "Metallic reservoir tank (water storage)"),
    CostCategory("3130", "PLANT_PROCESSING", "Installation and commissioning (all plant components)"),
    # CAMP_DEVELOPMENT (~140 employees)
    CostCategory("4000", "CAMP_DEVELOPMENT", "Prefab housing (accommodation blocks)"),
    CostCategory("4010", "CAMP_DEVELOPMENT", "Offices (admin/site office buildings)"),
    CostCategory("4020", "CAMP_DEVELOPMENT", "Power plant (generators, fuel storage, switchgear)"),
    CostCategory("4030", "CAMP_DEVELOPMENT", "Wiring and electrification (camp-wide)"),
    CostCategory("4040", "CAMP_DEVELOPMENT", "Starlink and external router / connectivity infrastructure"),
    CostCategory("4050", "CAMP_DEVELOPMENT", "Water, sanitation and civil works (camp)"),
    # HSE_ADMIN
    CostCategory("5000", "HSE_ADMIN", "Health and safety (PPE, medical, emergency response)"),
    CostCategory("5010", "HSE_ADMIN", "Kitchen (catering, feeding, mess hall)"),
    CostCategory("5020", "HSE_ADMIN", "HR (recruitment, welfare, community relations)"),
    CostCategory("5030", "HSE_ADMIN", "Accounting (finance, audit, statutory filings)"),
    CostCategory("5040", "HSE_ADMIN", "Insurance"),
    CostCategory("5050", "HSE_ADMIN", "Taxes and statutory charges (non-recoverable)"),
    CostCategory("5060", "HSE_ADMIN", "Data, software and information security"),
    CostCategory("5070", "HSE_ADMIN", "Studies, reporting and project management"),
    CostCategory("5080", "HSE_ADMIN", "Environmental management and rehabilitation"),
    CostCategory("5090", "HSE_ADMIN", "Security and community relations"),
    # CONTINGENCY
    CostCategory("9000", "CONTINGENCY", "Contingency reserve"),
)

_CODE_INDEX = {c.code: c for c in COST_CODE_TAXONOMY}


def lookup_category(cost_code: str) -> CostCategory | None:
    return _CODE_INDEX.get(cost_code)


# ---------------------------------------------------------------------------
# Phase -> tranche map (Alluvial_Campaign_Control_Workbook_Guyana.xlsx!Budget)
# ---------------------------------------------------------------------------

CAMPAIGN_PHASES: tuple[tuple[str, str], ...] = (
    ("P0", "Mobilisation, legal and financing set-up"),
    ("P1", "Desk study, appraisal and tenure"),
    ("P2", "Scouting and ground-truthing"),
    ("P3", "Pits and bulk sampling"),
    ("P4", "Washing and grade determination"),
    ("P5", "Delineation and data compilation"),
    ("P6", "Feasibility and Gate C"),
    ("P7", "Plant build"),
    ("P8", "Operate and optimise"),
)

# (tranche, release condition, key looked up in `gates_passed`)
TRANCHE_RELEASE_CONDITIONS: tuple[tuple[str, str, str], ...] = (
    ("T0", "Budget baseline approved", "T0"),
    ("T1", "Gate A passed", "A"),
    ("T2", "Gate B passed", "B"),
    ("T3", "Gate C passed", "C"),
)


def evaluate_tranche_release(gates_passed: dict[str, bool]) -> list[dict]:
    """gates_passed keys: "T0" (baseline approved), "A", "B", "C". A tranche is
    released only when its own gate and every earlier one has passed."""
    out = []
    all_earlier_passed = True
    for tranche_id, condition, gate_key in TRANCHE_RELEASE_CONDITIONS:
        all_earlier_passed = all_earlier_passed and bool(gates_passed.get(gate_key, False))
        out.append({"tranche": tranche_id, "condition": condition, "released": all_earlier_passed})
    return out


# Alluvial_Campaign_Control_Workbook_Guyana.xlsx!Budget uses its own 100-800
# codes; this is the one place they are translated to this taxonomy.
LEGACY_CAMPAIGN_CODE_MAP: dict[str, str] = {
    "100": "1050",  # Legal, permits and registration
    "110": "5040",  # Insurance
    "120": "5050",  # Taxes and statutory (non-recoverable)
    "200": "1040",  # Technical personnel and field crew
    "210": "5090",  # Camp, welfare, security and community
    "300": "1000",  # Mobilisation and logistics
    "310": "1070",  # Field equipment and consumables
    "320": "2010",  # Excavation, haulage and hire
    "400": "1090",  # Laboratory, assay and QAQC
    "500": "5060",  # Data, software and security
    "600": "3020",  # Plant components and fabrication
    "610": "3010",  # Civil works
    "620": "3030",  # Power and water systems
    "700": "9000",  # Contingency
    "800": "5070",  # Studies, reporting and project management
}


def map_legacy_campaign_code(legacy_code: str) -> str | None:
    """None when the legacy code is unknown -- callers must flag it, not guess."""
    return LEGACY_CAMPAIGN_CODE_MAP.get(str(legacy_code).strip())


# ---------------------------------------------------------------------------
# Budget lines: BAC / EV / AC / variance / CPI (Budget sheet)
# ---------------------------------------------------------------------------


@dataclass
class BudgetLine:
    cost_code: str
    planned_bac_usd: float
    earned_value_usd: float = 0.0
    actual_validated_usd: float = 0.0
    vouchers_on_hold_usd: float = 0.0


@dataclass
class BudgetLineResult:
    cost_code: str
    category: str
    phase: Phase
    planned_bac_usd: float
    earned_value_usd: float
    actual_validated_usd: float
    variance_usd: float
    pct_consumed: float
    cost_performance_index: float | None
    vouchers_on_hold_usd: float


def evaluate_budget_line(line: BudgetLine) -> BudgetLineResult:
    cat = lookup_category(line.cost_code)
    variance = line.planned_bac_usd - line.actual_validated_usd
    pct_consumed = (line.actual_validated_usd / line.planned_bac_usd) if line.planned_bac_usd > 0 else 0.0
    cpi = (line.earned_value_usd / line.actual_validated_usd) if line.actual_validated_usd > 0 else None
    return BudgetLineResult(
        cost_code=line.cost_code, category=cat.name if cat else "UNKNOWN CODE",
        phase=cat.phase if cat else "CONTINGENCY",
        planned_bac_usd=line.planned_bac_usd, earned_value_usd=line.earned_value_usd,
        actual_validated_usd=line.actual_validated_usd, variance_usd=variance,
        pct_consumed=pct_consumed, cost_performance_index=cpi,
        vouchers_on_hold_usd=line.vouchers_on_hold_usd,
    )


def rollup_budget_by_phase(lines: list[BudgetLine]) -> dict[str, dict]:
    results = [evaluate_budget_line(l) for l in lines]
    phases: dict[str, dict] = {}
    for r in results:
        p = phases.setdefault(r.phase, {"planned_bac_usd": 0.0, "actual_validated_usd": 0.0,
                                         "earned_value_usd": 0.0, "vouchers_on_hold_usd": 0.0, "lines": []})
        p["planned_bac_usd"] += r.planned_bac_usd
        p["actual_validated_usd"] += r.actual_validated_usd
        p["earned_value_usd"] += r.earned_value_usd
        p["vouchers_on_hold_usd"] += r.vouchers_on_hold_usd
        p["lines"].append(r)
    for p in phases.values():
        p["variance_usd"] = p["planned_bac_usd"] - p["actual_validated_usd"]
        p["pct_consumed"] = (p["actual_validated_usd"] / p["planned_bac_usd"]) if p["planned_bac_usd"] > 0 else 0.0
    return phases


# ---------------------------------------------------------------------------
# Voucher validation workflow (Vouchers sheet)
# ---------------------------------------------------------------------------


@dataclass
class Voucher:
    voucher_id: str
    voucher_date: date | None
    cost_code: str
    payee: str
    description: str
    amount_usd: float
    has_invoice: bool
    has_contract_or_po: bool
    has_receipt_or_acceptance: bool
    has_tax_ref: bool
    approval_level_given: int  # 1, 2 or 3


APPROVAL_LEVEL_1_MAX_USD = 500.0
APPROVAL_LEVEL_2_MAX_USD = 5000.0


def required_approval_level(amount_usd: float) -> int:
    if amount_usd <= APPROVAL_LEVEL_1_MAX_USD:
        return 1
    if amount_usd <= APPROVAL_LEVEL_2_MAX_USD:
        return 2
    return 3


def validate_voucher(v: Voucher) -> dict:
    """A voucher counts as actual spend only when VALID: invoice, contract/PO,
    receipt/acceptance, tax ref, correct cost code, and sufficient approval."""
    code_valid = lookup_category(v.cost_code) is not None
    required_level = required_approval_level(v.amount_usd)
    approval_ok = v.approval_level_given >= required_level
    hold_reasons = []
    if not v.has_invoice:
        hold_reasons.append("No invoice.")
    if not v.has_contract_or_po:
        hold_reasons.append("No contract/PO.")
    if not v.has_receipt_or_acceptance:
        hold_reasons.append("No receipt or acceptance.")
    if not v.has_tax_ref:
        hold_reasons.append("No tax reference.")
    if not code_valid:
        hold_reasons.append(f"Unknown cost code {v.cost_code}.")
    if not approval_ok:
        hold_reasons.append(f"Approval level {v.approval_level_given} below required level {required_level}.")
    status = "VALID" if not hold_reasons else "HOLD"
    return {
        "voucher_id": v.voucher_id, "status": status, "code_valid": code_valid,
        "required_approval_level": required_level, "hold_reasons": hold_reasons,
    }


def summarize_vouchers(vouchers: list[Voucher]) -> dict:
    results = [validate_voucher(v) for v in vouchers]
    valid_total = sum(v.amount_usd for v, r in zip(vouchers, results) if r["status"] == "VALID")
    hold_total = sum(v.amount_usd for v, r in zip(vouchers, results) if r["status"] == "HOLD")
    return {
        "voucher_count": len(vouchers), "valid_total_usd": valid_total, "hold_total_usd": hold_total,
        "results": results,
    }


# ---------------------------------------------------------------------------
# Trommel / plant BOM costing (Trommel_BOM sheet)
# ---------------------------------------------------------------------------


@dataclass
class BOMLine:
    component_id: str
    assembly: str
    component: str
    cost_code: str
    qty: float
    unit: str
    unit_cost_usd: float | None  # None = not yet quoted
    criticality: Literal["A", "B", "C"] = "B"
    lead_time_wk: float = 0.0
    status: str = "To source"


@dataclass
class BOMLineResult:
    component_id: str
    line_cost_usd: float
    quoted: bool


def evaluate_bom_line(line: BOMLine) -> BOMLineResult:
    unit_cost = line.unit_cost_usd or 0.0
    return BOMLineResult(component_id=line.component_id, line_cost_usd=unit_cost * line.qty,
                          quoted=line.unit_cost_usd is not None)


def rollup_bom_total(lines: list[BOMLine]) -> dict:
    results = [evaluate_bom_line(l) for l in lines]
    total = sum(r.line_cost_usd for r in results)
    quoted_count = sum(1 for r in results if r.quoted)
    return {
        "total_usd": total, "quoted_count": quoted_count, "total_lines": len(lines),
        "fully_quoted": quoted_count == len(lines), "lines": results,
    }


DEFAULT_TROMMEL_BOM_ASSEMBLIES: tuple[str, ...] = (
    "Trommel", "Frame and structure", "Drive", "Recovery", "Water", "Power",
    "Civil", "Support", "Site", "Logistics", "Commissioning",
)


# ---------------------------------------------------------------------------
# Camp development costing (~140 employees) -- structured placeholder
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CampSizingAssumptions:
    headcount: int = 140
    m2_per_bed_prefab: float = 6.0       # placeholder floor area per bed
    beds_per_room: float = 4.0
    office_m2_per_admin_staff: float = 8.0
    admin_staff_fraction: float = 0.15   # of headcount
    power_kw_per_person: float = 0.6     # camp hotel load, excludes plant load
    generator_oversize_factor: float = 1.3


def estimate_camp_requirements(a: CampSizingAssumptions = CampSizingAssumptions()) -> dict:
    """Structured sizing placeholder -- NOT an engineering design. All figures
    must be replaced with a quoted BOQ before use in a feasibility decision
    (same discipline as the source workbook's 'ALL INPUTS ARE PLACEHOLDERS')."""
    housing_m2 = a.headcount * a.m2_per_bed_prefab
    rooms = -(-a.headcount // int(a.beds_per_room))  # ceil
    admin_staff = a.headcount * a.admin_staff_fraction
    office_m2 = admin_staff * a.office_m2_per_admin_staff
    camp_kw = a.headcount * a.power_kw_per_person
    generator_kw = camp_kw * a.generator_oversize_factor
    return {
        "headcount": a.headcount, "housing_m2": housing_m2, "prefab_rooms": rooms,
        "office_m2": office_m2, "camp_hotel_load_kw": camp_kw,
        "recommended_generator_kw": generator_kw,
        "note": "Placeholder sizing only; replace with a quoted BOQ before use in any feasibility decision.",
    }
