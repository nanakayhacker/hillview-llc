"""
Loads the real source workbooks (data/workbooks/) into the core/ dataclasses,
so the Streamlit UI and MCP tools run against real project data rather than
synthetic fixtures. Every loader is read-only and raises nothing on a
missing optional sheet -- callers get an empty list/None instead, so one
missing workbook never crashes the whole app.
"""
from __future__ import annotations

import warnings
from pathlib import Path

import openpyxl

from alluvial_mcp.core.grade import HorizonInput, PanEntryInput
from alluvial_mcp.core.finance import CashEntry
from alluvial_mcp.core.cost_tracking import BudgetLine, Voucher, BOMLine

WORKBOOKS_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "workbooks"


def _open(path: Path):
    warnings.filterwarnings("ignore")
    return openpyxl.load_workbook(path, data_only=True, keep_vba=path.suffix == ".xlsm")


def workbook_path(name: str) -> Path:
    return WORKBOOKS_DIR / name


def workbook_exists(name: str) -> bool:
    return workbook_path(name).exists()


# ---------------------------------------------------------------------------
# Refined_Au_Grade_Model.xlsx!QUALITATIVE PANNING LOG -> HorizonInput groups
# ---------------------------------------------------------------------------


def load_panning_log(filename: str = "Refined_Au_Grade_Model.xlsx") -> dict[str, list[HorizonInput]]:
    path = workbook_path(filename)
    if not path.exists():
        return {}
    wb = _open(path)
    ws = wb["QUALITATIVE PANNING LOG"]
    out: dict[str, list[HorizonInput]] = {}
    horizon_counter = 0
    for row in ws.iter_rows(min_row=3, values_only=True):
        pit_id, from_m, to_m, _int, material, _col, min_zone, p1, p2, p3, description = (row + (None,) * 11)[:11]
        if pit_id is None:
            continue
        horizon_counter += 1
        pans = [PanEntryInput(1, p1), PanEntryInput(2, p2), PanEntryInput(3, p3)]
        h = HorizonInput(
            horizon_id=str(horizon_counter), pit_id=pit_id, from_m=float(from_m), to_m=float(to_m),
            material=material or "", min_zone=min_zone or "ORE", description=description, pans=pans,
        )
        out.setdefault(pit_id, []).append(h)
    return out


# ---------------------------------------------------------------------------
# Cost_Grade_Heuristic_Prioritized_VAM_Cost_MATRIX.xlsx -> pit/distance/cost
# ---------------------------------------------------------------------------


def load_cost_grade_vam_workbook(filename: str = "Cost_Grade_Heuristic_Prioritized_VAM_Cost_MATRIX.xlsx") -> dict:
    path = workbook_path(filename)
    if not path.exists():
        return {}
    wb = _open(path)
    pit_ws = wb["Pit Data"]
    pit_ids, grades = [], []
    for row in pit_ws.iter_rows(min_row=4, max_row=8, values_only=True):
        pit_id, _material, _vol, grade = row[0], row[1], row[2], row[3]
        if pit_id:
            pit_ids.append(pit_id)
            grades.append(grade)

    dist_ws = wb["Distance Matrix"]
    stockpile_ids = [c.value for c in next(dist_ws.iter_rows(min_row=2, max_row=2))][1:]
    distance_matrix = [list(row)[1:] for row in dist_ws.iter_rows(min_row=3, max_row=7, values_only=True)]

    cost_ws = wb["Haul Cost Matrix"]
    cost_matrix = [list(row)[1:] for row in cost_ws.iter_rows(min_row=3, max_row=7, values_only=True)]

    return {
        "pit_ids": pit_ids, "grades": grades, "stockpile_ids": stockpile_ids,
        "distance_matrix": distance_matrix, "cost_matrix": cost_matrix,
    }


# ---------------------------------------------------------------------------
# COMPREHENSIVE_FEEDING.xlsx!CASH BOOK -> opening balance + entries
# ---------------------------------------------------------------------------


def load_cash_book(filename: str = "COMPREHENSIVE_FEEDING.xlsx", max_rows: int = 200) -> dict:
    path = workbook_path(filename)
    if not path.exists():
        return {"opening_balance": 0.0, "entries": []}
    wb = _open(path)
    ws = wb["CASH BOOK"]
    opening_balance = ws["F7"].value or 0.0
    entries: list[CashEntry] = []
    for row in ws.iter_rows(min_row=8, max_row=8 + max_rows, max_col=9, values_only=True):
        date_, desc, supplier, ref, proj, received, paid, _bal, typ = row
        if desc is None and proj is None:
            continue
        entries.append(CashEntry(
            date=date_, description=desc or "", supplier_customer=supplier, ref_no=ref,
            project_code=proj or "NA", cash_received=received or 0.0, cash_paid=paid or 0.0,
            category_code=typ or "NA",
        ))
    return {"opening_balance": opening_balance, "entries": entries}


