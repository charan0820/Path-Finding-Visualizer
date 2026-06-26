# graph/loader.py
"""
Handles downloading and caching road network data from OpenStreetMap.

OSMnx is used because it handles:
  - Overpass API querying
  - One-way street direction
  - Graph simplification (removes degree-2 nodes)
  - Coordinate projection
  - Caching to avoid repeated downloads

The cache saves as .graphml — a standard XML graph format.
"""

import logging
from pathlib import Path
import osmnx as ox
import networkx as nx

log = logging.getLogger(__name__)

# OSMnx settings: cache API responses, use drive network type
ox.settings.use_cache = True
ox.settings.log_console = False


def load_graph(
    place_name: str,
    cache_dir: str = "data",
    network_type: str = "drive",
) -> nx.MultiDiGraph:
    """
    Load road network for a place, using local cache if available.

    Args:
        place_name: Any place OSM recognises, e.g. "Manhattan, New York, USA"
                    or "Cambridge, UK" or "Shibuya, Tokyo, Japan"
        cache_dir:  Directory to store cached .graphml files
        network_type: OSMnx network type. "drive" for roads, "walk" for paths.

    Returns:
        NetworkX MultiDiGraph where:
          - nodes have 'x' (longitude) and 'y' (latitude) attributes
          - edges have 'length' (metres), 'name', 'speed_kph', 'travel_time'

    Raises:
        ValueError: if place_name is not found in OSM
        ConnectionError: if OSM download fails and no cache exists
    """
    cache_path = _cache_path(place_name, cache_dir)

    if cache_path.exists():
        log.info(f"Loading cached graph: {cache_path}")
        graph = ox.load_graphml(cache_path)
        _log_graph_stats(graph, place_name)
        return graph

    log.info(f"Downloading road network for '{place_name}' from OSM...")
    try:
        graph = ox.graph_from_place(
            place_name,
            network_type=network_type,
            simplify=True,          # remove degree-2 nodes (cleaner graph)
            retain_all=False,       # keep only largest connected component
        )
    except Exception as e:
        raise ConnectionError(
            f"Could not download road network for '{place_name}'. "
            f"Check the place name is valid in OpenStreetMap. Error: {e}"
        ) from e

    # Add travel time to edges (useful for future extensions)
    graph = ox.add_edge_speeds(graph)
    graph = ox.add_edge_travel_times(graph)

    # Save to cache
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    ox.save_graphml(graph, cache_path)
    log.info(f"Cached graph to {cache_path}")

    _log_graph_stats(graph, place_name)
    return graph


def get_nearest_node(
    graph: nx.MultiDiGraph, lat: float, lng: float
) -> int:
    """
    Find the graph node closest to given GPS coordinates.

    Uses OSMnx's spatial index for O(log n) lookup.

    Args:
        graph: Road network graph
        lat:   Latitude (y-axis)
        lng:   Longitude (x-axis)

    Returns:
        OSM node ID (integer)
    """
    return ox.nearest_nodes(graph, X=lng, Y=lat)


def _cache_path(place_name: str, cache_dir: str) -> Path:
    # Sanitise place name for use as filename
    safe_name = place_name.lower().replace(",", "").replace(" ", "_")
    return Path(cache_dir) / f"{safe_name}.graphml"


def _log_graph_stats(graph: nx.MultiDiGraph, place_name: str) -> None:
    nodes = graph.number_of_nodes()
    edges = graph.number_of_edges()
    log.info(f"Graph for '{place_name}': {nodes:,} nodes, {edges:,} edges")