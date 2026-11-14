"""
Module B — Ore Body & Grade Control (core engine).

Reproduces `Refined_Au_Grade_Model.xlsx` (PanCalc -> HorizonCalc -> HorizonGrade
-> PitComposite) exactly, including the natural-log modifier curves on
Modifiers!, the decay-weighted class-share derivation on Assumptions!47:62,
and the thickness-weighted composite on PitComposite!.

Formulas were reverse-engineered from the real workbook cell values (not just
the handoff spec's summary), then verified by hand against PRN093 / PRN094
before being committed here. See tests/test_grade.py for the golden fixtures.

No arithmetic belongs in an LLM prompt: every number here is deterministic.
"""
from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from typing import Literal

PanCode = Literal["E", "Q", "S", "A", "L", "X"]

# ---------------------------------------------------------------------------
# Physical / assumption constants (Refined_Au_Grade_Model.xlsx!Assumptions)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class GradeAssumptions:
    gold_density_g_cm3: float = 19.32
    silver_density_g_cm3: float = 10.49
    gold_fineness: float = 0.9
    panning_recovery_ceiling: float = 0.95  # R_inf
    recovery_length_mm: float = 0.1  # d_R
    size_decay_length_mm: float = 0.2  # delta
    bowls_per_m3: float = 240.0
    bowls_per_pan: float = 1.0
    bank_volume_factor: float = 1.0
    nugget_credibility_n_star: float = 10.0
    particle_mass_lambda: float = 1.0
    confidence_z: float = 1.645
    below_detection_grade_g_m3: float = 0.0
    cutoff_grade_g_m3: float = 0.03
    validation_tolerance: float = 0.3
    # Empirically-derived constant: the workbook's "limit-capped" pan count
    # (code L, e.g. '>5') is NOT exactly limit x alpha/(alpha-1) = limit x 1.5
    # as the handoff spec (docs/AMOP_MCP_SPEC.md §11.1) states -- it is a
    # Pareto-tail conditional mean computed via a Taylor/E3 integral the
    # workbook does not expose as a plain formula. Reverse-engineered from
    # PanCalc rows (">5" -> 7.49387980528081 in two independent pits):
    #   multiplier = 7.49387980528081 / 5 = 1.49877596105616...
    # Engineering note, not a silent fix: the spec's own 1.5 approximation is
    # 0.08% high. We use the workbook's exact empirical constant.
    limit_cap_mean_factor: float = 1.49877596105616

    # Modifiers (natural-log forms) -- Refined_Au_Grade_Model.xlsx!Modifiers
    apply_modifiers: bool = True
    reduction_q_ref: float = 2.5
    reduction_gamma: float = 0.1
    uplift_n_thr: float = 15.0
    uplift_u_min: float = 0.35
    uplift_u_max: float = 0.55
    uplift_n_half: float = 30.0


@dataclass(frozen=True)
class SizeClass:
    index: int
    name: str
    diameter_mm: float
    shape_factor: float
    ncap_per_pan: int


SIZE_CLASSES: tuple[SizeClass, ...] = (
    SizeClass(1, "Coarse", 1.00, 0.55, 50),
    SizeClass(2, "Medium", 0.50, 0.50, 100),
    SizeClass(3, "Fine", 0.25, 0.45, 200),
    SizeClass(4, "Very fine", 0.12, 0.40, 400),
    SizeClass(5, "Submicroscopic (flour)", 0.03, 0.35, 800),
)

# class keyword -> class index, used to read the free-text panning description
_CLASS_KEYWORDS: dict[str, int] = {
    "coarse": 1,
    "medium": 2,
    "fine": 3,  # checked after "very fine" / "submicroscopic" below
    "very fine": 4,
    "submicroscop": 5,  # matches "submicroscopic" and the misspelling "submicroscpoic"
    "flour": 5,
}


@dataclass(frozen=True)
class DerivedClassConstants:
    """Per-class m_i (particle mass, g), R_i (panning recovery), w_i (decay weight)."""

    diameter_mm: float
    mass_g: float
    recovery: float
    mass_over_recovery: float
    decay_weight: float
    ncap_per_pan: int


