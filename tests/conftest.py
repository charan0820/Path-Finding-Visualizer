"""
Shared test fixtures.

All fixtures use synthetic graphs — no OSM download, no network, fast.
The fake_road_graph fixture mimics the interface of graph.builder.RoadGraph
exactly, so tests are valid against the real implementation after merge.
"""

import math
import pytest
import networkx as nx


# ------------------------------------------------------------------ #
# Minimal RoadGraph stand-in for testing                              #
# ------------------------------------------------------------------ #

class _FakeNodeData:
    """Matches the interface of graph.builder.NodeData."""
    def __init__(self, node_id: int, lat: float, lng: float):
        self.node_id = node_id
        self.lat = lat
        self.lng = lng


class FakeRoadGraph:
    def __init__(self, nx_graph: nx.DiGraph):
        self._g = nx_graph

    def has_node(self, node_id: int) -> bool:
        return node_id in self._g

    def get_node(self, node_id: int) -> _FakeNodeData:
        data = self._g.nodes[node_id]
        return _FakeNodeData(node_id=node_id, lat=data['lat'], lng=data['lng'])

    def get_neighbors(self, node_id: int) -> list[tuple[int, float]]:
        return [
            (neighbor, self._g[node_id][neighbor]['length'])
            for neighbor in self._g.successors(node_id)
        ]

    def get_predecessors(self, node_id: int) -> list[tuple[int, float]]:
        return [
            (pred, self._g[pred][node_id]['length'])
            for pred in self._g.predecessors(node_id)
        ]

    def underlying_graph(self) -> nx.DiGraph:
        return self._g

    def node_count(self) -> int:
        return self._g.number_of_nodes()


# ------------------------------------------------------------------ #
# Graph fixtures                                                       #
# ------------------------------------------------------------------ #

@pytest.fixture
def direct_graph():
    """
    Two nodes, one edge. Simplest possible path.

    Origin (0) ---100m---> Destination (1)

    Coordinates chosen so haversine ≈ 100m (≤ edge length).
    """
    g = nx.DiGraph()
    g.add_node(0, lat=51.5000, lng=-0.1000)
    g.add_node(1, lat=51.5009, lng=-0.1000)  # ~100m north
    g.add_edge(0, 1, length=100.0)
    return FakeRoadGraph(g)


@pytest.fixture
def grid_graph():
    """
    3x3 grid. Nodes numbered 0-8, row-major.

    0 - 1 - 2
    |   |   |
    3 - 4 - 5
    |   |   |
    6 - 7 - 8

    All edges bidirectional, 100m each.
    Optimal path 0→8: length 400m (right then down, or down then right).
    Any longer path (e.g. via 4 but backtracking) must be rejected.
    """
    g = nx.DiGraph()

    # Lay out nodes on a ~100m grid (1 degree lat ≈ 111,000m)
    step = 100 / 111_000  # degrees per 100m
    for row in range(3):
        for col in range(3):
            node_id = row * 3 + col
            g.add_node(node_id, lat=51.5 + row * step, lng=-0.1 + col * step)

    edges = [
        (0,1),(1,2),(3,4),(4,5),(6,7),(7,8),   # horizontal
        (0,3),(1,4),(2,5),(3,6),(4,7),(5,8),   # vertical
    ]
    for u, v in edges:
        g.add_edge(u, v, length=100.0)
        g.add_edge(v, u, length=100.0)

    return FakeRoadGraph(g)


@pytest.fixture
def disconnected_graph():
    """
    Two isolated components. No path from 0 to 3.

    Component A: 0 → 1
    Component B: 2 → 3
    """
    g = nx.DiGraph()
    g.add_node(0, lat=51.50, lng=-0.10)
    g.add_node(1, lat=51.51, lng=-0.10)
    g.add_node(2, lat=51.60, lng=-0.20)
    g.add_node(3, lat=51.61, lng=-0.20)
    g.add_edge(0, 1, length=1000.0)
    g.add_edge(2, 3, length=1000.0)
    return FakeRoadGraph(g)


@pytest.fixture
def one_way_graph():
    """
    One-way street. Path exists A→B→C but not C→A.

    0 →→→ 1 →→→ 2    (one-way, 200m each)
    """
    g = nx.DiGraph()
    g.add_node(0, lat=51.500, lng=-0.100)
    g.add_node(1, lat=51.500, lng=-0.098)
    g.add_node(2, lat=51.500, lng=-0.096)
    g.add_edge(0, 1, length=200.0)
    g.add_edge(1, 2, length=200.0)
    return FakeRoadGraph(g)