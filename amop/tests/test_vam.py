"""
Golden fixtures:
  - Cost_Grade_Heuristic_Prioritized_VAM_Cost_MATRIX.xlsx!Heuristic Calculation
    (NOT the workbook's own !Verification sheet, which is stale -- see
    README.md "Engineering corrections" / DATA-11).
  - VAM_OPTIMISER_MACRO.xlsm ALLOCATION + SUMMARY (independent solver,
    same cost matrix, cross-validates the heuristic AND the VAM algorithm).
"""
import pytest

from alluvial_mcp.core.vam import HeuristicParameters, build_heuristic_matrix, solve_vam

GRADES = [0.3, 0.15, 0.3, 0.2, 0.9]
DISTANCE = [
    [1732.7, 1633.4, 1599.2, 63.7],
    [34.1, 139.4, 166.4, 1748.9],
    [22.8, 141.8, 163.5, 1741.2],
    [45.7, 165.1, 185.8, 1760.5],
    [53.3, 171.1, 187.8, 1755.2],
]
COST = [
    [4, 34, 79.9576137712976, 68],
    [67.12, 42.4, 61, 87.44651222318704],
    [45.83, 54, 65, 87.05805534239781],
    [86.23, 60.88, 30.45, 88.02400240843403],
    [56.78, 212, 100, 87.76185105158163],
]
EXPECTED_H_FROM_HEURISTIC_CALC = [
    [5.307736279756766, 46.30013162107885, 115.3209576312102, 72.47610000250847],
    [75.40271077178352, 46.58258131954558, 69.7385031473042, 138.5444190109793],
    [46.46133762820513, 57.07150433154347, 70.39686319080778, 129.59616287246286],
    [98.51232134696095, 68.20296922127638, 32.40766789186459, 137.07152242297113],
    [44.36735718579156, 217.42779536168496, 86.69474681386978, 98.28408973414727],
]


def test_bounded_heuristic_matrix_matches_workbook():
    out = build_heuristic_matrix(COST, GRADES, DISTANCE, HeuristicParameters())
    h = out["H"]
    for i in range(5):
        for j in range(4):
            assert h[i][j] == pytest.approx(EXPECTED_H_FROM_HEURISTIC_CALC[i][j], rel=1e-9)


def test_vam_solver_matches_independent_macro_workbook():
    supply = [450, 300, 200, 1200, 300]
    demand = [800, 400, 600, 800]
    src_ids = ["PIT-01", "PIT-02", "PIT-03", "PIT-04", "PIT-05"]
    dst_ids = ["STK-A", "STK-B", "STK-C", "STK-D"]

    res = solve_vam(EXPECTED_H_FROM_HEURISTIC_CALC, supply, demand, src_ids, dst_ids)

    expected_allocation = {
        "PIT-01": [0, 0, 0, 450],
        "PIT-02": [300, 0, 0, 0],
        "PIT-03": [200, 0, 0, 0],
        "PIT-04": [0, 400, 600, 200],
        "PIT-05": [300, 0, 0, 0],
    }
    for i, pit_id in enumerate(src_ids):
        assert res.allocation[i] == pytest.approx(expected_allocation[pit_id])

    assert res.total_cost == pytest.approx(151977.6258222659, rel=1e-9)
    assert "DUMMY-PIT" in res.balance_note
