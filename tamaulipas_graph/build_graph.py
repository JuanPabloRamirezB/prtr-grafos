"""Build and render the Municipio <-> Sustancia PRTR graph for Tamaulipas.

Reads the raw PRTR csv, filters to Tamaulipas, aggregates emissions
(Kg/ano) between each municipio and each sustancia, then renders a
two-column bipartite layout (locations left, substances right, each
ranked by total emissions) - a force-directed layout collapses on this
graph because it's dense and bipartite, so columns keep every node
readable:
  - tamaulipas_graph.png  (static, matplotlib)
  - tamaulipas_graph.html (interactive, plotly - hover for details)
"""
import csv
import math
import os
import sys
sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")))
import prtr_hover as H
import prtr_ui as U

import matplotlib.pyplot as plt
import networkx as nx
import plotly.graph_objects as go

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "..", "prtr_raw_for_stori_stori.csv")
STATE_FILTER = "Tamaulipas"

# Reference palette (dataviz skill) - categorical slots 1 (blue) & 2 (orange)
COLOR_LOCATION = "#2a78d6"
COLOR_SUBSTANCE = "#eb6834"
INK_PRIMARY = "#0b0b0b"
INK_SECONDARY = "#52514e"
INK_MUTED = "#898781"
SURFACE = "#fcfcfb"
EDGE_COLOR = "#898781"

# ---------------------------------------------------------------------------
# 1. Load + aggregate
# ---------------------------------------------------------------------------
edges = {}
loc_totals = {}
sub_totals = {}

with open(SRC, encoding="utf-8") as f:
    reader = csv.DictReader(f)
    for row in reader:
        spatial_parts = row["spatial"].split(".")
        if spatial_parts[0] != STATE_FILTER:
            continue
        loc = ".".join(spatial_parts[:2]) if len(spatial_parts) >= 2 else row["spatial"]

        interest_parts = row["interest"].split(".")
        substance = interest_parts[-3] if len(interest_parts) >= 3 else row["interest"]

        try:
            value = float(row["observation"])
        except ValueError:
            continue

        key = (loc, substance)
        entry = edges.setdefault(key, {"weight": 0.0, "count": 0})
        entry["weight"] += value
        entry["count"] += 1

        loc_totals[loc] = loc_totals.get(loc, 0.0) + value
        sub_totals[substance] = sub_totals.get(substance, 0.0) + value

G = nx.Graph()
for loc, total in loc_totals.items():
    G.add_node(loc, kind="location", total_kg=total)
for sub, total in sub_totals.items():
    G.add_node(sub, kind="substance", total_kg=total)
for (loc, sub), data in edges.items():
    G.add_edge(loc, sub, weight=data["weight"], count=data["count"])

print(f"Nodes: {G.number_of_nodes()} (locations: {len(loc_totals)}, substances: {len(sub_totals)})")
print(f"Edges: {G.number_of_edges()}")

# ---------------------------------------------------------------------------
# 2. Two-column bipartite layout, each column ranked by total emissions
# ---------------------------------------------------------------------------
locs_sorted = sorted(loc_totals, key=lambda n: -loc_totals[n])
subs_sorted = sorted(sub_totals, key=lambda n: -sub_totals[n])

def column_positions(names, x):
    n = len(names)
    return {name: (x, 1 - (i / max(n - 1, 1))) for i, name in enumerate(names)}

pos = {}
pos.update(column_positions(locs_sorted, 0.0))
pos.update(column_positions(subs_sorted, 1.0))

# ---------------------------------------------------------------------------
# 3. Size / width encodings (log scale - emissions span orders of magnitude)
# ---------------------------------------------------------------------------
def scaled(value, values, lo, hi):
    vmin, vmax = min(values), max(values)
    if vmax == vmin:
        return (lo + hi) / 2
    t = (math.log1p(value) - math.log1p(vmin)) / (math.log1p(vmax) - math.log1p(vmin))
    return lo + t * (hi - lo)

all_totals = list(loc_totals.values()) + list(sub_totals.values())
node_size_px = {n: scaled(d["total_kg"], all_totals, 40, 420) for n, d in G.nodes(data=True)}

all_weights = [d["weight"] for _, _, d in G.edges(data=True)]
edge_width = {(u, v): scaled(d["weight"], all_weights, 0.25, 2.2) for u, v, d in G.edges(data=True)}

# ---------------------------------------------------------------------------
# 4. Static PNG (matplotlib) - tall figure, one row per substance
# ---------------------------------------------------------------------------
n_rows = max(len(locs_sorted), len(subs_sorted))
fig_h = max(10, n_rows * 0.26)
fig, ax = plt.subplots(figsize=(13, fig_h), facecolor=SURFACE)
ax.set_facecolor(SURFACE)

