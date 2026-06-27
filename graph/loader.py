"""
Handles downloading and caching road network data from OpenStreetMap.
"""

import logging
import time
from pathlib import Path

import osmnx as ox
import networkx as nx

import tempfile
import os
import requests
import io

log = logging.getLogger(__name__)

ox.settings.use_cache = True
ox.settings.log_console = False
ox.settings.requests_timeout = 300
ox.settings.overpass_rate_limit = False
# This must be tiny — OSMnx subdivides automatically when exceeded
# 1 degree² ≈ 12,000 km² — set to ~0.01 degree² per sub-query
ox.settings.max_query_area_size = 10_000_000  # ~0.1 degree²

# Use a more reliable Overpass endpoint
ox.settings.overpass_url = "https://overpass.kumi.systems/api/interpreter"


# Tight bounding boxes for known large cities (north, south, east, west)
# These cover only the urban core, not the entire administrative region
# which is what Nominatim returns and causes the "474x too large" error
CITY_BBOXES: dict[str, tuple[float, float, float, float]] = {
    "amsterdam, netherlands":       (52.395, 52.340, 4.940,    4.840),
    "manhattan, new york, usa":     (40.800, 40.720, -73.940, -74.010),
    "shibuya, tokyo, japan":        (35.668, 35.648, 139.715, 139.685),
    "london, uk":                   (51.530, 51.470, -0.070,  -0.170),
    "paris, france":                (48.880, 48.830,  2.380,   2.290),
    "berlin, germany":              (52.545, 52.480, 13.450,  13.340),
    "barcelona, spain":             (41.415, 41.365,  2.205,   2.130),
    # Small cities — use tight bbox to avoid Overpass hanging
    "piedmont, california, usa":    (37.835, 37.810, -122.210, -122.250),
    "cambridge, uk":                (52.230, 52.185,   0.155,    0.085),
}

CITY_GRID_SIZE: dict[str, int] = {
    "amsterdam, netherlands":   4,
    "manhattan, new york, usa": 4,
    "shibuya, tokyo, japan":    3,
    "london, uk":               4,
    "paris, france":            3,
    "berlin, germany":          3,
    "barcelona, spain":         3,
    # Small cities only need 2x2 = 4 tiles
    "piedmont, california, usa": 2,
    "cambridge, uk":             2,
}

def load_graph(
    place_name: str,
    cache_dir: str = "data",
    network_type: str = "drive",
) -> nx.MultiDiGraph:
    cache_path = _cache_path(place_name, cache_dir)

    if cache_path.exists():
        log.info(f"Loading cached graph: {cache_path}")
        graph = ox.load_graphml(cache_path)

        if not nx.is_strongly_connected(graph):
            log.warning(
                f"Cached graph not strongly connected "
                f"({nx.number_strongly_connected_components(graph)} components). "
                f"Deleting and redownloading..."
            )
            cache_path.unlink()
            return load_graph(place_name, cache_dir, network_type)

        _log_graph_stats(graph, place_name)
        return graph

    log.info(f"Downloading road network for '{place_name}' from OSM...")

    place_key  = place_name.lower().strip()
    matched_key = next((k for k in CITY_BBOXES if k == place_key), None)

    if matched_key:
        bbox      = CITY_BBOXES[matched_key]
        grid_size = CITY_GRID_SIZE.get(matched_key, 2)
        log.info(
            f"Using hardcoded bbox for '{place_name}' "
            f"with {grid_size}x{grid_size} grid"
        )
        graph = _load_tiled(bbox, grid_size, network_type)
    else:
        log.info(f"No hardcoded bbox for '{place_name}' — using tiled geocoded bbox")
        bbox = _get_bbox_from_geocoder(place_name)
        if bbox is None:
            raise ConnectionError(
                f"Could not find '{place_name}' in OpenStreetMap. "
                "Check spelling or try a more specific name."
            )
        graph = _load_tiled(bbox, grid_size=2, network_type=network_type)

    # Final SCC extraction before caching
    if not nx.is_strongly_connected(graph):
        log.warning(
            f"Graph has {nx.number_strongly_connected_components(graph)} "
            f"components — extracting largest SCC..."
        )
        largest_scc = max(nx.strongly_connected_components(graph), key=len)
        graph = graph.subgraph(largest_scc).copy()
        log.info(
            f"After SCC extraction: {graph.number_of_nodes():,} nodes, "
            f"{graph.number_of_edges():,} edges"
        )

    # DO NOT call ox.add_edge_speeds or ox.add_edge_travel_times
    # — these make additional Overpass requests and hang
    # Edge lengths from the OSM XML are sufficient for A* and Dijkstra

    assert nx.is_strongly_connected(graph), \
        "Graph still not strongly connected after SCC extraction"

    cache_path.parent.mkdir(parents=True, exist_ok=True)
    ox.save_graphml(graph, cache_path)
    log.info(f"Cached to {cache_path}")

    _log_graph_stats(graph, place_name)
    return graph


