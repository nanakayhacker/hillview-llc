"""Shared Streamlit helpers: data access with caching, verdict badges, DATA_ISSUE banners."""
from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from alluvial_mcp.core import workbook_loader as wl  # noqa: E402
from alluvial_mcp.core.grade import build_pit_composite  # noqa: E402

DATA_ISSUES_REGISTRY = [
    {"id": "DATA-01", "workbook": "Refined_Au_Grade_Model.xlsx", "sheet": "QUALITATIVE PANNING LOG",
     "cell": "INT column, PRN093 rows 5-7", "issue": "INT != To - From", "correct_value": "Use To - From"},
    {"id": "DATA-02", "workbook": "Refined_Au_Grade_Model.xlsx", "sheet": "QUALITATIVE PANNING LOG",
     "cell": "PRN093 2.6-2.8 m", "issue": "Not panned", "correct_value": "Exclude; flag NOT PANNED"},
    {"id": "DATA-03", "workbook": "FINALGEOS/FINAL2GEOS", "sheet": "Energy_Consumption", "cell": "B16",
     "issue": "Energy cost rate = 12", "correct_value": "Should be 0.12"},
    {"id": "DATA-06", "workbook": "Cost_Grade_Heuristic_Prioritized_VAM_Cost_MATRIX.xlsx", "sheet": "Pit Data",
     "cell": "PIT-05 grade", "issue": "0.9 (bounded) vs 0.6 (original)", "correct_value": "Use 0.9 (bounded)"},
    {"id": "DATA-11", "workbook": "Cost_Grade_Heuristic_Prioritized_VAM_Cost_MATRIX.xlsx", "sheet": "Verification",
     "issue": "Stale: does not match the workbook's own Heuristic Calculation sheet, nor the "
              "independent VAM_OPTIMISER_MACRO.xlsm which cross-validates Heuristic Calculation exactly",
     "correct_value": "Use Heuristic Calculation, not Verification (see README)"},
]


def verdict_badge(verdict: str) -> None:
    if verdict == "PASS":
        st.success(f"Verdict: {verdict}")
    elif verdict == "CONDITIONAL":
        st.warning(f"Verdict: {verdict}")
    else:
        st.error(f"Verdict: {verdict}")


def data_issue_banner(relevant_ids: list[str] | None = None) -> None:
    issues = DATA_ISSUES_REGISTRY if relevant_ids is None else [i for i in DATA_ISSUES_REGISTRY if i["id"] in relevant_ids]
    if not issues:
        return
    with st.expander(f"⚠️ {len(issues)} known DATA_ISSUE finding(s) in the source workbooks", expanded=False):
        for i in issues:
            st.markdown(f"**{i['id']}** -- `{i['workbook']}` / `{i['sheet']}`: {i['issue']}. *{i['correct_value']}*")


@st.cache_data
def get_panning_log():
    return wl.load_panning_log()


@st.cache_data
def get_pit_composites():
    log = wl.load_panning_log()
    return {pit_id: build_pit_composite(pit_id, horizons) for pit_id, horizons in log.items()}


@st.cache_data
def get_cost_grade_vam():
    return wl.load_cost_grade_vam_workbook()


@st.cache_data
def get_cash_book():
    return wl.load_cash_book()


@st.cache_data
def get_campaign_budget():
    return wl.load_campaign_budget()


@st.cache_data
def get_campaign_vouchers():
    return wl.load_campaign_vouchers()


@st.cache_data
def get_trommel_bom():
    return wl.load_trommel_bom()


def explain_this(label: str, tool: str, formula_citation: str, inputs: dict) -> None:
    with st.expander(f"Explain: {label}"):
        st.caption(f"Computed by `{tool}` -- {formula_citation}")
        st.json(inputs)
