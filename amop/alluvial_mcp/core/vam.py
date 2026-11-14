"""
Module C — Geospatial VAM & Stockpile Optimization (core engine).

Two independent pieces, each verified against real workbook output:

1. The BOUNDED grade/distance/cost heuristic matrix H(i,j)
   (Cost_Grade_Heuristic_Prioritized_VAM_Cost_MATRIX.xlsx!Verification,
   tolerance rel=1e-4 per docs/AMOP_MCP_SPEC.md §7.1).
2. Vogel's Approximation Method itself, with the same iteration-log shape,
   dummy-row/column balancing and tie-break rule as VAM_OPTIMISER_MACRO.xlsm
   ("Highest penalty; tie -> lowest cell cost; tie -> largest residual
   capacity.").

VAM is a penalty-based heuristic, not a certified optimum -- `verify_vam_
optimality` cross-checks it against the true LP optimum via
scipy.optimize.linprog (substituting for the handoff spec's non-existent
"ORKit" MODI/stepping-stone dependency; see requirements.txt).
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field


# ---------------------------------------------------------------------------
# C1/C2/C3 — bounded heuristic matrix
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class HeuristicParameters:
    alpha: float = 1.0   # grade sensitivity exponent
    beta: float = 1.0    # distance-score shape exponent
    gamma: float = 1.0   # cost-score shape exponent
    lam: float = 0.5     # grade-penalty strength (lambda)
    w_distance: float = 0.5
    w_cost: float = 0.5
    theta: float = 0.3   # max spatial cost adjustment


def euclidean_distance_matrix(
    sources: list[tuple[float, float]], destinations: list[tuple[float, float]]
) -> list[list[float]]:
    return [
        [math.hypot(sx - dx, sy - dy) for dx, dy in destinations]
        for sx, sy in sources
    ]


def build_haul_cost_matrix(distances_m: list[list[float]], rate_per_m3_per_km: float) -> list[list[float]]:
    return [[d / 1000.0 * rate_per_m3_per_km for d in row] for row in distances_m]


def compute_grade_priority_factor(grades: list[float], alpha: float = 1.0) -> list[float]:
    g_max = max(grades)
    if g_max <= 0:
        return [0.0 for _ in grades]
    return [(g / g_max) ** alpha for g in grades]


def compute_grade_penalty(gpf: list[float], lam: float = 0.5) -> list[float]:
    return [1 + lam * (1 - g) for g in gpf]


def build_heuristic_matrix(
    cost_matrix: list[list[float]],
    grades: list[float],
    distance_matrix: list[list[float]],
    params: HeuristicParameters | None = None,
) -> dict:
    """
    GPF(i)   = (G(i)/Gmax)^alpha
    GP(i)    = 1 + lambda*(1 - GPF(i))
    DNF(i,j) = (D(i,j)-Dmin)/(Dmax-Dmin)
    CNF(i,j) = (C(i,j)-Cmin)/(Cmax-Cmin)
    SM(i,j)  = (1-theta) + 2*theta*(w_D*DNF^beta + w_C*CNF^gamma)
    H(i,j)   = C(i,j) * GP(i) * SM(i,j)
    """
    p = params or HeuristicParameters()
    gpf = compute_grade_priority_factor(grades, p.alpha)
    gp = compute_grade_penalty(gpf, p.lam)

    flat_d = [v for row in distance_matrix for v in row]
    flat_c = [v for row in cost_matrix for v in row]
    d_min, d_max = min(flat_d), max(flat_d)
    c_min, c_max = min(flat_c), max(flat_c)
    d_span = (d_max - d_min) or 1.0
    c_span = (c_max - c_min) or 1.0

    n_rows, n_cols = len(cost_matrix), len(cost_matrix[0])
    h = [[0.0] * n_cols for _ in range(n_rows)]
    sm_out = [[0.0] * n_cols for _ in range(n_rows)]
    for i in range(n_rows):
        for j in range(n_cols):
            dnf = (distance_matrix[i][j] - d_min) / d_span
            cnf = (cost_matrix[i][j] - c_min) / c_span
            sm = (1 - p.theta) + 2 * p.theta * (p.w_distance * dnf ** p.beta + p.w_cost * cnf ** p.gamma)
            sm_out[i][j] = sm
            h[i][j] = cost_matrix[i][j] * gp[i] * sm

    # Bounded-ness assertion per spec §4.3: H in [C*(1-theta), C*GP_max*(1+theta)]
    gp_max = max(gp)
    for i in range(n_rows):
        for j in range(n_cols):
            lo = cost_matrix[i][j] * (1 - p.theta)
            hi = cost_matrix[i][j] * gp_max * (1 + p.theta)
            if not (lo - 1e-6 <= h[i][j] <= hi + 1e-6):
                raise AssertionError(
                    f"Heuristic matrix bound violated at ({i},{j}): H={h[i][j]} not in [{lo},{hi}]"
                )

    return {"H": h, "GPF": gpf, "GP": gp, "SM": sm_out}


# ---------------------------------------------------------------------------
# C4 — stockpile compatibility (grade-target deficit)
# ---------------------------------------------------------------------------


def compute_stockpile_compatibility(
    pit_grades: list[float], target_grades: list[float | None]
) -> list[list[float]]:
    """1.0 = perfectly compatible; falls off as |pit_grade - target| grows."""
    out = []
    for g in pit_grades:
        row = []
        for t in target_grades:
            if t is None or t <= 0:
                row.append(1.0)
            else:
                row.append(max(0.0, 1 - abs(g - t) / t))
        out.append(row)
    return out


# ---------------------------------------------------------------------------
# C5 — Vogel's Approximation Method (with audit trail)
# ---------------------------------------------------------------------------


@dataclass
class VAMIteration:
    iteration: int
    selected_type: str  # "Row" | "Col"
    selected_id: str
    penalty: float
    source: str
    destination: str
    qty_allocated: float
    unit_cost: float
    subtotal: float
    supply_remaining: float
    demand_remaining: float
    tie_rule: str
    status: str


@dataclass
class VAMResult:
    allocation: list[list[float]]
    total_cost: float
    iterations: list[VAMIteration]
    feasible: bool
    row_sums: list[float]
    column_sums: list[float]
    balance_note: str
    source_ids: list[str]
    destination_ids: list[str]


_TIE_RULE_NOTE = "Highest penalty; tie -> lowest cell cost; tie -> largest residual capacity."


def solve_vam(
    cost_matrix: list[list[float]],
    supply: list[float],
    demand: list[float],
    source_ids: list[str] | None = None,
    destination_ids: list[str] | None = None,
) -> VAMResult:
    n_src, n_dst = len(supply), len(demand)
    source_ids = source_ids or [f"S{i+1}" for i in range(n_src)]
    destination_ids = destination_ids or [f"D{j+1}" for j in range(n_dst)]

    total_supply, total_demand = sum(supply), sum(demand)
    balance_note = "Balanced: supply equals demand."
    cost = [row[:] for row in cost_matrix]
    sup = supply[:]
    dem = demand[:]
    src_ids = source_ids[:]
    dst_ids = destination_ids[:]

    if total_supply > total_demand:
        dem.append(total_supply - total_demand)
        dst_ids.append("DUMMY-STOCKPILE")
        for row in cost:
            row.append(0.0)
        balance_note = f"Added DUMMY-STOCKPILE for unused supply: {total_supply - total_demand}."
    elif total_demand > total_supply:
        sup.append(total_demand - total_supply)
        src_ids.append("DUMMY-PIT")
        cost.append([0.0] * len(dem))
        balance_note = f"Added DUMMY-PIT for unused stockpile capacity: {total_demand - total_supply}."

    n_rows, n_cols = len(sup), len(dem)
    allocation = [[0.0] * n_cols for _ in range(n_rows)]
    active_rows = set(range(n_rows))
    active_cols = set(range(n_cols))
    sup_rem = sup[:]
    dem_rem = dem[:]

    iterations: list[VAMIteration] = []
    iter_no = 0
    BIG = float("inf")

    while active_rows and active_cols:
        iter_no += 1
        row_penalty = {}
        for i in active_rows:
            costs = sorted(cost[i][j] for j in active_cols)
            row_penalty[i] = (costs[1] - costs[0]) if len(costs) > 1 else costs[0]
        col_penalty = {}
        for j in active_cols:
            costs = sorted(cost[i][j] for i in active_rows)
            col_penalty[j] = (costs[1] - costs[0]) if len(costs) > 1 else costs[0]

        best_row_pen = max(row_penalty.values()) if row_penalty else -BIG
        best_col_pen = max(col_penalty.values()) if col_penalty else -BIG

        if best_row_pen >= best_col_pen:
            candidates = [i for i, p in row_penalty.items() if p == best_row_pen]
            selected_type, chosen_idx, penalty = "Row", min(candidates), best_row_pen
            min_cost = min(cost[chosen_idx][j] for j in active_cols)
            col_candidates = [j for j in active_cols if cost[chosen_idx][j] == min_cost]
            j_sel = max(col_candidates, key=lambda j: dem_rem[j])
            i_sel = chosen_idx
        else:
            candidates = [j for j, p in col_penalty.items() if p == best_col_pen]
            selected_type, chosen_idx, penalty = "Col", min(candidates), best_col_pen
            min_cost = min(cost[i][chosen_idx] for i in active_rows)
            row_candidates = [i for i in active_rows if cost[i][chosen_idx] == min_cost]
            i_sel = max(row_candidates, key=lambda i: sup_rem[i])
            j_sel = chosen_idx

        qty = min(sup_rem[i_sel], dem_rem[j_sel])
        unit_cost = cost[i_sel][j_sel]
        allocation[i_sel][j_sel] += qty
        sup_rem[i_sel] -= qty
        dem_rem[j_sel] -= qty

        iterations.append(VAMIteration(
            iteration=iter_no, selected_type=selected_type,
            selected_id=(src_ids[i_sel] if selected_type == "Row" else dst_ids[j_sel]),
            penalty=penalty, source=src_ids[i_sel], destination=dst_ids[j_sel],
            qty_allocated=qty, unit_cost=unit_cost, subtotal=qty * unit_cost,
            supply_remaining=sup_rem[i_sel], demand_remaining=dem_rem[j_sel],
            tie_rule=_TIE_RULE_NOTE, status="Allocated",
        ))

        if sup_rem[i_sel] <= 1e-9:
            active_rows.discard(i_sel)
        if dem_rem[j_sel] <= 1e-9:
            active_cols.discard(j_sel)

    real_allocation = [row[:n_dst] for row in allocation[:n_src]]
    total_cost = sum(
        real_allocation[i][j] * cost_matrix[i][j] for i in range(n_src) for j in range(n_dst)
    )
    row_sums = [sum(r) for r in real_allocation]
    col_sums = [sum(real_allocation[i][j] for i in range(n_src)) for j in range(n_dst)]
    feasible = adjudicate_vam_solution(real_allocation, supply, demand)["verdict"] == "VAM_ACCEPTED"

    return VAMResult(
        allocation=real_allocation, total_cost=total_cost, iterations=iterations,
        feasible=feasible, row_sums=row_sums, column_sums=col_sums,
        balance_note=balance_note, source_ids=source_ids, destination_ids=destination_ids,
    )


# ---------------------------------------------------------------------------
# C6 — naive proportional baseline + savings
# ---------------------------------------------------------------------------


def compute_naive_proportional_baseline(
    supply: list[float], demand: list[float], cost_matrix: list[list[float]]
) -> dict:
    total_demand = sum(demand)
    allocation = [
        [supply[i] * demand[j] / total_demand for j in range(len(demand))]
        for i in range(len(supply))
    ]
    total_cost = sum(
        allocation[i][j] * cost_matrix[i][j] for i in range(len(supply)) for j in range(len(demand))
    )
    return {"allocation": allocation, "total_cost": total_cost}


def compute_vam_savings(vam_cost: float, naive_cost: float) -> dict:
    savings_usd = naive_cost - vam_cost
    savings_pct = (savings_usd / naive_cost) if naive_cost > 0 else 0.0
    return {"savings_usd": savings_usd, "savings_pct": savings_pct}


# ---------------------------------------------------------------------------
# VAM adjudication / optimality verification
# ---------------------------------------------------------------------------


def adjudicate_vam_solution(
    allocation: list[list[float]], supply: list[float], demand: list[float],
    vam_cost: float | None = None, naive_cost: float | None = None,
) -> dict:
    """R-2.2. No source ships more than its supply, no destination receives
    more than its demand, the smaller of total supply/demand is fully placed,
    nothing is negative and (when both costs are given) VAM is no dearer than
    the naive baseline. Returns the failing constraint names."""
    tol = 1e-6
    row_sums = [sum(r) for r in allocation]
    col_sums = [sum(allocation[i][j] for i in range(len(allocation))) for j in range(len(allocation[0]))]
    failing = []
    if any(row_sums[i] > supply[i] + tol for i in range(len(supply))):
        failing.append("supply_exceeded")
    if any(col_sums[j] > demand[j] + tol for j in range(len(demand))):
        failing.append("demand_exceeded")
    if abs(sum(row_sums) - min(sum(supply), sum(demand))) > tol:
        failing.append("volume_not_fully_allocated")
    if any(v < -1e-9 for row in allocation for v in row):
        failing.append("negative_allocation")
    if vam_cost is not None and naive_cost is not None and vam_cost > naive_cost + tol:
        failing.append("vam_dearer_than_naive")
    return {"verdict": "VAM_REJECTED" if failing else "VAM_ACCEPTED", "row_sums": row_sums,
            "column_sums": col_sums, "failing_constraints": failing}


def verify_vam_optimality(allocation: list[list[float]], cost_matrix: list[list[float]],
                           supply: list[float], demand: list[float]) -> dict:
    """
    Cross-checks the VAM heuristic allocation against the true LP transportation
    optimum via scipy.optimize.linprog (substitutes for the handoff spec's
    non-installable "ORKit" MODI/stepping-stone dependency).
    """
    from scipy.optimize import linprog

    n_src, n_dst = len(supply), len(demand)
    c = [cost_matrix[i][j] for i in range(n_src) for j in range(n_dst)]
    a_eq, b_eq = [], []
    for i in range(n_src):
        row = [1.0 if k // n_dst == i else 0.0 for k in range(n_src * n_dst)]
        a_eq.append(row)
        b_eq.append(supply[i])
    for j in range(n_dst):
        row = [1.0 if k % n_dst == j else 0.0 for k in range(n_src * n_dst)]
        a_eq.append(row)
        b_eq.append(demand[j])

    total_supply, total_demand = sum(supply), sum(demand)
    bound_type = "eq" if abs(total_supply - total_demand) < 1e-6 else "supply_le_or_demand_le"
    res = linprog(c, A_eq=a_eq if bound_type == "eq" else None, b_eq=b_eq if bound_type == "eq" else None,
                   A_ub=a_eq if bound_type != "eq" else None, b_ub=b_eq if bound_type != "eq" else None,
                   bounds=(0, None), method="highs")

    vam_cost = sum(allocation[i][j] * cost_matrix[i][j] for i in range(n_src) for j in range(n_dst))
    lp_optimum = res.fun if res.success else None
    gap_pct = ((vam_cost - lp_optimum) / lp_optimum) if (lp_optimum and lp_optimum > 0) else None
    return {
        "lp_optimum_cost": lp_optimum, "vam_cost": vam_cost, "optimality_gap_pct": gap_pct,
        "lp_solve_success": res.success,
    }