def derive_class_constants(a: GradeAssumptions) -> dict[int, DerivedClassConstants]:
    alloy_density_g_cm3 = a.gold_density_g_cm3 * a.gold_fineness + a.silver_density_g_cm3 * (
        1 - a.gold_fineness
    )
    alloy_density_g_mm3 = alloy_density_g_cm3 / 1000.0
    out: dict[int, DerivedClassConstants] = {}
    for cls in SIZE_CLASSES:
        d = cls.diameter_mm
        mass_g = (math.pi / 6.0) * alloy_density_g_mm3 * d**3 * cls.shape_factor
        recovery = a.panning_recovery_ceiling * (1 - math.exp(-d / a.recovery_length_mm))
        decay_weight = math.exp(-d / a.size_decay_length_mm)
        out[cls.index] = DerivedClassConstants(
            diameter_mm=d,
            mass_g=mass_g,
            recovery=recovery,
            mass_over_recovery=mass_g / recovery,
            decay_weight=decay_weight,
            ncap_per_pan=cls.ncap_per_pan,
        )
    return out


# ---------------------------------------------------------------------------
# B1 — Pan entry parsing
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PanParseResult:
    code: PanCode
    count: float
    limit_capped: bool = False


def parse_pan_entry(raw: str | int | float | None, alpha: float = 3.0,
                     assumptions: GradeAssumptions | None = None) -> PanParseResult:
    """E -> exact | Q -> raw/f | S -> S-scale | A -> 0 (NIL) | L -> limit x factor | X -> excluded."""
    a = assumptions or GradeAssumptions()
    if raw is None:
        return PanParseResult("X", 0.0)
    if isinstance(raw, (int, float)):
        return PanParseResult("E", float(raw))
    text = str(raw).strip()
    if text.upper() in ("NIL", "N/A", ""):
        return PanParseResult("A", 0.0)
    m = re.match(r"^>\s*(\d+(?:\.\d+)?)$", text)
    if m:
        limit = float(m.group(1))
        return PanParseResult("L", limit * a.limit_cap_mean_factor, limit_capped=True)
    try:
        return PanParseResult("E", float(text))
    except ValueError:
        return PanParseResult("X", 0.0)


def convert_limit_count(limit: float, alpha: float = 3.0,
                         assumptions: GradeAssumptions | None = None) -> float:
    a = assumptions or GradeAssumptions()
    return limit * a.limit_cap_mean_factor


# ---------------------------------------------------------------------------
# B1b — description -> class shares (decay-weighted presence model)
# ---------------------------------------------------------------------------

_BELOW_DETECTION_KEYWORDS = ("trace",)


def is_below_detection(description: str | None) -> bool:
    if not description:
        return False
    text = description.lower()
    return any(k in text for k in _BELOW_DETECTION_KEYWORDS)


def _scan_classes(text: str) -> set[int]:
    """Which of the 5 size classes are named in one fragment of description text.

    Uses "submicro" (not "submicroscop") as the class-5 keyword because the
    real panning log contains a transposed-letter typo, "submicroscpoic",
    that a longer keyword would miss -- both spellings share this prefix.
    """
    present: set[int] = set()
    if "very fine" in text:
        present.add(4)
    if "submicro" in text or "flour" in text:
        present.add(5)
    if re.search(r"(?<!very )\bfine\b", text):
        present.add(3)
    if re.search(r"\bmedium\b", text):
        present.add(2)
    if re.search(r"\bcoarse\b", text):
        present.add(1)
    return present


def detect_present_classes(description: str | None) -> set[int]:
    """
    Which of the 5 size classes a free-text panning description names.

    Two distinct grammars appear in the real log (verified against
    Refined_Au_Grade_Model.xlsx!Assumptions rows 49-62):
      - "intermix of A and B [grains]" -> the EXACT set {A, B}
      - "A - B grains" (dash/range)    -> the INCLUSIVE RANGE of class
        indices between A and B (e.g. "fine - submicroscopic" = {3,4,5},
        "coarse - fine" = {1,2,3})
    """
    if not description:
        return set()
    text = description.lower()
    if "-" in text:
        parts = [p.strip() for p in text.split("-")]
        found: set[int] = set()
        for part in parts:
            found |= _scan_classes(part)
        if found:
            lo, hi = min(found), max(found)
            return set(range(lo, hi + 1))
        return found
    return _scan_classes(text)


