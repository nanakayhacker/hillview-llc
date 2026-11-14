"""Golden fixtures: Alluvial_Campaign_Control_Workbook_Guyana.xlsx Vouchers sheet samples."""
from alluvial_mcp.core.cost_tracking import Voucher, validate_voucher, required_approval_level


def test_voucher_v003_held_for_missing_invoice():
    v = Voucher("V-003", None, "1050", "x", "Insurance sample", 3520, False, True, True, True, 2)
    result = validate_voucher(v)
    assert result["status"] == "HOLD"
    assert "No invoice." in result["hold_reasons"]


def test_voucher_v001_valid():
    v = Voucher("V-001", None, "1050", "x", "Legal sample", 3290, True, True, True, True, 3)
    result = validate_voucher(v)
    assert result["status"] == "VALID"
    assert result["hold_reasons"] == []


def test_approval_level_thresholds():
    assert required_approval_level(100) == 1
    assert required_approval_level(500) == 1
    assert required_approval_level(501) == 2
    assert required_approval_level(5000) == 2
    assert required_approval_level(5001) == 3


def test_unknown_cost_code_flagged():
    v = Voucher("V-999", None, "9999", "x", "bad code", 10, True, True, True, True, 1)
    result = validate_voucher(v)
    assert result["code_valid"] is False
    assert result["status"] == "HOLD"