for (u, v) in G.edges():
    x = [pos[u][0], pos[v][0]]
    y = [pos[u][1], pos[v][1]]
    ax.plot(x, y, color=EDGE_COLOR, linewidth=edge_width[(u, v)], alpha=0.18, zorder=1)

xs = [pos[n][0] for n in locs_sorted]
ys = [pos[n][1] for n in locs_sorted]
sizes = [node_size_px[n] for n in locs_sorted]
ax.scatter(xs, ys, s=sizes, c=COLOR_LOCATION, alpha=0.9, edgecolors="white", linewidths=0.6, zorder=2, label="Municipio")
for n in locs_sorted:
    x, y = pos[n]
    label = n.split(".")[-1] if "." in n else n
    ax.annotate(label, (x, y), fontsize=6.8, color=INK_PRIMARY, ha="right", va="center",
                xytext=(-8, 0), textcoords="offset points", zorder=3)

xs = [pos[n][0] for n in subs_sorted]
ys = [pos[n][1] for n in subs_sorted]
sizes = [node_size_px[n] for n in subs_sorted]
ax.scatter(xs, ys, s=sizes, c=COLOR_SUBSTANCE, alpha=0.9, edgecolors="white", linewidths=0.6, zorder=2, label="Sustancia")
for n in subs_sorted:
    x, y = pos[n]
    ax.annotate(n, (x, y), fontsize=6.8, color=INK_PRIMARY, ha="left", va="center",
                xytext=(8, 0), textcoords="offset points", zorder=3)

ax.set_title("PRTR Tamaulipas — Municipio ↔ Sustancia (Kg/año)", fontsize=15, color=INK_PRIMARY, pad=16)
ax.legend(loc="upper center", bbox_to_anchor=(0.5, 1.01), ncol=2, frameon=False,
          labelcolor=INK_SECONDARY, fontsize=10)
ax.text(0.5, -0.006, "Tamaño del nodo = emisión total acumulada (Kg/año). Grosor de línea = emisión por relación. Columnas ordenadas de mayor a menor emisión.",
        transform=ax.transAxes, ha="center", fontsize=8, color=INK_MUTED)
ax.set_xlim(-0.35, 1.35)
ax.set_ylim(-0.02, 1.06)
ax.axis("off")

png_path = os.path.join(HERE, "tamaulipas_graph.png")
fig.savefig(png_path, dpi=150, bbox_inches="tight", facecolor=SURFACE)
plt.close(fig)
print(f"Written {png_path}")

# ---------------------------------------------------------------------------
# 5. Interactive HTML (plotly) - same two-column layout + hover tooltips
# ---------------------------------------------------------------------------
edge_x, edge_y = [], []
for u, v in G.edges():
    edge_x += [pos[u][0], pos[v][0], None]
    edge_y += [pos[u][1], pos[v][1], None]

edge_trace = go.Scatter(
    x=edge_x, y=edge_y, mode="lines",
    line=dict(color=EDGE_COLOR, width=0.6),
    opacity=0.25, hoverinfo="none", showlegend=False, meta=dict(role="edges"),
)

traces = [edge_trace]
for kind, color, label, names in (
    ("location", COLOR_LOCATION, "Municipio", locs_sorted),
    ("substance", COLOR_SUBSTANCE, "Sustancia", subs_sorted),
):
    xs = [pos[n][0] for n in names]
    ys = [pos[n][1] for n in names]
    sizes = [node_size_px[n] ** 0.5 for n in names]
    hover = [H.hover(n, extra=[f"Conexiones: {G.degree[n]}"]) for n in names]
    traces.append(go.Scatter(
        x=xs, y=ys, mode="markers", name=label,
        marker=dict(size=sizes, color=color, line=dict(width=1, color="white"), opacity=0.9),
        hovertext=hover, hoverinfo="text", meta=dict(role="nodes"),
    ))

traces.append(H.edge_midpoints(list(G.edges()), lambda u, v: H.edge_hover(u, v), pos))
fig2 = go.Figure(data=traces)
fig2.update_layout(
    title=dict(text="PRTR Tamaulipas — Municipio ↔ Sustancia (Kg/año)", font=dict(color=INK_PRIMARY, size=18)),
    plot_bgcolor=SURFACE, paper_bgcolor=SURFACE,
    xaxis=dict(visible=False), yaxis=dict(visible=False),
    legend=dict(font=dict(color=INK_SECONDARY)),
    margin=dict(l=20, r=20, t=60, b=20),
    hoverlabel=H.HOVERLABEL,
    height=1400,
)

html_path = os.path.join(HERE, "tamaulipas_graph.html")
U.write(fig2, html_path)
print(f"Written {html_path}")