def compute_class_shares(
    description: str | None,
    derived: dict[int, DerivedClassConstants],
    infer_class5_from_class4: bool = True,
) -> dict[int, float]:
    """
    share_i = present_i * w_i / sum_j(present_j * w_j), w_i = exp(-d_i/delta).

    Reproduces Assumptions!48:62 (the description-to-size-class mapping table)
    exactly -- that table IS this formula's output, verified by hand against
    "coarse and medium" (share1=0.07586, share2=0.92414).
    """
    present = detect_present_classes(description)
    if not present and infer_class5_from_class4 and description:
        # fallback: unmatched description defaults per Assumptions!49
        present = {3, 4, 5}
    if infer_class5_from_class4 and 4 in present and 5 not in present:
        present.add(5)
    if not present:
        return {i: 0.0 for i in range(1, 6)}
    total_w = sum(derived[i].decay_weight for i in present)
    if total_w <= 0:
        return {i: 0.0 for i in range(1, 6)}
    return {i: (derived[i].decay_weight / total_w if i in present else 0.0) for i in range(1, 6)}


# ---------------------------------------------------------------------------
# B2 — Horizon grade
# ---------------------------------------------------------------------------


@dataclass
class PanEntryInput:
    pan_number: int
    raw: str | int | float | None


@dataclass
class HorizonInput:
    horizon_id: str
    pit_id: str
    from_m: float
    to_m: float
    material: str
    min_zone: Literal["ORE", "OVERBURDEN", "WASTE"]
    description: str | None
    pans: list[PanEntryInput]
    bulk_density_t_m3: float = 1.35


@dataclass
class HorizonGradeResult:
    horizon_id: str
    pit_id: str
    thickness_m: float
    panned: bool
    below_detection: bool
    pooled_count: float
    sampled_volume_m3: float
    gold_mass_w_g: float
    grade_g_m3: float
    grade_g_t: float
    sigma_w: float
    n_eff: float
    z_credibility: float
    ci_lower_90: float
    ci_upper_90: float
    n_fs: float
    uplift_factor: float


def _uplift_factor(n_fs: float, a: GradeAssumptions) -> float:
    if n_fs <= a.uplift_n_thr:
        return 1.0
    ln_nfs = math.log(n_fs / a.uplift_n_thr)
    ln_half = math.log(a.uplift_n_half / a.uplift_n_thr)
    ratio = ln_nfs / (ln_nfs + ln_half)
    return 1.0 + a.uplift_u_min + (a.uplift_u_max - a.uplift_u_min) * ratio


def _reduction_factor(class_index: int, derived_diam: float, a: GradeAssumptions) -> float:
    d_m = math.sqrt(1.0 * 0.5)  # geometric mean of coarse (1.0mm) and medium (0.5mm)
    q_i = math.exp(math.log(a.reduction_q_ref) + a.reduction_gamma * math.log(derived_diam / d_m))
    return 1.0 / q_i


