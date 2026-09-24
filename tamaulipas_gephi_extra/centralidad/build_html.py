"""Interactive HTML twin of centralidad_toolkit.png - same two-column
bipartite layout ranked by betweenness centrality, with PageRank in the
hover text. Recomputed with networkx (same metrics Gephi's Statistics
engine computed) rather than round-tripping Gephi's exported GEXF."""
import csv
import math
import os
import sys
sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")))
import prtr_hover as H
import prtr_ui as U

import networkx as nx
import plotly.graph_objects as go

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "..", "..", "prtr_raw_for_stori_stori.csv")
STATE_FILTER = "Tamaulipas"

COLOR_LOCATION = "#2a78d6"
COLOR_SUBSTANCE = "#eb6834"
INK_PRIMARY = "#0b0b0b"
SURFACE = "#fcfcfb"
EDGE_COLOR = "#898781"

edges = {}
loc_totals = {}
sub_totals = {}
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
        key = (loc, sub)
        edges[key] = edges.get(key, 0.0) + v
        loc_totals[loc] = loc_totals.get(loc, 0.0) + v
        sub_totals[sub] = sub_totals.get(sub, 0.0) + v

G = nx.Graph()
for loc in loc_totals:
    G.add_node(loc, kind="location")
for sub in sub_totals:
    G.add_node(sub, kind="substance")
for (loc, sub), kg in edges.items():
    G.add_edge(loc, sub, weight=kg)

betweenness = nx.betweenness_centrality(G, weight=None, normalized=True)
pagerank = nx.pagerank(G, weight="weight")

locs_sorted = sorted(loc_totals, key=lambda n: -betweenness[n])
subs_sorted = sorted(sub_totals, key=lambda n: -betweenness[n])


def column_positions(names, x):
    n = len(names)
    return {name: (x, 1 - (i / max(n - 1, 1))) for i, name in enumerate(names)}


pos = {}
pos.update(column_positions(locs_sorted, 0.0))
pos.update(column_positions(subs_sorted, 1.0))


def scaled(value, values, lo, hi):
    vmin, vmax = min(values), max(values)
    if vmax == vmin:
        return (lo + hi) / 2
    t = (math.log1p(value) - math.log1p(vmin)) / (math.log1p(vmax) - math.log1p(vmin))
    return lo + t * (hi - lo)


all_bet = list(betweenness.values())
node_size = {n: scaled(betweenness[n], all_bet, 6, 42) for n in G.nodes()}

edge_x, edge_y = [], []
for loc, sub in edges:
    edge_x += [pos[loc][0], pos[sub][0], None]
    edge_y += [pos[loc][1], pos[sub][1], None]
edge_trace = go.Scatter(x=edge_x, y=edge_y, mode="lines", line=dict(color=EDGE_COLOR, width=0.6),
                         opacity=0.3, hoverinfo="none", showlegend=False, meta=dict(role="edges"))

traces = [edge_trace]
for names, color, label in ((locs_sorted, COLOR_LOCATION, "Municipio"), (subs_sorted, COLOR_SUBSTANCE, "Sustancia")):
    xs = [pos[n][0] for n in names]
    ys = [pos[n][1] for n in names]
    sizes = [node_size[n] for n in names]
    hover = [H.hover(n, extra=[f"<b>Centralidad</b>: betweenness {betweenness[n]:.4f} · PageRank {pagerank[n]:.4f}", f"Conexiones: {G.degree[n]}"]) for n in names]
    traces.append(go.Scatter(x=xs, y=ys, mode="markers", marker=dict(size=sizes, color=color, line=dict(width=1, color="white")),
                              hovertext=hover, hoverinfo="text", meta=dict(role="nodes"), name=label))

traces.append(H.edge_midpoints(list(edges), lambda u, v: H.edge_hover(u, v), pos))
fig = go.Figure(data=traces)
fig.update_layout(
    title=dict(text="Tamaulipas — centralidad de intermediación (betweenness) y PageRank", font=dict(color=INK_PRIMARY, size=18)),
    plot_bgcolor=SURFACE, paper_bgcolor=SURFACE,
    xaxis=dict(visible=False, range=[-0.5, 1.5]), yaxis=dict(visible=False, range=[-0.03, 1.06]),
    margin=dict(l=20, r=20, t=60, b=20), height=2000,
    hoverlabel=H.HOVERLABEL,
)
out = os.path.join(HERE, "centralidad.html")
U.write(fig, out)
print(f"Written {out}")

print("Top 10 betweenness:")
for n in sorted(G.nodes(), key=lambda n: -betweenness[n])[:10]:
    print(f"  {betweenness[n]:.4f}  {n}  (pagerank={pagerank[n]:.4f})")
