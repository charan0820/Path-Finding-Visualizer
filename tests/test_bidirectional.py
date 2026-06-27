"""
Tests for BidirectionalDijkstra and BidirectionalBFS.
"""
import pytest
from algorithms.bidirectional_dijkstra import BidirectionalDijkstra
from algorithms.bidirectional_bfs import BidirectionalBFS
from algorithms.astar import AStarPathfinder


class TestBidirectionalDijkstra:

    def test_direct_path_found(self, direct_graph):
        result = BidirectionalDijkstra(direct_graph).find_path(0, 1)
        assert result is not None
        assert result.path == [0, 1]

    def test_no_path_returns_none(self, disconnected_graph):
        result = BidirectionalDijkstra(disconnected_graph).find_path(0, 3)
        assert result is None

    def test_same_origin_destination(self, direct_graph):
        result = BidirectionalDijkstra(direct_graph).find_path(0, 0)
        assert result is not None
        assert result.path == [0]

    def test_one_way_forward(self, one_way_graph):
        result = BidirectionalDijkstra(one_way_graph).find_path(0, 2)
        assert result is not None
        assert result.path == [0, 1, 2]

    def test_one_way_reverse_none(self, one_way_graph):
        result = BidirectionalDijkstra(one_way_graph).find_path(2, 0)
        assert result is None

    def test_same_path_length_as_astar(self, grid_graph):
        bidir  = BidirectionalDijkstra(grid_graph).find_path(0, 8)
        astar  = AStarPathfinder(grid_graph).find_path(0, 8)
        assert bidir is not None and astar is not None
        assert bidir.path_length_m == pytest.approx(astar.path_length_m, abs=0.01)

    def test_explores_fewer_nodes_than_dijkstra(self, grid_graph):
        from algorithms.dijkstra import DijkstraPathfinder
        bidir   = BidirectionalDijkstra(grid_graph).find_path(0, 8)
        dijkstra = DijkstraPathfinder(grid_graph).find_path(0, 8)
        assert bidir is not None and dijkstra is not None
        assert bidir.nodes_explored <= dijkstra.nodes_explored

    def test_path_is_valid_sequence(self, grid_graph):
        result = BidirectionalDijkstra(grid_graph).find_path(0, 8)
        assert result is not None
        neighbor_map = {
            n: {nb for nb, _ in grid_graph.get_neighbors(n)}
            for n in range(9)
        }
        for u, v in zip(result.path, result.path[1:]):
            assert v in neighbor_map[u], f"Edge {u}→{v} does not exist"


class TestBidirectionalBFS:

    def test_direct_path_found(self, direct_graph):
        result = BidirectionalBFS(direct_graph).find_path(0, 1)
        assert result is not None
        assert result.path == [0, 1]

    def test_no_path_returns_none(self, disconnected_graph):
        result = BidirectionalBFS(disconnected_graph).find_path(0, 3)
        assert result is None

    def test_same_origin_destination(self, direct_graph):
        result = BidirectionalBFS(direct_graph).find_path(0, 0)
        assert result is not None
        assert result.path == [0]

    def test_one_way_forward(self, one_way_graph):
        result = BidirectionalBFS(one_way_graph).find_path(0, 2)
        assert result is not None
        assert result.path == [0, 1, 2]

    def test_one_way_reverse_none(self, one_way_graph):
        result = BidirectionalBFS(one_way_graph).find_path(2, 0)
        assert result is None

    def test_path_is_valid_sequence(self, grid_graph):
        result = BidirectionalBFS(grid_graph).find_path(0, 8)
        assert result is not None
        neighbor_map = {
            n: {nb for nb, _ in grid_graph.get_neighbors(n)}
            for n in range(9)
        }
        for u, v in zip(result.path, result.path[1:]):
            assert v in neighbor_map[u], f"Edge {u}→{v} does not exist"

    def test_path_starts_and_ends_correctly(self, grid_graph):
        result = BidirectionalBFS(grid_graph).find_path(0, 8)
        assert result is not None
        assert result.path[0] == 0
        assert result.path[-1] == 8

    def test_explores_fewer_nodes_than_unidirectional_bfs(self, grid_graph):
        """
        Bidirectional BFS should explore fewer nodes than
        running BFS from just one direction.
        We approximate unidirectional BFS node count via Dijkstra
        (same exploration pattern, no heuristic).
        """
        from algorithms.dijkstra import DijkstraPathfinder
        bidir    = BidirectionalBFS(grid_graph).find_path(0, 8)
        dijkstra = DijkstraPathfinder(grid_graph).find_path(0, 8)
        assert bidir is not None and dijkstra is not None
        assert bidir.nodes_explored <= dijkstra.nodes_explored