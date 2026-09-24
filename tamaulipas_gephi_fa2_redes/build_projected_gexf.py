"""GEXF inputs for the two projected networks (same construction as
tamaulipas_projected_networks/): Sustancia<->Sustancia (Jaccard >= 0.7 over the
municipios reporting each) and Municipio<->Municipio (cosine >= 0.7 over
log1p Kg/ano per substance). Communities are NOT computed here - Gephi's own
Modularity does that in the Java step."""
import csv, math, os
import networkx as nx
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "..", "prtr_raw_for_stori_stori.csv")
JACCARD, COSINE = 0.7, 0.7

muni_sub = {}
with open(SRC, encoding="utf-8") as f:
    for row in csv.DictReader(f):
        sp = row["spatial"].split(".")
        if sp[0] != "Tamaulipas":
            continue
        loc = ".".join(sp[:2])
        ip = row["interest"].split(".")
        sub = ip[-3] if len(ip) >= 3 else row["interest"]
        try:
            v = float(row["observation"])
        except ValueError:
            continue
        muni_sub.setdefault(loc, {})
        muni_sub[loc][sub] = muni_sub[loc].get(sub, 0.0) + v

# --- Sustancia <-> Sustancia
count = {}
pairs = {}
for subs in muni_sub.values():
    present = sorted(subs)
    for s in present:
        count[s] = count.get(s, 0) + 1
    for i in range(len(present)):
        for j in range(i + 1, len(present)):
            pairs[(present[i], present[j])] = pairs.get((present[i], present[j]), 0) + 1
Gs = nx.Graph()
for (a, b), c in pairs.items():
    j = c / (count[a] + count[b] - c)
    if j >= JACCARD:
        Gs.add_edge(a, b, weight=j)
for n in Gs.nodes():
    Gs.nodes[n]["label"] = n
    Gs.nodes[n]["n_municipios"] = count[n]
nx.write_gexf(Gs, os.path.join(HERE, "sustancia_sustancia", "sustancia_sustancia.gexf"))
print("sustancia_sustancia:", Gs.number_of_nodes(), "nodes", Gs.number_of_edges(), "edges")

# --- Municipio <-> Municipio
subs_all = sorted({s for d in muni_sub.values() for s in d})
idx = {s: i for i, s in enumerate(subs_all)}
munis = sorted(muni_sub)
vec = {}
for m in munis:
    v = np.zeros(len(subs_all))
    for s, kg in muni_sub[m].items():
        v[idx[s]] = math.log1p(kg)
    vec[m] = v
Gm = nx.Graph()
for i in range(len(munis)):
    for j in range(i + 1, len(munis)):
        a, b = munis[i], munis[j]
        sim = float(vec[a] @ vec[b] / (np.linalg.norm(vec[a]) * np.linalg.norm(vec[b])))
        if sim >= COSINE:
            Gm.add_edge(a, b, weight=sim)
for n in Gm.nodes():
    Gm.nodes[n]["label"] = n
    Gm.nodes[n]["total_kg"] = sum(muni_sub[n].values())
nx.write_gexf(Gm, os.path.join(HERE, "municipio_municipio", "municipio_municipio.gexf"))
print("municipio_municipio:", Gm.number_of_nodes(), "nodes", Gm.number_of_edges(), "edges")
