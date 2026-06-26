# algorithms/base.py
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional
import networkx as nx

@dataclass
class SearchResult:
    path: list[int]           # ordered list of node IDs
    explored: list[int]       # nodes visited in exploration order (for animation)
    path_length_m: float      # total path length in metres
    nodes_explored: int
    runtime_ms: float

class PathfindingAlgorithm(ABC):
    """Abstract base for all pathfinding algorithms.
    
    To add a new algorithm:
    1. Subclass this
    2. Implement find_path()
    3. Register in AlgorithmRegistry
    That's it — the UI picks it up automatically.
    """

    def __init__(self, graph: nx.MultiDiGraph):
        self.graph = graph

    @abstractmethod
    def find_path(
        self,
        origin_node: int,
        destination_node: int,
    ) -> Optional[SearchResult]:
        """Find shortest path. Return None if no path exists."""
        ...

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable algorithm name for UI display."""
        ...

    def _reconstruct_path(
        self, came_from: dict[int, int], current: int
    ) -> list[int]:
        path = [current]
        while current in came_from:
            current = came_from[current]
            path.append(current)
        return list(reversed(path))

    def _path_length_m(self, path: list[int]) -> float:
        total = 0.0
        for u, v in zip(path, path[1:]):
            edge_data = self.graph.get_edge_data(u, v)
            # MultiDiGraph can have parallel edges; take the shortest
            lengths = [d.get('length', 0) for d in edge_data.values()]
            total += min(lengths)
        return total


# Simple registry so the UI can list available algorithms
class AlgorithmRegistry:
    _registry: dict[str, type[PathfindingAlgorithm]] = {}

    @classmethod
    def register(cls, algorithm_cls: type[PathfindingAlgorithm]):
        cls._registry[algorithm_cls.name.fget(None)] = algorithm_cls  # type: ignore
        return algorithm_cls

    @classmethod
    def get(cls, name: str) -> type[PathfindingAlgorithm]:
        return cls._registry[name]

    @classmethod
    def available(cls) -> list[str]:
        return list(cls._registry.keys())