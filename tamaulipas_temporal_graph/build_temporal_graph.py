"""Temporal version of the Tamaulipas Municipio <-> Sustancia PRTR graph.

Same bipartite structure as data/tamaulipas_graph (two columns, locations
left / substances right, each ranked by their all-years total so positions
never jump between frames), but now split by `temporal` (year) and animated:
  - tamaulipas_temporal.html   interactive, play/pause + year slider (plotly)
  - tamaulipas_temporal_snapshots.png   4 static year snapshots side by side
"""
import csv
import math
import os
import sys
sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")))
import prtr_hover as H
import prtr_ui as U

import matplotlib.pyplot as plt
import plotly.graph_objects as go

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "..", "prtr_raw_for_stori_stori.csv")
STATE_FILTER = "Tamaulipas"

COLOR_LOCATION = "#2a78d6"
COLOR_SUBSTANCE = "#eb6834"
INK_PRIMARY = "#0b0b0b"
INK_SECONDARY = "#52514e"
INK_MUTED = "#898781"
SURFACE = "#fcfcfb"
EDGE_COLOR = "#898781"

# ---------------------------------------------------------------------------
# 1. Load Tamaulipas rows -> per (year, municipio, sustancia) Kg/ano
# ---------------------------------------------------------------------------
# yearly[year][(loc, sub)] = kg ;  loc_totals/sub_totals = all-years totals (for layout+scale)
yearly = {}
loc_totals = {}
sub_totals = {}
edge_totals = {}

with open(SRC, encoding="utf-8") as f:
    reader = csv.DictReader(f)
    for row in reader:
        spatial_parts = row["spatial"].split(".")
        if spatial_parts[0] != STATE_FILTER:
            continue
        loc = ".".join(spatial_parts[:2])

        interest_parts = row["interest"].split(".")
        substance = interest_parts[-3] if len(interest_parts) >= 3 else row["interest"]

        try:
            value = float(row["observation"])
        except ValueError:
            continue

        try:
            year = int(row["temporal"])
        except ValueError:
            continue

        key = (loc, substance)
        yearly.setdefault(year, {})
        yearly[year][key] = yearly[year].get(key, 0.0) + value

        loc_totals[loc] = loc_totals.get(loc, 0.0) + value
        sub_totals[substance] = sub_totals.get(substance, 0.0) + value
        edge_totals[key] = edge_totals.get(key, 0.0) + value

years = sorted(yearly)
print(f"Years: {years[0]}-{years[-1]} ({len(years)} years)")
print(f"Locations: {len(loc_totals)}  Substances: {len(sub_totals)}  Edges (any year): {len(edge_totals)}")

# ---------------------------------------------------------------------------
# 2. Fixed two-column layout (ranked by ALL-YEARS total, same across frames)
# ---------------------------------------------------------------------------
locs_sorted = sorted(loc_totals, key=lambda n: -loc_totals[n])
subs_sorted = sorted(sub_totals, key=lambda n: -sub_totals[n])


def column_positions(names, x):
    n = len(names)
    return {name: (x, 1 - (i / max(n - 1, 1))) for i, name in enumerate(names)}


pos = {}
pos.update(column_positions(locs_sorted, 0.0))
pos.update(column_positions(subs_sorted, 1.0))


def scaled(value, vmin, vmax, lo, hi):
    if vmax <= vmin or value <= 0:
        return lo
    t = (math.log1p(value) - math.log1p(vmin)) / (math.log1p(vmax) - math.log1p(vmin))
    return lo + max(0.0, min(1.0, t)) * (hi - lo)


loc_vmin, loc_vmax = min(loc_totals.values()), max(loc_totals.values())
sub_vmin, sub_vmax = min(sub_totals.values()), max(sub_totals.values())
edge_vmin, edge_vmax = min(edge_totals.values()), max(edge_totals.values())

# per-year totals, so node size reflects THAT year's emissions (comparable
# across frames because lo/hi bounds come from the all-years min/max, not
# re-normalized per frame - otherwise every year's biggest node would look
# equally large and the animation wouldn't show growth/decline)
year_loc_totals = {y: {} for y in years}
year_sub_totals = {y: {} for y in years}
for y, edges in yearly.items():
    for (loc, sub), kg in edges.items():
        year_loc_totals[y][loc] = year_loc_totals[y].get(loc, 0.0) + kg
        year_sub_totals[y][sub] = year_sub_totals[y].get(sub, 0.0) + kg

# ---------------------------------------------------------------------------
# 3. Interactive animated HTML (plotly frames + slider + play/pause)
# ---------------------------------------------------------------------------
def frame_data(year):
    edges = yearly[year]
    edge_x, edge_y = [], []
    for (loc, sub) in edges:
        edge_x += [pos[loc][0], pos[sub][0], None]
        edge_y += [pos[loc][1], pos[sub][1], None]
    edge_trace = go.Scatter(x=edge_x, y=edge_y, mode="lines",
                             line=dict(color=EDGE_COLOR, width=0.6),
                             opacity=0.35, hoverinfo="none", showlegend=False, meta=dict(role="edges"))

    loc_kg = year_loc_totals[year]
    xs = [pos[n][0] for n in locs_sorted]
    ys = [pos[n][1] for n in locs_sorted]
    sizes = [max(4, scaled(loc_kg.get(n, 0), loc_vmin, loc_vmax, 8, 45)) for n in locs_sorted]
    hover = [H.hover(n, year=year) for n in locs_sorted]
    loc_trace = go.Scatter(x=xs, y=ys, mode="markers+text", name="Municipio", text=[n.split(".")[-1] for n in locs_sorted],
                            textposition="middle left", textfont=dict(size=8, color=INK_SECONDARY),
                            marker=dict(size=sizes, color=COLOR_LOCATION, line=dict(width=1, color="white")),
                            hovertext=hover, hovertemplate="%{hovertext}<extra></extra>", meta=dict(role="nodes"))

    sub_kg = year_sub_totals[year]
    xs = [pos[n][0] for n in subs_sorted]
    ys = [pos[n][1] for n in subs_sorted]
    sizes = [max(4, scaled(sub_kg.get(n, 0), sub_vmin, sub_vmax, 8, 45)) for n in subs_sorted]
    hover = [H.hover(n, year=year) for n in subs_sorted]
    sub_trace = go.Scatter(x=xs, y=ys, mode="markers+text", name="Sustancia", text=list(subs_sorted),
                            textposition="middle right", textfont=dict(size=8, color=INK_SECONDARY),
                            marker=dict(size=sizes, color=COLOR_SUBSTANCE, line=dict(width=1, color="white")),
                            hovertext=hover, hovertemplate="%{hovertext}<extra></extra>", meta=dict(role="nodes"))

    mid = H.edge_midpoints(list(edges.keys()), lambda u, v: H.edge_hover(u, v, year=year), pos, template=True)
    return [edge_trace, loc_trace, sub_trace, mid]


