"""Build a bipartite Municipio <-> Sustancia graph from the PRTR dataset for Gephi.

Nodes:
  - location nodes: "Estado.Municipio" (spatial truncated to 2 components)
  - substance nodes: pollutant name (3rd-from-last "." component of `interest`)

Edge weight: sum of `observation` (Kg/ano) between a location and a substance,
aggregated across all activities/years/media.
"""
import csv
import networkx as nx

SRC = "prtr_raw_for_stori_stori.csv"
STATE_FILTER = "Tamaulipas"
OUT = f"prtr_municipio_sustancia_{STATE_FILTER.lower()}.gexf"

edges = {}  # (loc, sub) -> {"weight": float, "count": int}
loc_totals = {}
sub_totals = {}

with open(SRC, encoding="utf-8") as f:
    reader = csv.DictReader(f)
    for row in reader:
        spatial_parts = row["spatial"].split(".")
        if STATE_FILTER and spatial_parts[0] != STATE_FILTER:
            continue
        loc = ".".join(spatial_parts[:2]) if len(spatial_parts) >= 2 else row["spatial"]

        interest_parts = row["interest"].split(".")
        substance = interest_parts[-3] if len(interest_parts) >= 3 else row["interest"]

        try:
            value = float(row["observation"])
        except ValueError:
            continue

        key = (loc, substance)
        entry = edges.setdefault(key, {"weight": 0.0, "count": 0})
        entry["weight"] += value
        entry["count"] += 1

        loc_totals[loc] = loc_totals.get(loc, 0.0) + value
        sub_totals[substance] = sub_totals.get(substance, 0.0) + value

G = nx.Graph()

for loc, total in loc_totals.items():
    G.add_node(f"LOC::{loc}", label=loc, type="location", total_kg=total)

for sub, total in sub_totals.items():
    G.add_node(f"SUB::{sub}", label=sub, type="substance", total_kg=total)

for (loc, sub), data in edges.items():
    G.add_edge(f"LOC::{loc}", f"SUB::{sub}", weight=data["weight"], count=data["count"])

print(f"Nodes: {G.number_of_nodes()} (locations: {len(loc_totals)}, substances: {len(sub_totals)})")
print(f"Edges: {G.number_of_edges()}")

nx.write_gexf(G, OUT)
print(f"Written {OUT}")
