"""Municipio <-> Medio (agua/aire/suelo/...) bipartite graph for Tamaulipas.
This is the same bipartite pattern as Municipio<->Sustancia, but substances
are contracted into their reporting medium - a much coarser, aggregate view.
"""
import csv
import os

import networkx as nx

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "..", "..", "prtr_raw_for_stori_stori.csv")
STATE_FILTER = "Tamaulipas"

edges = {}
loc_totals = {}
medio_totals = {}

with open(SRC, encoding="utf-8") as f:
    reader = csv.DictReader(f)
    for row in reader:
        spatial_parts = row["spatial"].split(".")
        if spatial_parts[0] != STATE_FILTER:
            continue
        loc = ".".join(spatial_parts[:2])

        interest_parts = row["interest"].split(".")
        medio = interest_parts[-1] if interest_parts else "desconocido"

        try:
            value = float(row["observation"])
        except ValueError:
            continue

        key = (loc, medio)
        edges[key] = edges.get(key, 0.0) + value
        loc_totals[loc] = loc_totals.get(loc, 0.0) + value
        medio_totals[medio] = medio_totals.get(medio, 0.0) + value

G = nx.Graph()
for loc, total in loc_totals.items():
    G.add_node(f"LOC::{loc}", label=loc, type="location", total_kg=total)
for medio, total in medio_totals.items():
    G.add_node(f"MED::{medio}", label=medio, type="medio", total_kg=total)
for (loc, medio), kg in edges.items():
    G.add_edge(f"LOC::{loc}", f"MED::{medio}", weight=kg)

print(f"Nodes: {G.number_of_nodes()} (locations: {len(loc_totals)}, medios: {len(medio_totals)})")
print(f"Edges: {G.number_of_edges()}")

out_path = os.path.join(HERE, "municipio_medio.gexf")
nx.write_gexf(G, out_path)
print(f"Written {out_path}")