init_data = frame_data(years[0])
frames = [go.Frame(data=frame_data(y), name=str(y)) for y in years]

fig = go.Figure(data=init_data, frames=frames)

fig.update_layout(
    title=dict(text=f"PRTR Tamaulipas — Municipio ↔ Sustancia por año ({years[0]}-{years[-1]})",
               font=dict(color=INK_PRIMARY, size=18)),
    plot_bgcolor=SURFACE, paper_bgcolor=SURFACE,
    xaxis=dict(visible=False, range=[-0.5, 1.5]),
    yaxis=dict(visible=False, range=[-0.03, 1.06]),
    margin=dict(l=20, r=20, t=70, b=20),
    height=2000,
    hoverlabel=H.HOVERLABEL,
    updatemenus=[dict(
        type="buttons", showactive=False, x=0.05, y=1.05, xanchor="left",
        buttons=[
            dict(label="Reproducir", method="animate",
                 args=[None, dict(frame=dict(duration=700, redraw=True), fromcurrent=True,
                                   transition=dict(duration=200))]),
            dict(label="Pausar", method="animate",
                 args=[[None], dict(frame=dict(duration=0, redraw=False), mode="immediate")]),
        ],
    )],
    sliders=[dict(
        active=0, x=0.05, y=1.0, len=0.9,
        currentvalue=dict(prefix="Año: ", font=dict(color=INK_PRIMARY, size=14)),
        steps=[dict(label=str(y), method="animate",
                    args=[[str(y)], dict(frame=dict(duration=0, redraw=True), mode="immediate")])
               for y in years],
    )],
)

html_path = os.path.join(HERE, "tamaulipas_temporal.html")
# adjacency for the search: every (municipio, sustancia) pair that exists in ANY year
union = [(pos[l], pos[s]) for (l, s) in edge_totals]
U.write(fig, html_path, union_edges=union, placeholder="Buscar municipio o sustancia (nombre o símbolo)…")
print(f"Written {html_path}")

# ---------------------------------------------------------------------------
# 4. Static snapshots (4 years) for a quick non-interactive look
# ---------------------------------------------------------------------------
snapshot_years = [years[0], years[len(years) // 3], years[2 * len(years) // 3], years[-1]]

fig2, axes = plt.subplots(1, 4, figsize=(28, 14), facecolor=SURFACE)
for ax, year in zip(axes, snapshot_years):
    ax.set_facecolor(SURFACE)
    edges = yearly[year]
    for (loc, sub) in edges:
        x = [pos[loc][0], pos[sub][0]]
        y = [pos[loc][1], pos[sub][1]]
        ax.plot(x, y, color=EDGE_COLOR, linewidth=0.6, alpha=0.3, zorder=1)

    loc_kg = year_loc_totals[year]
    xs = [pos[n][0] for n in locs_sorted]
    ys = [pos[n][1] for n in locs_sorted]
    sizes = [scaled(loc_kg.get(n, 0), loc_vmin, loc_vmax, 15, 260) for n in locs_sorted]
    ax.scatter(xs, ys, s=sizes, c=COLOR_LOCATION, alpha=0.9, edgecolors="white", linewidths=0.4, zorder=2)

    sub_kg = year_sub_totals[year]
    xs = [pos[n][0] for n in subs_sorted]
    ys = [pos[n][1] for n in subs_sorted]
    sizes = [scaled(sub_kg.get(n, 0), sub_vmin, sub_vmax, 15, 260) for n in subs_sorted]
    ax.scatter(xs, ys, s=sizes, c=COLOR_SUBSTANCE, alpha=0.9, edgecolors="white", linewidths=0.4, zorder=2)

    total_year = sum(loc_kg.values())
    ax.set_title(f"{year}\n{total_year:,.0f} Kg", fontsize=13, color=INK_PRIMARY)
    ax.set_xlim(-0.35, 1.35)
    ax.set_ylim(-0.02, 1.06)
    ax.axis("off")

fig2.suptitle("PRTR Tamaulipas — evolución Municipio ↔ Sustancia (4 cortes)", fontsize=16, color=INK_PRIMARY, y=0.99)
fig2.text(0.5, 0.005, "Tamaño = emisión de ese año (escala log, comparable entre paneles). "
                       "Filas fijas: municipios (izq.) y sustancias (der.) ordenados por su total historico.",
          ha="center", fontsize=9, color=INK_MUTED)

png_path = os.path.join(HERE, "tamaulipas_temporal_snapshots.png")
fig2.savefig(png_path, dpi=140, bbox_inches="tight", facecolor=SURFACE)
plt.close(fig2)
print(f"Written {png_path}")
