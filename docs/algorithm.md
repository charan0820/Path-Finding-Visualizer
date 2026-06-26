# A* Implementation Notes

This document explains the engineering decisions in `algorithms/astar.py`
in detail. It exists so interviewers can ask deep questions and get
honest, documented answers.

## Why A* over Dijkstra

Dijkstra explores nodes in order of distance from the origin — it fans
out in all directions equally. On a city road network with a known
destination, this wastes time exploring nodes in the wrong direction.

A\* adds a heuristic `h(n)` — an estimate of the remaining distance from
node `n` to the destination. The algorithm prioritises nodes with low
`f(n) = g(n) + h(n)`, where `g(n)` is the known cost from the origin.
With an admissible heuristic, A\* is guaranteed to find the optimal path
while exploring fewer nodes than Dijkstra.

The haversine heuristic is admissible because:

```
road_distance(n, goal) ≥ straight_line_distance(n, goal)
```

This holds for any road network (you cannot travel in a straight line
through buildings). Therefore `h(n) ≤ true_remaining_cost(n)` always,
and A\* optimality is guaranteed.

## The duplicate-entry heap strategy

When a shorter path to a node is discovered, we push a new entry onto
the heap rather than updating the existing one. This creates duplicate
entries, but avoids the O(n) cost of finding and updating an entry in an
unsorted structure.

Stale duplicates are harmless: when one is popped, the node is already
in the closed set, so we skip it immediately.

Alternative: use a decrease-key heap (e.g. a Fibonacci heap). This gives
O(1) decrease-key vs O(log n) for re-insertion. However:
- Python has no standard Fibonacci heap
- On real road networks the number of duplicates is small
- The implementation complexity is significant

The re-insertion strategy is used by most practical A\* implementations
including NetworkX's own `astar_path`.

## Stopping condition

We stop when the destination node is **popped from the open set**, not
when it is first discovered (added to the open set).

Stopping at discovery is incorrect: a node may be discovered via a
suboptimal path, and a better path may be found later. Popping from the
heap guarantees we have found the optimal path (all lower-cost nodes have
already been finalised).

## Heuristic implementation

```python
def _haversine_m(node_a, node_b) -> float:
    R = 6_371_000  # Earth radius in metres
    lat1, lon1 = math.radians(node_a.lat), math.radians(node_a.lng)
    lat2, lon2 = math.radians(node_b.lat), math.radians(node_b.lng)
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat/2)**2 + math.cos(lat1)*math.cos(lat2)*math.sin(dlon/2)**2
    return R * 2 * math.asin(math.sqrt(a))
```

Using the Euclidean distance in projected coordinates (metres) would also
work for small areas, but haversine is correct globally and the cost
is two extra trig calls per node expansion — negligible.

## Complexity analysis

Let V = number of nodes, E = number of edges.

- Each node is added to the heap at most once per incoming edge: O(E)
  heap insertions total.
- Each insertion/extraction is O(log |heap|) = O(log E) = O(log V)
  (since E ≤ V² for simple graphs).
- Total: **O((V + E) log V)**

Space: g\_score, came\_from, and closed\_set each store at most V entries.
The heap stores at most E entries. Total: **O(V + E)** = **O(E)**.

For the graphs used in this project (city neighbourhoods, 1,000–70,000
nodes), these bounds are comfortable on a laptop.