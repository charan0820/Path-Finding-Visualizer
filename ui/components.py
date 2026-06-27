"""
Sidebar components: city loader and coordinate input panels.

This file is entirely owned by Person 2.
It reads/writes state exclusively through ui.state — never st.session_state directly.
It never imports from ui.app.

Coordinate input strategy
--------------------------
OSM node IDs are meaningless to users. Instead, the user enters lat/lng
coordinates (or an address — see the geocoding section), and we snap to
the nearest graph node. This is the same approach used by Google Maps
("your route starts near X street") and is correct for road network routing.
"""

from __future__ import annotations
import time
import streamlit as st

from ui import state
from graph.loader import load_graph, get_nearest_node
from graph.builder import RoadGraph

# Add this dict at the top of components.py after imports

CITY_COORD_BOUNDS: dict[str, dict] = {
    "amsterdam, netherlands": {
        "north": 52.395, "south": 52.340,
        "east":  4.940,  "west":  4.840,
        "example_origin":      (52.3676, 4.9041),
        "example_destination": (52.3588, 4.9089),
    },
    "manhattan, new york, usa": {
        "north": 40.800, "south": 40.720,
        "east": -73.940, "west": -74.010,
        "example_origin":      (40.7484, -73.9856),
        "example_destination": (40.7614, -73.9776),
    },
    "shibuya, tokyo, japan": {
        "north": 35.668, "south": 35.648,
        "east": 139.715, "west": 139.685,
        "example_origin":      (35.6595, 139.7004),
        "example_destination": (35.6641, 139.6981),
    },
    "london, uk": {
        "north": 51.530, "south": 51.470,
        "east":  -0.070, "west":  -0.170,
        "example_origin":      (51.5074, -0.1278),
        "example_destination": (51.5033, -0.1195),
    },
    "paris, france": {
        "north": 48.880, "south": 48.830,
        "east":   2.380, "west":   2.290,
        "example_origin":      (48.8566,  2.3522),
        "example_destination": (48.8738,  2.2950),
    },
    "berlin, germany": {
        "north": 52.545, "south": 52.480,
        "east":  13.450, "west":  13.340,
        "example_origin":      (52.5200, 13.4050),
        "example_destination": (52.5170, 13.3880),
    },
    "barcelona, spain": {
        "north": 41.415, "south": 41.365,
        "east":   2.205, "west":   2.130,
        "example_origin":      (41.3851,  2.1734),
        "example_destination": (41.4036,  2.1744),
    },
    # Small cities use place-name query so bounds are approximate
    "piedmont, california, usa": {
        "north": 37.835, "south": 37.810,
        "east": -122.210, "west": -122.250,
        "example_origin":      (37.8244, -122.2282),
        "example_destination": (37.8219, -122.2235),
    },
    "cambridge, uk": {
        "north": 52.230, "south": 52.185,
        "east":   0.155, "west":   0.085,
        "example_origin":      (52.2054,  0.1132),
        "example_destination": (52.2134,  0.0992),
    },
}


# ------------------------------------------------------------------ #
# Public entry point — called by ui/app.py                           #
# ------------------------------------------------------------------ #

def render_sidebar() -> None:
    """Render the full sidebar. Called once per Streamlit rerun."""
    with st.sidebar:
        st.header("⚙️ Configuration")

        _render_city_loader()

        if state.is_graph_loaded():
            st.divider()
            _render_coordinate_inputs()
            st.divider()
            _render_graph_info()


# ------------------------------------------------------------------ #
# City loader section                                                  #
# ------------------------------------------------------------------ #

def _render_city_loader() -> None:
    st.subheader("1. Choose a city")

    # Preset cities for quick access
    PRESETS = {
        "Custom...": None,
        "Piedmont, CA (small — fast)":   "Piedmont, California, USA",
        "Cambridge, UK (medium)":         "Cambridge, UK",
        "Manhattan, NYC (large)":         "Manhattan, New York, USA",
        "Shibuya, Tokyo (large)":         "Shibuya, Tokyo, Japan",
        "Amsterdam (medium)":             "Amsterdam, Netherlands",
    }

    preset = st.selectbox(
        "Quick select",
        options=list(PRESETS.keys()),
        index=0,
        help="Pick a preset city or enter a custom OSM place name below.",
    )

    # Prefill custom input from preset selection
    prefill = PRESETS[preset] or ""
    place_input = st.text_input(
        "Place name (OpenStreetMap)",
        value=prefill,
        placeholder="e.g. Piedmont, California, USA",
        help=(
            "Any place recognised by OpenStreetMap. "
            "Smaller areas load faster — a neighbourhood is better than a whole city."
        ),
    )

    load_clicked = st.button(
        "Load Road Network",
        type="primary",
        use_container_width=True,
        disabled=not place_input.strip(),
    )

    if load_clicked and place_input.strip():
        _load_graph_with_feedback(place_input.strip())


