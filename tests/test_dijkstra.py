"""
Tests for DijkstraPathfinder.
Same fixtures as test_astar.py — Dijkstra must produce identical
path lengths (both are optimal) but will explore more nodes.
"""

import pytest
from algorithms.dijkstra import DijkstraPathfinder
from algorithms.astar import AStarPathfinder
from algorithms.base import SearchResult


class TestDijkstraCorrectness:

    def test_direct_path_found(self, direct_graph):
        result = DijkstraPathfinder(direct_graph).find_path(0, 1)
        assert result is not None
        assert result.path == [0, 1]

    def test_same_origin_and_destination(self, direct_graph):
        result = DijkstraPathfinder(direct_graph).find_path(0, 0)
        assert result is not None
        assert result.path == [0]
        assert result.path_length_m == pytest.approx(0.0)

    def test_no_path_returns_none(self, disconnected_graph):
        result = DijkstraPathfinder(disconnected_graph).find_path(0, 3)
        assert result is None

    def test_one_way_forward_path_exists(self, one_way_graph):
        result = DijkstraPathfinder(one_way_graph).find_path(0, 2)
        assert result is not None
        assert result.path == [0, 1, 2]

    def test_one_way_reverse_returns_none(self, one_way_graph):
        result = DijkstraPathfinder(one_way_graph).find_path(2, 0)
        assert result is None

    def test_grid_optimal_path_length(self, grid_graph):
        result = DijkstraPathfinder(grid_graph).find_path(0, 8)
        assert result is not None
        assert result.path_length_m == pytest.approx(400.0, abs=0.01)

    def test_grid_path_is_valid_sequence(self, grid_graph):
        result = DijkstraPathfinder(grid_graph).find_path(0, 8)
        assert result is not None
        neighbor_map = {
            node: {n for n, _ in grid_graph.get_neighbors(node)}
            for node in range(9)
        }
        for u, v in zip(result.path, result.path[1:]):
            assert v in neighbor_map[u], f"Edge {u}→{v} does not exist"


class TestDijkstraVsAstar:
    """
    Dijkstra and A* must always agree on path length (both optimal).
    Dijkstra should explore >= nodes than A* (no heuristic to guide it).
    """

    def test_same_path_length_as_astar(self, grid_graph):
        dijkstra_result = DijkstraPathfinder(grid_graph).find_path(0, 8)
        astar_result    = AStarPathfinder(grid_graph).find_path(0, 8)
        assert dijkstra_result is not None
        assert astar_result is not None
        assert dijkstra_result.path_length_m == pytest.approx(
            astar_result.path_length_m, abs=0.01
        )

    def test_explores_more_nodes_than_astar(self, grid_graph):
        dijkstra_result = DijkstraPathfinder(grid_graph).find_path(0, 8)
        astar_result    = AStarPathfinder(grid_graph).find_path(0, 8)
        assert dijkstra_result is not None
        assert astar_result is not None
        assert dijkstra_result.nodes_explored >= astar_result.nodes_explored