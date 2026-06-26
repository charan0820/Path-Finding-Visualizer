# scripts/sanity_check.py
"""
Quick verification that the data pipeline works end-to-end.
Run this first before touching any algorithm code.

Usage: python -m scripts.sanity_check
"""

import logging
import sys
import osmnx as ox

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

# Import our modules
sys.path.insert(0, ".")
from graph.loader import load_graph, get_nearest_node
from graph.builder import RoadGraph


def main():
    # Use a small city for fast download (~2,000 nodes)
    PLACE = "Piedmont, California, USA"
    
    print(f"\n--- Phase 1: Loading graph for '{PLACE}' ---")
    nx_graph = load_graph(PLACE)
    
    print(f"\n--- Phase 2: Building RoadGraph interface ---")
    road_graph = RoadGraph(nx_graph)
    print(f"Nodes: {road_graph.node_count:,}")
    print(f"Edges: {road_graph.edge_count:,}")
    
    print(f"\n--- Phase 3: Node lookup test ---")
    # Piedmont City Hall coordinates
    test_lat, test_lng = 37.8244, -122.2282
    node_id = get_nearest_node(nx_graph, lat=test_lat, lng=test_lng)
    node = road_graph.get_node(node_id)
    print(f"Nearest node to ({test_lat}, {test_lng}): node {node_id}")
    print(f"  Located at: ({node.lat:.6f}, {node.lng:.6f})")
    
    neighbors = road_graph.get_neighbors(node_id)
    print(f"  Neighbors: {len(neighbors)}")
    for neighbor_id, length in neighbors[:3]:
        print(f"    → node {neighbor_id}: {length:.1f}m")
    
    print(f"\n--- Phase 4: Plotting graph ---")
    fig, ax = ox.plot_graph(
        nx_graph,
        figsize=(10, 10),
        node_size=5,
        edge_linewidth=0.5,
        show=False,
        save=True,
        filepath="data/graph_plot.png",
    )
    print("Graph plotted → data/graph_plot.png")
    
    print("\n✓ Phase 1 complete. Ready to implement A*.")


if __name__ == "__main__":
    main()