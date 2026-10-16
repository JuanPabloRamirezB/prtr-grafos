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
import unicodedata

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
CSV = os.path.join(HERE, "prtr_raw_for_stori_stori.csv")

GP = "graphs_pollutants"
N = f"{GP}/nacional_gephi"
ES = f"{GP}/estados"

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

STATES = [
    "Aguascalientes", "Baja California", "Baja California Sur", "Campeche", "Chiapas", "Chihuahua",
    "Ciudad de México", "Coahuila de Zaragoza", "Colima", "Durango", "Guanajuato", "Guerrero", "Hidalgo",
    "Jalisco", "México", "Michoacán de Ocampo", "Morelos", "Nayarit", "Nuevo León", "Oaxaca", "Puebla",
    "Querétaro", "Quintana Roo", "San Luis Potosí", "Sinaloa", "Sonora", "Tabasco", "Tamaulipas", "Tlaxcala",
    "Veracruz de Ignacio de la Llave", "Yucatán", "Zacatecas",
]


def slugify(name):
    return unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode().lower().replace(" ", "_")


def focal_of(slug):
    path = os.path.join(HERE, ES, slug, f"{slug}_gephi_extra", "ego_network", "focal.txt")
    with open(path, encoding="utf-8") as f:
        return f.readline().strip(), f.readline().strip()


