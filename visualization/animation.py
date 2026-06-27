"""
Renders the A* exploration animation as a single self-contained HTML file
with JavaScript driving the animation internally.

Instead of replacing the Folium iframe on every frame (which causes flicker),
we build one HTML file that contains all explored nodes and the final path,
then use JS setTimeout to reveal them progressively.

The iframe is embedded once and never replaced — zero flicker.
"""

from __future__ import annotations
import json
import time
from typing import TYPE_CHECKING

import streamlit.components.v1 as components

if TYPE_CHECKING:
    from graph.builder import RoadGraph
    from algorithms.base import SearchResult


def animate_search(
    road_graph: "RoadGraph",
    result: "SearchResult",
    origin_node: int,
    destination_node: int,
    placeholder,
    frame_delay_s: float = 0.05,
    step_size: int = None,
    map_height_px: int = 500,
) -> None:
    """
    Render the search animation as a single HTML file with JS animation.
    The placeholder is used once — no flickering from repeated iframe swaps.
    """
    total_explored = len(result.explored)
    if step_size is None:
        step_size = max(1, total_explored // 60)

    # Build frame snapshots — list of node counts to reveal per frame
    frame_indices = list(range(0, total_explored, step_size))
    if not frame_indices or frame_indices[-1] != total_explored:
        frame_indices.append(total_explored)

    # Collect node coordinates for explored nodes
    explored_coords = []
    for node_id in result.explored:
        node = road_graph.get_node(node_id)
        explored_coords.append([node.lat, node.lng])

    # Collect path coordinates
    path_coords = []
    for node_id in result.path:
        node = road_graph.get_node(node_id)
        path_coords.append([node.lat, node.lng])

    # Origin and destination
    origin_node_data = road_graph.get_node(origin_node)
    dest_node_data   = road_graph.get_node(destination_node)

    # Centre map on midpoint of path
    if path_coords:
        centre_lat = sum(c[0] for c in path_coords) / len(path_coords)
        centre_lng = sum(c[1] for c in path_coords) / len(path_coords)
    else:
        centre_lat = origin_node_data.lat
        centre_lng = origin_node_data.lng

    frame_delay_ms = int(frame_delay_s * 1000)

    html = _build_animation_html(
        centre_lat=centre_lat,
        centre_lng=centre_lng,
        explored_coords=explored_coords,
        path_coords=path_coords,
        frame_indices=frame_indices,
        frame_delay_ms=frame_delay_ms,
        origin=origin_node_data,
        destination=dest_node_data,
        map_height_px=map_height_px,
    )

    with placeholder:
        components.html(html, height=map_height_px + 40, scrolling=False)


def render_final_map(
    road_graph: "RoadGraph",
    result: "SearchResult",
    origin_node: int,
    destination_node: int,
    placeholder,
    map_height_px: int = 500,
) -> None:
    """Render the final state with no animation — all nodes and path visible."""
    explored_coords = [
        [road_graph.get_node(n).lat, road_graph.get_node(n).lng]
        for n in result.explored
    ]
    path_coords = [
        [road_graph.get_node(n).lat, road_graph.get_node(n).lng]
        for n in result.path
    ]

    origin_data = road_graph.get_node(origin_node)
    dest_data   = road_graph.get_node(destination_node)

    if path_coords:
        centre_lat = sum(c[0] for c in path_coords) / len(path_coords)
        centre_lng = sum(c[1] for c in path_coords) / len(path_coords)
    else:
        centre_lat = origin_data.lat
        centre_lng = origin_data.lng

    # Final frame — all nodes visible immediately, no animation
    html = _build_animation_html(
        centre_lat=centre_lat,
        centre_lng=centre_lng,
        explored_coords=explored_coords,
        path_coords=path_coords,
        frame_indices=[len(explored_coords)],  # single frame = instant
        frame_delay_ms=0,
        origin=origin_data,
        destination=dest_data,
        map_height_px=map_height_px,
    )

    with placeholder:
        components.html(html, height=map_height_px + 40, scrolling=False)


def _build_animation_html(
    centre_lat: float,
    centre_lng: float,
    explored_coords: list,
    path_coords: list,
    frame_indices: list,
    frame_delay_ms: int,
    origin,
    destination,
    map_height_px: int,
) -> str:
    """
    Build a self-contained HTML page with Leaflet.js and JS animation.

    All node coordinates are embedded as JSON. A JS interval reveals
    nodes frame by frame, then draws the path on the final frame.
    The map is never recreated — only markers are added.
    """

    explored_json     = json.dumps(explored_coords)
    path_json         = json.dumps(path_coords)
    frame_indices_json = json.dumps(frame_indices)

    return f"""
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8"/>
<style>
  body {{ margin: 0; padding: 0; background: #fff; }}
  #map {{ width: 100%; height: {map_height_px}px; }}
  #progress-bar-container {{
    width: 100%;
    height: 6px;
    background: #e0e0e0;
  }}
  #progress-bar {{
    height: 6px;
    width: 0%;
    background: #E8453C;
    transition: width 0.1s linear;
  }}
  #status {{
    font-family: sans-serif;
    font-size: 12px;
    color: #666;
    padding: 4px 8px;
    text-align: right;
  }}
</style>
<link
  rel="stylesheet"
  href="https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.css"
/>
<script
  src="https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.js">
</script>
</head>
<body>

<div id="progress-bar-container">
  <div id="progress-bar"></div>
</div>
<div id="status">Initialising...</div>
<div id="map"></div>

<script>
// All data embedded at render time
const exploredCoords  = {explored_json};
const pathCoords      = {path_json};
const frameIndices    = {frame_indices_json};
const frameDelayMs    = {frame_delay_ms};
const originLatLng    = [{origin.lat}, {origin.lng}];
const destLatLng      = [{destination.lat}, {destination.lng}];
const totalExplored   = exploredCoords.length;

// Initialise Leaflet map — done once, never recreated
const map = L.map('map').setView([{centre_lat}, {centre_lng}], 14);
L.tileLayer('https://{{s}}.basemaps.cartocdn.com/light_all/{{z}}/{{x}}/{{y}}{{r}}.png', {{
  attribution: '© OpenStreetMap contributors © CARTO',
  subdomains: 'abcd',
  maxZoom: 19
}}).addTo(map);

// Reusable circle marker options
const exploredStyle = {{
  radius: 4,
  color: '#4A90D9',
  fillColor: '#4A90D9',
  fillOpacity: 0.6,
  weight: 1,
  interactive: false,
}};

// Track rendered markers so we only add NEW ones each frame
let lastRenderedIndex = 0;
let pathDrawn = false;
let currentFrame = 0;

const progressBar = document.getElementById('progress-bar');
const statusEl    = document.getElementById('status');

function renderFrame() {{
  const frameIndex = frameIndices[currentFrame];
  const isFinalFrame = currentFrame === frameIndices.length - 1;

  // Only add nodes that haven't been rendered yet
  for (let i = lastRenderedIndex; i < frameIndex; i++) {{
    L.circleMarker(exploredCoords[i], exploredStyle).addTo(map);
  }}
  lastRenderedIndex = frameIndex;

  // Update progress bar
  const pct = Math.round((frameIndex / totalExplored) * 100);
  progressBar.style.width = pct + '%';

  if (isFinalFrame) {{
    statusEl.textContent = 'Path found — ' + totalExplored.toLocaleString() + ' nodes explored';

    // Draw path polyline on final frame
    if (pathCoords.length > 0 && !pathDrawn) {{
      L.polyline(pathCoords, {{
        color: '#E8453C',
        weight: 5,
        opacity: 0.85,
        interactive: false,
      }}).addTo(map);
      pathDrawn = true;
    }}

  }} else {{
    statusEl.textContent = 'Exploring... ' + frameIndex.toLocaleString() + ' / ' + totalExplored.toLocaleString() + ' nodes';
    currentFrame++;
    setTimeout(renderFrame, frameDelayMs);
  }}
}}

// Start animation after map tiles load
map.whenReady(function() {{
  // Origin and destination visible immediately — before animation starts
  L.circleMarker(originLatLng, {{
    radius: 9,
    color: '#2ECC71',
    fillColor: '#2ECC71',
    fillOpacity: 0.95,
    weight: 2,
  }}).bindTooltip('Origin').addTo(map);

  L.circleMarker(destLatLng, {{
    radius: 9,
    color: '#E8453C',
    fillColor: '#E8453C',
    fillOpacity: 0.95,
    weight: 2,
  }}).bindTooltip('Destination').addTo(map);

  setTimeout(renderFrame, 100);
}});
</script>
</body>
</html>
"""