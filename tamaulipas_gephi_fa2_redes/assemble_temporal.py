"""Assemble the Gephi-rendered temporal outputs:
 - temporal_snapshots_fa2.png : 2x2 sheet of the Gephi PNG frames (4 years)
 - temporal_fa2.html          : plotly animation (play/pause + year slider) using the
                                ForceAtlas2 positions Gephi computed on the union graph
"""
import math
import os
import sys
sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")))
import prtr_hover as H
import prtr_ui as U
import matplotlib.image as mpimg
import matplotlib.pyplot as plt
import networkx as nx
import plotly.graph_objects as go

HERE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "temporal")
years = [int(y) for y in open(os.path.join(HERE, "years.txt")).read().split(",")]
INK, SURFACE, EDGE = "#0b0b0b", "#fcfcfb", "#898781"

# ---- contact sheet from Gephi PNG frames
snap = [2004, 2010, 2016, 2022]
fig, axes = plt.subplots(2, 2, figsize=(18, 15.5), facecolor=SURFACE)
for ax, y in zip(axes.ravel(), snap):
    ax.imshow(mpimg.imread(os.path.join(HERE, "frames", f"temporal_{y}.png")))
    ax.set_title(str(y), fontsize=15, color=INK)
    ax.axis("off")
fig.suptitle("PRTR Tamaulipas — Municipio ↔ Sustancia por año (Gephi Toolkit + ForceAtlas2)", fontsize=16, color=INK)
fig.text(0.5, 0.005, "Posiciones idénticas en los 4 paneles (ForceAtlas2 sobre la unión de todos los años). "
         "Tamaño = Kg de ese año (escala log común); gris = sin reporte ese año.", ha="center", fontsize=9, color="#898781")
fig.tight_layout(rect=(0, 0.01, 1, 0.97))
out_png = os.path.join(HERE, "temporal_snapshots_fa2.png")
fig.savefig(out_png, dpi=110, facecolor=SURFACE)
print("Written", out_png)

# ---- plotly animation
data = nx.read_gexf(os.path.join(HERE, "temporal_union.gexf"))
pos_g = nx.read_gexf(os.path.join(HERE, "temporal_union_fa2.gexf"))
pos = {n: (d["viz"]["position"]["x"], d["viz"]["position"]["y"]) for n, d in pos_g.nodes(data=True)}

allv = [d[f"kg_{y}"] for _, d in data.nodes(data=True) for y in years if d[f"kg_{y}"] > 0]
gmin, gmax = min(allv), max(allv)


def size(v):
    t = (math.log1p(v) - math.log1p(gmin)) / (math.log1p(gmax) - math.log1p(gmin))
    return 8 + max(0, min(1, t)) * 30


kinds = {"location": ("Municipio", "#2a78d6"), "substance": ("Sustancia", "#eb6834")}


def frame(y):
    ex, ey = [], []
    for u, v, d in data.edges(data=True):
        if d[f"y_{y}"] > 0:
            ex += [pos[u][0], pos[v][0], None]
            ey += [pos[u][1], pos[v][1], None]
    traces = [go.Scatter(x=ex, y=ey, mode="lines", line=dict(color=EDGE, width=0.6), opacity=0.35,
                         hoverinfo="none", showlegend=False, meta=dict(role="edges"))]
    for kind, (label, color) in kinds.items():
        ns = [(n, d) for n, d in data.nodes(data=True) if d["type"] == kind]
        act = [d[f"kg_{y}"] > 0 for _, d in ns]
        traces.append(go.Scatter(
            x=[pos[n][0] for n, _ in ns], y=[pos[n][1] for n, _ in ns], mode="markers+text", name=label,
            text=[d["label"] if a else "" for (n, d), a in zip(ns, act)],
            textposition="top center", textfont=dict(size=8, color=INK),
            marker=dict(size=[size(d[f"kg_{y}"]) if a else 4 for (n, d), a in zip(ns, act)],
                        color=[color if a else "#c3c2b7" for a in act], line=dict(width=1, color="white")),
            hovertext=[H.hover(d['label'], year=y) for n, d in ns], hovertemplate="%{hovertext}<extra></extra>", meta=dict(role="nodes")))
    act_edges = [(u, v) for u, v, d in data.edges(data=True) if d[f"y_{y}"] > 0]
    traces.append(H.edge_midpoints(act_edges, lambda u, v: H.edge_hover(data.nodes[u]['label'], data.nodes[v]['label'], year=y), pos, template=True))
    return traces


fig2 = go.Figure(data=frame(years[0]), frames=[go.Frame(data=frame(y), name=str(y)) for y in years])
fig2.update_layout(
    title=dict(text=f"PRTR Tamaulipas — Municipio ↔ Sustancia por año ({years[0]}-{years[-1]}), ForceAtlas2",
               font=dict(color=INK, size=18)),
    plot_bgcolor=SURFACE, paper_bgcolor=SURFACE,
    xaxis=dict(visible=False), yaxis=dict(visible=False, scaleanchor="x"),
    margin=dict(l=20, r=20, t=110, b=20), height=1000,
    hoverlabel=H.HOVERLABEL,
    updatemenus=[dict(type="buttons", showactive=False, x=0.05, y=1.09, xanchor="left", buttons=[
        dict(label="Reproducir", method="animate",
             args=[None, dict(frame=dict(duration=700, redraw=True), fromcurrent=True, transition=dict(duration=200))]),
        dict(label="Pausar", method="animate", args=[[None], dict(frame=dict(duration=0, redraw=False), mode="immediate")])])],
    sliders=[dict(active=0, x=0.05, y=1.03, len=0.9, currentvalue=dict(prefix="Año: ", font=dict(color=INK, size=14)),
                  steps=[dict(label=str(y), method="animate", args=[[str(y)], dict(frame=dict(duration=0, redraw=True), mode="immediate")]) for y in years])],
)
out_html = os.path.join(HERE, "temporal_fa2.html")
union = [(pos[u], pos[v]) for u, v in data.edges()]     # every edge that exists in ANY year
U.write(fig2, out_html, union_edges=union, placeholder="Buscar municipio o sustancia (nombre o símbolo)…")
print("Written", out_html)
