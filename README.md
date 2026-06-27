# A* & Dijkstra Pathfinding Visualizer on Real Road Networks

> A* and Dijkstra pathfinding implemented from scratch on real OpenStreetMap 
> road networks, with animated node exploration, performance metrics, and 
> support for 9 cities — built entirely in Python.

**[▶ Live Demo](https://your-app.streamlit.app)** · [Architecture](#architecture) · [How it works](#how-it-works) · [Run locally](#run-locally)

---

![Demo](assets/demo.gif)

---

## Features

- A\* and Dijkstra implemented from scratch — no routing libraries
- Real road networks from OpenStreetMap via a custom tiled Overpass API download system
- Animated node exploration showing the search frontier expanding in real time
- Side-by-side algorithm comparison — see how A\* and Dijkstra differ in nodes explored
- Performance metrics: path length, nodes explored, runtime, search efficiency
- Coordinate bounds validation per city — clear error messages for out-of-range inputs
- Strongly connected component extraction — guarantees a valid path always exists
- Modular architecture — new algorithms plug in by subclassing one abstract class
- Deployed on Streamlit Cloud with 9 preloaded cities

---

## Demo

![Pathfinding Animation](assets/demo.gif)

For a full walkthrough, watch the demo video:

**[▶ Watch on YouTube](https://youtube.com/your-video-link)**

---

## Supported Cities

| City | Nodes | Edges |
|---|---|---|
| Piedmont, California, USA | ~2,000 | ~4,000 |
| Cambridge, UK | ~5,000 | ~11,000 |
| Amsterdam, Netherlands | ~18,000 | ~38,000 |
| Manhattan, New York, USA | ~30,000 | ~70,000 |
| Shibuya, Tokyo, Japan | ~8,000 | ~17,000 |
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
│   ├── base.py          # Abstract PathfindingAlgorithm + SearchResult dataclass
│   ├── astar.py         # A* with haversine heuristic, min-heap, closed-set filtering
│   └── dijkstra.py      # Dijkstra — optimal, no heuristic, explores more nodes than A*
│
├── graph/
│   ├── loader.py        # Tiled Overpass API download, SCC extraction, GraphML cache
│   └── builder.py       # RoadGraph interface over NetworkX MultiDiGraph
│
├── visualization/
│   ├── map_view.py      # Folium map rendering (explored nodes + path overlay)
│   └── animation.py     # Streamlit progressive frame animation driver
│
├── metrics/
│   └── performance.py   # SearchMetrics dataclass + derived statistics
│
├── ui/
│   ├── state.py         # Centralised Streamlit session state management
│   ├── app.py           # Main Streamlit app shell and render logic
│   └── components.py    # Sidebar: city loader, coordinate input, bounds validation
│
├── tests/
│   ├── conftest.py      # FakeRoadGraph fixtures — no network, no OSM
│   ├── test_astar.py    # Correctness, optimality, edge cases
│   ├── test_dijkstra.py # Correctness + comparison against A* path lengths
│   ├── test_heuristic.py# Haversine admissibility proof via unit tests
│   └── test_metrics.py  # SearchMetrics derivation and formatting
│
├── requirements.txt
├── packages.txt         # System deps for Streamlit Cloud (libspatialindex)
└── main.py              # Entry point: streamlit run main.py
```

### Data flow

```
OSM / GraphML cache
       │
       ▼
  graph/loader.py
  ┌─────────────────────────────────────────┐
  │ 1. Check GraphML cache                  │
  │ 2. If miss → tile bbox into N×N grid    │
  │ 3. Query each tile directly via Overpass│
  │    - 3 retries, 3 endpoint rotation     │
  │    - Write XML to temp file             │
  │    - Parse with ox.graph_from_xml       │
  │ 4. Merge tiles with nx.compose_all      │
  │ 5. Extract largest SCC                  │
  │ 6. Save to GraphML cache                │
  └─────────────────────────────────────────┘
       │
       ▼
  graph/builder.py         RoadGraph — clean interface for algorithm layer
       │
       ▼
  algorithms/              A* or Dijkstra → SearchResult
       │            │
       ▼            ▼
visualization/   metrics/
map_view.py      performance.py
       │            │
       └─────┬──────┘
             ▼
         ui/app.py          Streamlit shell — wires everything together
```

---

## How it works

### Graph representation

OpenStreetMap road data is downloaded via direct Overpass API queries and 
stored as a NetworkX `MultiDiGraph` — a directed graph where nodes are road 
intersections and edges are road segments with a `length` attribute in metres. 
One-way streets are directed edges, handled correctly by both algorithms.

Large cities are split into an N×N grid of tiles. Each tile is queried 
separately, parsed from OSM XML, then merged. After merging, the largest 
strongly connected component is extracted — this guarantees any two nodes 
in the final graph are mutually reachable.

### A\* algorithm

Maintains a min-heap open set keyed on `f(n) = g(n) + h(n)`, where `g(n)` 
is the known cost from origin and `h(n)` is the haversine distance to the 
destination. The haversine heuristic is admissible — it never overestimates, 
so A\* is guaranteed to find the optimal path while exploring fewer nodes 
than Dijkstra.

**Time complexity:** O((V + E) log V) · **Space complexity:** O(V)

### Dijkstra's algorithm

Identical to A\* but with `h(n) = 0` — priority is `g(n)` only. Explores 
nodes in order of true distance from origin, fanning out in all directions 
equally. Always finds the optimal path but typically explores more nodes 
than A\* on geographic graphs.

**Time complexity:** O((V + E) log V) · **Space complexity:** O(V)

### Algorithm comparison

| | A\* | Dijkstra |
|---|---|---|
| Heuristic | Haversine distance | None |
| Nodes explored | Fewer (guided) | More (exhaustive) |
| Path optimality | Guaranteed | Guaranteed |
| Best for | Single destination | All destinations |

### Extending with a new algorithm

```python
# algorithms/your_algorithm.py
from algorithms.base import PathfindingAlgorithm, SearchResult

class YourAlgorithm(PathfindingAlgorithm):
    name = "Your Algorithm"

    def find_path(self, origin_node, destination_node):
        # implement here
        ...
```

Then add one line to `ALGORITHM_REGISTRY` in `ui/app.py`:

```python
ALGORITHM_REGISTRY = {
    "A*":             AStarPathfinder,
    "Dijkstra":       DijkstraPathfinder,
    "Your Algorithm": YourAlgorithm,     # ← one line
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

**First run:** downloads the road network from OpenStreetMap (~1–5 minutes 
depending on city size). Subsequent runs load from local cache instantly.

### Run tests

```bash
pytest tests/ -v
# All tests use synthetic graphs — no network access, runs in under 5 seconds
```

---

## Tech stack

| Layer | Library | Why |
|---|---|---|
| Road data | Overpass API (direct) | Bypasses OSMnx area size limits for large cities |
| Graph parsing | OSMnx 1.9+ | `graph_from_xml` for clean OSM → NetworkX conversion |
| Graph | NetworkX 3.2+ | MultiDiGraph for one-way streets |
| Nearest node | scikit-learn 1.4+ | Spatial index for O(log n) coordinate snapping |
| Visualization | Folium 0.15+ | Leaflet.js interactive maps |
| UI | Streamlit 1.31+ | Fast interactive apps, free cloud deployment |
| Algorithms | Pure Python | No routing library — implemented from scratch |

---

## Performance

| City | Nodes | A\* runtime | Dijkstra runtime | A\* nodes explored |
|---|---|---|---|---|
| Piedmont, CA | ~2,000 | < 10ms | < 15ms | 100–400 |
| Cambridge, UK | ~5,000 | < 30ms | < 50ms | 200–800 |
| Amsterdam | ~18,000 | < 100ms | < 200ms | 500–2,000 |
| Manhattan | ~30,000 | < 200ms | < 400ms | 1,000–5,000 |

---

## What I learned

- Implementing A\* and Dijkstra with correct tie-breaking, stale-entry 
  filtering, and admissible heuristic selection for geographic coordinates
- Building a fault-tolerant tiled download system with retry logic, 
  endpoint rotation, and automatic fallback for large city road networks
- Strongly connected component extraction to guarantee path existence 
  across merged multi-tile graphs
- Modular Python architecture with strict layer separation — algorithms 
  never import from UI, UI never imports from graph layer
- Streamlit session state management for multi-step interactive apps
- Writing a test suite that runs without network access using synthetic 
  fixture graphs

---

## Future extensions

- [ ] Bidirectional A\* — search from both ends simultaneously
- [ ] Jump Point Search — order-of-magnitude speedup on uniform grids
- [ ] D\* Lite — dynamic replanning when edge weights change
- [ ] Algorithm comparison mode — run two algorithms side by side on the same query
- [ ] Turn restrictions — model `via` relations from OSM data
- [ ] Isochrone maps — all nodes reachable within N minutes

---

## License

MIT