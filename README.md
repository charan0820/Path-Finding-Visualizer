# Pathfinding Visualizer on Real Road Networks

> A*, Dijkstra, Bidirectional Dijkstra, and Bidirectional BFS implemented
> from scratch on real OpenStreetMap road networks — with animated node
> exploration, performance metrics, and support for 9 cities.

[Architecture](#architecture) · [How it works](#how-it-works) · [Run locally](#run-locally)

## Demo

---

![Demo](assets/Demo.gif)

---

## Algorithms

| Algorithm | Strategy | Path Optimal | Notes |
|---|---|---|---|
| A\* | Heuristic-guided | ✅ | Fewest nodes explored |
| Dijkstra | Exhaustive by distance | ✅ | Baseline comparison |
| Bidirectional Dijkstra | Two frontiers meeting in middle | ✅ | ~2x faster than Dijkstra in practice |
| Bidirectional BFS | Two frontiers by hop count | ❌ | Fewest road segments, not shortest distance |

---

## Features

- Four pathfinding algorithms implemented from scratch — no routing libraries
- Real road networks downloaded directly from the Overpass API
- Animated node exploration showing each algorithm's search frontier in real time
- Per-algorithm performance metrics: path length, nodes explored, runtime, search efficiency
- Algorithm selector — switch between all four on the same coordinate pair to compare
- Fault-tolerant tiled download system — large cities split into N×N grid of tiles with retry and endpoint rotation
- Strongly connected component extraction — guarantees a valid path always exists between any two points
- Coordinate bounds validation per city — clear error messages before search runs
- Deployed on Streamlit Cloud with 9 preloaded cities

---

## Supported Cities

| City | Approx Nodes | Approx Edges |
|---|---|---|
| Piedmont, California, USA | ~2,000 | ~4,000 |
| Cambridge, UK | ~5,000 | ~11,000 |
| Amsterdam, Netherlands | ~18,000 | ~38,000 |
| Shibuya, Tokyo, Japan | ~8,000 | ~17,000 |
| Manhattan, New York, USA | ~30,000 | ~70,000 |
| London, UK | ~25,000 | ~55,000 |
| Paris, France | ~20,000 | ~45,000 |
| Berlin, Germany | ~22,000 | ~48,000 |
| Barcelona, Spain | ~12,000 | ~26,000 |

---

## Architecture

```
pathfinding-visualizer/
│
├── algorithms/
│   ├── base.py                    # Abstract PathfindingAlgorithm + SearchResult
│   ├── astar.py                   # A* with haversine heuristic
│   ├── dijkstra.py                # Dijkstra — no heuristic
│   ├── bidirectional_dijkstra.py  # Two Dijkstra frontiers meeting in middle
│   └── bidirectional_bfs.py       # Two BFS frontiers by hop count
│
├── graph/
│   ├── loader.py                  # Tiled Overpass download, SCC extraction, cache
│   └── builder.py                 # RoadGraph interface over NetworkX MultiDiGraph
│
├── visualization/
│   ├── map_view.py                # Folium map rendering
│   └── animation.py               # Streamlit progressive frame animation
│
├── metrics/
│   └── performance.py             # SearchMetrics dataclass + derived stats
│
├── ui/
│   ├── state.py                   # Centralised Streamlit session state
│   ├── app.py                     # Main app shell and render logic
│   └── components.py              # Sidebar: city loader, coordinate input, validation
│
├── tests/
│   ├── conftest.py                # FakeRoadGraph fixtures — no network required
│   ├── test_astar.py
│   ├── test_dijkstra.py
│   ├── test_bidirectional.py
│   ├── test_heuristic.py
│   └── test_metrics.py
│
├── requirements.txt
├── packages.txt
└── main.py
```

### Data flow

```
Overpass API  ──►  graph/loader.py
                   ┌──────────────────────────────────────┐
                   │ 1. Check GraphML cache                │
                   │ 2. Split bbox into N×N tiles          │
                   │ 3. Query each tile via Overpass QL    │
                   │    · 3 retries per tile               │
                   │    · 3-endpoint rotation              │
                   │    · Parse OSM XML → NetworkX graph   │
                   │ 4. Merge all tiles                    │
                   │ 5. Extract largest SCC                │
                   │ 6. Save to GraphML cache              │
                   └──────────────────────────────────────┘
                          │
                          ▼
               graph/builder.py  ──►  RoadGraph interface
                          │
                          ▼
               algorithms/       ──►  SearchResult
               (A*, Dijkstra,          path, explored,
                Bidir Dijkstra,        path_length_m,
                Bidir BFS)             nodes_explored,
                          │            runtime_ms
                    ┌─────┴──────┐
                    ▼            ▼
            visualization/   metrics/
            map_view.py      performance.py
                    │            │
                    └─────┬──────┘
                          ▼
                      ui/app.py  ──►  Streamlit
```

---

## How it works

### Graph representation

Road networks are downloaded via direct Overpass API queries — bypassing
OSMnx's area size limits which caused connection drops on large cities.
Each city is split into an N×N grid of tiles, each queried separately as
OSM XML, parsed with `ox.graph_from_xml`, and merged with
`nx.compose_all`. After merging, the largest strongly connected component
is extracted, guaranteeing any two nodes are mutually reachable.

The merged graph is stored as a NetworkX `MultiDiGraph` — a directed graph
where nodes are road intersections and edges are road segments with a
`length` attribute in metres. One-way streets are directed edges, handled
correctly by all four algorithms. The graph is cached as GraphML after
first load — subsequent loads are instant.

### A\*

Maintains a min-heap open set keyed on `f(n) = g(n) + h(n)`, where `g(n)`
is the known cost from origin and `h(n)` is the haversine distance to the
destination. The haversine heuristic is admissible — it never overestimates
true road distance — so A\* is guaranteed to find the optimal path while
expanding fewer nodes than Dijkstra.

### Dijkstra

Identical to A\* with `h(n) = 0`. Priority is `g(n)` only — explores nodes
in order of true distance from origin, fanning out in all directions equally.
Always finds the optimal path. Useful as a correctness baseline and to
visually demonstrate why a heuristic matters.

### Bidirectional Dijkstra

Runs two simultaneous Dijkstra searches — forward from origin, backward
from destination using reversed edges. Searches alternate, always expanding
the cheaper frontier. A candidate path is recorded when a node appears in
both closed sets. The search terminates when the sum of both frontiers'
minimum costs exceeds the best candidate — guaranteeing optimality. Explores
roughly half the nodes of standard Dijkstra in practice.

### Bidirectional BFS

Runs two simultaneous BFS searches by hop count rather than edge weight.
Finds the path with the fewest road segments, not the shortest distance —
so the result may differ from the other three algorithms. Useful for
illustrating the difference between hop-optimal and distance-optimal paths.

### Algorithm comparison

| | A\* | Dijkstra | Bidir Dijkstra | Bidir BFS |
|---|---|---|---|---|
| Heuristic | Haversine | None | None | None |
| Search direction | Forward | Forward | Both | Both |
| Optimises for | Distance | Distance | Distance | Hops |
| Path optimal by distance | ✅ | ✅ | ✅ | ❌ |
| Nodes explored | Fewest | Most | ~Half of Dijkstra | Varies |
| Time complexity | O((V+E) log V) | O((V+E) log V) | O((V+E) log V) | O(V+E) |

### Adding a new algorithm

```python
# algorithms/your_algorithm.py
from algorithms.base import PathfindingAlgorithm, SearchResult

class YourAlgorithm(PathfindingAlgorithm):
    name = "Your Algorithm"

    def find_path(self, origin_node, destination_node):
        # implement here
        ...
```

Then one line in `ui/app.py`:

```python
ALGORITHM_REGISTRY = {
    "A*":                     AStarPathfinder,
    "Dijkstra":               DijkstraPathfinder,
    "Bidirectional Dijkstra": BidirectionalDijkstra,
    "Bidirectional BFS":      BidirectionalBFS,
    "Your Algorithm":         YourAlgorithm,   # ← done
}
```

The UI, visualization, metrics, and animation all work automatically.

---

## Run locally

```bash
git clone https://github.com/your-username/pathfinding-visualizer
cd pathfinding-visualizer

python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt

streamlit run main.py
```

Open `http://localhost:8501`.

First load downloads the road network (~1–5 minutes depending on city).
Subsequent loads are instant from the local GraphML cache.

### Run tests

```bash
pytest tests/ -v
# 53 tests, all synthetic graphs, no network access, under 5 seconds
```

---

## Tech stack

| Layer | Library | Why |
|---|---|---|
| Road data | Overpass API (direct) | Bypasses OSMnx area limits for large cities |
| Graph parsing | OSMnx 1.9+ | `graph_from_xml` for OSM → NetworkX conversion |
| Graph | NetworkX 3.2+ | MultiDiGraph for directed, one-way street support |
| Nearest node | scikit-learn 1.4+ | Spatial index for O(log n) coordinate snapping |
| Visualization | Folium 0.15+ | Leaflet.js interactive maps as self-contained HTML |
| UI | Streamlit 1.31+ | Interactive app with free cloud deployment |
| Algorithms | Pure Python + heapq | No routing library — all implemented from scratch |

---

## Performance

Tested on a standard laptop. First load times are one-time — subsequent
loads are instant from cache.

| City | Nodes | A\* | Dijkstra | Bidir Dijkstra |
|---|---|---|---|---|
| Piedmont, CA | ~2,000 | < 10ms | < 20ms | < 10ms |
| Cambridge, UK | ~5,000 | < 30ms | < 60ms | < 30ms |
| Amsterdam | ~18,000 | < 100ms | < 250ms | < 120ms |
| Manhattan | ~30,000 | < 200ms | < 500ms | < 220ms |

---

## What I learned

- Implementing four pathfinding algorithms from scratch with correct
  stopping conditions, tie-breaking, and optimality guarantees
- Building a fault-tolerant tiled Overpass API download pipeline with
  retry logic, three-endpoint rotation, and automatic cache invalidation
- Strongly connected component extraction to guarantee path existence
  on merged multi-tile graphs with one-way streets
- Designing a modular algorithm interface where new algorithms plug in
  with zero changes to the UI, visualization, or metrics layers
- Streamlit session state management for multi-step interactive apps
  with algorithm switching and result caching
- Writing a test suite that runs in under 5 seconds with no network
  access using synthetic fixture graphs

---

## Resume bullets

```
- Implemented A*, Dijkstra, Bidirectional Dijkstra, and Bidirectional BFS
  from scratch on real OpenStreetMap road networks; animated node exploration
  on interactive Leaflet.js maps via Folium and Streamlit — live at [url]

- Built a fault-tolerant tiled Overpass API download system with automatic
  retry, three-endpoint rotation, and strongly connected component extraction
  to guarantee valid paths on city-scale graphs of 30,000+ nodes across 9 cities

- Designed a modular algorithm architecture with an abstract base class —
  new algorithms register in one line with zero changes to UI, visualization,
  or metrics layers; validated with 53 pytest tests on synthetic graphs
```

---

## Future extensions

- [ ] Jump Point Search — order-of-magnitude speedup on uniform grids
- [ ] D\* Lite — dynamic replanning when edge weights change
- [ ] Bidirectional A\* — combine heuristic guidance with two-frontier search
- [ ] Algorithm comparison mode — run two algorithms side by side on the same query
- [ ] Isochrone maps — all nodes reachable within N minutes
- [ ] Turn restrictions — model `via` relations from OSM data

---

## License

MIT
