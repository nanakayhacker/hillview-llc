"""Golden fixtures: FINALGEOS_VAM_..._GEOSPATIAL.xlsx Plant_Parameters/Recovery_Dashboard."""
import pytest

from alluvial_mcp.core.plant import (
    PlantParameters, evaluate_plant_efficiency, compute_recovered_oz, compute_gross_revenue,
    compute_daily_energy_cost, compute_net_revenue, total_connected_load_kw,
)


def test_plant_efficiency_matches_workbook():
    r = evaluate_plant_efficiency(PlantParameters())
    assert r.rpm_factor == pytest.approx(0.99)
    assert r.tilt_factor == pytest.approx(0.92)
    assert r.water_flow_factor == pytest.approx(1.0)
    assert r.overall_efficiency == pytest.approx(0.8379360000000001)
    assert r.effective_recovery == pytest.approx(0.7541424000000001)
    assert r.max_daily_capacity_m3 == pytest.approx(946)


def test_recovery_and_revenue_chain_matches_workbook():
    r = evaluate_plant_efficiency(PlantParameters())
    recovered_oz = compute_recovered_oz(492.9157894736842, r.effective_recovery)
    assert recovered_oz == pytest.approx(11.951346198067066)
    gross = compute_gross_revenue(recovered_oz, 4050)
    assert gross == pytest.approx(48402.952102171614)


def test_energy_cost_data_issue_flagged_not_silently_fixed():
    load = total_connected_load_kw()
    assert load == 184
    energy = compute_daily_energy_cost(load, 22, 12)
    assert energy["daily_kwh"] == 4048
    assert energy["daily_cost_as_entered_usd"] == pytest.approx(48576)
    assert energy["data_issue"]["id"] == "DATA-03"
    assert energy["data_issue"]["recommended_value"] == 0.12
    # as-entered figure must NOT be silently replaced
    assert energy["daily_cost_as_entered_usd"] != energy["daily_cost_corrected_usd"]


def test_net_revenue_matches_workbook():
    net = compute_net_revenue(48402.952102171614, 48576, 0)
    assert net["net_revenue_after_energy_usd"] == pytest.approx(-173.04789782838634)
