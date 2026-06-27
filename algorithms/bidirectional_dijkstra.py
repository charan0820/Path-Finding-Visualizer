"""
Bidirectional Dijkstra on an OSM road network.

Runs two simultaneous Dijkstra searches:
  - Forward search  from origin      → expanding outward
  - Backward search from destination → expanding inward

Searches meet in the middle, cutting explored nodes roughly in half
compared to standard Dijkstra.

Meeting condition
-----------------
After each node expansion, check if the popped node has been visited
by the OTHER search. When it has, a candidate path is found.
We cannot stop immediately — a shorter path may exist through a
different meeting node. We stop when the sum of the two frontiers'
minimum f-scores exceeds the best candidate path found so far.

Time complexity  : O((V + E) log V) — same asymptotic as Dijkstra
                   but ~2x faster in practice on road networks
Space complexity : O(V)
"""

import heapq
import math
import time

from .base import PathfindingAlgorithm, SearchResult


class BidirectionalDijkstra(PathfindingAlgorithm):

    name = "Bidirectional Dijkstra"

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

        # Forward search structures
        g_fwd: dict[int, float]   = {origin_node: 0.0}
        open_fwd: list            = [(0.0, origin_node)]
        closed_fwd: set[int]      = set()
        came_from_fwd: dict[int, int] = {}

        # Backward search structures
        # Backward search uses REVERSED edges — neighbours in reverse graph
        g_bwd: dict[int, float]   = {destination_node: 0.0}
        open_bwd: list            = [(0.0, destination_node)]
        closed_bwd: set[int]      = set()
        came_from_bwd: dict[int, int] = {}

        # Best complete path found so far
        best_cost    = math.inf
        meeting_node = None
        explored: list[int] = []

        while open_fwd or open_bwd:
            # Alternate: expand one node from whichever frontier is cheaper
            fwd_min = open_fwd[0][0] if open_fwd else math.inf
            bwd_min = open_bwd[0][0] if open_bwd else math.inf

            # Stopping condition: frontiers have met and no cheaper path exists
            if fwd_min + bwd_min >= best_cost:
                break

            if fwd_min <= bwd_min:
                # Expand forward
                _, current = heapq.heappop(open_fwd)
                if current in closed_fwd:
                    continue
                closed_fwd.add(current)
                explored.append(current)

                for neighbor, edge_length in self.graph.get_neighbors(current):
                    if neighbor in closed_fwd:
                        continue
                    tentative_g = g_fwd[current] + edge_length
                    if tentative_g < g_fwd.get(neighbor, math.inf):
                        came_from_fwd[neighbor] = current
                        g_fwd[neighbor] = tentative_g
                        heapq.heappush(open_fwd, (tentative_g, neighbor))

                    # Check if backward search has already reached this neighbor
                    if neighbor in closed_bwd:
                        candidate = tentative_g + g_bwd[neighbor]
                        if candidate < best_cost:
                            best_cost    = candidate
                            meeting_node = neighbor

            else:
                # Expand backward (reverse graph — predecessors not successors)
                _, current = heapq.heappop(open_bwd)
                if current in closed_bwd:
                    continue
                closed_bwd.add(current)
                explored.append(current)

                for neighbor, edge_length in self._get_predecessors(current):
                    if neighbor in closed_bwd:
                        continue
                    tentative_g = g_bwd[current] + edge_length
                    if tentative_g < g_bwd.get(neighbor, math.inf):
                        came_from_bwd[neighbor] = current
                        g_bwd[neighbor] = tentative_g
                        heapq.heappush(open_bwd, (tentative_g, neighbor))

                    if neighbor in closed_fwd:
                        candidate = g_fwd[neighbor] + tentative_g
                        if candidate < best_cost:
                            best_cost    = candidate
                            meeting_node = neighbor

        if meeting_node is None:
            return None

        # Reconstruct path: forward half + backward half
        path = self._reconstruct_bidir_path(
            came_from_fwd, came_from_bwd,
            origin_node, destination_node, meeting_node,
        )

        elapsed_ms = (time.perf_counter() - start_time) * 1000
        return SearchResult(
            path=path,
            explored=explored,
            path_length_m=self._path_length_m(path),
            nodes_explored=len(explored),
            runtime_ms=elapsed_ms,
        )

    def _get_predecessors(self, node_id: int) -> list[tuple[int, float]]:
        """
        Return (predecessor, edge_length) for all incoming edges.
        Delegates to RoadGraph.get_predecessors() — no underlying_graph access needed.
        """
        return self.graph.get_predecessors(node_id)

    def _reconstruct_bidir_path(
        self,
        came_from_fwd: dict[int, int],
        came_from_bwd: dict[int, int],
        origin: int,
        destination: int,
        meeting_node: int,
    ) -> list[int]:
        """
        Stitch forward and backward paths at the meeting node.

        Forward half:  origin → meeting_node  (via came_from_fwd)
        Backward half: meeting_node → destination (via came_from_bwd,
                       which stores edges in reverse, so we reverse it)
        """
        # Forward half: walk came_from_fwd from meeting_node to origin
        fwd_path = [meeting_node]
        node = meeting_node
        while node in came_from_fwd:
            node = came_from_fwd[node]
            fwd_path.append(node)
        fwd_path.reverse()  # origin → meeting_node

        # Backward half: walk came_from_bwd from meeting_node to destination
        bwd_path = []
        node = meeting_node
        while node in came_from_bwd:
            node = came_from_bwd[node]
            bwd_path.append(node)
        # bwd_path is meeting_node+1 → destination (no need to reverse)

        return fwd_path + bwd_path