def _load_tiled(
    bbox: tuple[float, float, float, float],
    grid_size: int,
    network_type: str,
) -> nx.MultiDiGraph:
    log.info("DEBUG: entered _load_tiled")
    log.info("DEBUG: entered _download_tile_with_retry")
    log.info("DEBUG: about to POST to Overpass")
    log.info("DEBUG: POST complete, parsing response")
    log.info("DEBUG: about to call ox.graph_from_xml")
    log.info("DEBUG: graph_from_xml complete")
    north, south, east, west = bbox
    lat_step = (north - south) / grid_size
    lng_step = (east - west) / grid_size

    graphs = []
    total_tiles = grid_size * grid_size

    for row in range(grid_size):
        for col in range(grid_size):
            tile_south = south + row * lat_step
            tile_north = tile_south + lat_step
            tile_west  = west  + col * lng_step
            tile_east  = tile_west + lng_step

            tile_num = row * grid_size + col + 1
            log.info(
                f"Tile {tile_num}/{total_tiles}: "
                f"N{tile_north:.4f} S{tile_south:.4f} "
                f"E{tile_east:.4f} W{tile_west:.4f}"
            )

            tile_graph = _download_tile_with_retry(
                north=tile_north,
                south=tile_south,
                east=tile_east,
                west=tile_west,
                network_type=network_type,
            )

            if tile_graph is not None:
                graphs.append(tile_graph)

            if tile_num < total_tiles:
                time.sleep(3)

    if not graphs:
        raise ConnectionError(
            "All tile downloads failed. "
            "The Overpass API may be overloaded — try again in a few minutes."
        )

    log.info(f"Merging {len(graphs)}/{total_tiles} tiles...")
    combined = nx.compose_all(graphs)

    # Simplify once after merge
    log.info("Simplifying merged graph...")
    combined = ox.simplify_graph(combined)

    # Extract largest strongly connected component
    # This fixes "no path found" errors caused by disconnected nodes
    # at tile boundaries — guarantees any two nodes are mutually reachable
    log.info("Extracting largest strongly connected component...")
    strongly_connected = [
        c for c in nx.strongly_connected_components(combined)
    ]
    largest = max(strongly_connected, key=len)
    combined = combined.subgraph(largest).copy()

    log.info(
        f"Final graph: {combined.number_of_nodes():,} nodes, "
        f"{combined.number_of_edges():,} edges "
        f"({len(strongly_connected)} components found, kept largest)"
    )

    return combined

OVERPASS_ENDPOINTS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter", 
    "https://maps.mail.ru/osm/tools/overpass/api/interpreter",
]


