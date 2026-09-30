"""Interactive HTML for the national mortality Gephi Toolkit graphs (mirrors
graphs_pollutants/nacional_gephi/nacional_html.py's conventions). Positions,
colors and sizes come from the *_fa2/_toolkit.gexf that Gephi exported;
labels/attributes come from the source (pre-Gephi) GEXF; tooltips come from
mortality_hover.py; search / group buttons come from the shared prtr_ui.
NOT wired into build_index.py / index.html yet - staging output only.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.normpath(os.path.join(HERE, "..", "..")))
import networkx as nx
import plotly.graph_objects as go
import prtr_ui as U
import mortality_hover as H

U.PLURAL["Cause"] = "causes"
U.PLURAL["State"] = "states"
U.PLURAL["Municipality"] = "municipalities"

INK, SURFACE, EDGE = "#0b0b0b", "#fcfcfb", "#898781"
rgb = lambda c: f"rgb({c['r']},{c['g']},{c['b']})"
key_of = lambda n: n.split("::", 1)[1] if "::" in n else n


def load(folder, fa2, src):
    return nx.read_gexf(os.path.join(HERE, folder, fa2)), nx.read_gexf(os.path.join(HERE, folder, src))


def node_extra(d):
    ex = []
    if "Modularity Class" in d:
        ex.append(f"<b>Community (Gephi Modularity)</b>: #{int(d['Modularity Class']) + 1}")
    return ex


def groups_of(G, S, ids):
    if "type" in S.nodes[ids[0]]:
        first = "State" if all("." not in key_of(n) for n in ids if S.nodes[n]["type"] == "location") else "Municipality"
        return [(first, [n for n in ids if S.nodes[n]["type"] == "location"]),
                ("Cause", [n for n in ids if S.nodes[n]["type"] != "location"])]
    if "Modularity Class" in G.nodes[ids[0]]:
        cls = sorted({int(G.nodes[n]["Modularity Class"]) for n in ids})
        return [(f"Community {c + 1}", [n for n in ids if int(G.nodes[n]["Modularity Class"]) == c]) for c in cls]
    return [("", ids)]


def node_hover(n, S, loc_level, is_bipartite, chapter):
    d = S.nodes[n]
    key = key_of(n)
    extra = node_extra(nx_dummy_get(S, n)) + []
    if is_bipartite and d.get("type") == "causa":
        return H.hover_causa(key, chapter, desc=d.get("label"), national_total=d.get("total_kg"), extra=extra, loc_level=loc_level)
    return H.hover_location(key, loc_level, chapter, extra=extra)


def nx_dummy_get(S, n):
    return S.nodes[n]


def render(folder, fa2, src, out, title, label_top, mid_top, px, is_bipartite, chapter, placeholder=None,
           draw_min_weight=None, webgl=False, edge_opacity=0.25, edge_width=0.5, node_min_size=5, node_border_width=1):
    G, S = load(folder, fa2, src)
    ids = list(G.nodes())
    P = {n: (G.nodes[n]["viz"]["position"]["x"], G.nodes[n]["viz"]["position"]["y"]) for n in ids}
    top = set(sorted(ids, key=lambda n: -float(S.nodes[n].get("total_kg", 0)))[:label_top])
    disp = {n: S.nodes[n].get("label", key_of(n)) for n in ids}
    drawn_edges = [(u, v) for u, v in G.edges() if draw_min_weight is None or float(S[u][v].get("weight", 0)) > draw_min_weight]
    ex, ey = [], []
    for u, v in drawn_edges:
        ex += [P[u][0], P[v][0], None]; ey += [P[u][1], P[v][1], None]
    ScatterEdges = go.Scattergl if webgl else go.Scatter
    lines = ScatterEdges(x=ex, y=ey, mode="lines", line=dict(color=EDGE, width=edge_width), opacity=edge_opacity,
                         hoverinfo="none", showlegend=False, meta=dict(role="edges"))

    NodeScatter = go.Scattergl if webgl else go.Scatter
    loc_level = "municipio" if "municipio" in folder else "estado"

    def node_trace(sub, name):
        return NodeScatter(
            x=[P[n][0] for n in sub], y=[P[n][1] for n in sub], mode="markers+text", name=name, showlegend=bool(name),
            text=[disp[n] if n in top else "" for n in sub], textposition="top center", textfont=dict(size=8, color=INK),
            marker=dict(size=[max(node_min_size, G.nodes[n]["viz"]["size"] * px) for n in sub],
                        color=[rgb(G.nodes[n]["viz"]["color"]) for n in sub], line=dict(width=node_border_width, color="white"), opacity=0.92),
            hovertext=[node_hover(n, S, loc_level, is_bipartite, chapter) + f"<br>Connections in this network: {G.degree[n]}" for n in sub],
            hoverinfo="text", meta=dict(role="nodes"))

    node_traces = [node_trace(sub, name) for name, sub in groups_of(G, S, ids)]
    edges = sorted(G.edges(), key=lambda e: -float(S[e[0]][e[1]].get("weight", 0)))[:mid_top]

    if is_bipartite:
        def txt(u, v):
            loc, cau = (u, v) if S.nodes[u]["type"] == "location" else (v, u)
            lk, ck = key_of(loc), key_of(cau)
            level = "municipio" if "." in lk else "estado"
            return H.edge_hover_loc_causa(lk, level, ck, chapter, float(S[u][v]["weight"]), desc=S.nodes[cau].get("label"))
    else:
        def txt(u, v):
            return H.sim_edge_hover(key_of(u), key_of(v), float(S[u][v]["weight"]), "chapter" if chapter else "specific")

    mids = H.edge_midpoints(edges, txt, P) if hasattr(H, "edge_midpoints") else _mids(edges, txt, P)
    note = f" · hover on {len(edges):,} of {G.number_of_edges():,} edges (the heaviest)" if len(edges) < G.number_of_edges() else ""
    if len(drawn_edges) < G.number_of_edges():
        note += f" · drawing {len(drawn_edges):,} of {G.number_of_edges():,} edges (>{draw_min_weight:g} deaths)"
    fig = go.Figure(data=[lines] + node_traces + [mids])
    fig.update_layout(title=dict(text=title + note, font=dict(color=INK, size=17)), plot_bgcolor=SURFACE, paper_bgcolor=SURFACE,
                      xaxis=dict(visible=False), yaxis=dict(visible=False, scaleanchor="x"),
                      height=1000, hoverlabel=H.HOVERLABEL)
    path = os.path.join(HERE, folder, out)
    U.write(fig, path, placeholder=placeholder)


def _mids(edges, textfn, pos):
    xs, ys, tx = [], [], []
    for u, v in edges:
        xs.append((pos[u][0] + pos[v][0]) / 2); ys.append((pos[u][1] + pos[v][1]) / 2)
        tx.append(textfn(u, v))
    return go.Scatter(x=xs, y=ys, mode="markers", marker=dict(size=9, color="rgba(0,0,0,0)"),
                      hovertext=tx, hoverinfo="text", showlegend=False, meta=dict(role="edgehover"))


def render_geo(folder, fa2, src, out, title, chapter, placeholder=None):
    G, S = load(folder, fa2, src)
    ids = list(G.nodes())
    ll = {n: (float(S.nodes[n]["lat"]), float(S.nodes[n]["lon"])) for n in ids}
    la, lo = [], []
    for u, v in G.edges():
        la += [ll[u][0], ll[v][0], None]; lo += [ll[u][1], ll[v][1], None]
    lines = go.Scattergeo(lat=la, lon=lo, mode="lines", line=dict(width=0.8, color=EDGE), opacity=0.4, hoverinfo="none",
                          showlegend=False, meta=dict(role="edges"))
    traces = []
    for name, sub in groups_of(G, S, ids):
        traces.append(go.Scattergeo(
            lat=[ll[n][0] for n in sub], lon=[ll[n][1] for n in sub], mode="markers+text", text=sub, textposition="top center",
            textfont=dict(size=9, color=INK), name=name, showlegend=bool(name),
            marker=dict(size=[max(8, G.nodes[n]["viz"]["size"] * 0.8) for n in sub], color=[rgb(G.nodes[n]["viz"]["color"]) for n in sub],
                        line=dict(width=1, color="white")),
            hovertext=[node_hover(n, S, "estado", False, chapter) + f"<br>States with a similar cause profile: {G.degree[n]}" for n in sub],
            hoverinfo="text", meta=dict(role="nodes")))
    mids = H.edge_midpoints(list(G.edges()), lambda u, v: H.sim_edge_hover(u, v, float(S[u][v]["weight"]),
                                                                            "chapter" if chapter else "specific"),
                             None, geo=True, latlon=ll)
    fig = go.Figure(data=[lines] + traces + [mids])
    fig.update_geos(scope="north america", resolution=50, showcountries=True, countrycolor="#c3c2b7", showland=True, landcolor="#f2f1ec",
                    showocean=True, oceancolor="#eaf2f8", lataxis_range=[13.5, 33.5], lonaxis_range=[-119, -85])
    fig.update_layout(title=dict(text=title, font=dict(color=INK, size=17)), paper_bgcolor=SURFACE, height=900,
                      hoverlabel=H.HOVERLABEL)
    U.write(fig, os.path.join(HERE, folder, out), placeholder=placeholder)


# ---- monkeypatch: mortality_hover has no edge_midpoints of its own (kept module small);
# reuse prtr_hover's generic implementation (no PRTR-specific state involved).
if not hasattr(H, "edge_midpoints"):
    import prtr_hover as _PH
    H.edge_midpoints = _PH.edge_midpoints


render("estado_estado", "estado_estado_capitulo_fa2.gexf", "estado_estado_capitulo.gexf", "estado_estado_capitulo_fa2.html",
       "Mexico — mortality-cause profile similarity between states (23 ICD chapters, ForceAtlas2 + Gephi Modularity)",
       32, 200, 0.9, False, True, placeholder="Search state…")
render("estado_estado", "estado_estado_especifico_fa2.gexf", "estado_estado_especifico.gexf", "estado_estado_especifico_fa2.html",
       "Mexico — mortality-cause profile similarity between states (top 100 specific causes, ForceAtlas2 + Gephi Modularity)",
       32, 200, 0.9, False, False, placeholder="Search state…")

render("estado_causa", "estado_causa_capitulo_fa2.gexf", "estado_causa_capitulo.gexf", "estado_causa_capitulo_fa2.html",
       "Mexico — State ↔ Cause of death (23 ICD chapters, ForceAtlas2)", 55, 736, 0.9, True, True)
render("estado_causa", "estado_causa_especifico_fa2.gexf", "estado_causa_especifico.gexf", "estado_causa_especifico_fa2.html",
       "Mexico — State ↔ Cause of death (top 100 specific ICD codes nationally by death count, ForceAtlas2)",
       90, 3200, 0.9, True, False)

render("municipio_causa", "municipio_causa_capitulo_fa2.gexf", "municipio_causa_capitulo.gexf", "municipio_causa_capitulo_fa2.html",
       "Mexico — Municipality ↔ Cause of death (2,378 municipalities, 23 ICD chapters, ForceAtlas2)",
       45, 2500, 0.6, True, True)
render("municipio_causa", "municipio_causa_especifico_fa2.gexf", "municipio_causa_especifico.gexf", "municipio_causa_especifico_fa2.html",
       "Mexico — Municipality ↔ Cause of death (top 100 specific ICD codes, >100 deaths/edge, ForceAtlas2)",
       45, 2500, 0.6, True, False)

render("municipio_causa", "municipio_causa_especifico_completo_fa2.gexf", "municipio_causa_especifico_completo.gexf",
       "municipio_causa_especifico_completo_ligero_fa2.html",
       "Mexico — Municipality ↔ Cause of death (ALL 2,378 municipalities, ALL 1,511 specific ICD codes, ForceAtlas2)",
       45, 2500, 1.0, True, False, draw_min_weight=100, webgl=True,
       edge_opacity=0.12, edge_width=0.4, node_min_size=6, node_border_width=1.5)

render_geo("geografico", "estado_geo_capitulo_toolkit.gexf", "estado_geo_capitulo.gexf", "estado_geo_capitulo.html",
           "Mexico — mortality-cause profile similarity between states (23 ICD chapters), on the map", True,
           placeholder="Search state…")
render_geo("geografico", "estado_geo_especifico_toolkit.gexf", "estado_geo_especifico.gexf", "estado_geo_especifico.html",
           "Mexico — mortality-cause profile similarity between states (top 100 specific causes), on the map", False,
           placeholder="Search state…")

print("ALL HTML WRITTEN")
