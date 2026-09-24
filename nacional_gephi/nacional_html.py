"""Interactive HTML for the national Gephi Toolkit graphs. Positions, colors and
sizes come from the *_fa2.gexf that Gephi exported; names/labels come from the
source GEXF (Gephi's render blanks the labels of small nodes); tooltips come
from prtr_hover (national scope); search / group buttons come from prtr_ui."""
import os
import shutil
import sys
sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")))
import networkx as nx
import plotly.graph_objects as go
import prtr_hover as H
import prtr_ui as U

HERE = os.path.dirname(os.path.abspath(__file__))
INK, SURFACE, EDGE = "#0b0b0b", "#fcfcfb", "#898781"
rgb = lambda c: f"rgb({c['r']},{c['g']},{c['b']})"
key_of = lambda n: n.split("::", 1)[1] if "::" in n else n


def load(folder, fa2, src):
    return nx.read_gexf(os.path.join(HERE, folder, fa2)), nx.read_gexf(os.path.join(HERE, folder, src))


def node_extra(d):
    ex = []
    if "Modularity Class" in d:
        ex.append(f"<b>Comunidad (Modularity de Gephi)</b>: #{int(d['Modularity Class']) + 1}")
    return ex


def groups_of(G, S, ids, level):
    """[(group name, [node ids])]: node type for bipartite graphs, Gephi community otherwise."""
    if "type" in S.nodes[ids[0]]:
        first = "Estado" if level == "estado" else "Municipio"
        return [(first, [n for n in ids if S.nodes[n]["type"] == "location"]),
                ("Sustancia", [n for n in ids if S.nodes[n]["type"] != "location"])]
    if "Modularity Class" in G.nodes[ids[0]]:
        cls = sorted({int(G.nodes[n]["Modularity Class"]) for n in ids})
        return [(f"Comunidad {c + 1}", [n for n in ids if int(G.nodes[n]["Modularity Class"]) == c]) for c in cls]
    return [("", ids)]


def render(folder, fa2, src, out, title, level, label_top, mid_top, px, pair_edges=False, search_out=None, placeholder=None):
    H.configure(None, level)
    G, S = load(folder, fa2, src)
    ids = list(G.nodes())
    P = {n: (G.nodes[n]["viz"]["position"]["x"], G.nodes[n]["viz"]["position"]["y"]) for n in ids}
    top = set(sorted(ids, key=lambda n: -float(S.nodes[n].get("total_kg", 0)))[:label_top])
    disp = {n: S.nodes[n].get("label", key_of(n)) for n in ids}
    ex, ey = [], []
    for u, v in G.edges():
        ex += [P[u][0], P[v][0], None]; ey += [P[u][1], P[v][1], None]
    lines = go.Scatter(x=ex, y=ey, mode="lines", line=dict(color=EDGE, width=0.5), opacity=0.25,
                       hoverinfo="none", showlegend=False, meta=dict(role="edges"))

    def node_trace(sub, name):
        return go.Scatter(
            x=[P[n][0] for n in sub], y=[P[n][1] for n in sub], mode="markers+text", name=name, showlegend=bool(name),
            text=[disp[n] if n in top else "" for n in sub], textposition="top center", textfont=dict(size=8, color=INK),
            marker=dict(size=[max(5, G.nodes[n]["viz"]["size"] * px) for n in sub],
                        color=[rgb(G.nodes[n]["viz"]["color"]) for n in sub], line=dict(width=1, color="white"), opacity=0.92),
            hovertext=[H.hover(key_of(n), extra=node_extra(G.nodes[n]) + [f"Conexiones en esta red: {G.degree[n]}"]) for n in sub],
            hoverinfo="text", meta=dict(role="nodes"))

    node_traces = [node_trace(sub, name) for name, sub in groups_of(G, S, ids, level)]
    edges = sorted(G.edges(), key=lambda e: -float(S[e[0]][e[1]].get("weight", 0)))[:mid_top]
    if pair_edges:
        txt = lambda u, v: H.muni_pair_hover(key_of(u), key_of(v), float(S[u][v]["weight"]))
    else:
        txt = lambda u, v: H.edge_hover(key_of(u), key_of(v))
    mids = H.edge_midpoints(edges, txt, P)
    note = f" · hover en {len(edges):,} de {G.number_of_edges():,} aristas (las de mayor peso)" if len(edges) < G.number_of_edges() else ""
    fig = go.Figure(data=[lines] + node_traces + [mids])
    fig.update_layout(title=dict(text=title + note, font=dict(color=INK, size=17)), plot_bgcolor=SURFACE, paper_bgcolor=SURFACE,
                      xaxis=dict(visible=False), yaxis=dict(visible=False, scaleanchor="x"),
                      height=1000, hoverlabel=H.HOVERLABEL)
    path = os.path.join(HERE, folder, out)
    U.write(fig, path, placeholder=placeholder)
    if search_out:                       # same capabilities under the historical "_buscador" name
        shutil.copyfile(path, os.path.join(HERE, folder, search_out))
        print("Written", os.path.join(HERE, folder, search_out))