def _download_tile_with_retry(
    north: float,
    south: float,
    east: float,
    west: float,
    network_type: str,
    max_retries: int = 3,
    retry_delay_s: float = 30.0,
) -> nx.MultiDiGraph | None:
    way_filter = _network_type_to_filter(network_type)
    query = f"""
    [out:xml][timeout:180][bbox:{south},{west},{north},{east}];
    (
        way[{way_filter}];
    );
    out body;
    >;
    out skel qt;
    """

    for attempt in range(1, max_retries + 1):
        endpoint = OVERPASS_ENDPOINTS[(attempt - 1) % len(OVERPASS_ENDPOINTS)]
        log.info(f"  Attempt {attempt}/{max_retries} via {endpoint}")

        try:
            response = requests.post(
                endpoint,
                data={"data": query},
                timeout=180,
                headers={
                    "Content-Type": "application/x-www-form-urlencoded",
                    "User-Agent": "pathfinding-visualizer/1.0",
                },
            )

            if response.status_code == 429:
                wait = 60 if attempt == 1 else 120
                log.warning(f"  Rate limited — waiting {wait}s before retry...")
                time.sleep(wait)
                continue

            response.raise_for_status()

            content = response.text

            if "<osm" not in content:
                log.warning("  Unexpected response — not OSM XML")
                time.sleep(retry_delay_s)
                continue

            if "<way" not in content and "<node" not in content:
                log.warning("  Empty tile — no roads in this bbox")
                return None

            # Write to temp file — graph_from_xml requires a filepath
            with tempfile.NamedTemporaryFile(
                mode="w",
                suffix=".osm",
                encoding="utf-8",
                delete=False,
            ) as tmp:
                tmp.write(content)
                tmp_path = tmp.name

            try:
                graph = ox.graph_from_xml(tmp_path, simplify=False, retain_all=False)
                log.info(f"  Tile OK: {graph.number_of_nodes()} nodes")
                return graph
            finally:
                os.unlink(tmp_path)

        except Exception as e:
            log.warning(f"  Attempt {attempt}/{max_retries} failed: {e}")
            if attempt < max_retries:
                log.info(f"  Retrying in {retry_delay_s}s...")
                time.sleep(retry_delay_s)
            else:
                log.error("  All attempts failed for this tile.")
                return None

def _network_type_to_filter(network_type: str) -> str:
    """Convert OSMnx network_type string to Overpass way filter."""
    filters = {
        "drive": '"highway"~"motorway|trunk|primary|secondary|tertiary|residential|unclassified|living_street|service"',
        "walk":  '"highway"~"footway|path|pedestrian|steps|corridor|living_street|residential|service|track"',
        "bike":  '"highway"~"cycleway|path|footway|residential|service|track|living_street"',
        "all":   '"highway"',
    }
    return filters.get(network_type, filters["drive"])


def _get_bbox_from_geocoder(
    place_name: str,
) -> tuple[float, float, float, float] | None:
    """
    Geocode a place and return a tight bounding box.
    Used as fallback for unknown cities not in CITY_BBOXES.
    """
    try:
        from geopy.geocoders import Nominatim
        geolocator = Nominatim(user_agent="pathfinding-visualizer")
        location = geolocator.geocode(place_name, exactly_one=True, timeout=30)

        if location is None:
            return None

        # Use a fixed ~4km radius instead of the admin boundary
        # Admin boundaries from Nominatim are often country/region sized
        lat, lng = location.latitude, location.longitude
        delta = 0.036  # ~4km in degrees
        return lat + delta, lat - delta, lng + delta, lng - delta

    except Exception as e:
        log.error(f"Geocoding failed for '{place_name}': {e}")
        return None


def get_nearest_node(graph: nx.MultiDiGraph, lat: float, lng: float) -> int:
    try:
        node = ox.nearest_nodes(graph, X=lng, Y=lat)
        log.info(f"Nearest node to ({lat}, {lng}): {node}")
        return node
    except Exception as e:
        log.error(f"nearest_nodes failed: {e}")
        raise RuntimeError(
            f"Could not snap ({lat}, {lng}) to the road network. "
            f"Detail: {e}"
        ) from e


def _cache_path(place_name: str, cache_dir: str) -> Path:
    safe_name = place_name.lower().strip().replace(",", "").replace(" ", "_")
    return Path(cache_dir) / f"{safe_name}.graphml"


def _log_graph_stats(graph: nx.MultiDiGraph, place_name: str) -> None:
    nodes = graph.number_of_nodes()
    edges = graph.number_of_edges()
    log.info(f"Graph for '{place_name}': {nodes:,} nodes, {edges:,} edges")