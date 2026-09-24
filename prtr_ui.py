"""Shared interactive layer for every PRTR HTML graph (search box, type/group
buttons, legend, tooltip control).  One call replaces `fig.write_html(...)`:

    import prtr_ui as U
    fig = go.Figure([lines, nodesA, nodesB, mids])      # traces tagged with meta (below)
    U.write(fig, path)

Trace convention (set via `meta=dict(role=...)`):
    role="edges"      the thin line trace with all edges (optional)
    role="nodes"      one trace per group of nodes (`name` = group name, shown in the legend);
                      every point needs `hovertext` starting with <b>Name</b>
    role="edgehover"  invisible midpoints carrying the edge tooltips (prtr_hover.edge_midpoints)
Groups are node types (Municipio / Sustancia), roles (Foco / Vecino) or communities.
With 2-4 groups you get the button row  Todos | Solo X | Solo Y | Atenuar X | Atenuar Y ;
with more, two dropdowns (Ver / Atenuar). Dimming a group also hides its labels and its
tooltips (and the edge tooltips); "Solo" hides the other groups and the edges.
"""
import json
import math
import os
import re

import plotly.graph_objects as go

HERE = os.path.dirname(os.path.abspath(__file__))
INK = "#0b0b0b"
TRANSPARENT = "rgba(11,11,11,0)"
PLURAL = {"Municipio": "municipios", "Sustancia": "sustancias", "Estado": "estados", "Medio": "medios",
          "Foco": "el foco", "Municipio vecino": "municipios vecinos"}


def _role(t):
    m = t.meta
    return m.get("role") if isinstance(m, dict) else None


def _list(v, n=None, default=None):
    if v is None:
        return [default] * (n or 0)
    if isinstance(v, (list, tuple)):
        return list(v)
    try:                                   # numpy array
        return list(v)
    except TypeError:
        return [v] * (n or 0)


def _name(h):
    m = re.search(r"<b>(.*?)</b>", h or "")
    return (m.group(1) if m else (h or "")).strip()


def _color_css(c):
    return c if isinstance(c, str) else "#888888"


