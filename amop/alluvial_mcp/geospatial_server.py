"""Module C — Geospatial VAM & Stockpile Optimization MCP server (docs/AMOP_MCP_SPEC.md §4.3)."""
from __future__ import annotations

from fastmcp import FastMCP

from alluvial_mcp.core import vam as core
from alluvial_mcp.mcp_utils import MUTATING, READ_ONLY, to_jsonable

mcp = FastMCP("alluvial-geospatial")


@mcp.tool(annotations=READ_ONLY)
def build_distance_matrix(sources: list[list[float]], destinations: list[list[float]]) -> dict:
    """sources/destinations: [[easting, northing], ...]. Returns Euclidean distances in metres."""
    return {"distance_matrix": core.euclidean_distance_matrix(
        [tuple(s) for s in sources], [tuple(d) for d in destinations]
    )}


@mcp.tool(annotations=READ_ONLY)
def build_haul_cost_matrix(distances_m: list[list[float]], rate_per_m3_per_km: float) -> dict:
    return {"haul_cost_matrix": core.build_haul_cost_matrix(distances_m, rate_per_m3_per_km)}


@mcp.tool(annotations=READ_ONLY)
def compute_grade_priority_factor(grades: list[float], alpha: float = 1.0) -> dict:
    return {"gpf": core.compute_grade_priority_factor(grades, alpha)}


@mcp.tool(annotations=READ_ONLY)
def build_heuristic_matrix(cost_matrix: list[list[float]], grades: list[float],
                            distance_matrix: list[list[float]], alpha: float = 1.0, beta: float = 1.0,
                            gamma: float = 1.0, lam: float = 0.5, w_distance: float = 0.5,
                            w_cost: float = 0.5, theta: float = 0.3) -> dict:
    """Bounded grade/distance/cost heuristic: H(i,j) = C(i,j) * GP(i) * SM(i,j), bounded to
    [C*(1-theta), C*GP_max*(1+theta)]. Verified against Cost_Grade_Heuristic_Prioritized_
    VAM_Cost_MATRIX.xlsx!Heuristic Calculation (see README "Engineering corrections")."""
    params = core.HeuristicParameters(alpha=alpha, beta=beta, gamma=gamma, lam=lam,
                                       w_distance=w_distance, w_cost=w_cost, theta=theta)
    return to_jsonable(core.build_heuristic_matrix(cost_matrix, grades, distance_matrix, params))


@mcp.tool(annotations=READ_ONLY)
def compute_stockpile_compatibility(pit_grades: list[float], target_grades: list[float | None]) -> dict:
    return {"compatibility_matrix": core.compute_stockpile_compatibility(pit_grades, target_grades)}


@mcp.tool(annotations=READ_ONLY)
def solve_vam(cost_matrix: list[list[float]], supply: list[float], demand: list[float],
              source_ids: list[str] | None = None, destination_ids: list[str] | None = None) -> dict:
    """Vogel's Approximation Method with a full iteration audit log and dummy-row/column
    balancing. A penalty-based heuristic, not a certified optimum -- pair with
    verify_vam_optimality. Verified against VAM_OPTIMISER_MACRO.xlsm."""
    return to_jsonable(core.solve_vam(cost_matrix, supply, demand, source_ids, destination_ids))


@mcp.tool(annotations=READ_ONLY)
def verify_vam_optimality(allocation: list[list[float]], cost_matrix: list[list[float]],
                           supply: list[float], demand: list[float]) -> dict:
    """Cross-checks a VAM allocation against the true LP transportation optimum (scipy.linprog)."""
    return to_jsonable(core.verify_vam_optimality(allocation, cost_matrix, supply, demand))


@mcp.tool(annotations=READ_ONLY)
def compute_naive_proportional_baseline(supply: list[float], demand: list[float],
                                         cost_matrix: list[list[float]]) -> dict:
    return to_jsonable(core.compute_naive_proportional_baseline(supply, demand, cost_matrix))


@mcp.tool(annotations=READ_ONLY)
def compute_vam_savings(vam_cost: float, naive_cost: float) -> dict:
    return to_jsonable(core.compute_vam_savings(vam_cost, naive_cost))


@mcp.tool(annotations=READ_ONLY)
def adjudicate_vam_solution(allocation: list[list[float]], supply: list[float], demand: list[float]) -> dict:
    """VAM_ACCEPTED iff row sums match supply, allocation non-negative; names the failing constraint otherwise."""
    return to_jsonable(core.adjudicate_vam_solution(allocation, supply, demand))


if __name__ == "__main__":
    mcp.run()
