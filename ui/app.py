"""
Main Streamlit application.

Layout
------
  Sidebar  : city loader, coordinate inputs (rendered by ui/components.py)
  Main     : map placeholder, metrics panel

Data flow (one direction only)
-------------------------------
  Sidebar inputs → session state → main panel reads state → renders

Person 1 owns this file and ui/state.py.
Person 2 owns ui/components.py (coordinate inputs + location search).
They never touch the same file.
"""

import streamlit as st

from ui import state
from ui.components import render_sidebar
from visualization.map_view import render_search_result
from visualization.animation import animate_search, render_final_map
from metrics.performance import metrics_from_result
from algorithms.astar import AStarPathfinder
from algorithms.dijkstra import DijkstraPathfinder
from algorithms.bidirectional_dijkstra import BidirectionalDijkstra
from algorithms.bidirectional_bfs import BidirectionalBFS

ALGORITHM_REGISTRY = {
    "A*":                    AStarPathfinder,
    "Dijkstra":              DijkstraPathfinder,
    "Bidirectional Dijkstra": BidirectionalDijkstra,
    "Bidirectional BFS":     BidirectionalBFS,
}

def run_app() -> None:
    """Entry point — called by main.py."""
    st.set_page_config(
        page_title="Pathfinding Visualizer",
        page_icon="🗺️",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    state.init_state()

    _render_header()

    # Sidebar is fully owned by Person 2 via ui/components.py
    render_sidebar()

    # Main panel
    map_placeholder = st.empty()
    _render_main(map_placeholder)


def _render_header() -> None:
    st.title("🗺️ Pathfinding on Real Road Networks")
    st.caption(
        "Select a city, pick origin and destination coordinates, "
        "and watch the algorithm explore the road network in real time."
    )
    st.divider()


def _render_main(map_placeholder) -> None:
    """
    Main panel rendering logic.

    States (in order of priority):
      1. No graph loaded → show instruction placeholder
      2. Graph loaded, no nodes selected → show empty base map
      3. Nodes selected, search not run → show Run Search button
      4. Search running → show spinner
      5. Result available → show animated map + metrics
    """

    """st.write({
        "graph_loaded": state.is_graph_loaded(),
        "origin": state.get_origin(),
        "destination": state.get_destination(),
        "nodes_selected": state.nodes_selected(),
        "has_result": state.has_result(),
        "is_searching": state.is_searching(),
    })"""

    if not state.is_graph_loaded():
        _render_empty_state()
        return

    graph = state.get_graph()

    # Show base map when graph is loaded but no result yet
    if not state.has_result() and not state.is_searching():
        if state.nodes_selected():
            _render_search_controls(graph, map_placeholder)
        else:
            _render_awaiting_nodes(map_placeholder, graph)
        return

    # Search in progress
    if state.is_searching():
        with st.spinner("Running A* search..."):
            _run_search(graph, map_placeholder)
        return

    # Result ready
    if state.has_result():
        _render_result(graph, map_placeholder)


def _render_empty_state() -> None:
    st.info("👈 Enter a city name in the sidebar to get started.")
    st.markdown(
        """
        **What this app does:**
        - Downloads a real road network from OpenStreetMap
        - Lets you pick any two points on the map
        - Runs A* pathfinding and animates the search

        **Try:** *Manhattan, New York, USA* · *Cambridge, UK* · *Shibuya, Tokyo, Japan*
        """
    )


def _render_awaiting_nodes(map_placeholder, graph) -> None:
    st.info(
        f"✅ Loaded **{state.get_place()}** — "
        f"{graph.node_count:,} nodes, {graph.edge_count:,} edges.  \n"
        "Now enter origin and destination coordinates in the sidebar."
    )


def _render_search_controls(graph, map_placeholder) -> None:
    origin = state.get_origin()
    dest   = state.get_destination()

    origin_data = graph.get_node(origin)
    dest_data   = graph.get_node(dest)

    st.success(
        f"**Origin:** node {origin} ({origin_data.lat:.5f}, {origin_data.lng:.5f})  \n"
        f"**Destination:** node {dest} ({dest_data.lat:.5f}, {dest_data.lng:.5f})"
    )

    # Algorithm selector — renders first, value is committed to state on change
    algorithm = st.selectbox(
        "Algorithm",
        options=list(ALGORITHM_REGISTRY.keys()),
        index=list(ALGORITHM_REGISTRY.keys()).index(state.get_algorithm()),
        key="algorithm_selectbox",
        on_change=_on_algorithm_change,
    )

    col1, col2 = st.columns([1, 4])
    with col1:
        if st.button("▶ Run Search", type="primary", use_container_width=True):
            state.set_searching(True)
            st.rerun()
    with col2:
        animate = st.checkbox("Animate node exploration", value=True)
        st.session_state["animate_search"] = animate


def _on_algorithm_change() -> None:
    """Called when the selectbox changes — commits selection to state and clears result."""
    selected = st.session_state["algorithm_selectbox"]
    state.set_algorithm(selected)
    state.clear_result()  # force re-run with new algorithm


def _run_search(graph, map_placeholder) -> None:
    origin = state.get_origin()
    dest   = state.get_destination()

    algorithm_name  = state.get_algorithm()  # ← read from state, not session_state directly
    algorithm_class = ALGORITHM_REGISTRY[algorithm_name]

    result = algorithm_class(graph).find_path(origin, dest)
    state.set_searching(False)

    if result is None:
        st.error(
            "No path found between these two points. "
            "This can happen with one-way streets or disconnected road segments. "
            "Try different coordinates."
        )
        return

    metrics = metrics_from_result(result, algorithm_name, origin, dest)
    state.set_result(result, metrics)
    st.rerun()


def _render_result(graph, map_placeholder) -> None:
    result  = state.get_result()
    metrics = state.get_metrics()
    origin  = state.get_origin()
    dest    = state.get_destination()

    # Show which algorithm produced this result
    st.info(f"Showing result for **{metrics.algorithm_name}**")

    _render_metrics_panel(metrics)
    st.divider()

    if not state.is_animation_done() and st.session_state.get("animate_search", True):
        animate_search(
            road_graph=graph,
            result=result,
            origin_node=origin,
            destination_node=dest,
            placeholder=map_placeholder,
            frame_delay_s=0.04,
            step_size=max(1, len(result.explored) // 60),
        )
        state.set_animation_done()
    else:
        render_final_map(
            road_graph=graph,
            result=result,
            origin_node=origin,
            destination_node=dest,
            placeholder=map_placeholder,
        )

    if st.button("🔄 New Search", use_container_width=False):
        state.clear_result()
        st.rerun()


def _render_metrics_panel(metrics) -> None:
    """Render the four key metrics as Streamlit metric cards."""
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("Path Length", f"{metrics.path_length_km:.2f} km")
    with c2:
        st.metric("Nodes Explored", f"{metrics.nodes_explored:,}")
    with c3:
        st.metric("Runtime", f"{metrics.runtime_ms:.1f} ms")
    with c4:
        st.metric("Search Efficiency", f"{metrics.exploration_efficiency:.1%}")