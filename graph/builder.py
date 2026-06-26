# graph/builder.py
"""
Wraps the raw OSM graph in a clean interface for the algorithm layer.

The algorithm layer should never call OSMnx directly — it talks to
GraphInterface. This decouples algorithms from the data source and makes
testing trivial (you can pass in a synthetic graph).
"""

from dataclasses import dataclass
import networkx as nx


@dataclass
class NodeData:
    node_id: int
    lat: float
    lng: float


@dataclass  
class EdgeData:
    length_m: float
    name: str


class RoadGraph:
    """
    Clean interface over a NetworkX MultiDiGraph road network.
    
    Algorithms use this class, not NetworkX directly.
    This makes it easy to swap the underlying data source later.
    """

    def __init__(self, nx_graph: nx.MultiDiGraph):
        self._g = nx_graph

    @property
    def node_count(self) -> int:
        return self._g.number_of_nodes()

    @property
    def edge_count(self) -> int:
        return self._g.number_of_edges()

    def get_node(self, node_id: int) -> NodeData:
        data = self._g.nodes[node_id]
        return NodeData(
            node_id=node_id,
            lat=data['y'],
            lng=data['x'],
        )

    def get_neighbors(self, node_id: int) -> list[tuple[int, float]]:
        """
        Return (neighbor_id, edge_length_metres) for all outgoing edges.
        
        For MultiDiGraph (parallel edges allowed), returns the shortest
        edge to each neighbor — what matters for routing.
        """
        neighbors = []
        for neighbor, edge_dict in self._g[node_id].items():
            # edge_dict: {0: {...}, 1: {...}} for parallel edges
            min_length = min(
                data.get('length', float('inf'))
                for data in edge_dict.values()
            )
            if min_length < float('inf'):
                neighbors.append((neighbor, min_length))
        return neighbors

    def has_node(self, node_id: int) -> bool:
        return node_id in self._g

    def underlying_graph(self) -> nx.MultiDiGraph:
        """
        Escape hatch for OSMnx operations (plotting, saving, etc).
        Algorithms should not use this.
        """
        return self._g