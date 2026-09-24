"""Two one-mode ('projected') networks built from the Tamaulipas PRTR bipartite
graph (Municipio <-> Sustancia):

  1. Sustancia <-> Sustancia: two substances are linked if the same municipio
     reports both; weight = number of municipios where that co-occurs.
  2. Municipio <-> Municipio: two municipios are linked by the cosine
     similarity of their emission profile (log Kg/ano per substance).

Both are rendered as force-directed layouts (unlike the bipartite graph, a
one-mode projection isn't dense-bipartite, so spring_layout actually spreads
it out), colored by detected community (Louvain), sized by degree/strength.
Outputs (per network): a static PNG (matplotlib) and an interactive HTML
(plotly, hover tooltips).
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
import numpy as np
import plotly.graph_objects as go

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "..", "prtr_raw_for_stori_stori.csv")
STATE_FILTER = "Tamaulipas"

# Reference palette (dataviz skill) - fixed categorical order, slots 1-8
CAT_COLORS = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100",
              "#e87ba4", "#008300", "#4a3aa7", "#e34948"]
OTHER_COLOR = "#c3c2b7"
INK_PRIMARY = "#0b0b0b"
INK_SECONDARY = "#52514e"
INK_MUTED = "#898781"
SURFACE = "#fcfcfb"
EDGE_COLOR = "#898781"

# ---------------------------------------------------------------------------
# 1. Load Tamaulipas rows -> per-municipio substance totals (Kg/ano)
# ---------------------------------------------------------------------------
# muni_sub_totals[municipio][substance] = summed Kg/ano
muni_sub_totals = {}

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

        muni_sub_totals.setdefault(loc, {})
        muni_sub_totals[loc][substance] = muni_sub_totals[loc].get(substance, 0.0) + value

municipios = sorted(muni_sub_totals)
all_substances = sorted({s for subs in muni_sub_totals.values() for s in subs})
print(f"{len(municipios)} municipios, {len(all_substances)} sustancias (Tamaulipas)")


def scaled(value, values, lo, hi):
    vmin, vmax = min(values), max(values)
    if vmax == vmin:
        return (lo + hi) / 2
    t = (math.log1p(value) - math.log1p(vmin)) / (math.log1p(vmax) - math.log1p(vmin))
    return lo + t * (hi - lo)


def community_layout(comp, comm_of, seed=7):
    """Layout a dense component in two independent passes: first place each
    community as a single point in a small meta-graph (so communities repel
    each other), then layout each community's own nodes locally and offset by
    its meta position. A single spring_layout over all nodes at once - even
    with community-seeded initial positions - kept relaxing back into one
    pile because attraction across communities is nearly as strong as within;
    doing it in two independent passes removes that global pull entirely."""
    comm_ids = sorted({comm_of[n] for n in comp.nodes()})
    if len(comm_ids) <= 1:
        return None

    meta = nx.Graph()
    meta.add_nodes_from(comm_ids)
    for u, v, d in comp.edges(data=True):
        cu, cv = comm_of[u], comm_of[v]
        if cu == cv:
            continue
        w = d.get("weight", 1.0)
        if meta.has_edge(cu, cv):
            meta[cu][cv]["weight"] += w
        else:
            meta.add_edge(cu, cv, weight=w)
    meta_pos = nx.spring_layout(meta, weight="weight", seed=seed,
                                 k=2.0 / math.sqrt(max(len(comm_ids), 1)), iterations=200)

    pos = {}
    scale = 3.6
    for c in comm_ids:
        nodes_c = [n for n in comp.nodes() if comm_of[n] == c]
        if len(nodes_c) == 1:
            local = {nodes_c[0]: (0.0, 0.0)}
        else:
            sub = comp.subgraph(nodes_c)
            k = 1.1 / math.sqrt(len(nodes_c))
            local = nx.spring_layout(sub, weight=None, k=k, iterations=300, seed=seed)
        cx, cy = meta_pos[c]
        for n, (x, y) in local.items():
            pos[n] = (cx * scale + x, cy * scale + y)
    return pos


def multi_component_layout(G, node_comm=None, seed=7):
    """Lay out each connected component independently (spring layout, no
    weight-based attraction so dense near-cliques don't collapse to a point),
    then pack components into grid cells so far-apart components don't distort
    each other's scale - a single global spring_layout put every disconnected
    cluster in one shared coordinate system and it either collapsed into a
    single point or scattered a couple of components far off-canvas.

    A large component that itself contains several Louvain communities still
    collapses under plain spring_layout (it's dense - every community is
    heavily linked to every other). When node_comm is given, big components
    seed spring_layout with one ring position per community first, so the
    optimizer separates communities instead of settling into one pile.
    """
    components = [G.subgraph(c).copy() for c in nx.connected_components(G)]
    components.sort(key=lambda c: -c.number_of_nodes())
    cols = max(1, math.ceil(math.sqrt(len(components))))

    pos = {}
    col_widths = {}
    row_heights = {}
    local_positions = []
    for comp in components:
        n = comp.number_of_nodes()
        if n == 1:
            local = {next(iter(comp.nodes())): (0.0, 0.0)}
            radius = 0.3
        else:
            local = None
            if node_comm and n > 15:
                local = community_layout(comp, node_comm, seed=seed)
            if local is None:
                k = 2.5 / math.sqrt(n)
                local = nx.spring_layout(comp, weight=None, k=k, iterations=400, seed=seed)
            radius = max(abs(x) for x, _ in local.values()) or 1.0
            radius = max(radius, max(abs(y) for _, y in local.values()))
        local_positions.append((comp, local, radius))

    for idx, (comp, local, radius) in enumerate(local_positions):
        row, col = divmod(idx, cols)
        col_widths[col] = max(col_widths.get(col, 0), radius)
        row_heights[row] = max(row_heights.get(row, 0), radius)

    col_x = {}
    x_cursor = 0.0
    for c in range(cols):
        col_x[c] = x_cursor
        x_cursor += 2 * col_widths.get(c, 1.0) + 1.2

    row_y = {}
    y_cursor = 0.0
    for r in range(math.ceil(len(components) / cols)):
        row_y[r] = y_cursor
        y_cursor -= 2 * row_heights.get(r, 1.0) + 1.2

    for idx, (comp, local, radius) in enumerate(local_positions):
        row, col = divmod(idx, cols)
        cx, cy = col_x[col], row_y[row]
        for n, (x, y) in local.items():
            pos[n] = (cx + x, cy + y)
    return pos


def color_by_community(G, seed=42):
    communities = nx.community.louvain_communities(G, weight="weight", seed=seed)
    communities = sorted(communities, key=len, reverse=True)
    node_color = {}
    node_comm = {}
    for i, comm in enumerate(communities):
        color = CAT_COLORS[i] if i < len(CAT_COLORS) else OTHER_COLOR
        for n in comm:
            node_color[n] = color
            node_comm[n] = i if i < len(CAT_COLORS) else -1
    return node_color, node_comm, len(communities)


def render(G, out_prefix, title, subtitle, node_color, node_comm, size_attr="strength", pair_hover=None, search_placeholder="Buscar por nombre…"):
    pos = multi_component_layout(G, node_comm=node_comm)

    sizes_vals = [d[size_attr] for _, d in G.nodes(data=True)]
    node_size_px = {n: scaled(d[size_attr], sizes_vals, 80, 1600) for n, d in G.nodes(data=True)}
    weights_vals = [d["weight"] for _, _, d in G.edges(data=True)]
    edge_w = {(u, v): scaled(d["weight"], weights_vals, 0.3, 2.5) for u, v, d in G.edges(data=True)}

    # --- static PNG ---
    fig, ax = plt.subplots(figsize=(15, 13), facecolor=SURFACE)
    ax.set_facecolor(SURFACE)
    for u, v in G.edges():
        x = [pos[u][0], pos[v][0]]
        y = [pos[u][1], pos[v][1]]
        ax.plot(x, y, color=EDGE_COLOR, linewidth=edge_w[(u, v)], alpha=0.25, zorder=1)
    xs = [pos[n][0] for n in G.nodes()]
    ys = [pos[n][1] for n in G.nodes()]
    sizes = [node_size_px[n] for n in G.nodes()]
    colors = [node_color[n] for n in G.nodes()]
    ax.scatter(xs, ys, s=sizes, c=colors, alpha=0.92, edgecolors="white", linewidths=0.7, zorder=2)
    for n in G.nodes():
        x, y = pos[n]
        ax.annotate(n, (x, y), fontsize=7.5, color=INK_PRIMARY, ha="center", va="bottom",
                    xytext=(0, 7), textcoords="offset points", zorder=3)
    ax.set_title(title, fontsize=16, color=INK_PRIMARY, pad=14)
    ax.text(0.5, -0.01, subtitle, transform=ax.transAxes, ha="center", fontsize=8.5, color=INK_MUTED)
    ax.axis("off")
    png_path = os.path.join(HERE, f"{out_prefix}.png")
    fig.savefig(png_path, dpi=150, bbox_inches="tight", facecolor=SURFACE)
    plt.close(fig)
    print(f"Written {png_path}")

    # --- interactive HTML ---
    edge_x, edge_y = [], []
    for u, v in G.edges():
        edge_x += [pos[u][0], pos[v][0], None]
        edge_y += [pos[u][1], pos[v][1], None]
    edge_trace = go.Scatter(x=edge_x, y=edge_y, mode="lines",
                             line=dict(color=EDGE_COLOR, width=0.7),
                             opacity=0.3, hoverinfo="none", showlegend=False, meta=dict(role="edges"))

    def node_hover(n):
        return H.hover(n, extra=[
            (f"<b>Comunidad detectada (Louvain)</b>: #{node_comm[n] + 1}" if node_comm.get(n, -1) >= 0 else "Comunidad: otras"),
            f"Conexiones en esta red: {G.degree[n]} · peso medio {sum(d['weight'] for _, _, d in G.edges(n, data=True)) / max(G.degree[n], 1):.2f}"])

    node_traces = []
    for c in sorted({node_comm.get(n, -1) for n in G.nodes()}):      # one trace per community
        sub = [n for n in G.nodes() if node_comm.get(n, -1) == c]
        node_traces.append(go.Scatter(
            x=[pos[n][0] for n in sub], y=[pos[n][1] for n in sub], mode="markers+text", text=sub,
            textposition="top center", textfont=dict(size=8, color=INK_SECONDARY),
            name=(f"Comunidad {c + 1}" if c >= 0 else "Otras comunidades"),
            marker=dict(size=[node_size_px[n] ** 0.5 for n in sub], color=[node_color[n] for n in sub],
                        line=dict(width=1, color="white"), opacity=0.92),
            hovertext=[node_hover(n) for n in sub], hoverinfo="text", meta=dict(role="nodes")))

    data = [edge_trace] + node_traces
    if pair_hover:
        data.append(H.edge_midpoints(list(G.edges()), lambda u, v: pair_hover(u, v, G[u][v]['weight']), pos))
    fig2 = go.Figure(data=data)
    fig2.update_layout(
        title=dict(text=title, font=dict(color=INK_PRIMARY, size=18)),
        plot_bgcolor=SURFACE, paper_bgcolor=SURFACE,
        xaxis=dict(visible=False), yaxis=dict(visible=False),
        margin=dict(l=20, r=20, t=60, b=20),
        hoverlabel=H.HOVERLABEL,
        height=1000,
    )
    html_path = os.path.join(HERE, f"{out_prefix}.html")
    U.write(fig2, html_path, placeholder=search_placeholder)
    print(f"Written {html_path}")


# ---------------------------------------------------------------------------
# 2. Sustancia <-> Sustancia (co-occurrence across municipios, Jaccard-weighted)
# ---------------------------------------------------------------------------
# Raw co-occurrence counts turned out to be a bad edge weight here: substances
# that are simply common (reported almost everywhere, e.g. heavy metals under
# broad reporting rules) trivially "co-occur" with everything, producing a
# near-complete graph (>=80% density at every count threshold tried). Jaccard
# (co-occurrence / union of municipios reporting either) corrects for that base
# rate, so only genuinely paired substances stay connected.
JACCARD_THRESHOLD = 0.7

pair_counts = {}
sub_muni_count = {s: 0 for s in all_substances}
for loc, subs in muni_sub_totals.items():
    present = sorted(subs)
    for s in present:
        sub_muni_count[s] += 1
    for i in range(len(present)):
        for j in range(i + 1, len(present)):
            key = (present[i], present[j])
            pair_counts[key] = pair_counts.get(key, 0) + 1

Gs = nx.Graph()
for s in all_substances:
    Gs.add_node(s, strength=sub_muni_count[s])
for (a, b), count in pair_counts.items():
    union = sub_muni_count[a] + sub_muni_count[b] - count
    jaccard = count / union if union > 0 else 0.0
    if jaccard >= JACCARD_THRESHOLD:
        Gs.add_edge(a, b, weight=jaccard)
Gs.remove_nodes_from(list(nx.isolates(Gs)))

print(f"Sustancia-Sustancia: {Gs.number_of_nodes()} nodos, {Gs.number_of_edges()} aristas "
      f"(Jaccard >= {JACCARD_THRESHOLD})")

sub_color, sub_comm, n_comm_sub = color_by_community(Gs)
render(
    Gs, "sustancia_sustancia",
    "Tamaulipas — Coocurrencia de sustancias (municipios en comun)",
    f"Dos sustancias se conectan si su similitud de Jaccard (municipios que reportan una y/u otra) >= {JACCARD_THRESHOLD}. "
    f"Color = comunidad (Louvain, {n_comm_sub} grupos). Tamano = # municipios que la reportan.",
    sub_color, sub_comm, size_attr="strength", pair_hover=H.sub_pair_hover, search_placeholder="Buscar sustancia (nombre o símbolo)…",
)

# ---------------------------------------------------------------------------
# 3. Municipio <-> Municipio (cosine similarity of emission profile)
# ---------------------------------------------------------------------------
sub_index = {s: i for i, s in enumerate(all_substances)}
vectors = {}
for loc in municipios:
    vec = np.zeros(len(all_substances))
    for s, kg in muni_sub_totals[loc].items():
        vec[sub_index[s]] = math.log1p(kg)
    vectors[loc] = vec

SIM_THRESHOLD = 0.7

Gm = nx.Graph()
for loc in municipios:
    Gm.add_node(loc, strength=sum(muni_sub_totals[loc].values()))

for i in range(len(municipios)):
    for j in range(i + 1, len(municipios)):
        a, b = municipios[i], municipios[j]
        va, vb = vectors[a], vectors[b]
        denom = np.linalg.norm(va) * np.linalg.norm(vb)
        sim = float(np.dot(va, vb) / denom) if denom > 0 else 0.0
        if sim >= SIM_THRESHOLD:
            Gm.add_edge(a, b, weight=sim)
Gm.remove_nodes_from(list(nx.isolates(Gm)))

print(f"Municipio-Municipio: {Gm.number_of_nodes()} nodos, {Gm.number_of_edges()} aristas "
      f"(umbral similitud coseno >= {SIM_THRESHOLD})")

muni_color, muni_comm, n_comm_muni = color_by_community(Gm)
render(
    Gm, "municipio_municipio",
    "Tamaulipas — Similitud de perfil de emisiones entre municipios",
    f"Dos municipios se conectan si su similitud coseno (perfil de sustancias, log Kg/ano) >= {SIM_THRESHOLD}. "
    f"Color = comunidad (Louvain, {n_comm_muni} grupos). Tamano = emision total (Kg/ano).",
    muni_color, muni_comm, size_attr="strength", pair_hover=H.muni_pair_hover, search_placeholder="Buscar municipio…",
)
