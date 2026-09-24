"""National-level GEXF inputs (all 32 states, 716 municipios, 135 substances):
  estado_estado      : states linked by cosine similarity of their emission profile
                       (log1p Kg per substance); threshold = 70th percentile of all pairs
  estado_sustancia   : bipartite Estado <-> Sustancia
  geografico         : same as estado_estado, nodes carry lat/lon of the state capital
  municipio_sustancia: bipartite Municipio <-> Sustancia (716 + 135 nodes)
Communities are computed later by Gephi's own Modularity."""
import csv, math, os
import networkx as nx
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "..", "prtr_raw_for_stori_stori.csv")

# state capital (lat, lon) - schematic accuracy, enough to place nodes on a map
COORDS = {
 "Aguascalientes": (21.8853, -102.2916), "Baja California": (32.6245, -115.4523),
 "Baja California Sur": (24.1426, -110.3128), "Campeche": (19.8301, -90.5349),
 "Chiapas": (16.7528, -93.1152), "Chihuahua": (28.6353, -106.0889),
 "Ciudad de México": (19.4326, -99.1332), "Coahuila de Zaragoza": (25.4232, -100.9924),
 "Colima": (19.2433, -103.7250), "Durango": (24.0277, -104.6532),
 "Guanajuato": (21.0190, -101.2574), "Guerrero": (17.5506, -99.5058),
 "Hidalgo": (20.1011, -98.7591), "Jalisco": (20.6597, -103.3496),
 "México": (19.2826, -99.6557), "Michoacán de Ocampo": (19.7060, -101.1950),
 "Morelos": (18.9186, -99.2342), "Nayarit": (21.5058, -104.8946),
 "Nuevo León": (25.6866, -100.3161), "Oaxaca": (17.0732, -96.7266),
 "Puebla": (19.0414, -98.2063), "Querétaro": (20.5888, -100.3899),
 "Quintana Roo": (18.5001, -88.2961), "San Luis Potosí": (22.1565, -100.9855),
 "Sinaloa": (24.8091, -107.3940), "Sonora": (29.0729, -110.9559),
 "Tabasco": (17.9895, -92.9475), "Tamaulipas": (23.7369, -99.1411),
 "Tlaxcala": (19.3182, -98.2375), "Veracruz de Ignacio de la Llave": (19.5438, -96.9102),
 "Yucatán": (20.9674, -89.5926), "Zacatecas": (22.7709, -102.5832),
}

est_sub, mun_sub = {}, {}
est_muni = {}
with open(SRC, encoding="utf-8") as f:
    for r in csv.DictReader(f):
        sp = r["spatial"].split("."); p = r["interest"].split(".")
        try: v = float(r["observation"])
        except ValueError: continue
        e = sp[0]; m = ".".join(sp[:2]); s = p[-3] if len(p) >= 3 else r["interest"]
        est_sub.setdefault(e, {}); est_sub[e][s] = est_sub[e].get(s, 0.0) + v
        mun_sub.setdefault(m, {}); mun_sub[m][s] = mun_sub[m].get(s, 0.0) + v
        est_muni.setdefault(e, set()).add(m)
subs = sorted({s for d in est_sub.values() for s in d})
assert set(est_sub) == set(COORDS), set(est_sub) ^ set(COORDS)

# ---- estado <-> estado (cosine similarity)
idx = {s: i for i, s in enumerate(subs)}
ests = sorted(est_sub)
vec = {}
for e in ests:
    v = np.zeros(len(subs))
    for s, kg in est_sub[e].items():
        v[idx[s]] = math.log1p(kg)
    vec[e] = v
sims = {}
for i in range(len(ests)):
    for j in range(i + 1, len(ests)):
        a, b = ests[i], ests[j]
        sims[(a, b)] = float(vec[a] @ vec[b] / (np.linalg.norm(vec[a]) * np.linalg.norm(vec[b])))
thr = float(np.percentile(list(sims.values()), 70))
G = nx.Graph()
for e in ests:
    la, lo = COORDS[e]
    G.add_node(e, label=e, total_kg=sum(est_sub[e].values()), n_sustancias=len(est_sub[e]),
               n_municipios=len(est_muni[e]), lat=la, lon=lo)
for (a, b), sim in sims.items():
    if sim >= thr:
        G.add_edge(a, b, weight=sim)
print(f"estado_estado: cosine >= {thr:.3f} -> {G.number_of_nodes()} nodes, {G.number_of_edges()} edges, "
      f"isolates={len(list(nx.isolates(G)))}")
nx.write_gexf(G, os.path.join(HERE, "estado_estado", "estado_estado.gexf"))
nx.write_gexf(G, os.path.join(HERE, "geografico", "estado_geo.gexf"))

# ---- bipartite helpers
def bip(groups, kind_prefix, name):
    B = nx.Graph()
    sub_tot = {}
    for g, d in groups.items():
        B.add_node("LOC::" + g, label=g, type="location", total_kg=sum(d.values()))
        for s, kg in d.items():
            sub_tot[s] = sub_tot.get(s, 0.0) + kg
    for s, kg in sub_tot.items():
        B.add_node("SUB::" + s, label=s, type="substance", total_kg=kg)
    for g, d in groups.items():
        for s, kg in d.items():
            B.add_edge("LOC::" + g, "SUB::" + s, weight=kg)
    for n, d in B.nodes(data=True):
        d["log_total"] = math.log10(1 + d["total_kg"])   # ranking size on a log scale (totals span 10+ orders)
    print(f"{name}: {B.number_of_nodes()} nodes, {B.number_of_edges()} edges")
    return B

nx.write_gexf(bip(est_sub, "e", "estado_sustancia"), os.path.join(HERE, "estado_sustancia", "estado_sustancia.gexf"))
Bm = bip(mun_sub, "m", "municipio_sustancia")
for n, d in Bm.nodes(data=True):
    if d["type"] == "location":
        est, mun = n[5:].split(".", 1)
        d["label"] = f"{mun} ({est})"      # short display label; the lookup key is the node id
nx.write_gexf(Bm, os.path.join(HERE, "municipio_sustancia", "municipio_sustancia.gexf"))
