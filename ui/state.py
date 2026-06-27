"""
Centralised Streamlit session state management.

All mutable app state lives here. UI components read and write through
these functions — never touching st.session_state keys directly.
This makes state transitions explicit and testable.
"""

import streamlit as st
from dataclasses import dataclass
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from algorithms.base import SearchResult
    from metrics.performance import SearchMetrics
    from graph.builder import RoadGraph


# Keys — defined once so typos cause NameErrors, not silent bugs
_GRAPH_KEY        = "road_graph"
_PLACE_KEY        = "current_place"
_ORIGIN_KEY       = "origin_node"
_DEST_KEY         = "destination_node"
_RESULT_KEY       = "search_result"
_METRICS_KEY      = "search_metrics"
_LOADING_KEY      = "graph_loading"
_SEARCHING_KEY    = "searching"
_ANIMATED_KEY     = "animation_done"


def init_state() -> None:
    defaults = {
        _GRAPH_KEY:      None,
        _PLACE_KEY:      None,
        _ORIGIN_KEY:     None,
        _DEST_KEY:       None,
        _RESULT_KEY:     None,
        _METRICS_KEY:    None,
        _LOADING_KEY:    False,
        _SEARCHING_KEY:  False,
        _ANIMATED_KEY:   False,
        _ALGORITHM_KEY:  "A*",      # ← add this
    }
    for key, default in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = default


# ------------------------------------------------------------------ #
# Graph state                                                          #
# ------------------------------------------------------------------ #

def set_graph(graph: "RoadGraph", place_name: str) -> None:
    st.session_state[_GRAPH_KEY]  = graph
    st.session_state[_PLACE_KEY]  = place_name
    # Clear downstream state when graph changes
    clear_search()


def get_graph() -> Optional["RoadGraph"]:
    return st.session_state[_GRAPH_KEY]


def get_place() -> Optional[str]:
    return st.session_state[_PLACE_KEY]


def is_graph_loaded() -> bool:
    return st.session_state[_GRAPH_KEY] is not None


def set_loading(value: bool) -> None:
    st.session_state[_LOADING_KEY] = value


def is_loading() -> bool:
    return st.session_state[_LOADING_KEY]


# ------------------------------------------------------------------ #
# Node selection state                                                 #
# ------------------------------------------------------------------ #

def set_origin(node_id: int) -> None:
    st.session_state[_ORIGIN_KEY] = node_id
    clear_result()


def set_destination(node_id: int) -> None:
    st.session_state[_DEST_KEY] = node_id
    clear_result()


def get_origin() -> Optional[int]:
    return st.session_state[_ORIGIN_KEY]


def get_destination() -> Optional[int]:
    return st.session_state[_DEST_KEY]


def nodes_selected() -> bool:
    return (
        st.session_state[_ORIGIN_KEY] is not None
        and st.session_state[_DEST_KEY] is not None
    )


# ------------------------------------------------------------------ #
# Search result state                                                  #
# ------------------------------------------------------------------ #

def set_result(result: "SearchResult", metrics: "SearchMetrics") -> None:
    st.session_state[_RESULT_KEY]   = result
    st.session_state[_METRICS_KEY]  = metrics
    st.session_state[_ANIMATED_KEY] = False


def get_result() -> Optional["SearchResult"]:
    return st.session_state[_RESULT_KEY]


def get_metrics() -> Optional["SearchMetrics"]:
    return st.session_state[_METRICS_KEY]


def has_result() -> bool:
    return st.session_state[_RESULT_KEY] is not None


def set_animation_done() -> None:
    st.session_state[_ANIMATED_KEY] = True


def is_animation_done() -> bool:
    return st.session_state[_ANIMATED_KEY]


def set_searching(value: bool) -> None:
    st.session_state[_SEARCHING_KEY] = value


def is_searching() -> bool:
    return st.session_state[_SEARCHING_KEY]


def clear_result() -> None:
    st.session_state[_RESULT_KEY]   = None
    st.session_state[_METRICS_KEY]  = None
    st.session_state[_ANIMATED_KEY] = False


def clear_search() -> None:
    st.session_state[_ORIGIN_KEY] = None
    st.session_state[_DEST_KEY]   = None
    clear_result()

_ALGORITHM_KEY = "selected_algorithm"

def set_algorithm(name: str) -> None:
    st.session_state[_ALGORITHM_KEY] = name

def get_algorithm() -> str:
    return st.session_state.get(_ALGORITHM_KEY, "A*")