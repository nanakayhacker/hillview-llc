"""Golden fixture: Alluvial_Campaign_Control_Workbook_Guyana.xlsx!Feasibility (full 6-year DCF)."""
import pytest

from alluvial_mcp.core.feasibility import FeasibilityAssumptions, run_feasibility_model, classify_resource_prototype


def test_feasibility_dcf_matches_workbook_exactly():
    r = run_feasibility_model(FeasibilityAssumptions())
    e = r.annual_economics
    assert e.material_processed_m3_yr == pytest.approx(192984)
    assert e.recovered_gold_oz_yr == pytest.approx(930.68625717363)
    assert e.gross_revenue_usd_yr == pytest.approx(4188088.157281335)
    assert e.royalty_usd_yr == pytest.approx(209404.40786406677)
    assert e.operating_cost_usd_yr == pytest.approx(2715808)
    assert e.ebitda_usd_yr == pytest.approx(1262875.7494172682)
    assert e.operating_breakeven_grade_g_m3 == pytest.approx(0.1365179125080131)
    assert e.all_in_breakeven_grade_g_m3 == pytest.approx(0.15088614840387676)
    assert e.total_initial_capex_usd == pytest.approx(1715000.0000000002)

    assert r.npv_usd == pytest.approx(1894893.2578734749, rel=1e-6)
    assert r.irr == pytest.approx(0.4653556287901903, rel=1e-5)
    assert r.payback_years == 2

    year6 = r.cash_flows[6]
    assert year6.depreciation_usd == 0.0  # depreciation period is 5 years, project life is 6
    assert year6.tax_usd == pytest.approx(505150.2997669073)
    assert year6.free_cash_flow_usd == pytest.approx(757725.449650361)


def test_jorc_prototype_classification_is_explicitly_non_compliant():
    c = classify_resource_prototype("PRN094", z_credibility=0.67040657991777, qaqc_pass=True,
                                     class_vs_cutoff="ABOVE CUT-OFF")
    assert c.resource_category == "INDICATED"
    assert c.reserve_category == "PROBABLE"

    c_low = classify_resource_prototype("PRN093", z_credibility=0.554753626789433, qaqc_pass=True,
                                         class_vs_cutoff="BELOW CUT-OFF")
    assert c_low.resource_category == "INFERRED"
    assert c_low.reserve_category == "NOT CONVERTIBLE"
