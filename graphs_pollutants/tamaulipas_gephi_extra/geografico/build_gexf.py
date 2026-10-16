"""Municipio <-> Municipio similarity network (same construction as
tamaulipas_projected_networks/municipio_municipio), but with each node
placed at its REAL geographic coordinate instead of a force-directed layout -
shows whether "similar industrial emission profile" lines up with
geographic proximity.
"""
import csv
import math
import os
import sys

import networkx as nx
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "..", "..", "..", "prtr_raw_for_stori_stori.csv")
STATE_FILTER = sys.argv[1] if len(sys.argv) > 1 else "Tamaulipas"
OUT_DIR = sys.argv[2] if len(sys.argv) > 2 else HERE
SIM_THRESHOLD = 0.7

# Municipal-seat coordinates (lat, lon) from INEGI (via poblacion_municipios.csv:
# clave_entidad,entidad,clave_municipio,municipio,longitud,latitud,poblacion).
# Matched by (state, municipio) name text, same convention as the rest of this
# codebase (PRTR's own `spatial` column is text, not INEGI numeric codes).
COORDS = {}
with open(os.path.join(HERE, "..", "..", "..", "poblacion_municipios.csv"), encoding="utf-8") as f:
    for row in csv.DictReader(f):
        if row["entidad"] == STATE_FILTER:
            COORDS[row["municipio"]] = (float(row["latitud"]), float(row["longitud"]))

CAT_COLORS = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#4a3aa7", "#e34948"]

muni_sub_totals = {}
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
        except ValueError:
            continue
        muni_sub_totals.setdefault(loc, {})
        muni_sub_totals[loc][sub] = muni_sub_totals[loc].get(sub, 0.0) + v

municipios = sorted(muni_sub_totals)
all_substances = sorted({s for d in muni_sub_totals.values() for s in d})
sub_index = {s: i for i, s in enumerate(all_substances)}

vectors = {}
for loc in municipios:
    vec = np.zeros(len(all_substances))
    for s, kg in muni_sub_totals[loc].items():
        vec[sub_index[s]] = math.log1p(kg)
    vectors[loc] = vec

G = nx.Graph()
for loc in municipios:
    short = loc.split(".")[-1]
    if short not in COORDS:
        print(f"WARNING: no coords for {short}, skipping")
        continue
    lat, lon = COORDS[short]
    G.add_node(loc, label=short, lat=lat, lon=lon, total_kg=sum(muni_sub_totals[loc].values()))

for i in range(len(municipios)):
    for j in range(i + 1, len(municipios)):
        a, b = municipios[i], municipios[j]
        if a not in G or b not in G:
            continue
        va, vb = vectors[a], vectors[b]
        denom = np.linalg.norm(va) * np.linalg.norm(vb)
        sim = float(np.dot(va, vb) / denom) if denom > 0 else 0.0
        if sim >= SIM_THRESHOLD:
            G.add_edge(a, b, weight=sim)

communities = nx.community.louvain_communities(G, weight="weight", seed=42)
communities = sorted(communities, key=len, reverse=True)
for i, comm in enumerate(communities):
    color = CAT_COLORS[i % len(CAT_COLORS)]
    for n in comm:
        G.nodes[n]["community"] = i
        G.nodes[n]["color_hex"] = color

print(f"Nodes: {G.number_of_nodes()}  Edges: {G.number_of_edges()}  Communities: {len(communities)}")
out = os.path.join(OUT_DIR, "municipio_geo.gexf")
nx.write_gexf(G, out)
print(f"Written {out}")
