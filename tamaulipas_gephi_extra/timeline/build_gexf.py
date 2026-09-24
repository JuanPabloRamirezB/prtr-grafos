"""Municipio<->Sustancia bipartite graph enriched with temporal info:
first_year (when that node first appears in the PRTR record) and
n_years_active (how many distinct years it reported). This is the static
"temporal fingerprint" companion to the full year-by-year animation already
built in data/tamaulipas_temporal_graph/.
"""
import csv
import os

import networkx as nx

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "..", "..", "prtr_raw_for_stori_stori.csv")
STATE_FILTER = "Tamaulipas"

edges = {}
loc_totals = {}
sub_totals = {}
loc_years = {}
sub_years = {}

with open(SRC, encoding="utf-8") as f:
    reader = csv.DictReader(f)
    for row in reader:
        sp = row["spatial"].split(".")
        if sp[0] != STATE_FILTER:
            continue
        loc = ".".join(sp[:2])
        ip = row["interest"].split(".")
        sub = ip[-3] if len(ip) >= 3 else row["interest"]
        try:
            v = float(row["observation"])
            year = int(row["temporal"])
        except ValueError:
            continue

        key = (loc, sub)
        edges[key] = edges.get(key, 0.0) + v
        loc_totals[loc] = loc_totals.get(loc, 0.0) + v
        sub_totals[sub] = sub_totals.get(sub, 0.0) + v
        loc_years.setdefault(loc, set()).add(year)
        sub_years.setdefault(sub, set()).add(year)

G = nx.Graph()
for loc, total in loc_totals.items():
    years = loc_years[loc]
    G.add_node(f"LOC::{loc}", label=loc, type="location", total_kg=total,
               first_year=min(years), n_years_active=len(years))
for sub, total in sub_totals.items():
    years = sub_years[sub]
    G.add_node(f"SUB::{sub}", label=sub, type="substance", total_kg=total,
               first_year=min(years), n_years_active=len(years))
for (loc, sub), kg in edges.items():
    G.add_edge(f"LOC::{loc}", f"SUB::{sub}", weight=kg)

print(f"Nodes: {G.number_of_nodes()}  Edges: {G.number_of_edges()}")
out = os.path.join(HERE, "temporal_fingerprint.gexf")
nx.write_gexf(G, out)
print(f"Written {out}")