# ---------------------------------------------------------------------------
# Alluvial_Campaign_Control_Workbook_Guyana.xlsx -> Budget / Vouchers / BOM
# ---------------------------------------------------------------------------


def load_campaign_budget(filename: str = "Alluvial_Campaign_Control_Workbook_Guyana.xlsx") -> list[BudgetLine]:
    path = workbook_path(filename)
    if not path.exists():
        return []
    wb = _open(path)
    ws = wb["Budget"]
    lines = []
    for row in ws.iter_rows(min_row=6, max_row=20, values_only=True):
        code = row[0]
        if not isinstance(code, (str, int)) or not str(code).isdigit():
            continue
        planned, earned, actual = row[2] or 0.0, row[3] or 0.0, row[4] or 0.0
        hold = row[8] or 0.0
        lines.append(BudgetLine(cost_code=_map_legacy_cost_code(str(code)), planned_bac_usd=planned,
                                 earned_value_usd=earned, actual_validated_usd=actual, vouchers_on_hold_usd=hold))
    return lines


_LEGACY_CODE_MAP = {
    "100": "1050", "110": "5000", "120": "5030", "200": "1040", "210": "4000",
    "300": "1000", "310": "1070", "320": "2000", "400": "5000", "500": "4040",
    "600": "3000", "610": "3010", "620": "3030", "700": "9000", "800": "1010",
}


def _map_legacy_cost_code(legacy_code: str) -> str:
    """Maps the source workbook's 100-800 codes onto this platform's extended taxonomy."""
    return _LEGACY_CODE_MAP.get(legacy_code, "9000")


def load_campaign_vouchers(filename: str = "Alluvial_Campaign_Control_Workbook_Guyana.xlsx") -> list[Voucher]:
    path = workbook_path(filename)
    if not path.exists():
        return []
    wb = _open(path)
    ws = wb["Vouchers"]
    vouchers = []
    for row in ws.iter_rows(min_row=8, max_row=207, max_col=12, values_only=True):
        voucher_id = row[0]
        if not voucher_id or not str(voucher_id).startswith("V-"):
            continue
        _date, legacy_code, payee, desc, amount, inv, po, receipt, tax, appr_given, _appr_req = row[1:12]
        vouchers.append(Voucher(
            voucher_id=voucher_id, voucher_date=None, cost_code=_map_legacy_cost_code(str(legacy_code)),
            payee=payee or "", description=desc or "", amount_usd=amount or 0.0,
            has_invoice=(inv == "Y"), has_contract_or_po=(po == "Y"),
            has_receipt_or_acceptance=(receipt == "Y"), has_tax_ref=(tax == "Y"),
            approval_level_given=int(appr_given) if appr_given else 1,
        ))
    return vouchers


_BOM_COMPONENT_ID_RE = __import__("re").compile(r"^[A-Z]\d{2}$")


def load_trommel_bom(filename: str = "Alluvial_Campaign_Control_Workbook_Guyana.xlsx") -> list[BOMLine]:
    """Trommel_BOM mixes the component list (IDs like 'B01') with unrelated
    reference tables further down the sheet (contract modules 'M1'-'M6',
    sign-off gates 'SG1'-'SG7', a bidder-scoring table) -- only rows whose ID
    matches one letter + two digits are real BOM line items."""
    path = workbook_path(filename)
    if not path.exists():
        return []
    wb = _open(path)
    ws = wb["Trommel_BOM"]
    lines = []
    for row in ws.iter_rows(min_row=6, max_row=66, max_col=15, values_only=True):
        comp_id = row[0]
        if not comp_id or not _BOM_COMPONENT_ID_RE.match(str(comp_id)):
            continue
        assembly, component, _spec, qty, unit, criticality, lead_time, _route, _module, _gate, _bench, unit_cost, _line_cost, status = row[1:15]
        lines.append(BOMLine(
            component_id=comp_id, assembly=assembly or "", component=component or "",
            cost_code="3000", qty=qty or 0, unit=unit or "ea", unit_cost_usd=unit_cost,
            criticality=criticality or "B", lead_time_wk=lead_time or 0, status=status or "To source",
        ))
    return lines