def write(fig, path, top_margin=None, union_edges=None, placeholder=None):
    # vertical layout in pixels above the plot area: legend 6, group buttons 38, note 72, (animations: slider 205)
    height = fig.layout.height or 600
    anim = bool(fig.layout.sliders)
    top = max(top_margin or (250 if anim else 130), fig.layout.margin.t or 0)
    plot_h = max(height - top - 20, 200)
    py = lambda px: 1 + px / plot_h
    menu_y, note_y = py(38), py(72)
    roles = [_role(t) for t in fig.data]
    node_i = [i for i, r in enumerate(roles) if r == "nodes"]
    if not node_i:
        raise ValueError("no traces with meta.role == 'nodes'")
    line_i = next((i for i, r in enumerate(roles) if r == "edges"), None)
    geo = fig.data[node_i[0]].type == "scattergeo"
    xy = (lambda t: (t.lon, t.lat)) if geo else (lambda t: (t.x, t.y))

    # ---- node table (one entry per point of every node trace)
    name, grp, tr, ix, X, Y, size, search = [], [], [], [], [], [], [], []
    RX, RY = [], []          # unrounded coordinates (used to match edge endpoints to nodes)
    gname, gcolor = [], []
    for g, i in enumerate(node_i):
        t = fig.data[i]
        xs, ys = xy(t)
        n = len(xs)
        hov = _list(t.hovertext, n, "")
        sz = _list(t.marker.size, n, 8)
        gname.append(t.name or "")
        col = _list(t.marker.color, n, "#888888")
        gcolor.append(_color_css(col[0] if col else None))
        for j in range(n):
            nm = _name(hov[j]) or str(_list(t.text, n, "")[j])
            sym = re.search(r"símbolo ([^ <·]+)", hov[j] or "")
            name.append(nm)
            grp.append(g)
            tr.append(i)
            ix.append(j)
            X.append(round(float(xs[j]), 4))
            Y.append(round(float(ys[j]), 4))
            RX.append(float(xs[j]))
            RY.append(float(ys[j]))
            size.append(float(sz[j]))
            search.append(nm + (" " + sym.group(1) if sym else ""))
    order = sorted(range(len(name)), key=lambda k: -size[k])
    rank = [0] * len(name)
    for r, k in enumerate(order):
        rank[k] = r

    # ---- adjacency from the edge line trace (or from the explicit union of edges)
    coord = {(round(RX[k], 3), round(RY[k], 3)): k for k in range(len(name))}
    segs = []
    if union_edges is not None:
        segs = list(union_edges)
    elif line_i is not None:
        lx, ly = xy(fig.data[line_i])
        lx, ly = list(lx), list(ly)
        for a in range(0, len(lx) - 1, 3):
            segs.append(((lx[a], ly[a]), (lx[a + 1], ly[a + 1])))
    nbrs = [set() for _ in name]
    for (p, q) in segs:
        u = coord.get((round(float(p[0]), 3), round(float(p[1]), 3)))
        v = coord.get((round(float(q[0]), 3), round(float(q[1]), 3)))
        if u is not None and v is not None and u != v:
            nbrs[u].add(v)
            nbrs[v].add(u)

    # ---- overlay traces (selection edges + selection labels)
    if geo:
        fig.add_trace(go.Scattergeo(lon=[], lat=[], mode="lines", line=dict(color="#e34948", width=1.6), opacity=0.9,
                                    hoverinfo="none", showlegend=False, meta=dict(role="overlay")))
        fig.add_trace(go.Scattergeo(lon=[], lat=[], text=[], mode="text", textposition="top center",
                                    textfont=dict(size=9, color=INK), hoverinfo="none", showlegend=False, meta=dict(role="overlay")))
    else:
        fig.add_trace(go.Scatter(x=[], y=[], mode="lines", line=dict(color="#e34948", width=1.4), opacity=0.9,
                                 hoverinfo="none", showlegend=False, meta=dict(role="overlay")))
        fig.add_trace(go.Scatter(x=[], y=[], text=[], mode="text", textposition="top center",
                                 textfont=dict(size=9, color=INK), hoverinfo="none", showlegend=False, meta=dict(role="overlay")))
    HL, LB = len(fig.data) - 2, len(fig.data) - 1
    roles = roles + ["overlay", "overlay"]

    # ---- group controls
    k = len(node_i)
    orig_op = [1 if t.opacity is None else t.opacity for t in fig.data]
    orig_hov = [t.hoverinfo if isinstance(t.hoverinfo, str) else "all" for t in fig.data]
    for i, r in enumerate(roles):
        if r in ("edges", "overlay"):
            orig_hov[i] = "none"

    def plural(nm):
        return PLURAL.get(nm, nm)

    def mode(kind, g=None):
        vis, mop, tfc, opa, hov = [], [], [], [], []
        for i, r in enumerate(roles):
            if r == "nodes":
                gi = node_i.index(i)
                dimmed = kind == "dim" and gi == g
                shown = not (kind == "solo" and gi != g)
                vis.append(bool(shown)); mop.append(0.12 if dimmed else 0.92)
                tfc.append(TRANSPARENT if dimmed else INK); opa.append(orig_op[i])
                hov.append("skip" if dimmed else orig_hov[i])
            elif r in ("edges", "edgehover"):
                vis.append(kind != "solo"); mop.append(1); tfc.append(INK)
                opa.append(0.08 if (kind == "dim" and r == "edges") else orig_op[i])
                hov.append("skip" if (kind == "dim" and r == "edgehover") else orig_hov[i])
            else:
                vis.append(True); mop.append(1); tfc.append(INK); opa.append(orig_op[i]); hov.append("none")
        return [{"visible": vis, "marker.opacity": mop, "textfont.color": tfc, "opacity": opa, "hoverinfo": hov},
                list(range(len(roles)))]

    menus = list(fig.layout.updatemenus or [])
    note = None
    if k >= 2:
        names = gname
        if k <= 4:
            buttons = [dict(label="Todos", method="restyle", args=mode("all"))]
            buttons += [dict(label=f"Solo {plural(names[g])}", method="restyle", args=mode("solo", g)) for g in range(k)]
            buttons += [dict(label=f"Atenuar {plural(names[g])}", method="restyle", args=mode("dim", g)) for g in range(k)]
            menus.append(dict(type="buttons", direction="right", x=0, y=menu_y, xanchor="left", yanchor="bottom",
                              pad=dict(r=4, t=0, b=0), buttons=buttons))
        else:
            ver = [dict(label="Todos", method="restyle", args=mode("all"))]
            ver += [dict(label=f"Solo {names[g]}", method="restyle", args=mode("solo", g)) for g in range(k)]
            ate = [dict(label="Ninguno atenuado", method="restyle", args=mode("all"))]
            ate += [dict(label=f"Atenuar {names[g]}", method="restyle", args=mode("dim", g)) for g in range(k)]
            menus.append(dict(type="dropdown", direction="down", x=0, y=menu_y, xanchor="left", yanchor="bottom", buttons=ver))
            menus.append(dict(type="dropdown", direction="down", x=0.17, y=menu_y, xanchor="left", yanchor="bottom", buttons=ate))
        what = "tipo de nodo" if k == 2 else "grupo de nodos"
        note = (f"Clic en la leyenda para ocultar un {what}; los botones también permiten atenuarlo (se ocultan sus etiquetas y su tooltip, "
                "y las aristas tampoco muestran tooltip). Las aristas se ocultan al mostrar un solo grupo.")
    lay = dict(updatemenus=menus, margin=dict(l=20, r=20, t=top, b=20))
    if k >= 2:
        lay["legend"] = dict(orientation="h", x=0, y=py(6), yanchor="bottom", itemsizing="constant", font=dict(size=13))
        for i in node_i:
            fig.data[i].showlegend = True
    if fig.layout.title.text:
        lay["title"] = dict(y=1 - 14 / height, yanchor="top")
    fig.update_layout(**lay)
    if anim:                              # play/pause buttons next to the group buttons, slider above the note
        for m in fig.layout.updatemenus:
            if m.buttons and m.buttons[0].method == "animate":
                m.update(direction="right", x=0.62, y=menu_y, xanchor="left", yanchor="bottom", pad=dict(r=4, t=0, b=0))
        for sl in fig.layout.sliders:
            sl.update(y=py(205), yanchor="top")
    if note:
        fig.add_annotation(x=0, y=note_y, xref="paper", yref="paper", xanchor="left", yanchor="bottom", showarrow=False,
                           font=dict(size=11, color="#52514e"), text=note)

    if placeholder is None:
        placeholder = ("Buscar " + " o ".join(g.lower() for g in gname) + " (nombre o símbolo)…") if (k == 2 and all(gname)) else "Buscar por nombre…"
    data = dict(name=name, grp=grp, tr=tr, ix=ix, x=X, y=Y, rank=rank, search=search, nbrs=[sorted(s) for s in nbrs],
                gname=gname, gcolor=gcolor, nt=node_i, HL=HL, LB=LB, geo=geo, placeholder=placeholder,
                lines=line_i, lineOpacity=(orig_op[line_i] if line_i is not None else 1),
                home=os.path.relpath(HERE, os.path.dirname(os.path.abspath(path))).replace(os.sep, "/") + "/index.html")
    js = open(os.path.join(HERE, "ui_snippet.js"), encoding="utf-8").read().replace("__DATA__", json.dumps(data, ensure_ascii=True))
    fig.write_html(path, include_plotlyjs="cdn", post_script=js)
    print("Written", path)
