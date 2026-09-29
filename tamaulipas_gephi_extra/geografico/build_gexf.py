"""Municipio <-> Municipio similarity network (same construction as
tamaulipas_projected_networks/municipio_municipio), but with each node
placed at its REAL geographic coordinate instead of a force-directed layout -
shows whether "similar industrial emission profile" lines up with
geographic proximity.
"""
import csv
import math
import os

import networkx as nx
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "..", "..", "prtr_raw_for_stori_stori.csv")
STATE_FILTER = "Tamaulipas"
SIM_THRESHOLD = 0.7

# Approximate municipal-seat coordinates (lat, lon) - public geography,
# schematic accuracy (not survey-grade), enough to place nodes on a real map.
COORDS = {
    "Altamira": (22.3958, -97.9333),
    "Valle Hermoso": (25.6667, -97.8667),
    "Reynosa": (26.0922, -98.2853),
    "Ciudad Madero": (22.2667, -97.8333),
    "Río Bravo": (25.9836, -98.1006),
    "Xicoténcatl": (22.9964, -98.9439),
    "El Mante": (22.7333, -98.9833),
    "Nuevo Laredo": (27.4764, -99.5164),
    "Tampico": (22.2331, -97.8614),
    "Matamoros": (25.8697, -97.5044),
    "Soto la Marina": (23.7683, -98.2103),
    "Miguel Alemán": (26.3975, -99.0261),
    "Mier": (26.4306, -99.1503),
    "Victoria": (23.7369, -99.1411),
    "Antiguo Morelos": (22.5667, -99.1167),
    "San Fernando": (24.85, -98.1667),
    "Hidalgo": (24.2667, -99.1167),
    "Llera": (23.3167, -99.0167),
    "Jaumave": (23.4167, -99.3833),
    "Camargo": (26.2667, -98.8167),
}

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
out = os.path.join(HERE, "municipio_geo.gexf")
nx.write_gexf(G, out)
print(f"Written {out}")
