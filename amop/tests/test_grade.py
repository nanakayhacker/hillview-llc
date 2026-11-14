"""Golden fixtures: Refined_Au_Grade_Model.xlsx PRN093 / PRN094 (real field data)."""
import pytest

from alluvial_mcp.core.grade import HorizonInput, PanEntryInput, build_pit_composite


def _prn093():
    return [
        HorizonInput("1", "PRN093", 0, 1.3, "SOIL", "OVERBURDEN", None,
                     [PanEntryInput(1, "NIL"), PanEntryInput(2, "NIL"), PanEntryInput(3, "NIL")]),
        HorizonInput("2", "PRN093", 1.3, 1.8, "GRAVEL", "ORE", "traces",
                     [PanEntryInput(1, 0), PanEntryInput(2, 1), PanEntryInput(3, 1)]),
        HorizonInput("3", "PRN093", 1.8, 2.3, "GRAVEL", "ORE", "intermix of fine and submicroscopic grains",
                     [PanEntryInput(1, ">5"), PanEntryInput(2, 2), PanEntryInput(3, 8)]),
        HorizonInput("4", "PRN093", 2.3, 2.6, "GRAVEL", "ORE", "intermix of fine and submicroscopic grains",
                     [PanEntryInput(1, 7), PanEntryInput(2, 5), PanEntryInput(3, 2)]),
        HorizonInput("5", "PRN093", 2.6, 2.8, "SAPROLITE", "ORE", None,
                     [PanEntryInput(1, None), PanEntryInput(2, None), PanEntryInput(3, None)]),
    ]


def _prn094():
    return [
        HorizonInput("1", "PRN094", 0, 1.1, "SOIL", "OVERBURDEN", None,
                     [PanEntryInput(1, "NIL"), PanEntryInput(2, "NIL"), PanEntryInput(3, "NIL")]),
        HorizonInput("2", "PRN094", 1.1, 1.6, "GRAVEL", "ORE", "intermix of medium and submicroscopic grains",
                     [PanEntryInput(1, 1), PanEntryInput(2, 2), PanEntryInput(3, ">5")]),
        HorizonInput("3", "PRN094", 1.6, 2.1, "GRAVEL", "ORE", "fine - submicroscpoic grains",
                     [PanEntryInput(1, ">10"), PanEntryInput(2, 5), PanEntryInput(3, 10)]),
        HorizonInput("4", "PRN094", 2.1, 2.3, "SAPROLITE", "ORE", "fine - submicroscpoic grains",
                     [PanEntryInput(1, 6), PanEntryInput(2, 3), PanEntryInput(3, 0)]),
    ]


def test_prn093_composite_matches_workbook():
    c = build_pit_composite("PRN093", _prn093())
    assert c.grade_g_m3 == pytest.approx(0.0198096671985811, rel=1e-9)
    assert c.z_credibility == pytest.approx(0.554753626789433, rel=1e-6)
    assert c.ci_lower_90 == pytest.approx(0.00756705937194999, rel=1e-6)
    assert c.ci_upper_90 == pytest.approx(0.0320522750252122, rel=1e-6)
    assert c.panned_ore_thickness_m == pytest.approx(1.3)
    assert c.total_ore_thickness_m == pytest.approx(1.5)
    assert c.class_vs_cutoff == "BELOW CUT-OFF"
    assert c.sum_n_eff == pytest.approx(8.09127502358025, rel=1e-6)


def test_prn094_composite_matches_workbook():
    c = build_pit_composite("PRN094", _prn094())
    assert c.grade_g_m3 == pytest.approx(0.0342176113849711, rel=1e-9)
    assert c.z_credibility == pytest.approx(0.67040657991777, rel=1e-6)
    assert c.ci_lower_90 == pytest.approx(0.0142825578212782, rel=1e-6)
    assert c.ci_upper_90 == pytest.approx(0.054152664948664, rel=1e-6)
    assert c.sum_n_eff == pytest.approx(11.0989544448884, rel=1e-6)


def test_dash_range_description_parsing():
    """'fine - submicroscopic grains' (dash) = classes {3,4,5}; the literal
    typo 'submicroscpoic' must still resolve via the 'submicro' keyword."""
    from alluvial_mcp.core.grade import detect_present_classes
    assert detect_present_classes("fine - submicroscpoic grains") == {3, 4, 5}
    assert detect_present_classes("coarse - fine") == {1, 2, 3}
    assert detect_present_classes("intermix of fine and submicroscopic grains") == {3, 5}
    assert detect_present_classes("intermix of medium and submicroscopic grains") == {2, 5}


def test_below_detection_grade_is_zero():
    from alluvial_mcp.core.grade import compute_horizon_grade
    h = HorizonInput("x", "PX", 0, 0.5, "GRAVEL", "ORE", "traces",
                      [PanEntryInput(1, 0), PanEntryInput(2, 1), PanEntryInput(3, 1)])
    r = compute_horizon_grade(h)
    assert r.gold_mass_w_g == 0.0
    assert r.below_detection is True
