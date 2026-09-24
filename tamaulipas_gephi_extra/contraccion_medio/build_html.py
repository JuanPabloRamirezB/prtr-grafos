"""Interactive HTML twin of municipio_medio_toolkit.png - same two-column
layout, rendered from the same source data."""
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
COLOR_MEDIO = "#eb6834"
INK_PRIMARY = "#0b0b0b"
SURFACE = "#fcfcfb"
EDGE_COLOR = "#898781"

edges = {}
loc_totals = {}
medio_totals = {}

with open(SRC, encoding="utf-8") as f:
    reader = csv.DictReader(f)
    for row in reader:
        sp = row["spatial"].split(".")
        if sp[0] != STATE_FILTER:
            continue
        loc = ".".join(sp[:2])
        ip = row["interest"].split(".")
        medio = ip[-1] if ip else "desconocido"
        try:
            value = float(row["observation"])
        except ValueError:
            continue
        key = (loc, medio)
        edges[key] = edges.get(key, 0.0) + value
        loc_totals[loc] = loc_totals.get(loc, 0.0) + value
        medio_totals[medio] = medio_totals.get(medio, 0.0) + value

locs_sorted = sorted(loc_totals, key=lambda n: -loc_totals[n])
medios_sorted = sorted(medio_totals, key=lambda n: -medio_totals[n])


def column_positions(names, x):
    n = len(names)
    return {name: (x, 1 - (i / max(n - 1, 1))) for i, name in enumerate(names)}


pos = {}
pos.update(column_positions(locs_sorted, 0.0))
pos.update(column_positions(medios_sorted, 1.0))


def scaled(value, values, lo, hi):
    vmin, vmax = min(values), max(values)
    if vmax == vmin:
        return (lo + hi) / 2
    t = (math.log1p(value) - math.log1p(vmin)) / (math.log1p(vmax) - math.log1p(vmin))
    return lo + t * (hi - lo)


all_totals = list(loc_totals.values()) + list(medio_totals.values())
node_size = {n: scaled(v, all_totals, 10, 45) for n, v in {**loc_totals, **medio_totals}.items()}

edge_x, edge_y = [], []
for (loc, medio) in edges:
    edge_x += [pos[loc][0], pos[medio][0], None]
    edge_y += [pos[loc][1], pos[medio][1], None]
edge_trace = go.Scatter(x=edge_x, y=edge_y, mode="lines", line=dict(color=EDGE_COLOR, width=0.7),
                         opacity=0.35, hoverinfo="none", showlegend=False, meta=dict(role="edges"))

traces = [edge_trace]
for names, color, label in ((locs_sorted, COLOR_LOCATION, "Municipio"), (medios_sorted, COLOR_MEDIO, "Medio")):
    totals = loc_totals if names is locs_sorted else medio_totals
    xs = [pos[n][0] for n in names]
    ys = [pos[n][1] for n in names]
    sizes = [node_size[n] for n in names]
    hover = [H.hover(n) for n in names]
    traces.append(go.Scatter(x=xs, y=ys, mode="markers+text", text=names, textposition="middle right" if names is locs_sorted else "middle left",
                              textfont=dict(size=9, color=INK_PRIMARY),
                              marker=dict(size=sizes, color=color, line=dict(width=1, color="white")),
                              hovertext=hover, hoverinfo="text", meta=dict(role="nodes"), name=label))

traces.append(H.edge_midpoints(list(edges), lambda u, v: H.edge_hover(u, v), pos))
fig = go.Figure(data=traces)
fig.update_layout(
    title=dict(text="Tamaulipas — Municipio ↔ Medio de descarga", font=dict(color=INK_PRIMARY, size=18)),
    plot_bgcolor=SURFACE, paper_bgcolor=SURFACE,
    xaxis=dict(visible=False, range=[-0.6, 1.6]), yaxis=dict(visible=False, range=[-0.05, 1.1]),
    margin=dict(l=20, r=20, t=60, b=20), height=1000,
    hoverlabel=H.HOVERLABEL,
)
out = os.path.join(HERE, "municipio_medio.html")
U.write(fig, out)
print(f"Written {out}")