# Each state's own output folder mirrors graphs_pollutants/estados/<slug>/<slug>_*/...,
# every path below relative to that folder's parent (i.e. prefixed with f"{ES}/{slug}/").
STATE_TYPES = [
    dict(id="s-bipartito", type="Bipartite", title="Municipality ↔ Substance",
         desc="Each state's municipalities and the substances they report, in two columns ranked by cumulative emissions. "
              "Pick a state below to open its graph.",
         variant_tpl=[("Two columns · Plotly", "{s}_graph/{s}_graph.html", "{s}_graph/{s}_graph.png", None, None),
                      ("Two columns · Gephi Toolkit", None, "{s}_graph_toolkit/{s}_graph_toolkit.png",
                       "{s}_graph_toolkit/{s}_graph_toolkit.pdf", "{s}_graph_toolkit/{s}_graph_toolkit_layout.gexf")]),
    dict(id="s-sustancias", type="Similarity", title="Substances reported together",
         desc="Two substances are linked if their municipalities overlap (Jaccard ≥ 0.7) — the chemical families usually "
              "show up as separate clusters.",
         variant_tpl=[("ForceAtlas2 · Gephi + Modularity", "{s}_gephi_fa2_redes/sustancia_sustancia/sustancia_sustancia_fa2.html",
                       "{s}_gephi_fa2_redes/sustancia_sustancia/sustancia_sustancia_fa2.png",
                       "{s}_gephi_fa2_redes/sustancia_sustancia/sustancia_sustancia_fa2.pdf",
                       "{s}_gephi_fa2_redes/sustancia_sustancia/sustancia_sustancia_fa2.gexf"),
                      ("Hierarchical layout · Plotly + Louvain", "{s}_projected_networks/sustancia_sustancia.html",
                       "{s}_projected_networks/sustancia_sustancia.png", None, None)]),
    dict(id="s-municipios", type="Similarity", title="Municipalities with a similar profile",
         desc="Municipalities are linked by the cosine similarity of their emissions profile (≥ 0.7), grouping the state's "
              "industrial corridor apart from its rural municipalities.",
         variant_tpl=[("ForceAtlas2 · Gephi + Modularity", "{s}_gephi_fa2_redes/municipio_municipio/municipio_municipio_fa2.html",
                       "{s}_gephi_fa2_redes/municipio_municipio/municipio_municipio_fa2.png",
                       "{s}_gephi_fa2_redes/municipio_municipio/municipio_municipio_fa2.pdf",
                       "{s}_gephi_fa2_redes/municipio_municipio/municipio_municipio_fa2.gexf"),
                      ("Hierarchical layout · Plotly + Louvain", "{s}_projected_networks/municipio_municipio.html",
                       "{s}_projected_networks/municipio_municipio.png", None, None)]),
    dict(id="s-temporal", type="Temporal", title="Evolution by year, 2004–2022",
         desc="The municipality ↔ substance bipartite graph year by year, with a play button and slider. Positions are "
              "fixed, so nodes never jump.",
         variant_tpl=[("ForceAtlas2 · Gephi Toolkit", "{s}_gephi_fa2_redes/temporal/temporal_fa2.html",
                       "{s}_gephi_fa2_redes/temporal/temporal_snapshots_fa2.png", None, None),
                      ("Two columns · Plotly", "{s}_temporal_graph/{s}_temporal.html",
                       "{s}_temporal_graph/{s}_temporal_snapshots.png", None, None)]),
    dict(id="s-centralidad", type="Centrality", title="Centrality: who connects the most",
         desc="Betweenness and PageRank computed by Gephi. Node size follows centrality in the interactive version.",
         variant_tpl=[("ForceAtlas2 · Gephi Toolkit", "{s}_gephi_extra/centralidad/centralidad_fa2.html",
                       "{s}_gephi_extra/centralidad/centralidad_toolkit_fa2.png",
                       "{s}_gephi_extra/centralidad/centralidad_toolkit_fa2.pdf",
                       "{s}_gephi_extra/centralidad/centralidad_toolkit_fa2.gexf"),
                      ("Two columns · Gephi Toolkit", "{s}_gephi_extra/centralidad/centralidad.html",
                       "{s}_gephi_extra/centralidad/centralidad_toolkit.png",
                       "{s}_gephi_extra/centralidad/centralidad_toolkit.pdf",
                       "{s}_gephi_extra/centralidad/centralidad_toolkit.gexf")]),
    dict(id="s-huella", type="Temporal", title="Temporal fingerprint of each node",
         desc="Color: the year a municipality or substance first appears. Size: how many years it has reported — shows "
              "who is a steady reporter and who joined later.",
         variant_tpl=[("ForceAtlas2 · Gephi Toolkit", "{s}_gephi_extra/timeline/timeline_fa2.html",
                       "{s}_gephi_extra/timeline/timeline_toolkit_fa2.png",
                       "{s}_gephi_extra/timeline/timeline_toolkit_fa2.pdf",
                       "{s}_gephi_extra/timeline/timeline_toolkit_fa2.gexf"),
                      ("Two columns · Gephi Toolkit", None, "{s}_gephi_extra/timeline/timeline_toolkit.png",
                       "{s}_gephi_extra/timeline/timeline_toolkit.pdf", "{s}_gephi_extra/timeline/timeline_toolkit.gexf")]),
    dict(id="s-mapa", type="Map", title="Map: municipalities by emissions profile",
         desc="The municipality-similarity network placed at each municipality's real coordinates.",
         variant_tpl=[("Real coordinates · Gephi Toolkit", "{s}_gephi_extra/geografico/municipio_geo.html",
                       "{s}_gephi_extra/geografico/municipio_geo_toolkit.png",
                       "{s}_gephi_extra/geografico/municipio_geo_toolkit.pdf",
                       "{s}_gephi_extra/geografico/municipio_geo_toolkit.gexf")]),
    dict(id="s-ego", type="Ego-network", title="Ego-network of the top emitter", needs_focal=True,
         desc="The state's biggest emitter, its main substances and the municipalities that share that profile — "
              "auto-detected per state, not hand-picked.",
         variant_tpl=[("ForceAtlas2 · Gephi Toolkit", "{s}_gephi_extra/ego_network/ego_{f}_fa2.html",
                       "{s}_gephi_extra/ego_network/ego_{f}_toolkit_fa2.png",
                       "{s}_gephi_extra/ego_network/ego_{f}_toolkit_fa2.pdf",
                       "{s}_gephi_extra/ego_network/ego_{f}_toolkit_fa2.gexf"),
                      ("Concentric · Gephi Toolkit", "{s}_gephi_extra/ego_network/ego_{f}.html",
                       "{s}_gephi_extra/ego_network/ego_{f}_toolkit.png",
                       "{s}_gephi_extra/ego_network/ego_{f}_toolkit.pdf",
                       "{s}_gephi_extra/ego_network/ego_{f}_toolkit.gexf")]),
    dict(id="s-medio", type="Medium", title="Municipality ↔ Release medium",
         desc="Substances collapsed into their release medium (air, water, soil, sewer system…) — usually “air” "
              "holds nearly all of the volume.",
         variant_tpl=[("ForceAtlas2 · Gephi Toolkit", "{s}_gephi_extra/contraccion_medio/municipio_medio_fa2.html",
                       "{s}_gephi_extra/contraccion_medio/municipio_medio_toolkit_fa2.png",
                       "{s}_gephi_extra/contraccion_medio/municipio_medio_toolkit_fa2.pdf",
                       "{s}_gephi_extra/contraccion_medio/municipio_medio_toolkit_fa2.gexf"),
                      ("Two columns · Gephi Toolkit", "{s}_gephi_extra/contraccion_medio/municipio_medio.html",
                       "{s}_gephi_extra/contraccion_medio/municipio_medio_toolkit.png",
                       "{s}_gephi_extra/contraccion_medio/municipio_medio_toolkit.pdf",
                       "{s}_gephi_extra/contraccion_medio/municipio_medio_toolkit.gexf")]),
]


