"""
Single registry of known defects in the source workbooks.

Rule (docs/AMOP_MCP_SPEC.md §8.4 #2): defects are surfaced, never silently
corrected. Engines, MCP servers, the pipeline and the UI all read this one
list, so a finding is described the same way everywhere.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DataIssue:
    id: str
    workbook: str
    sheet: str
    location: str
    issue: str
    recommended_handling: str
    domain: str  # grade | geospatial | plant | finance | prospecting

    def as_finding(self, value_found=None, action_taken: str = "none (surfaced to user)") -> dict:
        return {
            "finding": "DATA_ISSUE", "id": self.id, "workbook": self.workbook, "sheet": self.sheet,
            "cell": self.location, "issue": self.issue, "value_found": value_found,
            "recommended_handling": self.recommended_handling, "action_taken": action_taken,
        }


DATA_ISSUES: tuple[DataIssue, ...] = (
    DataIssue("DATA-01", "Refined_Au_Grade_Model.xlsx", "QUALITATIVE PANNING LOG", "INT column, PRN093 rows 5-7",
              "INT does not equal To - From", "Use To - From", "grade"),
    DataIssue("DATA-02", "Refined_Au_Grade_Model.xlsx", "QUALITATIVE PANNING LOG", "PRN093 2.6-2.8 m",
              "Ore horizon was never panned", "Exclude from the composite; report as unpanned thickness", "grade"),
    DataIssue("DATA-03", "FINALGEOS / FINAL2GEOS / OPTIMISED ..._GEOSPATIAL.xlsx", "Energy_Consumption", "B16",
              "Energy cost rate entered as 12 $/kWh", "0.12 $/kWh is intended; report both figures", "plant"),
    DataIssue("DATA-04", "FINALGEOS / FINAL2GEOS ..._GEOSPATIAL.xlsx", "Energy_Reduction_Simulator", "B48:B50",
              "Peak 0.22 / off-peak 0.11 $/kWh contradict the single rate of 12", "Use 0.12 as the working rate", "plant"),
    DataIssue("DATA-05", "FINAL2GEOS_..._GEOSPATIAL.xlsx", "Daily_Blend_Plan", "F7:F11",
              "#REF! errors", "Route through the holistic blend plan", "plant"),
    DataIssue("DATA-06", "Cost_Grade_Heuristic_Prioritized_VAM_Cost_MATRIX.xlsx", "Pit Data", "PIT-05 grade",
              "0.9 here vs 0.6 in the plant workbooks", "Use 0.9 for the bounded heuristic; 0.6 for plant feed", "geospatial"),
    DataIssue("DATA-07", "Guyana_Outreach_Cost_Pipeline_Workbook.xlsx", "Fraud_Check", "V07-V12",
              "Verification steps pending by default", "Never auto-clear", "finance"),
    DataIssue("DATA-08", "Geospatial_Grade_Controlled_VAM_Stockpile_Optimizer.xlsx", "Final Heuristic Matrix", "Verification",
              "Unbounded heuristic values up to ~700", "Superseded by the bounded reformulation", "geospatial"),
    DataIssue("DATA-09", "Operational_Optimization_Template.xlsx", "Optimizer Recommendations", "Haulage Rate",
              "Fixed fleet specification presented as a lever", "Treat as FIXED", "plant"),
    DataIssue("DATA-10", "COMPREHENSIVE_FEEDING.xlsx", "CASH BOOK", "H52",
              "Running-balance formula references row 54", "Recompute H_n = H_{n-1} + F_n - G_n", "finance"),
    DataIssue("DATA-11", "Cost_Grade_Heuristic_Prioritized_VAM_Cost_MATRIX.xlsx", "Verification", "B4:E8",
              "Stale: disagrees with the workbook's own Heuristic Calculation sheet and with VAM_OPTIMISER_MACRO.xlsm",
              "Use Heuristic Calculation as the reference", "geospatial"),
    DataIssue("DATA-12", "10_SEPT_2025_SUMMARY_ALLUVIAL_PROJECT_REPORT.xlsx", "UPDATED SUMMARY", "Pit Grade (g/m3) column",
              "Summary grade disagrees with the grade derived from ASUNAFU SAMPLE DATA_LOGS1 for 26 of 145 pits; "
              "for 24 the summary value equals the log-derived grade of a pit 1-3 rows later (row misalignment, "
              "e.g. AS060-AS072), and AS073/AS075 show 0 against a positive log grade",
              "Show both values with a reconciliation flag; do not choose one silently", "prospecting"),
    DataIssue("DATA-13", "10_SEPT_2025_SUMMARY_ALLUVIAL_PROJECT_REPORT.xlsx", "ASUNAFU COLLAR DATA / SAMPLE DATA_LOGS1",
              "Landform, SAMPLE_Type, Grade Comment columns",
              "Spelling/case variants of one category ('Aluvial'/'Alluvial', 'saprock'/'Saprock', 'Nill'/'Nil', trailing spaces)",
              "Group on a normalised label; keep the raw value", "prospecting"),
    DataIssue("DATA-14", "KISMET_DAILY_GROSS_ALLUVIAL_REPORT_2025.xlsx", "DRILLING", "Pad_ID / Hole_ID / cumulative rows",
              "Pad spelled both 'ASUNAFU' and 'ASUNAFO'; hole IDs AS023-AS031 are logged twice; cumulative rows contain #DIV/0!",
              "Normalise the pad label for grouping; report duplicates; skip cumulative rows", "prospecting"),
)

_BY_ID = {i.id: i for i in DATA_ISSUES}


def get_issue(issue_id: str) -> DataIssue:
    return _BY_ID[issue_id]


def issues_for(domain: str | None = None, ids: list[str] | None = None) -> list[DataIssue]:
    out = list(DATA_ISSUES)
    if domain is not None:
        out = [i for i in out if i.domain == domain]
    if ids is not None:
        out = [i for i in out if i.id in ids]
    return out
