"""FULL national Municipio<->Causa-especifica bipartite for the mortality dataset:
ALL 2,378 municipios x ALL 1,511 specific ICD causes (post-bugfix aggregation), no
top-N restriction and no per-edge death-count threshold - unlike the sibling
municipio_causa_especifico.gexf (top-100 causes, >100-deaths/edge prune).

Reuses the same cached aggregation as build_mortality_national_gexf.py
(/tmp/mortality_agg/agg.pkl), which already has both bugfixes applied at
aggregation time (CAUSA_DEF=="Total" excluded; specific rows with
Descripcion=="Total" excluded). Does not touch or re-run any of the 8 existing
outputs in this folder.
"""
import math
import os
import pickle

import networkx as nx

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = "/tmp/mortality_agg/agg.pkl"

agg = pickle.load(open(CACHE, "rb"))
mun_esp_all = agg["mun_esp"]          # (ent, mun, cd) -> conteo, ALL specific causes, unfiltered
causa_nat_esp = agg["causa_nat_esp"]  # cd -> national total conteo
causa_desc = agg["causa_desc"]        # cd -> Spanish description
mun_total = agg["mun_total"]          # (ent, mun) -> total conteo (all causes)

print(f"municipio x causa-especifica pairs (FULL, no restriction): {len(mun_esp_all):,}")
print(f"distinct causas: {len(causa_nat_esp):,}")
print(f"distinct municipios: {len({(e, m) for (e, m, cd) in mun_esp_all}):,}")

B = nx.Graph()
loc_keys, causa_tot_local = set(), {}
for (ent, mun, cd), conteo in mun_esp_all.items():
    loc_keys.add((ent, mun))
    causa_tot_local[cd] = causa_tot_local.get(cd, 0.0) + conteo

for (ent, mun) in loc_keys:
    loc = f"{ent}.{mun}"
    total = mun_total.get((ent, mun), 0.0)
    B.add_node("LOC::" + loc, label=f"{mun} ({ent})", type="location", total_kg=total)

for cd, tot in causa_tot_local.items():
    national = causa_nat_esp.get(cd, tot)
    B.add_node("CAU::" + cd, label=causa_desc.get(cd, cd), type="causa", total_kg=national)

for (ent, mun, cd), conteo in mun_esp_all.items():
    B.add_edge("LOC::" + f"{ent}.{mun}", "CAU::" + cd, weight=conteo)

for n, d in B.nodes(data=True):
    d["log_total"] = math.log10(1 + d["total_kg"])

print(f"municipio_causa (especifico_completo): {B.number_of_nodes():,} nodes, {B.number_of_edges():,} edges")

out = os.path.join(HERE, "municipio_causa", "municipio_causa_especifico_completo.gexf")
os.makedirs(os.path.dirname(out), exist_ok=True)
nx.write_gexf(B, out)
print("Written", out)
