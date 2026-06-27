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

    st.caption(
        "Enter coordinates as decimal degrees (e.g. 51.5074, -0.1278). "
        "The nearest road network node will be used automatically."
    )

    graph = state.get_graph()

    # --- Origin ---
    st.markdown("**Origin**")
    col1, col2 = st.columns(2)
    with col1:
        origin_lat = st.number_input(
            "Lat", key="origin_lat", value=0.0, format="%.6f",
            help="Latitude of your starting point"
        )
    with col2:
        origin_lng = st.number_input(
            "Lng", key="origin_lng", value=0.0, format="%.6f",
            help="Longitude of your starting point"
        )

    # --- Destination ---
    st.markdown("**Destination**")
    col3, col4 = st.columns(2)
    with col3:
        dest_lat = st.number_input(
            "Lat", key="dest_lat", value=0.0, format="%.6f",
            help="Latitude of your destination"
        )
    with col4:
        dest_lng = st.number_input(
            "Lng", key="dest_lng", value=0.0, format="%.6f",
            help="Longitude of your destination"
        )

    # Helper: show example coordinates for the loaded city
    _render_example_coordinates()

    st.markdown("")  # spacing

    #st.sidebar.write(f"DEBUG: {origin_lat}, {origin_lng}, {dest_lat}, {dest_lng}")

    set_clicked = st.button(
        "📍 Snap to nearest nodes",
        use_container_width=True,
        disabled=_coords_are_default(origin_lat, origin_lng, dest_lat, dest_lng),
        help="Finds the nearest road network node to each coordinate pair.",
    )

    if set_clicked:
        _snap_and_set_nodes(
            graph=graph,
            origin_lat=origin_lat, origin_lng=origin_lng,
            dest_lat=dest_lat,     dest_lng=dest_lng,
        )


def _snap_and_set_nodes(
    graph: RoadGraph,
    origin_lat: float, origin_lng: float,
    dest_lat: float,   dest_lng: float,
) -> None:
    """Snap lat/lng pairs to nearest graph nodes and update state."""
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

    except Exception as e:
        st.sidebar.error(f"Could not snap coordinates: {e}")

    st.rerun()


def _render_example_coordinates() -> None:
    """Show copy-pasteable example coordinates for the currently loaded city."""
    place = state.get_place()
    if not place:
        return

    EXAMPLES: dict[str, tuple[tuple[float, float], tuple[float, float]]] = {
        "Piedmont, California, USA": (
            (37.8244, -122.2282),   # City Hall
            (37.8219, -122.2235),   # Piedmont High School
        ),
        "Cambridge, UK": (
            (52.2054,  0.1132),     # King's College
            (52.2134,  0.0992),     # Cambridge train station
        ),
        "Manhattan, New York, USA": (
            (40.7484, -73.9856),    # Empire State Building
            (40.7614, -73.9776),    # Rockefeller Center
        ),
        "Shibuya, Tokyo, Japan": (
            (35.6595, 139.7004),    # Shibuya Crossing
            (35.6641, 139.6981),    # Yoyogi Park entrance
        ),
        "Amsterdam, Netherlands": (
            (52.3676,  4.9041),     # Dam Square
            (52.3588,  4.9089),     # Rijksmuseum
        ),
    }

    if place in EXAMPLES:
        origin_ex, dest_ex = EXAMPLES[place]
        with st.expander("📋 Example coordinates for this city", expanded=False):
            st.markdown(
                f"**Origin:** `{origin_ex[0]}, {origin_ex[1]}`  \n"
                f"**Destination:** `{dest_ex[0]}, {dest_ex[1]}`"
            )
            st.caption("Copy these into the fields above to try a quick search.")


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