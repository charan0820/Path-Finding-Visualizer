"""
Bidirectional BFS on an OSM road network.

Runs two simultaneous BFS searches:
  - Forward  from origin
  - Backward from destination

BFS explores by hop count (number of edges), not edge weight.
The meeting path minimises number of road segments, NOT distance.
This means the path is NOT guaranteed to be the shortest by distance.

Use case on road networks:
  Finds the path with fewest turns/intersections — useful for
  comparing against A* and Dijkstra to show the difference between
  hop-optimal and distance-optimal paths.

Time complexity  : O(V + E)   — no heap, just queues
Space complexity : O(V)
"""

import time
from collections import deque

from .base import PathfindingAlgorithm, SearchResult


class BidirectionalBFS(PathfindingAlgorithm):

    name = "Bidirectional BFS"

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

        # Forward BFS
        queue_fwd: deque[int]         = deque([origin_node])
        visited_fwd: set[int]         = {origin_node}
        came_from_fwd: dict[int, int] = {}

        # Backward BFS
        queue_bwd: deque[int]         = deque([destination_node])
        visited_bwd: set[int]         = {destination_node}
        came_from_bwd: dict[int, int] = {}

        explored: list[int] = []
        meeting_node: int | None = None

        while queue_fwd or queue_bwd:

            # Expand one level of forward BFS
            if queue_fwd:
                meeting_node = self._expand_bfs_level(
                    queue=queue_fwd,
                    visited_this=visited_fwd,
                    visited_other=visited_bwd,
                    came_from=came_from_fwd,
                    explored=explored,
                    forward=True,
                )
                if meeting_node is not None:
                    break

            # Expand one level of backward BFS
            if queue_bwd:
                meeting_node = self._expand_bfs_level(
                    queue=queue_bwd,
                    visited_this=visited_bwd,
                    visited_other=visited_fwd,
                    came_from=came_from_bwd,
                    explored=explored,
                    forward=False,
                )
                if meeting_node is not None:
                    break

        if meeting_node is None:
            return None

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

    def _expand_bfs_level(
        self,
        queue: deque,
        visited_this: set,
        visited_other: set,
        came_from: dict,
        explored: list,
        forward: bool,
    ) -> int | None:
        """
        Expand one node from the queue.
        Returns the meeting node if the frontiers have intersected, else None.
        """
        if not queue:
            return None

        current = queue.popleft()
        explored.append(current)

        neighbors = (
            self.graph.get_neighbors(current)
            if forward
            else self._get_predecessors(current)
        )

        for neighbor, _ in neighbors:
            if neighbor in visited_this:
                continue
            visited_this.add(neighbor)
            came_from[neighbor] = current
            queue.append(neighbor)

            if neighbor in visited_other:
                return neighbor  # frontiers met

        return None

    def _get_predecessors(self, node_id: int) -> list[tuple[int, float]]:
        """Return (predecessor, edge_length) for all incoming edges."""
        return self.graph.get_predecessors(node_id)

    def _reconstruct_bidir_path(
        self,
        came_from_fwd: dict[int, int],
        came_from_bwd: dict[int, int],
        origin: int,
        destination: int,
        meeting_node: int,
    ) -> list[int]:
        # Forward half: meeting_node → origin, then reverse
        fwd_path = [meeting_node]
        node = meeting_node
        while node in came_from_fwd:
            node = came_from_fwd[node]
            fwd_path.append(node)
        fwd_path.reverse()

        # Backward half: meeting_node → destination
        bwd_path = []
        node = meeting_node
        while node in came_from_bwd:
            node = came_from_bwd[node]
            bwd_path.append(node)

        return fwd_path + bwd_path