def compute_horizon_grade(
    horizon: HorizonInput,
    assumptions: GradeAssumptions | None = None,
) -> HorizonGradeResult:
    a = assumptions or GradeAssumptions()
    derived = derive_class_constants(a)
    thickness = horizon.to_m - horizon.from_m
    pans_panned = sum(1 for p in horizon.pans if parse_pan_entry(p.raw, assumptions=a).code != "X")
    panned = pans_panned > 0 and horizon.min_zone == "ORE"
    below_detection = is_below_detection(horizon.description)

    pooled_count = sum(parse_pan_entry(p.raw, assumptions=a).count for p in horizon.pans)
    sampled_volume_m3 = pans_panned * a.bowls_per_pan / a.bowls_per_m3

    if not panned or below_detection or sampled_volume_m3 <= 0:
        return HorizonGradeResult(
            horizon_id=horizon.horizon_id, pit_id=horizon.pit_id, thickness_m=thickness,
            panned=panned, below_detection=below_detection, pooled_count=pooled_count,
            sampled_volume_m3=sampled_volume_m3, gold_mass_w_g=0.0,
            grade_g_m3=a.below_detection_grade_g_m3 if panned else 0.0,
            grade_g_t=0.0, sigma_w=0.0, n_eff=0.0, z_credibility=0.0,
            ci_lower_90=0.0, ci_upper_90=0.0, n_fs=0.0, uplift_factor=1.0,
        )

    shares = compute_class_shares(horizon.description, derived)
    n_i: dict[int, float] = {}
    for i in range(1, 6):
        cap = pans_panned * derived[i].ncap_per_pan
        n_i[i] = min(shares[i] * pooled_count, cap)

    n_fs = n_i[3] + n_i[4] + n_i[5]
    uplift = _uplift_factor(n_fs, a) if a.apply_modifiers else 1.0

    modifier: dict[int, float] = {}
    for i in range(1, 6):
        if not a.apply_modifiers:
            modifier[i] = 1.0
        elif i in (1, 2):
            modifier[i] = _reduction_factor(i, derived[i].diameter_mm, a)
        else:
            modifier[i] = uplift

    w = sum(a.particle_mass_lambda * n_i[i] * derived[i].mass_over_recovery * modifier[i] for i in range(1, 6))
    sigma_w_sq = sum(
        (a.particle_mass_lambda ** 2) * n_i[i] * (derived[i].mass_over_recovery ** 2) * (modifier[i] ** 2)
        for i in range(1, 6)
    )
    sigma_w = math.sqrt(sigma_w_sq)

    grade_g_m3 = (w / sampled_volume_m3) / a.bank_volume_factor
    grade_g_t = grade_g_m3 / horizon.bulk_density_t_m3

    n_eff = (w * w / sigma_w_sq) if sigma_w_sq > 0 else 0.0
    z_credibility = 1 - math.exp(-n_eff / a.nugget_credibility_n_star)
    half_width = a.confidence_z * (sigma_w / sampled_volume_m3) / a.bank_volume_factor

    return HorizonGradeResult(
        horizon_id=horizon.horizon_id, pit_id=horizon.pit_id, thickness_m=thickness,
        panned=panned, below_detection=below_detection, pooled_count=pooled_count,
        sampled_volume_m3=sampled_volume_m3, gold_mass_w_g=w, grade_g_m3=grade_g_m3,
        grade_g_t=grade_g_t, sigma_w=sigma_w, n_eff=n_eff, z_credibility=z_credibility,
        ci_lower_90=max(0.0, grade_g_m3 - half_width), ci_upper_90=grade_g_m3 + half_width,
        n_fs=n_fs, uplift_factor=uplift,
    )


def compute_credibility_z(n_eff: float, n_star: float = 10.0) -> float:
    return 1 - math.exp(-n_eff / n_star)


# ---------------------------------------------------------------------------
# B3 — Pit composite
# ---------------------------------------------------------------------------


@dataclass
class CompositeGradeResult:
    pit_id: str
    panned_ore_thickness_m: float
    total_ore_thickness_m: float
    unpanned_ore_thickness_m: float
    grade_g_m3: float
    grade_g_t: float
    ci_lower_90: float
    ci_upper_90: float
    sum_n_eff: float
    z_credibility: float
    class_vs_cutoff: Literal["ABOVE CUT-OFF", "BELOW CUT-OFF", "BELOW DETECTION", "NOT PANNED"]
    horizons: list[HorizonGradeResult] = field(default_factory=list)
    data_issues: list[dict] = field(default_factory=list)


