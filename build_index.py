"""Builds index.html (the hub page for GitHub Pages) and assets/thumbs/*.jpg.

Everything is relative, so the site works under any Pages URL. Every linked file is
checked for existence; the header figures are computed from the dataset when the CSV
is present (it is git-ignored) and fall back to the last known values otherwise.

    python build_index.py
"""
import csv
import datetime
import html
import os
import sys

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
CSV = os.path.join(HERE, "prtr_raw_for_stori_stori.csv")

GP = "graphs_pollutants"
N, T = f"{GP}/nacional_gephi", f"{GP}/tamaulipas_gephi_extra"
R, G, P, TT, TK = (f"{GP}/tamaulipas_gephi_fa2_redes", f"{GP}/tamaulipas_graph", f"{GP}/tamaulipas_projected_networks",
                    f"{GP}/tamaulipas_temporal_graph", f"{GP}/tamaulipas_graph_toolkit")

GM = "graphs_mortality"
MN = f"{GM}/nacional_gephi"


def v(label, html=None, png=None, pdf=None, gexf=None, extra=None):
    return dict(label=label, html=html, png=png, pdf=pdf, gexf=gexf, extra=extra or [])


CARDS = [
    # ------------------------------------------------------------------ National
    dict(id="n-estado-estado", scope="National", type="Similarity", title="States with a similar emissions profile",
         desc="All 32 states linked by the cosine similarity of their substance profile (kg, log scale). Gephi detects the "
              "communities with Modularity; states with an outlier profile stay isolated.",
         thumb=f"{N}/estado_estado/estado_estado_fa2.png",
         variants=[v("ForceAtlas2 · Gephi Toolkit", f"{N}/estado_estado/estado_estado_fa2.html", f"{N}/estado_estado/estado_estado_fa2.png",
                     f"{N}/estado_estado/estado_estado_fa2.pdf", f"{N}/estado_estado/estado_estado_fa2.gexf")]),
    dict(id="n-estado-sustancia", scope="National", type="Bipartite", title="State ↔ Substance",
         desc="167 nodes and 1,543 edges: which states report which substances. States with very broad profiles sit on the "
              "periphery with their exclusive substances; heavy metals and CO₂ form the core.",
         thumb=f"{N}/estado_sustancia/estado_sustancia_fa2.png",
         variants=[v("ForceAtlas2 · Gephi Toolkit", f"{N}/estado_sustancia/estado_sustancia_fa2.html", f"{N}/estado_sustancia/estado_sustancia_fa2.png",
                     f"{N}/estado_sustancia/estado_sustancia_fa2.pdf", f"{N}/estado_sustancia/estado_sustancia_fa2.gexf")]),
    dict(id="n-municipio-sustancia", scope="National", type="Bipartite", title="Municipality ↔ Substance (716 municipalities)",
         desc="The largest graph: 851 nodes and 10,595 edges. A dense core of municipalities linked to the most-reported "
              "substances; more specific profiles toward the periphery. Tooltips on the 2,500 heaviest edges. ~2 MB page.",
         thumb=f"{N}/municipio_sustancia/municipio_sustancia_fa2.png",
         variants=[v("ForceAtlas2 · Gephi Toolkit", f"{N}/municipio_sustancia/municipio_sustancia_fa2.html", f"{N}/municipio_sustancia/municipio_sustancia_fa2.png",
                     f"{N}/municipio_sustancia/municipio_sustancia_fa2.pdf", f"{N}/municipio_sustancia/municipio_sustancia_fa2.gexf")]),
    dict(id="n-mapa", scope="National", type="Map", title="Map: states by emissions profile",
         desc="The state-similarity network placed at each state capital, on a map of Mexico. Shows whether a similar "
              "emissions profile lines up with geographic closeness.",
         thumb=f"{N}/geografico/estado_geo_toolkit.png",
         variants=[v("Real coordinates · Gephi Toolkit", f"{N}/geografico/estado_geo.html", f"{N}/geografico/estado_geo_toolkit.png",
                     f"{N}/geografico/estado_geo_toolkit.pdf", f"{N}/geografico/estado_geo_toolkit.gexf")]),
    # ------------------------------------------------------------------ Tamaulipas
    dict(id="t-bipartito", scope="Tamaulipas", type="Bipartite", title="Municipality ↔ Substance",
         desc="Tamaulipas' 20 municipalities and the 71 substances they report, in two columns ranked by cumulative emissions. "
              "The Gephi Toolkit version uses the same layout with size and color driven by an attribute.",
         thumb=f"{G}/tamaulipas_graph.png",
         variants=[v("Two columns · Plotly", f"{G}/tamaulipas_graph.html", f"{G}/tamaulipas_graph.png"),
                   v("Two columns · Gephi Toolkit", None, f"{TK}/tamaulipas_graph_toolkit.png", f"{TK}/tamaulipas_graph_toolkit.pdf",
                     f"{TK}/tamaulipas_graph_toolkit_layout.gexf")]),
    dict(id="t-sustancias", scope="Tamaulipas", type="Similarity", title="Substances reported together",
         desc="Two substances are linked if their municipalities overlap (Jaccard ≥ 0.7). The chemical families show up: "
              "chlorinated solvents, polycyclic aromatic hydrocarbons, heavy metals, aldehydes and refrigerant gases.",
         thumb=f"{R}/sustancia_sustancia/sustancia_sustancia_fa2.png",
         variants=[v("ForceAtlas2 · Gephi + Modularity", f"{R}/sustancia_sustancia/sustancia_sustancia_fa2.html", f"{R}/sustancia_sustancia/sustancia_sustancia_fa2.png",
                     f"{R}/sustancia_sustancia/sustancia_sustancia_fa2.pdf", f"{R}/sustancia_sustancia/sustancia_sustancia_fa2.gexf"),
                   v("Hierarchical layout · Plotly + Louvain", f"{P}/sustancia_sustancia.html", f"{P}/sustancia_sustancia.png")]),
    dict(id="t-municipios", scope="Tamaulipas", type="Similarity", title="Municipalities with a similar profile",
         desc="Municipalities are linked by the cosine similarity of their emissions profile (≥ 0.7). Three groups emerge: the "
              "industrial corridor (Altamira, Reynosa…), an intermediate group and the rural municipalities.",
         thumb=f"{R}/municipio_municipio/municipio_municipio_fa2.png",
         variants=[v("ForceAtlas2 · Gephi + Modularity", f"{R}/municipio_municipio/municipio_municipio_fa2.html", f"{R}/municipio_municipio/municipio_municipio_fa2.png",
                     f"{R}/municipio_municipio/municipio_municipio_fa2.pdf", f"{R}/municipio_municipio/municipio_municipio_fa2.gexf"),
                   v("Hierarchical layout · Plotly + Louvain", f"{P}/municipio_municipio.html", f"{P}/municipio_municipio.png")]),
    dict(id="t-temporal", scope="Tamaulipas", type="Temporal", title="Evolution by year, 2004–2022",
         desc="The municipality ↔ substance bipartite graph year by year, with a play button and slider. Positions are fixed, "
              "so nodes never jump; size is that year's kg (common log scale) and gray marks no report.",
         thumb=f"{R}/temporal/temporal_snapshots_fa2.png",
         variants=[v("ForceAtlas2 · Gephi Toolkit", f"{R}/temporal/temporal_fa2.html", f"{R}/temporal/temporal_snapshots_fa2.png",
                     extra=[(f"PDF {y}", f"{R}/temporal/temporal_{y}_fa2.pdf") for y in (2004, 2010, 2016, 2022)]),
                   v("Two columns · Plotly", f"{TT}/tamaulipas_temporal.html", f"{TT}/tamaulipas_temporal_snapshots.png")]),
    dict(id="t-centralidad", scope="Tamaulipas", type="Centrality", title="Centrality: who connects the most",
         desc="Betweenness and PageRank computed by Gephi. Altamira, Matamoros and Reynosa are the biggest bridges; carbon "
              "dioxide holds most of the PageRank. In the HTML, node size follows centrality.",
         thumb=f"{T}/centralidad/centralidad_toolkit_fa2.png",
         variants=[v("ForceAtlas2 · Gephi Toolkit", f"{T}/centralidad/centralidad_fa2.html", f"{T}/centralidad/centralidad_toolkit_fa2.png",
                     f"{T}/centralidad/centralidad_toolkit_fa2.pdf", f"{T}/centralidad/centralidad_toolkit_fa2.gexf"),
                   v("Two columns · Gephi Toolkit", f"{T}/centralidad/centralidad.html", f"{T}/centralidad/centralidad_toolkit.png",
                     f"{T}/centralidad/centralidad_toolkit.pdf", f"{T}/centralidad/centralidad_toolkit.gexf")]),
    dict(id="t-huella", scope="Tamaulipas", type="Temporal", title="Temporal fingerprint of each node",
         desc="Color: the year a municipality or substance first appears (dark blue = since 2004). Size: how many years it "
              "has reported. Shows who is a steady reporter and who joined later.",
         thumb=f"{T}/timeline/timeline_toolkit_fa2.png",
         variants=[v("ForceAtlas2 · Gephi Toolkit", f"{T}/timeline/timeline_fa2.html", f"{T}/timeline/timeline_toolkit_fa2.png",
                     f"{T}/timeline/timeline_toolkit_fa2.pdf", f"{T}/timeline/timeline_toolkit_fa2.gexf"),
                   v("Two columns · Gephi Toolkit", None, f"{T}/timeline/timeline_toolkit.png", f"{T}/timeline/timeline_toolkit.pdf",
                     f"{T}/timeline/timeline_toolkit.gexf")]),
    dict(id="t-mapa", scope="Tamaulipas", type="Map", title="Map: municipalities by emissions profile",
         desc="The municipality-similarity network on the real map. The border industrial towns are far apart but linked by "
              "profile; the rural group is geographically compact.",
         thumb=f"{T}/geografico/municipio_geo_toolkit.png",
         variants=[v("Real coordinates · Gephi Toolkit", f"{T}/geografico/municipio_geo.html", f"{T}/geografico/municipio_geo_toolkit.png",
                     f"{T}/geografico/municipio_geo_toolkit.pdf", f"{T}/geografico/municipio_geo_toolkit.gexf")]),
    dict(id="t-ego", scope="Tamaulipas", type="Ego-network", title="Ego-network of Altamira",
         desc="The state's biggest emitter: its 15 main substances and the 8 municipalities that share that profile. Three "
              "substances are exclusive to Altamira and hang off as leaves in the ForceAtlas2 version.",
         thumb=f"{T}/ego_network/ego_altamira_toolkit_fa2.png",
         variants=[v("ForceAtlas2 · Gephi Toolkit", f"{T}/ego_network/ego_altamira_fa2.html", f"{T}/ego_network/ego_altamira_toolkit_fa2.png",
                     f"{T}/ego_network/ego_altamira_toolkit_fa2.pdf", f"{T}/ego_network/ego_altamira_toolkit_fa2.gexf"),
                   v("Concentric · Gephi Toolkit", f"{T}/ego_network/ego_altamira.html", f"{T}/ego_network/ego_altamira_toolkit.png",
                     f"{T}/ego_network/ego_altamira_toolkit.pdf", f"{T}/ego_network/ego_altamira_toolkit.gexf")]),
    dict(id="t-medio", scope="Tamaulipas", type="Medium", title="Municipality ↔ Release medium",
         desc="Substances collapsed into their release medium (air, water, soil, sewer system…): 31 nodes instead of 91. "
              "“air” holds nearly all of the volume.",
         thumb=f"{T}/contraccion_medio/municipio_medio_toolkit_fa2.png",
         variants=[v("ForceAtlas2 · Gephi Toolkit", f"{T}/contraccion_medio/municipio_medio_fa2.html", f"{T}/contraccion_medio/municipio_medio_toolkit_fa2.png",
                     f"{T}/contraccion_medio/municipio_medio_toolkit_fa2.pdf", f"{T}/contraccion_medio/municipio_medio_toolkit_fa2.gexf"),
                   v("Two columns · Gephi Toolkit", f"{T}/contraccion_medio/municipio_medio.html", f"{T}/contraccion_medio/municipio_medio_toolkit.png",
                     f"{T}/contraccion_medio/municipio_medio_toolkit.pdf", f"{T}/contraccion_medio/municipio_medio_toolkit.gexf")]),
    # ------------------------------------------------------------------ Mortality (national only, no state-level yet)
    dict(id="m-estado-estado", dataset="Mortality", scope="National", type="Similarity",
         title="States with a similar cause-of-death profile",
         desc="All 32 states linked by the cosine similarity of their mortality-cause profile (log scale). Two versions: the "
              "23 broad ICD chapters, or the top 100 specific causes nationally by death count.",
         thumb=f"{MN}/estado_estado/estado_estado_capitulo_fa2.png",
         variants=[v("23 ICD chapters · ForceAtlas2", f"{MN}/estado_estado/estado_estado_capitulo_fa2.html", f"{MN}/estado_estado/estado_estado_capitulo_fa2.png",
                     f"{MN}/estado_estado/estado_estado_capitulo_fa2.pdf", f"{MN}/estado_estado/estado_estado_capitulo_fa2.gexf"),
                   v("Top 100 specific causes · ForceAtlas2", f"{MN}/estado_estado/estado_estado_especifico_fa2.html", f"{MN}/estado_estado/estado_estado_especifico_fa2.png",
                     f"{MN}/estado_estado/estado_estado_especifico_fa2.pdf", f"{MN}/estado_estado/estado_estado_especifico_fa2.gexf")]),
    dict(id="m-estado-causa", dataset="Mortality", scope="National", type="Bipartite",
         title="State ↔ Cause of death",
         desc="Which states record which causes of death. 23-chapter version (736 edges, near-complete coverage) or top 100 "
              "specific ICD codes nationally by death count (3,200 edges).",
         thumb=f"{MN}/estado_causa/estado_causa_capitulo_fa2.png",
         variants=[v("23 ICD chapters · ForceAtlas2", f"{MN}/estado_causa/estado_causa_capitulo_fa2.html", f"{MN}/estado_causa/estado_causa_capitulo_fa2.png",
                     f"{MN}/estado_causa/estado_causa_capitulo_fa2.pdf", f"{MN}/estado_causa/estado_causa_capitulo_fa2.gexf"),
                   v("Top 100 specific causes · ForceAtlas2", f"{MN}/estado_causa/estado_causa_especifico_fa2.html", f"{MN}/estado_causa/estado_causa_especifico_fa2.png",
                     f"{MN}/estado_causa/estado_causa_especifico_fa2.pdf", f"{MN}/estado_causa/estado_causa_especifico_fa2.gexf")]),
    dict(id="m-municipio-causa", dataset="Mortality", scope="National", type="Bipartite",
         title="Municipality ↔ Cause of death (2,378 municipalities)",
         desc="The largest graph on the site: three versions by granularity — 23 ICD chapters (48,539 edges), the top 100 "
              "specific causes with a >100-death threshold (17,344 edges), or all 1,511 specific causes with no cap at all "
              "(568,317 edges, WebGL rendering, only the heaviest edges are drawn and get tooltips).",
         thumb=f"{MN}/municipio_causa/municipio_causa_capitulo_fa2.png",
         variants=[v("23 ICD chapters · ForceAtlas2", f"{MN}/municipio_causa/municipio_causa_capitulo_fa2.html", f"{MN}/municipio_causa/municipio_causa_capitulo_fa2.png",
                     f"{MN}/municipio_causa/municipio_causa_capitulo_fa2.pdf", f"{MN}/municipio_causa/municipio_causa_capitulo_fa2.gexf"),
                   v("Top 100 specific causes (>100 deaths/edge) · ForceAtlas2", f"{MN}/municipio_causa/municipio_causa_especifico_fa2.html",
                     f"{MN}/municipio_causa/municipio_causa_especifico_fa2.png", f"{MN}/municipio_causa/municipio_causa_especifico_fa2.pdf",
                     f"{MN}/municipio_causa/municipio_causa_especifico_fa2.gexf"),
                   v("All 1,511 specific causes · WebGL", f"{MN}/municipio_causa/municipio_causa_especifico_completo_ligero_fa2.html",
                     gexf=f"{MN}/municipio_causa/municipio_causa_especifico_completo_fa2.gexf")]),
    dict(id="m-mapa", dataset="Mortality", scope="National", type="Map",
         title="Map: states by cause-of-death profile",
         desc="The state cause-of-death similarity network placed at each state capital, on a map of Mexico. Same two "
              "granularities as the similarity graph above.",
         thumb=f"{MN}/geografico/estado_geo_capitulo_toolkit.png",
         variants=[v("23 ICD chapters · real coordinates", f"{MN}/geografico/estado_geo_capitulo.html", f"{MN}/geografico/estado_geo_capitulo_toolkit.png",
                     f"{MN}/geografico/estado_geo_capitulo_toolkit.pdf", f"{MN}/geografico/estado_geo_capitulo_toolkit.gexf"),
                   v("Top 100 specific causes · real coordinates", f"{MN}/geografico/estado_geo_especifico.html", f"{MN}/geografico/estado_geo_especifico_toolkit.png",
                     f"{MN}/geografico/estado_geo_especifico_toolkit.pdf", f"{MN}/geografico/estado_geo_especifico_toolkit.gexf")]),
]
for c in CARDS:
    c.setdefault("dataset", "Pollutants")
