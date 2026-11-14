"""Golden fixtures: COMPREHENSIVE_FEEDING.xlsx cash book; Guyana_Outreach Fraud_Check/Stage_Costs."""
import pytest

from alluvial_mcp.core.finance import CashEntry, compute_running_balance, compute_risk_class, run_stage_cost_simulation


def test_cash_book_running_balance_matches_workbook():
    entries = [
        CashEntry(None, "TRAVEL & TRANSPORT", "x", "MPV100001", "ELIT", 0, 1101, "TT"),
        CashEntry(None, "TRAVEL & TRANSPORT", "x", "MPV100002", "ELIT", 0, 50, "TT"),
        CashEntry(None, "TRAVEL & TRANSPORT", "x", "MPV100003", "ELIT", 0, 170, "TT"),
    ]
    balances = [e["balance"] for e in compute_running_balance(52583.07149999976, entries)]
    assert balances == pytest.approx([51482.07149999976, 51432.07149999976, 51262.07149999976])


def test_fraud_check_risk_class_matches_workbook_p02_p03():
    p02 = compute_risk_class({"F03": True, "F15": True})
    assert p02["risk_score"] == pytest.approx(10.714285714285714)
    assert p02["risk_class"] == "RED"  # F15 is a hard stop
    assert p02["hard_stop_flags"] == ["F15"]

    p03 = compute_risk_class({"F13": True, "F14": True, "F16": True})
    assert p03["risk_score"] == pytest.approx(14.285714285714285)
    assert p03["hard_stop_count"] == 2


def test_fraud_check_p01_clean_prospect():
    from alluvial_mcp.core.finance import adjudicate_prospect_introduction
    verifications = {f"V{i:02d}": True for i in range(1, 11)}  # 10/12 = 0.8333 >= 0.75
    result = adjudicate_prospect_introduction({}, verifications)
    assert result["decision"] == "ALLOW"
    assert result["risk_class"] == "GREEN"


def test_stage_cost_simulation_matches_workbook_totals():
    sim = run_stage_cost_simulation("Base")
    assert sim["total_planned_cost_usd"] == pytest.approx(30715)
    assert sim["contingency_usd"] == pytest.approx(3071.5)
    assert sim["horizon_weeks"] == pytest.approx(35.5)
