"""Interactive HTML twin of ego_altamira_toolkit.png - same concentric
ego-network layout (focal center, substances inner ring, peer municipios
outer ring), rendered from the same source data."""
import csv
import math
import os
import sys
sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")))
import prtr_hover as H
import prtr_ui as U

import plotly.graph_objects as go

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "..", "..", "prtr_raw_for_stori_stori.csv")
STATE_FILTER = "Tamaulipas"
FOCAL = "Tamaulipas.Altamira"
TOP_N_SUBSTANCES = 15
PEER_OVERLAP_MIN = 6

COLOR_FOCAL = "#e34948"
COLOR_SUB = "#eb6834"
COLOR_PEER = "#2a78d6"
INK_PRIMARY = "#0b0b0b"
SURFACE = "#fcfcfb"
EDGE_COLOR = "#898781"

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
top_sub_names = [s for s, _ in top_subs]

peers = {}
for m, subs in muni_sub_kg.items():
    if m == FOCAL:
        continue
    overlap = set(subs) & set(top_sub_names)
    if len(overlap) >= PEER_OVERLAP_MIN:
        peers[m] = overlap
peers_sorted = sorted(peers, key=lambda m: -sum(muni_sub_kg[m][s] for s in peers[m]))

pos = {FOCAL: (0.0, 0.0)}
for i, s in enumerate(top_sub_names):
    angle = 2 * math.pi * i / len(top_sub_names)
    pos[s] = (math.cos(angle), math.sin(angle))
for i, m in enumerate(peers_sorted):
    angle = 2 * math.pi * i / len(peers_sorted) + math.pi / len(peers_sorted)
    pos[m] = (2.0 * math.cos(angle), 2.0 * math.sin(angle))

edge_x, edge_y = [], []
for s, kg in top_subs:
    edge_x += [pos[FOCAL][0], pos[s][0], None]
    edge_y += [pos[FOCAL][1], pos[s][1], None]
for m, overlap in peers.items():
    for s in overlap:
        edge_x += [pos[m][0], pos[s][0], None]
        edge_y += [pos[m][1], pos[s][1], None]
edge_trace = go.Scatter(x=edge_x, y=edge_y, mode="lines", line=dict(color=EDGE_COLOR, width=0.7),
                         opacity=0.4, hoverinfo="none", showlegend=False, meta=dict(role="edges"))

focal_trace = go.Scatter(x=[0], y=[0], mode="markers+text", text=[FOCAL], textposition="bottom center",
                          marker=dict(size=40, color=COLOR_FOCAL, line=dict(width=2, color="white")),
                          hovertext=[H.hover(FOCAL, extra=["<i>Foco de esta ego-network</i>"])],
                          hoverinfo="text", meta=dict(role="nodes"), name="Foco")

sub_trace = go.Scatter(
    x=[pos[s][0] for s in top_sub_names], y=[pos[s][1] for s in top_sub_names],
    mode="markers+text", text=top_sub_names, textposition="top center", textfont=dict(size=8),
    marker=dict(size=[12 + 18 * (kg / top_subs[0][1]) for _, kg in top_subs], color=COLOR_SUB,
                line=dict(width=1, color="white")),
    hovertext=[H.hover(s, extra=[f"<b>Altamira</b> aporta {kg:,.0f} Kg de esta sustancia"]) for s, kg in top_subs],
    hoverinfo="text", meta=dict(role="nodes"), name="Sustancia",
)

peer_trace = go.Scatter(
    x=[pos[m][0] for m in peers_sorted], y=[pos[m][1] for m in peers_sorted],
    mode="markers+text", text=peers_sorted, textposition="bottom center", textfont=dict(size=9),
    marker=dict(size=[18 + 14 * (len(peers[m]) / TOP_N_SUBSTANCES) for m in peers_sorted], color=COLOR_PEER,
                line=dict(width=1, color="white")),
    hovertext=[H.hover(m, extra=[f"<b>Vecino de Altamira</b>: comparte {len(peers[m])} de sus {TOP_N_SUBSTANCES} sustancias principales"]) for m in peers_sorted],
    hoverinfo="text", meta=dict(role="nodes"), name="Municipio vecino",
)

ego_edges = [(FOCAL, s) for s in top_sub_names] + [(m, s) for m, ov in peers.items() for s in ov]
mid_trace = H.edge_midpoints(ego_edges, lambda u, v: H.edge_hover(u, v), pos)
fig = go.Figure(data=[edge_trace, focal_trace, sub_trace, peer_trace, mid_trace])
fig.update_layout(
    title=dict(text="Ego-network: Tamaulipas.Altamira y sus municipios vecinos", font=dict(color=INK_PRIMARY, size=18)),
    plot_bgcolor=SURFACE, paper_bgcolor=SURFACE,
    xaxis=dict(visible=False, range=[-2.6, 2.6]), yaxis=dict(visible=False, range=[-2.4, 2.4]),
    margin=dict(l=20, r=20, t=60, b=20), height=1000,
    hoverlabel=H.HOVERLABEL,
)
out = os.path.join(HERE, "ego_altamira.html")
U.write(fig, out)
print(f"Written {out}")