def _load_graph_with_feedback(place_name: str) -> None:
    state.set_loading(True)

    LARGE_CITIES = ["manhattan", "shibuya", "amsterdam", "tokyo", "london", "paris"]
    is_large = any(city in place_name.lower() for city in LARGE_CITIES)

    with st.sidebar:
        if is_large:
            st.info(
                "⏳ Large city — downloading in tiles. "
                "This takes **5–10 minutes** on first load due to API rate limits. "
                "Subsequent loads are instant from cache. "
                "Do not close the app."
            )
        progress_bar = st.progress(0, text="Connecting to OpenStreetMap...")

    error_message = None

    try:
        progress_bar.progress(10, text="Fetching bounding box...")
        nx_graph = load_graph(place_name)
        progress_bar.progress(80, text="Building graph interface...")
        road_graph = RoadGraph(nx_graph)
        progress_bar.progress(95, text="Indexing nodes...")
        progress_bar.progress(100, text="Done!")
        state.set_graph(road_graph, place_name)

    except Exception as e:
        error_message = str(e)

    finally:
        state.set_loading(False)
        progress_bar.empty()

    if error_message:
        st.sidebar.error(
            f"❌ Failed to load '{place_name}'.  \n\n"
            f"**Error:** {error_message}  \n\n"
            "The Overpass API may be temporarily overloaded. "
            "Wait 2 minutes and try again, or try a smaller area."
        )
        st.stop()
    else:
        st.rerun()


# ------------------------------------------------------------------ #
# Coordinate input section                                             #
# ------------------------------------------------------------------ #

def _render_coordinate_inputs() -> None:
    st.subheader("2. Set origin & destination")

    graph  = state.get_graph()
    place  = state.get_place()
    bounds = CITY_COORD_BOUNDS.get(place.lower().strip()) if place else None

    # Show bounds info box
    if bounds:
        st.info(
            f"📍 **Valid coordinate range for {place}**  \n"
            f"Latitude:  `{bounds['south']}` → `{bounds['north']}`  \n"
            f"Longitude: `{bounds['west']}` → `{bounds['east']}`  \n\n"
            f"Coordinates outside this range will not be accepted."
        )
    else:
        st.caption(
            "Enter coordinates as decimal degrees (e.g. 51.5074, -0.1278). "
            "The nearest road network node will be used automatically."
        )

    # --- Origin ---
    st.markdown("**Origin**")
    col1, col2 = st.columns(2)
    with col1:
        origin_lat = st.number_input(
            "Lat", key="origin_lat", value=0.0, format="%.6f",
            help=f"Latitude: {bounds['south']} to {bounds['north']}" if bounds else "Latitude",
        )
    with col2:
        origin_lng = st.number_input(
            "Lng", key="origin_lng", value=0.0, format="%.6f",
            help=f"Longitude: {bounds['west']} to {bounds['east']}" if bounds else "Longitude",
        )

    # --- Destination ---
    st.markdown("**Destination**")
    col3, col4 = st.columns(2)
    with col3:
        dest_lat = st.number_input(
            "Lat", key="dest_lat", value=0.0, format="%.6f",
            help=f"Latitude: {bounds['south']} to {bounds['north']}" if bounds else "Latitude",
        )
    with col4:
        dest_lng = st.number_input(
            "Lng", key="dest_lng", value=0.0, format="%.6f",
            help=f"Longitude: {bounds['west']} to {bounds['east']}" if bounds else "Longitude",
        )

    # Show example coordinates
    _render_example_coordinates()

    st.markdown("")

    set_clicked = st.button(
        "📍 Snap to nearest nodes",
        use_container_width=True,
        disabled=_coords_are_default(origin_lat, origin_lng, dest_lat, dest_lng),
    )

    if set_clicked:
        # Validate bounds before snapping
        if bounds and not _validate_coords(
            origin_lat, origin_lng,
            dest_lat, dest_lng,
            bounds, place,
        ):
            return  # error already shown inside _validate_coords

        _snap_and_set_nodes(
            graph=graph,
            origin_lat=origin_lat, origin_lng=origin_lng,
            dest_lat=dest_lat,     dest_lng=dest_lng,
        )


