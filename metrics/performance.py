"""
Performance metrics for pathfinding runs.

SearchMetrics is populated by the algorithm layer and consumed by the UI.
Keeping metrics in their own module means the UI and algorithm layers
never import each other.
"""

from __future__ import annotations
from dataclasses import dataclass
import math


@dataclass
class SearchMetrics:
    """
    Human-readable summary of a single pathfinding run.

    All fields are computed from a SearchResult — this class adds
    formatting and derived statistics, not raw data.
    """
    algorithm_name: str
    origin_node: int
    destination_node: int

    # Core stats (from SearchResult)
    nodes_explored: int
    path_node_count: int
    path_length_m: float
    runtime_ms: float

    # Derived
    @property
    def path_length_km(self) -> float:
        return self.path_length_m / 1000

    @property
    def exploration_efficiency(self) -> float:
        """
        Ratio of path nodes to explored nodes (0–1).
        Higher = more efficient search (fewer wasted node expansions).
        A* typically achieves 0.3–0.8 on city graphs with a good heuristic.
        """
        if self.nodes_explored == 0:
            return 0.0
        return self.path_node_count / self.nodes_explored

    def as_dict(self) -> dict:
        """For display in Streamlit st.metric() or st.json()."""
        return {
            "Algorithm": self.algorithm_name,
            "Path length": f"{self.path_length_km:.2f} km",
            "Path nodes": self.path_node_count,
            "Nodes explored": f"{self.nodes_explored:,}",
            "Runtime": f"{self.runtime_ms:.1f} ms",
            "Efficiency": f"{self.exploration_efficiency:.1%}",
        }

    def summary_line(self) -> str:
        """One-line summary for logging and README screenshots."""
        return (
            f"{self.algorithm_name} | "
            f"{self.path_length_km:.2f} km | "
            f"{self.nodes_explored:,} nodes explored | "
            f"{self.runtime_ms:.1f} ms | "
            f"efficiency {self.exploration_efficiency:.1%}"
        )


def metrics_from_result(
    result,
    algorithm_name: str,
    origin_node: int,
    destination_node: int,
) -> SearchMetrics:
    """
    Build a SearchMetrics from a SearchResult.

    Args:
        result:           SearchResult from any PathfindingAlgorithm.
        algorithm_name:   Display name (e.g. "A*").
        origin_node:      Start node ID.
        destination_node: End node ID.

    Returns:
        SearchMetrics instance.
    """
    return SearchMetrics(
        algorithm_name=algorithm_name,
        origin_node=origin_node,
        destination_node=destination_node,
        nodes_explored=result.nodes_explored,
        path_node_count=len(result.path),
        path_length_m=result.path_length_m,
        runtime_ms=result.runtime_ms,
    )