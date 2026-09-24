"""Interactive HTML twin of municipio_geo_toolkit.png - same
municipio-similarity network, positioned on a real map (plotly Scattergeo,
no token needed) instead of an abstract layout."""
import csv
import math
import os
import sys
sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")))
import prtr_hover as H
import prtr_ui as U

import networkx as nx
import numpy as np
import plotly.graph_objects as go

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "..", "..", "prtr_raw_for_stori_stori.csv")
STATE_FILTER = "Tamaulipas"
SIM_THRESHOLD = 0.7

COORDS = {
    "Altamira": (22.3958, -97.9333), "Valle Hermoso": (25.6667, -97.8667),
    "Reynosa": (26.0922, -98.2853), "Ciudad Madero": (22.2667, -97.8333),
    "Río Bravo": (25.9836, -98.1006), "Xicoténcatl": (22.9964, -98.9439),
    "El Mante": (22.7333, -98.9833), "Nuevo Laredo": (27.4764, -99.5164),
    "Tampico": (22.2331, -97.8614), "Matamoros": (25.8697, -97.5044),
    "Soto la Marina": (23.7683, -98.2103), "Miguel Alemán": (26.3975, -99.0261),
    "Mier": (26.4306, -99.1503), "Victoria": (23.7369, -99.1411),
    "Antiguo Morelos": (22.5667, -99.1167), "San Fernando": (24.85, -98.1667),
    "Hidalgo": (24.2667, -99.1167), "Llera": (23.3167, -99.0167),
    "Jaumave": (23.4167, -99.3833), "Camargo": (26.2667, -98.8167),
}
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
        textfont=dict(size=9, color=INK_PRIMARY), name=f"Comunidad {CAT_COLORS.index(color) + 1}",
        marker=dict(size=[size_for(G.nodes[n]["total_kg"]) for n in sub], color=color, line=dict(width=1, color="white")),
        hovertext=[H.hover(n, extra=[f"<b>Grupo de perfil similar (Louvain)</b>: #{CAT_COLORS.index(node_color[n]) + 1}",
                                     f"Municipios con perfil similar (coseno ≥ {SIM_THRESHOLD}): {G.degree[n]}"]) for n in sub],
        hoverinfo="text", meta=dict(role="nodes")))

geo_mid = H.edge_midpoints(list(G.edges()), lambda u, v: H.muni_pair_hover(u, v, G[u][v]['weight']), None, geo=True,
                           latlon={n: COORDS[d['short']] for n, d in G.nodes(data=True)})
fig = go.Figure(data=[edge_trace] + node_traces + [geo_mid])
fig.update_geos(
    scope="north america", resolution=50, showcountries=True, countrycolor="#c3c2b7",
    showsubunits=True, subunitcolor="#c3c2b7", showland=True, landcolor="#f2f1ec",
    showocean=True, oceancolor="#eaf2f8", showlakes=False,
    lataxis_range=[21, 28.5], lonaxis_range=[-100.5, -96.5],
)
fig.update_layout(
    title=dict(text="Tamaulipas — similitud de perfil de emisiones, en el mapa real", font=dict(color=INK_PRIMARY, size=18)),
    paper_bgcolor=SURFACE, margin=dict(l=10, r=10, t=60, b=10), height=1000,
    hoverlabel=H.HOVERLABEL,
)
out = os.path.join(HERE, "municipio_geo.html")
U.write(fig, out, placeholder="Buscar municipio…")
print(f"Written {out}")