def build_state_cards():
    """One card per graph type (not per state): a <select> swaps which state's
    links/thumbnail are shown. Thumbnails always show Tamaulipas (present for every
    type, guaranteed to exist) regardless of the selected state."""
    cards = []
    for spec in STATE_TYPES:
        states_data = {}
        for name in STATES:
            slug = slugify(name)
            focal = focal_of(slug)[1] if spec.get("needs_focal") else None
            base = f"{ES}/{slug}/"
            variants = []
            for label, htp, pngp, pdfp, gexfp in spec["variant_tpl"]:
                fmt = lambda t: base + t.format(s=slug, f=focal) if t else None
                variants.append(v(label, fmt(htp), fmt(pngp), fmt(pdfp), fmt(gexfp)))
            states_data[name] = dict(slug=slug, focal=focal, variants=variants)
        cards.append(dict(id=spec["id"], scope="State", dataset="Pollutants", type=spec["type"], title=spec["title"],
                           desc=spec["desc"], thumb=f"{ES}/tamaulipas/" + spec["variant_tpl"][0][2].format(s="tamaulipas", f="altamira"),
                           states=states_data))
    return cards


STATE_CARDS = build_state_cards()


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
    for c in CARDS + STATE_CARDS:
        im = Image.open(os.path.join(HERE, c["thumb"])).convert("RGB")
        im.thumbnail((W, H), Image.LANCZOS)
        canvas = Image.new("RGB", (W, H), (252, 252, 251))
        canvas.paste(im, ((W - im.width) // 2, (H - im.height) // 2))
        canvas.save(os.path.join(HERE, "assets", "thumbs", c["id"] + ".jpg"), "JPEG", quality=84, optimize=True)


def esc(s):
    return html.escape(s, quote=True)


def variant_rows_html(variants):
    rows = []
    for x in variants:
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
    return "".join(rows)


def card_html(c):
    first_html = next((x["html"] for x in c["variants"] if x["html"]), None)
    href = first_html or c["variants"][0]["png"]
    text = f'{c["title"]} {c["desc"]} {c["type"]} {c["scope"]} {c["dataset"]} ' + " ".join(x["label"] for x in c["variants"])
    return f'''<article class="card" data-dataset="{esc(c["dataset"])}" data-scope="{esc(c["scope"])}" data-type="{esc(c["type"])}" data-text="{esc(text.lower())}">
  <a class="thumb" href="{esc(href)}" tabindex="-1" aria-hidden="true"><img src="assets/thumbs/{c["id"]}.jpg" alt="" width="640" height="400" loading="lazy"></a>
  <div class="body">
    <div class="tags"><span class="tag dataset-{esc(c["dataset"].lower())}">{esc(c["dataset"])}</span><span class="tag scope-{esc(c["scope"].lower())}">{esc(c["scope"])}</span><span class="tag">{esc(c["type"])}</span></div>
    <h3><a href="{esc(href)}">{esc(c["title"])}</a></h3>
    <p>{esc(c["desc"])}</p>
    {variant_rows_html(c["variants"])}
  </div>
</article>'''


def state_card_html(c):
    first_name = STATES[0]
    first_slug = slugify(first_name)
    opts = "".join(f'<option value="{esc(slugify(s))}">{esc(s)}</option>' for s in STATES)
    blocks = []
    for name in STATES:
        slug = slugify(name)
        variants = c["states"][name]["variants"]
        hidden_attr = "" if slug == first_slug else " hidden"
        blocks.append(f'<div class="svar" data-slug="{esc(slug)}"{hidden_attr}>{variant_rows_html(variants)}</div>')
    first_href = next((x["html"] for x in c["states"][first_name]["variants"] if x["html"]), None)
    text = f'{c["title"]} {c["desc"]} {c["type"]} State Pollutants ' + " ".join(STATES)
    return f'''<article class="card" data-dataset="Pollutants" data-scope="State" data-type="{esc(c["type"])}" data-text="{esc(text.lower())}">
  <a class="thumb" href="{esc(first_href)}" tabindex="-1" aria-hidden="true"><img src="assets/thumbs/{c["id"]}.jpg" alt="" width="640" height="400" loading="lazy"></a>
  <div class="body">
    <div class="tags"><span class="tag dataset-pollutants">Pollutants</span><span class="tag scope-state">State</span><span class="tag">{esc(c["type"])}</span></div>
    <h3><a href="{esc(first_href)}">{esc(c["title"])}</a></h3>
    <p>{esc(c["desc"])}</p>
    <label class="statesel-lbl">State: <select class="statesel">{opts}</select></label>
    {"".join(blocks)}
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
.tag.scope-national{background:var(--blue);color:#fff}.tag.scope-state{background:var(--orange);color:#fff}
.tag.dataset-pollutants{background:#1baf7a;color:#fff}.tag.dataset-mortality{background:#4a3aa7;color:#fff}
.statesel-lbl{font-size:.85rem;color:var(--ink2);display:flex;align-items:center;gap:6px}
.statesel{flex:1;padding:6px 8px;border:1px solid var(--line);border-radius:7px;background:var(--surface);color:var(--ink);font:inherit;font-size:.85rem}
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

  [].forEach.call(document.querySelectorAll('.statesel'),function(sel){
    sel.addEventListener('change',function(){
      var card=sel.closest('.card');
      [].forEach.call(card.querySelectorAll('.svar'),function(b){b.hidden=(b.dataset.slug!==sel.value);});
      var shown=card.querySelector('.svar:not([hidden])');
      var btn=shown.querySelector('.btn.primary')||shown.querySelector('.btn');
      if(btn){var href=btn.getAttribute('href');card.querySelector('.thumb').setAttribute('href',href);card.querySelector('h3 a').setAttribute('href',href);}
    });
  });
})();
"""


def main():
    missing = []
    for c in CARDS:
        for f in [c["thumb"]] + [p for x in c["variants"] for p in (x["html"], x["png"], x["pdf"], x["gexf"]) if p] + \
                 [p for x in c["variants"] for _, p in x["extra"]]:
            if not os.path.exists(os.path.join(HERE, f)):
                missing.append(f)
    for c in STATE_CARDS:
        for st in c["states"].values():
            for f in [p for x in st["variants"] for p in (x["html"], x["png"], x["pdf"], x["gexf"]) if p]:
                if not os.path.exists(os.path.join(HERE, f)):
                    missing.append(f)
    if missing:
        sys.exit("Missing files:\n  " + "\n  ".join(sorted(set(missing))))
    thumbs()
    s = stats()
    types = []
    for c in CARDS + STATE_CARDS:
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
<title>Mexico RECT & Mortality — interactive graphs</title>
<meta name="description" content="Networks of states, municipalities, substances and causes of death from two Mexican national datasets: the Registro de Emisiones y Transferencias Críticas (RECT, 2004–2022) and official mortality records (2000–2022).">
<meta name="theme-color" content="#2a78d6">
<style>{CSS}</style>
</head>
<body>
<header class="top"><div class="wrap">
  <h1>Mexico open data — interactive graphs</h1>
  <p class="lead">Two national datasets seen as networks. The <b>Registro de Emisiones y Transferencias Críticas</b> (RECT, {s["y0"]}–{s["y1"]}):
  which states and municipalities report which substances, which ones resemble each other, and how that changes year by year — at national
  level, and at the level of each of the 32 states individually (pick one from the dropdown on each "State" card). And Mexico's
  <b>official mortality records</b> (2000–2022, 53.7M entries): which states and municipalities report which causes of death, by ICD
  chapter or specific code — national level only for now. Every graph opens as an interactive page with a search box, or downloads as
  PNG, PDF and GEXF (for Gephi). Use the <b>Dataset</b> and <b>Scope</b> filters below to tell them apart.</p>
  <ul class="stats">
    <li><b>{s["estados"]}</b><span>RECT states</span></li>
    <li><b>{s["municipios"]:,}</b><span>RECT municipalities</span></li>
    <li><b>{s["sustancias"]}</b><span>substances</span></li>
    <li><b>{s["y0"]}–{s["y1"]}</b><span>RECT years</span></li>
    <li><b>{s["rows"]:,}</b><span>RECT reports</span></li>
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
    {chips("scope", ["National", "State"])}
    {chips("type", types)}
    <input id="q" type="search" placeholder="Search (e.g. temporal, metals, Jalisco)…" aria-label="Search graphs">
    <span id="count" aria-live="polite"></span>
  </div>
  <div class="grid">
{chr(10).join(card_html(c) for c in CARDS)}
{chr(10).join(state_card_html(c) for c in STATE_CARDS)}
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
    <p>The source is Mexico's RECT, with {s["rows"]:,} reports. Each report carries a kg/year value; the totals shown are the <b>sum of every report from {s["y0"]} to {s["y1"]}</b>, not an annual rate.
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
python nacional_gephi/nacional_html.py
graphs_pollutants/build_state.sh "Jalisco"         # regenerates all 9 graph types for one state
python build_index.py                             # this page</pre>
    <p><code>graphs_pollutants/build_state.sh</code> runs the full per-state pipeline (base GEXFs, ForceAtlas2/Modularity via the Gephi
    Toolkit, HTML rendering) for any of the 32 states — it's what produced every graph under <code>graphs_pollutants/estados/</code>,
    including Tamaulipas' own. The Gephi-rendered images (ForceAtlas2, Modularity, PDF/PNG) are produced by the Java programs in each
    folder together with <code>gephi-toolkit-0.10.1-all.jar</code>. See the project's <code>README.md</code> for details.</p>
    <p>The mortality graphs live under <code>graphs_mortality/nacional_gephi/</code>, built by <code>build_mortality_national_gexf.py</code>
    and <code>mortality_national_html.py</code> from Mexico's raw mortality CSVs plus <code>inegi_catalogo_municipios.csv</code> (a name
    catalog fetched from INEGI's public geostatistics API), same Gephi Toolkit pipeline as RECT.</p></div></details>
</section>
</main>
<footer><div class="wrap">Generated on {today}. The interactive graphs load Plotly from a CDN and need an internet connection.</div></footer>
<script>{JS}</script>
</body>
</html>
'''
    with open(os.path.join(HERE, "index.html"), "w", encoding="utf-8") as f:
        f.write(page)
    print(f"Written index.html ({len(CARDS)} cards + {len(STATE_CARDS)} state-selector cards covering {len(STATES)} states) "
          f"and {len(CARDS) + len(STATE_CARDS)} thumbnails")


if __name__ == "__main__":
    main()