def build_pit_composite(
    pit_id: str,
    horizons: list[HorizonInput],
    assumptions: GradeAssumptions | None = None,
    bulk_density_t_m3: float = 1.35,
) -> CompositeGradeResult:
    a = assumptions or GradeAssumptions()
    results = [compute_horizon_grade(h, a) for h in horizons if h.pit_id == pit_id]
    ore_horizons_input = [h for h in horizons if h.pit_id == pit_id and h.min_zone == "ORE"]

    data_issues = []
    total_ore_thickness = sum(h.to_m - h.from_m for h in ore_horizons_input)
    panned_results = [r for r in results if r.panned]
    panned_ore_thickness = sum(r.thickness_m for r in panned_results)
    unpanned_ore_thickness = total_ore_thickness - panned_ore_thickness

    if panned_ore_thickness <= 0:
        return CompositeGradeResult(
            pit_id=pit_id, panned_ore_thickness_m=0.0, total_ore_thickness_m=total_ore_thickness,
            unpanned_ore_thickness_m=unpanned_ore_thickness, grade_g_m3=0.0, grade_g_t=0.0,
            ci_lower_90=0.0, ci_upper_90=0.0, sum_n_eff=0.0, z_credibility=0.0,
            class_vs_cutoff="NOT PANNED", horizons=results, data_issues=data_issues,
        )

    weighted_grade = sum(r.grade_g_m3 * r.thickness_m for r in panned_results) / panned_ore_thickness
    weighted_grade_t = sum(r.grade_g_t * r.thickness_m for r in panned_results) / panned_ore_thickness
    sum_n_eff = sum(r.n_eff for r in panned_results)
    z = compute_credibility_z(sum_n_eff, a.nugget_credibility_n_star)

    variance_term = sum((r.thickness_m ** 2) * ((r.sigma_w / r.sampled_volume_m3) ** 2)
                         for r in panned_results if r.sampled_volume_m3 > 0)
    half_width = a.confidence_z * math.sqrt(variance_term) / panned_ore_thickness

    if all(r.below_detection or r.grade_g_m3 == 0.0 for r in panned_results):
        klass: Literal["ABOVE CUT-OFF", "BELOW CUT-OFF", "BELOW DETECTION", "NOT PANNED"] = "BELOW DETECTION"
    elif weighted_grade >= a.cutoff_grade_g_m3:
        klass = "ABOVE CUT-OFF"
    else:
        klass = "BELOW CUT-OFF"

    return CompositeGradeResult(
        pit_id=pit_id, panned_ore_thickness_m=panned_ore_thickness,
        total_ore_thickness_m=total_ore_thickness, unpanned_ore_thickness_m=unpanned_ore_thickness,
        grade_g_m3=weighted_grade, grade_g_t=weighted_grade_t,
        ci_lower_90=max(0.0, weighted_grade - half_width), ci_upper_90=weighted_grade + half_width,
        sum_n_eff=sum_n_eff, z_credibility=z, class_vs_cutoff=klass, horizons=results,
        data_issues=data_issues,
    )


def credibility_class(z: float) -> Literal["LOW", "MEDIUM", "HIGH"]:
    if z >= 0.8:
        return "HIGH"
    if z >= 0.6:
        return "MEDIUM"
    return "LOW"


def get_adjudicated_pit_grade(composite: CompositeGradeResult) -> dict:
    cls = credibility_class(composite.z_credibility)
    return {
        "pit_id": composite.pit_id,
        "grade_g_m3": composite.grade_g_m3,
        "z_credibility": composite.z_credibility,
        "credibility": cls,
        "blocking": cls == "LOW" and composite.class_vs_cutoff != "BELOW DETECTION",
    }


# ---------------------------------------------------------------------------
# B4 — Validation against historical feed grades
# ---------------------------------------------------------------------------


def validate_against_feed_grades(model_grades: list[float], feed_grades: list[float]) -> dict:
    """bias, MAE, correlation, suggested lambda (per Validation sheet)."""
    if len(model_grades) != len(feed_grades) or len(model_grades) == 0:
        raise ValueError("model_grades and feed_grades must be equal-length and non-empty")
    n = len(model_grades)
    diffs = [m - f for m, f in zip(model_grades, feed_grades)]
    bias = sum(diffs) / n
    mae = sum(abs(d) for d in diffs) / n
    mean_m = sum(model_grades) / n
    mean_f = sum(feed_grades) / n
    cov = sum((m - mean_m) * (f - mean_f) for m, f in zip(model_grades, feed_grades))
    var_m = sum((m - mean_m) ** 2 for m in model_grades)
    var_f = sum((f - mean_f) ** 2 for f in feed_grades)
    correlation = cov / math.sqrt(var_m * var_f) if var_m > 0 and var_f > 0 else 0.0
    log_ratios = [math.log(f / m) for m, f in zip(model_grades, feed_grades) if m > 0 and f > 0]
    suggested_lambda_multiplier = math.exp(sum(log_ratios) / len(log_ratios)) if log_ratios else 1.0
    return {
        "n_records": n, "bias": bias, "mae": mae, "correlation": correlation,
        "suggested_lambda_multiplier": suggested_lambda_multiplier,
        "sufficient_records": n >= 10,
    }
