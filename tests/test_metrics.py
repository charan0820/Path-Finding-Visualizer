# tests/test_metrics.py
"""
Tests for metrics/performance.py.
Uses the same FakeRoadGraph and fixtures from conftest.py.
"""
import pytest
from algorithms.astar import AStarPathfinder
from metrics.performance import metrics_from_result, SearchMetrics


class TestMetricsFromResult:

    def test_builds_from_direct_graph(self, direct_graph):
        result = AStarPathfinder(direct_graph).find_path(0, 1)
        metrics = metrics_from_result(result, "A*", 0, 1)
        assert isinstance(metrics, SearchMetrics)

    def test_path_length_correct(self, direct_graph):
        result = AStarPathfinder(direct_graph).find_path(0, 1)
        metrics = metrics_from_result(result, "A*", 0, 1)
        assert metrics.path_length_m == pytest.approx(100.0)
        assert metrics.path_length_km == pytest.approx(0.1)

    def test_nodes_explored_positive(self, grid_graph):
        result = AStarPathfinder(grid_graph).find_path(0, 8)
        metrics = metrics_from_result(result, "A*", 0, 8)
        assert metrics.nodes_explored > 0

    def test_efficiency_between_zero_and_one(self, grid_graph):
        result = AStarPathfinder(grid_graph).find_path(0, 8)
        metrics = metrics_from_result(result, "A*", 0, 8)
        assert 0.0 < metrics.exploration_efficiency <= 1.0

    def test_as_dict_has_expected_keys(self, direct_graph):
        result = AStarPathfinder(direct_graph).find_path(0, 1)
        metrics = metrics_from_result(result, "A*", 0, 1)
        d = metrics.as_dict()
        assert "Algorithm" in d
        assert "Path length" in d
        assert "Nodes explored" in d
        assert "Runtime" in d
        assert "Efficiency" in d

    def test_summary_line_contains_algorithm_name(self, direct_graph):
        result = AStarPathfinder(direct_graph).find_path(0, 1)
        metrics = metrics_from_result(result, "A*", 0, 1)
        assert "A*" in metrics.summary_line()

    def test_runtime_ms_non_negative(self, direct_graph):
        result = AStarPathfinder(direct_graph).find_path(0, 1)
        metrics = metrics_from_result(result, "A*", 0, 1)
        assert metrics.runtime_ms >= 0.0