def render_geo(folder, fa2, src, out, title, placeholder=None):
    H.configure(None, "estado")
    G, S = load(folder, fa2, src)
    ids = list(G.nodes())
    ll = {n: (float(S.nodes[n]["lat"]), float(S.nodes[n]["lon"])) for n in ids}
    la, lo = [], []
    for u, v in G.edges():
        la += [ll[u][0], ll[v][0], None]; lo += [ll[u][1], ll[v][1], None]
    lines = go.Scattergeo(lat=la, lon=lo, mode="lines", line=dict(width=0.8, color=EDGE), opacity=0.4, hoverinfo="none",
                          showlegend=False, meta=dict(role="edges"))
    traces = []
    for name, sub in groups_of(G, S, ids, "estado"):
        traces.append(go.Scattergeo(
            lat=[ll[n][0] for n in sub], lon=[ll[n][1] for n in sub], mode="markers+text", text=sub, textposition="top center",
            textfont=dict(size=9, color=INK), name=name, showlegend=bool(name),
            marker=dict(size=[max(8, G.nodes[n]["viz"]["size"] * 0.8) for n in sub], color=[rgb(G.nodes[n]["viz"]["color"]) for n in sub],
                        line=dict(width=1, color="white")),
            hovertext=[H.hover(n, extra=node_extra(G.nodes[n]) + [f"Estados con perfil similar (coseno ≥ umbral): {G.degree[n]}"]) for n in sub],
            hoverinfo="text", meta=dict(role="nodes")))
    mids = H.edge_midpoints(list(G.edges()), lambda u, v: H.muni_pair_hover(u, v, float(S[u][v]["weight"])), None, geo=True, latlon=ll)
    fig = go.Figure(data=[lines] + traces + [mids])
    fig.update_geos(scope="north america", resolution=50, showcountries=True, countrycolor="#c3c2b7", showland=True, landcolor="#f2f1ec",
                    showocean=True, oceancolor="#eaf2f8", lataxis_range=[13.5, 33.5], lonaxis_range=[-119, -85])
    fig.update_layout(title=dict(text=title, font=dict(color=INK, size=17)), paper_bgcolor=SURFACE, height=900,
                      hoverlabel=H.HOVERLABEL)
    U.write(fig, os.path.join(HERE, folder, out), placeholder=placeholder)


render("estado_estado", "estado_estado_fa2.gexf", "estado_estado.gexf", "estado_estado_fa2.html",
       "México — similitud de perfil de emisiones entre estados (ForceAtlas2 + Modularity de Gephi)", "estado", 32, 999, 0.9,
       pair_edges=True, placeholder="Buscar estado…")
render("estado_sustancia", "estado_sustancia_fa2.gexf", "estado_sustancia.gexf", "estado_sustancia_fa2.html",
       "México — Estado ↔ Sustancia (ForceAtlas2)", "estado", 90, 999, 0.9)
render("municipio_sustancia", "municipio_sustancia_fa2.gexf", "municipio_sustancia.gexf", "municipio_sustancia_fa2.html",
       "México — Municipio ↔ Sustancia (716 municipios, ForceAtlas2)", "municipio", 45, 2500, 0.6,
       search_out="municipio_sustancia_fa2_buscador.html")
render_geo("geografico", "estado_geo_toolkit.gexf", "estado_geo.gexf", "estado_geo.html",
           "México — similitud de perfil de emisiones entre estados, sobre el mapa", placeholder="Buscar estado…")
