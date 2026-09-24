"""Ego network of Altamira (Tamaulipas' top-emitting municipio): its top 15
substances by Kg/ano (hop 1), plus every other municipio that reports at
least 6 of those same 15 substances (hop 2) - "who else deals with what
Altamira deals with". Role attribute: focal / substance / peer_municipio.
"""
import csv
import os

import networkx as nx

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "..", "..", "prtr_raw_for_stori_stori.csv")
STATE_FILTER = "Tamaulipas"
FOCAL = "Tamaulipas.Altamira"
TOP_N_SUBSTANCES = 15
PEER_OVERLAP_MIN = 6

muni_sub_kg = {}
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
        muni_sub_kg.setdefault(loc, {})
        muni_sub_kg[loc][sub] = muni_sub_kg[loc].get(sub, 0.0) + v

top_subs = sorted(muni_sub_kg[FOCAL].items(), key=lambda x: -x[1])[:TOP_N_SUBSTANCES]
top_sub_names = {s for s, _ in top_subs}

peers = {}
for m, subs in muni_sub_kg.items():
    if m == FOCAL:
        continue
    overlap = set(subs) & top_sub_names
    if len(overlap) >= PEER_OVERLAP_MIN:
        peers[m] = overlap

print(f"Focal: {FOCAL}  top substances: {len(top_sub_names)}  peer municipios: {len(peers)}")

G = nx.Graph()
G.add_node(FOCAL, label=FOCAL, role="focal", total_kg=sum(muni_sub_kg[FOCAL].values()))
for s, kg in top_subs:
    G.add_node(s, label=s, role="substance", total_kg=kg)
    G.add_edge(FOCAL, s, weight=kg)

for m, overlap in peers.items():
    total = sum(muni_sub_kg[m][s] for s in overlap)
    G.add_node(m, label=m, role="peer_municipio", total_kg=total)
    for s in overlap:
        G.add_edge(m, s, weight=muni_sub_kg[m][s])

print(f"Nodes: {G.number_of_nodes()}  Edges: {G.number_of_edges()}")
out = os.path.join(HERE, "ego_altamira.gexf")
nx.write_gexf(G, out)
print(f"Written {out}")