def _validate_coords(
    origin_lat: float, origin_lng: float,
    dest_lat: float,   dest_lng: float,
    bounds: dict,
    place: str,
) -> bool:
    """
    Check both coordinate pairs are within the loaded city's bbox.
    Shows a specific error message for each violation.
    Returns True if all coords are valid, False otherwise.
    """
    north = bounds["north"]
    south = bounds["south"]
    east  = bounds["east"]
    west  = bounds["west"]

    errors = []

    # Check origin
    if not (south <= origin_lat <= north):
        errors.append(
            f"**Origin latitude** `{origin_lat}` is out of range.  \n"
            f"Must be between `{south}` and `{north}`."
        )
    if not (west <= origin_lng <= east):
        errors.append(
            f"**Origin longitude** `{origin_lng}` is out of range.  \n"
            f"Must be between `{west}` and `{east}`."
        )

    # Check destination
    if not (south <= dest_lat <= north):
        errors.append(
            f"**Destination latitude** `{dest_lat}` is out of range.  \n"
            f"Must be between `{south}` and `{north}`."
        )
    if not (west <= dest_lng <= east):
        errors.append(
            f"**Destination longitude** `{dest_lng}` is out of range.  \n"
            f"Must be between `{west}` and `{east}`."
        )

    if errors:
        error_text = "\n\n".join(errors)
        st.sidebar.error(
            f"❌ Coordinates out of bounds for **{place}**  \n\n"
            f"{error_text}  \n\n"
            f"Valid range — "
            f"Lat: `{south}` → `{north}` | "
            f"Lng: `{west}` → `{east}`"
        )
        return False

    return True


def _snap_and_set_nodes(
    graph: RoadGraph,
    origin_lat: float, origin_lng: float,
    dest_lat: float,   dest_lng: float,
) -> None:
    try:
        nx_graph = graph.underlying_graph()

        origin_node = get_nearest_node(nx_graph, lat=origin_lat, lng=origin_lng)
        dest_node   = get_nearest_node(nx_graph, lat=dest_lat,   lng=dest_lng)

        if origin_node == dest_node:
            st.sidebar.warning(
                "Origin and destination snapped to the same node. "
                "Try coordinates that are further apart."
            )
            return

        state.set_origin(origin_node)
        state.set_destination(dest_node)

        origin_data = graph.get_node(origin_node)
        dest_data   = graph.get_node(dest_node)

        st.sidebar.success(
            f"✅ Origin → node {origin_node}  \n"
            f"({origin_data.lat:.5f}, {origin_data.lng:.5f})  \n\n"
            f"✅ Destination → node {dest_node}  \n"
            f"({dest_data.lat:.5f}, {dest_data.lng:.5f})"
        )

    except RuntimeError as e:
        # Shows the exact error on the deployed app
        st.sidebar.error(f"❌ Snap failed: {e}")
        return
    except Exception as e:
        st.sidebar.error(
            f"❌ Unexpected error snapping coordinates: {e}  \n\n"
            "Check the Streamlit Cloud logs for details."
        )
        return

    st.rerun()


def _render_example_coordinates() -> None:
    place = state.get_place()
    if not place:
        return

    bounds = CITY_COORD_BOUNDS.get(place.lower().strip())
    if not bounds:
        return

    origin_ex = bounds["example_origin"]
    dest_ex   = bounds["example_destination"]

    with st.expander("📋 Example coordinates for this city", expanded=False):
        st.markdown(
            f"**Origin:** `{origin_ex[0]}, {origin_ex[1]}`  \n"
            f"**Destination:** `{dest_ex[0]}, {dest_ex[1]}`"
        )
        st.caption(
            f"Valid range — "
            f"Lat: `{bounds['south']}` → `{bounds['north']}` | "
            f"Lng: `{bounds['west']}` → `{bounds['east']}`"
        )

# ------------------------------------------------------------------ #
# Graph info section                                                   #
# ------------------------------------------------------------------ #

def _render_graph_info() -> None:
    graph = state.get_graph()
    if not graph:
        return

    st.subheader("ℹ️ Graph info")
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Nodes", f"{graph.node_count:,}")
    with col2:
        st.metric("Edges", f"{graph.edge_count:,}")

    if state.nodes_selected():
        st.caption(
            f"Origin node: `{state.get_origin()}`  \n"
            f"Destination: `{state.get_destination()}`"
        )


# ------------------------------------------------------------------ #
# Private helpers                                                      #
# ------------------------------------------------------------------ #

def _coords_are_default(
    origin_lat: float, origin_lng: float,
    dest_lat: float,   dest_lng: float,
) -> bool:
    """True if all inputs are still at their 0.0 default — button should be disabled."""
    return (
        origin_lat == 0.0 and origin_lng == 0.0
        and dest_lat == 0.0 and dest_lng == 0.0
    )