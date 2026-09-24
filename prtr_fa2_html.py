"""HTML for a Gephi-exported *_fa2.gexf (Tamaulipas): positions / colors / sizes come from the
viz: attributes Gephi wrote; tooltips from prtr_hover; search + group buttons from prtr_ui.
Nodes are grouped by ego role, node type or Gephi community, whichever the file carries."""
import glob
import os

import networkx as nx
import plotly.graph_objects as go

import prtr_hover as H
import prtr_ui as U

INK, SURFACE, EDGE = "#0b0b0b", "#fcfcfb", "#898781"
ROLE = {"focal": "Foco", "substance": "Sustancia", "peer_municipio": "Municipio vecino"}
TYPE = {"location": "Municipio", "substance": "Sustancia", "medio": "Medio"}
rgb = lambda c: f"rgb({c['r']},{c['g']},{c['b']})"


def _extra(G, n):
    d = G.nodes[n]
    ex = []
    if "Modularity Class" in d:
        ex.append(f"<b>Comunidad (Modularity de Gephi)</b>: #{int(d['Modularity Class']) + 1}")
    if "Betweenness Centrality" in d:
        ex.append(f"<b>Centralidad</b>: betweenness {float(d['Betweenness Centrality']):.1f} · PageRank {float(d.get('PageRank', 0)):.4f}")
    if "role" in d:
        ex.append("<b>Rol en la ego-network</b>: " + {"focal": "foco", "substance": "sustancia principal del foco",
                                                       "peer_municipio": "municipio vecino"}.get(d["role"], d["role"]))
    if "first_year" in d:
        ex.append(f"<b>Primer año en el registro</b>: {int(d['first_year'])} · años activo: {int(d['n_years_active'])}")
    ex.append(f"Conexiones en esta red: {G.degree[n]}")
    return ex


def _groups(G):
    ids = list(G.nodes())
    d0 = G.nodes[ids[0]]
    if "role" in d0:
        return [(ROLE.get(r, r), [n for n in ids if G.nodes[n]["role"] == r]) for r in ("focal", "substance", "peer_municipio")]
    if "type" in d0:
        vals = sorted({G.nodes[n]["type"] for n in ids}, key=lambda v: (v != "location", v))
        return [(TYPE.get(v, v), [n for n in ids if G.nodes[n]["type"] == v]) for v in vals]
    if "Modularity Class" in d0:
        cls = sorted({int(G.nodes[n]["Modularity Class"]) for n in ids})
        return [(f"Comunidad {c + 1}", [n for n in ids if int(G.nodes[n]["Modularity Class"]) == c]) for c in cls]
    return [("", ids)]


def render_gexf(path, out, title, placeholder=None):
    G = nx.read_gexf(path)
    lab = lambda n: G.nodes[n].get("label", n)
    P = {n: (G.nodes[n]["viz"]["position"]["x"], G.nodes[n]["viz"]["position"]["y"]) for n in G.nodes()}
    ex, ey = [], []
    for u, v in G.edges():
        ex += [P[u][0], P[v][0], None]; ey += [P[u][1], P[v][1], None]
    lines = go.Scatter(x=ex, y=ey, mode="lines", line=dict(color=EDGE, width=0.6), opacity=0.3,
                       hoverinfo="none", showlegend=False, meta=dict(role="edges"))
    traces = []
    for name, sub in _groups(G):
        if not sub:
            continue
        traces.append(go.Scatter(
            x=[P[n][0] for n in sub], y=[P[n][1] for n in sub], mode="markers+text", text=[lab(n) for n in sub],
            textposition="top center", textfont=dict(size=8, color=INK), name=name, showlegend=bool(name),
            marker=dict(size=[max(6, G.nodes[n]["viz"]["size"] ** 0.9) for n in sub],
                        color=[rgb(G.nodes[n]["viz"]["color"]) for n in sub], line=dict(width=1, color="white")),
            hovertext=[H.hover(lab(n), extra=_extra(G, n)) for n in sub], hoverinfo="text", meta=dict(role="nodes")))

    def edge_text(u, v):
        a, b, w = lab(u), lab(v), float(G[u][v].get("weight", 0))
        ka, kb = H.resolve(a)[0], H.resolve(b)[0]
        if ka == kb == "loc":
            return H.muni_pair_hover(a, b, w)
        if ka == kb == "sub":
            return H.sub_pair_hover(a, b, w)
        return H.edge_hover(a, b)

    mids = H.edge_midpoints(list(G.edges()), edge_text, P)
    fig = go.Figure(data=[lines] + traces + [mids])
    fig.update_layout(title=dict(text=title, font=dict(color=INK, size=18)), plot_bgcolor=SURFACE, paper_bgcolor=SURFACE,
                      xaxis=dict(visible=False), yaxis=dict(visible=False, scaleanchor="x"), height=1000, hoverlabel=H.HOVERLABEL)
    U.write(fig, out, placeholder=placeholder)


def render_folder(base, titles, skip=(), placeholders=None):
    for path in sorted(glob.glob(os.path.join(base, "*", "*_fa2.gexf"))):
        stem = os.path.splitext(os.path.basename(path))[0]
        if any(s in path for s in skip):
            continue
        out = os.path.join(os.path.dirname(path), stem.replace("_toolkit", "") + ".html")
        render_gexf(path, out, titles.get(stem, stem), (placeholders or {}).get(stem))
