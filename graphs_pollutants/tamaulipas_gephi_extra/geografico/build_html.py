"""Interactive HTML twin of municipio_geo_toolkit.png - same
municipio-similarity network, positioned on a real map (plotly Scattergeo,
no token needed) instead of an abstract layout."""
import csv
import math
import os
import sys
sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..")))
import prtr_hover as H
import prtr_ui as U

import networkx as nx
import numpy as np
import plotly.graph_objects as go

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "..", "..", "..", "prtr_raw_for_stori_stori.csv")
STATE_FILTER = sys.argv[1] if len(sys.argv) > 1 else "Tamaulipas"
OUT_DIR = sys.argv[2] if len(sys.argv) > 2 else HERE
SIM_THRESHOLD = 0.7
H.configure(STATE_FILTER, "municipio")

# Municipal-seat coordinates (lat, lon) from INEGI, see geografico/build_gexf.py's
# comment for the same catalog and matching convention.
COORDS = {}
with open(os.path.join(HERE, "..", "..", "..", "poblacion_municipios.csv"), encoding="utf-8") as f:
    for row in csv.DictReader(f):
        if row["entidad"] == STATE_FILTER:
            COORDS[row["municipio"]] = (float(row["latitud"]), float(row["longitud"]))
CAT_COLORS = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#4a3aa7", "#e34948"]
INK_PRIMARY = "#0b0b0b"
SURFACE = "#fcfcfb"

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
    if short in COORDS:
        G.add_node(loc, short=short, total_kg=sum(muni_sub_totals[loc].values()))

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
node_color = {}
for i, comm in enumerate(communities):
    for n in comm:
        node_color[n] = CAT_COLORS[i % len(CAT_COLORS)]

edge_lat, edge_lon = [], []
for u, v in G.edges():
    la, lo = COORDS[G.nodes[u]["short"]]
    lb, lob = COORDS[G.nodes[v]["short"]]
    edge_lat += [la, lb, None]
    edge_lon += [lo, lob, None]

edge_trace = go.Scattergeo(lat=edge_lat, lon=edge_lon, mode="lines",
                            line=dict(width=0.8, color="#898781"), opacity=0.5,
                            hoverinfo="none", showlegend=False, meta=dict(role="edges"))

totals = [d["total_kg"] for _, d in G.nodes(data=True)]
tmin, tmax = min(totals), max(totals)


def size_for(v):
    if tmax == tmin:
        return 20
    t = (math.log1p(v) - math.log1p(tmin)) / (math.log1p(tmax) - math.log1p(tmin))
    return 10 + t * 35


node_traces = []
for color in CAT_COLORS:                       # one trace per community (legend / buttons / dimming)
    sub = [n for n in G.nodes() if node_color[n] == color]
    if not sub:
        continue
    node_traces.append(go.Scattergeo(
        lat=[COORDS[G.nodes[n]["short"]][0] for n in sub], lon=[COORDS[G.nodes[n]["short"]][1] for n in sub],
        mode="markers+text", text=[G.nodes[n]["short"] for n in sub], textposition="top center",
        textfont=dict(size=9, color=INK_PRIMARY), name=f"Community {CAT_COLORS.index(color) + 1}",
        marker=dict(size=[size_for(G.nodes[n]["total_kg"]) for n in sub], color=color, line=dict(width=1, color="white")),
        hovertext=[H.hover(n, extra=[f"<b>Similar-profile group (Louvain)</b>: #{CAT_COLORS.index(node_color[n]) + 1}",
                                     f"Municipalities with a similar profile (cosine ≥ {SIM_THRESHOLD}): {G.degree[n]}"]) for n in sub],
        hoverinfo="text", meta=dict(role="nodes")))

geo_mid = H.edge_midpoints(list(G.edges()), lambda u, v: H.muni_pair_hover(u, v, G[u][v]['weight']), None, geo=True,
                           latlon={n: COORDS[d['short']] for n, d in G.nodes(data=True)})
fig = go.Figure(data=[edge_trace] + node_traces + [geo_mid])
lats = [c[0] for c in COORDS.values()]; lons = [c[1] for c in COORDS.values()]
pad_lat, pad_lon = max(0.5, (max(lats) - min(lats)) * 0.15), max(0.5, (max(lons) - min(lons)) * 0.15)
fig.update_geos(
    scope="north america", resolution=50, showcountries=True, countrycolor="#c3c2b7",
    showsubunits=True, subunitcolor="#c3c2b7", showland=True, landcolor="#f2f1ec",
    showocean=True, oceancolor="#eaf2f8", showlakes=False,
    lataxis_range=[min(lats) - pad_lat, max(lats) + pad_lat], lonaxis_range=[min(lons) - pad_lon, max(lons) + pad_lon],
)
fig.update_layout(
    title=dict(text=f"{STATE_FILTER} — emissions profile similarity, on the real map", font=dict(color=INK_PRIMARY, size=18)),
    paper_bgcolor=SURFACE, margin=dict(l=10, r=10, t=60, b=10), height=1000,
    hoverlabel=H.HOVERLABEL,
)
out = os.path.join(OUT_DIR, "municipio_geo.html")
U.write(fig, out, placeholder="Search municipality…")
print(f"Written {out}")
