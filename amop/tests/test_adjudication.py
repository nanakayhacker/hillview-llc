from alluvial_mcp.core.adjudication import adjudicate_full_chain


def test_full_chain_fails_on_energy_budget():
    v = adjudicate_full_chain(
        pit_shares_and_z={"PIT-04": (0.284, 0.72)},
        stockpile_deficits={"ST-03": 0.0},
        compatibility={"ST-03": 1.0},
        daily_energy_cost_usd=48576, gross_revenue_usd=48402.95,
        runway_weeks=3.1, blend_target_m3=950,
    )
    assert v.verdict == "FAIL"
    assert any("Energy cost" in b for b in v.blocking_reasons)


def test_full_chain_passes_when_all_rules_clear():
    v = adjudicate_full_chain(
        pit_shares_and_z={"PIT-04": (0.284, 0.72)},
        stockpile_deficits={"ST-03": 0.0},
        compatibility={"ST-03": 1.0},
        daily_energy_cost_usd=5000, gross_revenue_usd=48402.95,
        runway_weeks=3.1, blend_target_m3=950,
    )
    assert v.verdict == "PASS"


def test_grade_credibility_cap_enforced():
    v = adjudicate_full_chain(
        pit_shares_and_z={"PIT-LOW-Z": (0.5, 0.3)},  # share 0.5 > 0.20 cap at Z<0.6
        stockpile_deficits={}, compatibility={},
        daily_energy_cost_usd=0, gross_revenue_usd=1, runway_weeks=10, blend_target_m3=100,
    )
    assert v.verdict == "FAIL"
