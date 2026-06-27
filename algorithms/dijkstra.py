"""
Dijkstra's algorithm on an OSM road network.

Differences from A*:
- No heuristic — h(n) = 0 always
- Explores nodes in order of true distance from origin only
- Guaranteed optimal but explores more nodes than A* on average
- Useful as a correctness baseline: any path A* finds, Dijkstra finds too

Data structures
---------------
open_set   : min-heap of (g_score, node_id) — same as A* but keyed on
             g_score only, since there is no heuristic to add
closed_set : set of finalised node IDs
g_score    : dict of best known costs from origin
came_from  : dict of predecessor pointers for path reconstruction

Time complexity  : O((V + E) log V)
Space complexity : O(V)
"""

import heapq
import math
import time

from .base import PathfindingAlgorithm, SearchResult


class DijkstraPathfinder(PathfindingAlgorithm):

    name = "Dijkstra"

    def find_path(
        self,
        origin_node: int,
        destination_node: int,
    ) -> SearchResult | None:

        start_time = time.perf_counter()

        if not self.graph.has_node(origin_node):
            raise ValueError(f"Origin node {origin_node} not in graph")
        if not self.graph.has_node(destination_node):
            raise ValueError(f"Destination node {destination_node} not in graph")

        if origin_node == destination_node:
            return SearchResult(
                path=[origin_node],
                explored=[origin_node],
                path_length_m=0.0,
                nodes_explored=1,
                runtime_ms=0.0,
            )

        # g_score[n] = cheapest known cost from origin to n
        g_score: dict[int, float] = {origin_node: 0.0}

        # open_set entries: (g_score, node_id)
        # No heuristic — priority is distance from origin only
        open_set: list[tuple[float, int]] = [(0.0, origin_node)]

        closed_set: set[int] = set()
        came_from: dict[int, int] = {}
        explored: list[int] = []

        while open_set:
            current_g, current = heapq.heappop(open_set)

            # Skip stale heap entries
            if current in closed_set:
                continue

            closed_set.add(current)
            explored.append(current)

            if current == destination_node:
                path = self._reconstruct_path(came_from, current)
                elapsed_ms = (time.perf_counter() - start_time) * 1000
                return SearchResult(
                    path=path,
                    explored=explored,
                    path_length_m=self._path_length_m(path),
                    nodes_explored=len(explored),
                    runtime_ms=elapsed_ms,
                )

            for neighbor, edge_length in self.graph.get_neighbors(current):
                if neighbor in closed_set:
                    continue

                tentative_g = g_score[current] + edge_length

                if tentative_g < g_score.get(neighbor, math.inf):
                    came_from[neighbor] = current
                    g_score[neighbor] = tentative_g
                    heapq.heappush(open_set, (tentative_g, neighbor))

        return None