FRAMES = [(y, f"{R}/temporal/frames/temporal_{y}.png") for y in range(2004, 2023)]


def stats():
    if not os.path.exists(CSV):
        return dict(rows=188344, estados=32, municipios=716, sustancias=135, y0=2004, y1=2022, total=3.87e12)
    est, mun, sub, years, rows, total = set(), set(), set(), set(), 0, 0.0
    with open(CSV, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            sp = r["spatial"].split("."); p = r["interest"].split(".")
            try:
                val = float(r["observation"]); y = int(r["temporal"])
            except ValueError:
                continue
            rows += 1; total += val; years.add(y); est.add(sp[0]); mun.add(".".join(sp[:2])); sub.add(p[-3] if len(p) >= 3 else r["interest"])
    return dict(rows=rows, estados=len(est), municipios=len(mun), sustancias=len(sub), y0=min(years), y1=max(years), total=total)


def size_txt(path):
    b = os.path.getsize(os.path.join(HERE, path))
    return f"{b / 1e6:.1f} MB" if b >= 1e6 else f"{max(b // 1000, 1)} KB"


def thumbs():
    os.makedirs(os.path.join(HERE, "assets", "thumbs"), exist_ok=True)
    W, H = 640, 400
    for c in CARDS:
        im = Image.open(os.path.join(HERE, c["thumb"])).convert("RGB")
        im.thumbnail((W, H), Image.LANCZOS)
        canvas = Image.new("RGB", (W, H), (252, 252, 251))
        canvas.paste(im, ((W - im.width) // 2, (H - im.height) // 2))
        canvas.save(os.path.join(HERE, "assets", "thumbs", c["id"] + ".jpg"), "JPEG", quality=84, optimize=True)


def esc(s):
    return html.escape(s, quote=True)


def card_html(c):
    first_html = next((x["html"] for x in c["variants"] if x["html"]), None)
    href = first_html or c["variants"][0]["png"]
    rows = []
    for x in c["variants"]:
        btns = []
        if x["html"]:
            weight = size_txt(x["html"]) if os.path.getsize(os.path.join(HERE, x["html"])) > 1e6 else ""
            btns.append(f'<a class="btn primary" href="{esc(x["html"])}">Interactive' + (f" <small>{weight}</small>" if weight else "") + "</a>")
        for key, name in (("png", "PNG"), ("pdf", "PDF"), ("gexf", "GEXF")):
            if x[key]:
                btns.append(f'<a class="btn" href="{esc(x[key])}" title="{name} · {size_txt(x[key])}">{name}</a>')
        for label, path in x["extra"]:
            btns.append(f'<a class="btn" href="{esc(path)}" title="{size_txt(path)}">{esc(label)}</a>')
        rows.append(f'<div class="variant"><span class="vlabel">{esc(x["label"])}</span><div class="btns">{"".join(btns)}</div></div>')
    frames = ""
    if c["id"] == "t-temporal":
        links = "".join(f'<a href="{esc(p)}">{y}</a>' for y, p in FRAMES)
        frames = f'<details class="frames"><summary>Frames by year (Gephi PNG)</summary><div class="yrs">{links}</div></details>'
    text = f'{c["title"]} {c["desc"]} {c["type"]} {c["scope"]} {c["dataset"]} ' + " ".join(x["label"] for x in c["variants"])
    return f'''<article class="card" data-dataset="{esc(c["dataset"])}" data-scope="{esc(c["scope"])}" data-type="{esc(c["type"])}" data-text="{esc(text.lower())}">
  <a class="thumb" href="{esc(href)}" tabindex="-1" aria-hidden="true"><img src="assets/thumbs/{c["id"]}.jpg" alt="" width="640" height="400" loading="lazy"></a>
  <div class="body">
    <div class="tags"><span class="tag dataset-{esc(c["dataset"].lower())}">{esc(c["dataset"])}</span><span class="tag scope-{esc(c["scope"].lower())}">{esc(c["scope"])}</span><span class="tag">{esc(c["type"])}</span></div>
    <h3><a href="{esc(href)}">{esc(c["title"])}</a></h3>
    <p>{esc(c["desc"])}</p>
    {"".join(rows)}
    {frames}
  </div>
</article>'''


CSS = """
:root{color-scheme:light dark;--bg:#f9f9f7;--surface:#fcfcfb;--ink:#0b0b0b;--ink2:#52514e;--muted:#6f6d67;--line:#e1e0d9;--chip:#f2f1ec;
--blue:#2a78d6;--orange:#eb6834;--blue-ink:#1c5cab;--focus:#2a78d6}
@media (prefers-color-scheme:dark){:root{--bg:#0d0d0d;--surface:#1a1a19;--ink:#fff;--ink2:#c3c2b7;--muted:#a09e96;--line:#2c2c2a;--chip:#252523;
--blue:#3987e5;--orange:#d95926;--blue-ink:#86b6ef;--focus:#86b6ef}}
*{box-sizing:border-box}html{scroll-behavior:smooth}
body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.55 system-ui,-apple-system,"Segoe UI",Roboto,sans-serif}
a{color:var(--blue-ink)}a:focus-visible,button:focus-visible,input:focus-visible,summary:focus-visible{outline:3px solid var(--focus);outline-offset:2px;border-radius:4px}
.wrap{max-width:1240px;margin:0 auto;padding:0 20px}
header.top{padding:44px 0 26px;border-bottom:1px solid var(--line);background:linear-gradient(180deg,var(--surface),var(--bg))}
h1{font-size:clamp(1.7rem,4vw,2.5rem);line-height:1.15;margin:0 0 10px;letter-spacing:-.01em}
.lead{max-width:70ch;color:var(--ink2);margin:0 0 22px;font-size:1.05rem}
.stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:12px;margin:0;padding:0;list-style:none}
.stats li{background:var(--surface);border:1px solid var(--line);border-radius:10px;padding:12px 14px}
.stats b{display:block;font-size:1.35rem;line-height:1.2;font-variant-numeric:tabular-nums}
.stats span{color:var(--muted);font-size:.85rem}
.dot{display:inline-block;width:.7em;height:.7em;border-radius:50%;margin-right:.35em;vertical-align:baseline}
.dot.b{background:var(--blue)}.dot.o{background:var(--orange)}
section{padding:28px 0}
h2{font-size:1.35rem;margin:0 0 14px}
.tools{display:flex;flex-wrap:wrap;gap:10px 18px;align-items:center;margin-bottom:18px}
.chips{display:flex;flex-wrap:wrap;gap:6px;align-items:center}
.chips .lbl{color:var(--muted);font-size:.85rem;margin-right:2px}
.chip{border:1px solid var(--line);background:var(--surface);color:var(--ink);border-radius:999px;padding:5px 13px;font:inherit;font-size:.9rem;cursor:pointer}
.chip[aria-pressed=true]{background:var(--blue);border-color:var(--blue);color:#fff}
#q{flex:1;min-width:220px;max-width:380px;padding:9px 12px;border:1px solid var(--line);border-radius:8px;background:var(--surface);color:var(--ink);font:inherit}
#count{color:var(--muted);font-size:.9rem;margin-left:auto}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(340px,1fr));gap:18px}
.card{background:var(--surface);border:1px solid var(--line);border-radius:12px;overflow:hidden;display:flex;flex-direction:column}
.card[hidden]{display:none}
.thumb{display:block;background:#fcfcfb;border-bottom:1px solid var(--line)}
.thumb img{display:block;width:100%;height:auto;aspect-ratio:8/5}
.body{padding:14px 16px 16px;display:flex;flex-direction:column;gap:8px;flex:1}
.tags{display:flex;gap:6px;flex-wrap:wrap}
.tag{font-size:.74rem;text-transform:uppercase;letter-spacing:.04em;background:var(--chip);color:var(--ink2);border-radius:5px;padding:2px 7px}
.tag.scope-national{background:var(--blue);color:#fff}.tag.scope-tamaulipas{background:var(--orange);color:#fff}
.tag.dataset-pollutants{background:#1baf7a;color:#fff}.tag.dataset-mortality{background:#4a3aa7;color:#fff}
.card h3{margin:0;font-size:1.08rem;line-height:1.3}.card h3 a{color:var(--ink);text-decoration:none}.card h3 a:hover{text-decoration:underline}
.card p{margin:0;color:var(--ink2);font-size:.92rem}
.variant{border-top:1px dashed var(--line);padding-top:8px}
.vlabel{display:block;font-size:.78rem;color:var(--muted);margin-bottom:5px}
.btns{display:flex;flex-wrap:wrap;gap:6px}
.btn{display:inline-block;border:1px solid var(--line);background:var(--chip);color:var(--ink);text-decoration:none;border-radius:7px;padding:4px 10px;font-size:.85rem}
.btn:hover{border-color:var(--blue)}
.btn.primary{background:var(--blue);border-color:var(--blue);color:#fff;font-weight:600}
.btn small{font-weight:400;opacity:.85}
.frames{margin-top:4px;font-size:.85rem}.frames summary{cursor:pointer;color:var(--ink2)}
.yrs{display:flex;flex-wrap:wrap;gap:4px;margin-top:6px}.yrs a{padding:2px 7px;border:1px solid var(--line);border-radius:5px;text-decoration:none;background:var(--chip);color:var(--ink);font-size:.8rem}
.empty{color:var(--muted);padding:18px 0}
details.doc{background:var(--surface);border:1px solid var(--line);border-radius:10px;padding:0 16px;margin-bottom:12px}
details.doc summary{cursor:pointer;padding:13px 0;font-weight:600}
details.doc .in{padding:0 0 14px;color:var(--ink2)}
details.doc ul{margin:6px 0 0;padding-left:1.2em}details.doc li{margin:4px 0}
code{background:var(--chip);padding:1px 5px;border-radius:4px;font-size:.88em}
pre{background:var(--chip);padding:12px 14px;border-radius:8px;overflow:auto;font-size:.85rem}
footer{border-top:1px solid var(--line);padding:22px 0 40px;color:var(--muted);font-size:.88rem}
@media (max-width:520px){.grid{grid-template-columns:1fr}#count{margin-left:0}}
"""

JS = """
(function(){
  var cards=[].slice.call(document.querySelectorAll('.card')), q=document.getElementById('q'), out=document.getElementById('count'), empty=document.getElementById('empty');
  var st={dataset:'All',scope:'All',type:'All'};
  function norm(s){return s.normalize('NFD').replace(/[\\u0300-\\u036f]/g,'').toLowerCase();}
  var texts=cards.map(function(c){return norm(c.getAttribute('data-text'));});
  function apply(){
    var t=norm(q.value.trim()).split(/\\s+/).filter(Boolean), n=0;
    cards.forEach(function(c,i){
      var ok=(st.dataset==='All'||c.dataset.dataset===st.dataset)&&(st.scope==='All'||c.dataset.scope===st.scope)&&(st.type==='All'||c.dataset.type===st.type)&&t.every(function(w){return texts[i].indexOf(w)>=0;});
      c.hidden=!ok; if(ok)n++;
    });
    out.textContent=n+' of '+cards.length+' graphs'; empty.hidden=n>0;
  }
  [].forEach.call(document.querySelectorAll('.chips'),function(g){
    g.addEventListener('click',function(e){
      var b=e.target.closest('.chip'); if(!b)return;
      [].forEach.call(g.querySelectorAll('.chip'),function(x){x.setAttribute('aria-pressed',x===b?'true':'false');});
      st[g.dataset.key]=b.dataset.v; apply();
    });
  });
  q.addEventListener('input',apply); apply();
})();
"""


def main():
    missing = []
    for c in CARDS:
        for f in [c["thumb"]] + [p for x in c["variants"] for p in (x["html"], x["png"], x["pdf"], x["gexf"]) if p] + \
                 [p for x in c["variants"] for _, p in x["extra"]]:
            if not os.path.exists(os.path.join(HERE, f)):
                missing.append(f)
    missing += [p for _, p in FRAMES if not os.path.exists(os.path.join(HERE, p))]
    if missing:
        sys.exit("Missing files:\n  " + "\n  ".join(sorted(set(missing))))
    thumbs()
    s = stats()
    types = []
    for c in CARDS:
        if c["type"] not in types:
            types.append(c["type"])
    key_label = {"dataset": "Dataset", "scope": "Scope", "type": "Type"}
    chips = lambda key, vals: (f'<div class="chips" data-key="{key}"><span class="lbl">{key_label[key]}:</span>' +
                               "".join(f'<button class="chip" data-v="{esc(x)}" aria-pressed="{"true" if x == "All" else "false"}">{esc(x)}</button>' for x in ["All"] + vals) + "</div>")
    total_txt = f'{s["total"] / 1e12:.2f} trillion kg' if s["total"] >= 1e12 else f'{s["total"] / 1e9:,.0f} billion kg'
    today = datetime.date.today().strftime("%Y-%m-%d")
    page = f'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Mexico PRTR & Mortality — interactive graphs</title>
<meta name="description" content="Networks of states, municipalities, substances and causes of death from two Mexican national datasets: the Pollutant Release and Transfer Register (PRTR, 2004–2022) and official mortality records (2000–2022).">
<meta name="theme-color" content="#2a78d6">
<style>{CSS}</style>
</head>
<body>
<header class="top"><div class="wrap">
  <h1>Mexico open data — interactive graphs</h1>
  <p class="lead">Two national datasets seen as networks. The <b>Pollutant Release and Transfer Register</b> (PRTR, {s["y0"]}–{s["y1"]}):
  which states and municipalities report which substances, which ones resemble each other, and how that changes year by year — at national
  and Tamaulipas-state level. And Mexico's <b>official mortality records</b> (2000–2022, 53.7M entries): which states and municipalities
  report which causes of death, by ICD chapter or specific code — national level only for now. Every graph opens as an interactive page
  with a search box, or downloads as PNG, PDF and GEXF (for Gephi). Use the <b>Dataset</b> and <b>Scope</b> filters below to tell them apart.</p>
  <ul class="stats">
    <li><b>{s["estados"]}</b><span>PRTR states</span></li>
    <li><b>{s["municipios"]:,}</b><span>PRTR municipalities</span></li>
    <li><b>{s["sustancias"]}</b><span>substances</span></li>
    <li><b>{s["y0"]}–{s["y1"]}</b><span>PRTR years</span></li>
    <li><b>{s["rows"]:,}</b><span>PRTR reports</span></li>
    <li><b>{total_txt.split(" ")[0]}</b><span>{" ".join(total_txt.split(" ")[1:])} cumulative</span></li>
    <li><b>2,378</b><span>mortality municipalities</span></li>
    <li><b>1,511</b><span>specific causes of death</span></li>
  </ul>
</div></header>
<main class="wrap">
<section id="graficos" aria-labelledby="h-graf">
  <h2 id="h-graf">Graphs</h2>
  <div class="tools">
    {chips("dataset", ["Pollutants", "Mortality"])}
    {chips("scope", ["National", "Tamaulipas"])}
    {chips("type", types)}
    <input id="q" type="search" placeholder="Search (e.g. temporal, metals, Altamira)…" aria-label="Search graphs">
    <span id="count" aria-live="polite"></span>
  </div>
  <div class="grid">
{chr(10).join(card_html(c) for c in CARDS)}
  </div>
  <p id="empty" class="empty" hidden>No graph matches the filter.</p>
</section>

<section aria-labelledby="h-leer">
  <h2 id="h-leer">How to read the graphs</h2>
  <details class="doc" open><summary>Colors, sizes and connections</summary><div class="in"><ul>
    <li><span class="dot b"></span>Blue: states or municipalities. <span class="dot o"></span>Orange: substances. In the similarity networks, color marks the detected community; in the ego-network, red is the focal municipality.</li>
    <li><b>Node size</b>: cumulative emissions {s["y0"]}–{s["y1"]} (the sum of every report), almost always on a log scale because totals span more than ten orders of magnitude.</li>
    <li><b>Edges</b>: an edge exists when a municipality or state reported that substance. In the similarity networks, when two profiles are alike above a threshold (cosine or Jaccard ≥ 0.7).</li>
  </ul></div></details>
  <details class="doc"><summary>What you can do on the interactive pages</summary><div class="in"><ul>
    <li><b>Tooltip</b> on any node: total and share of the country or state, ranking, years reported, main medium and sector, substances or municipalities with the most kg. Hovering the midpoint of an edge shows the detail of that relationship.</li>
    <li><b>Search box</b> (top left): by name or chemical symbol, accent-insensitive. Picking a result zooms in, shows its card and highlights its connections.</li>
    <li><b>Buttons and legend</b>: hide or dim a node type (or a community). Dimming also hides its labels and tooltips.</li>
    <li>On the <b>animated</b> pages: play or drag the year slider; the search and the dim mode are kept when the year changes.</li>
    <li>Scroll or box-select to zoom; double-click to reset.</li>
  </ul></div></details>
</section>

<section aria-labelledby="h-notas">
  <h2 id="h-notas">Methodology notes</h2>
  <details class="doc"><summary>Data and units</summary><div class="in">
    <p>The source is Mexico's PRTR, with {s["rows"]:,} reports. Each report carries a kg/year value; the totals shown are the <b>sum of every report from {s["y0"]} to {s["y1"]}</b>, not an annual rate.
    States, municipalities and substances come from the <code>spatial</code> and <code>interest</code> columns. Some substances appear under several chemical forms (e.g. "Lead (compounds)" and "Lead (soluble compounds)") and are treated as distinct substances.</p></div></details>
  <details class="doc"><summary>Methods</summary><div class="in"><ul>
    <li><b>Similarity between municipalities or states</b>: cosine of the <code>log(1 + kg)</code> vector per substance. <b>Between substances</b>: Jaccard index over the municipalities reporting each one (corrects for very common substances co-occurring by chance).</li>
    <li><b>ForceAtlas2</b> (Gephi Toolkit) with edge-weight influence set to 0 on the bipartite graphs: a handful of huge emitters (Altamira, carbon dioxide) weigh ~1000x more than the rest and collapsed the layout. The similarity networks do use edge weight.</li>
    <li><b>Communities</b>: Louvain (Python) or Modularity (Gephi), depending on the graph. Centrality: Gephi's betweenness and PageRank.</li>
    <li><b>Maps</b>: approximate municipal-seat coordinates (schematic, not for cartographic use).</li>
  </ul></div></details>
  <details class="doc"><summary>Mortality graphs: what's different</summary><div class="in">
    <p>Built from Mexico's official mortality records (2000–2022, 53.7M entries after removing every aggregate/placeholder row — no "Total" state,
    municipality, sex, age bracket or unlabeled cause). Node/edge size is the <b>death count</b> (not a rate: age/sex-specific rates aren't
    additive, so counts are summed instead), and state/municipality names come from INEGI's official catalog rather than the source file's own
    text columns, which had corrupted accented characters.</p>
    <p>"Cause of death" comes in two granularities, shown as separate graph variants: the <b>23 ICD chapters</b> (broad categories, e.g. all
    circulatory diseases together) with no further pruning, or the <b>top 100 specific ICD codes</b> nationally by death count (e.g. "I21 —
    Acute myocardial infarction") — municipality-level specific-cause edges are additionally pruned to those with &gt;100 deaths accumulated
    over the period, since the most common causes are reported almost everywhere and would otherwise produce over a million edges. The
    municipality↔cause graph also has a third, uncapped variant with all 1,511 specific causes and every municipality (568,317 edges) — it
    draws in WebGL and only shows rich tooltips on its 2,500 heaviest edges, since a static PNG/PDF render at that scale is not practical.
    No state-level (Tamaulipas-style) mortality graphs exist yet.</p></div></details>
</section>

<section aria-labelledby="h-repro">
  <h2 id="h-repro">Reproduce</h2>
  <details class="doc"><summary>Project structure and commands</summary><div class="in">
    <p>Each folder holds the scripts and outputs for its graph. Shared modules live at the root: <code>prtr_hover.py</code> (tooltips), <code>prtr_i18n.py</code> (English translations for substances/media/sectors), <code>prtr_ui.py</code> and <code>ui_snippet.js</code> (search box and buttons), and <code>prtr_fa2_html.py</code>.
    The <code>prtr_raw_for_stori_stori.csv</code> dataset is not version-controlled: place it at the root to regenerate.</p>
<pre>pip install networkx plotly matplotlib numpy scipy pillow
python tamaulipas_graph/build_graph.py            # and the other build_*.py, fa2_html.py, assemble_temporal.py
python nacional_gephi/nacional_html.py
python build_index.py                             # this page</pre>
    <p>The Gephi-rendered images (ForceAtlas2, Modularity, PDF/PNG) are produced by the Java programs in each folder together with <code>gephi-toolkit-0.10.1-all.jar</code>. See the project's <code>README.md</code> for details.</p>
    <p>The mortality graphs live under <code>graphs_mortality/nacional_gephi/</code>, built by <code>build_mortality_national_gexf.py</code>
    and <code>mortality_national_html.py</code> from Mexico's raw mortality CSVs plus <code>inegi_catalogo_municipios.csv</code> (a name
    catalog fetched from INEGI's public geostatistics API), same Gephi Toolkit pipeline as PRTR.</p></div></details>
</section>
</main>
<footer><div class="wrap">Generated on {today}. The interactive graphs load Plotly from a CDN and need an internet connection.</div></footer>
<script>{JS}</script>
</body>
</html>
'''
    with open(os.path.join(HERE, "index.html"), "w", encoding="utf-8") as f:
        f.write(page)
    print(f"Written index.html ({len(CARDS)} cards) and {len(CARDS)} thumbnails")


if __name__ == "__main__":
    main()
