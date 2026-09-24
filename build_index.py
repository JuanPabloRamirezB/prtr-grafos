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

N, T = "nacional_gephi", "tamaulipas_gephi_extra"
R, G, P, TT, TK = "tamaulipas_gephi_fa2_redes", "tamaulipas_graph", "tamaulipas_projected_networks", "tamaulipas_temporal_graph", "tamaulipas_graph_toolkit"


def v(label, html=None, png=None, pdf=None, gexf=None, extra=None):
    return dict(label=label, html=html, png=png, pdf=pdf, gexf=gexf, extra=extra or [])


CARDS = [
    # ------------------------------------------------------------------ Nacional
    dict(id="n-estado-estado", scope="Nacional", type="Similitud", title="Estados con perfil de emisiones parecido",
         desc="Los 32 estados conectados por la similitud coseno de su perfil de sustancias (Kg en escala log). Gephi detecta las "
              "comunidades con Modularity; los estados con un perfil atípico quedan aislados.",
         thumb=f"{N}/estado_estado/estado_estado_fa2.png",
         variants=[v("ForceAtlas2 · Gephi Toolkit", f"{N}/estado_estado/estado_estado_fa2.html", f"{N}/estado_estado/estado_estado_fa2.png",
                     f"{N}/estado_estado/estado_estado_fa2.pdf", f"{N}/estado_estado/estado_estado_fa2.gexf")]),
    dict(id="n-estado-sustancia", scope="Nacional", type="Bipartito", title="Estado ↔ Sustancia",
         desc="167 nodos y 1,543 aristas: qué estados reportan qué sustancias. Los estados con perfiles muy amplios quedan en la "
              "periferia con sus sustancias exclusivas; los metales pesados y el CO₂ forman el núcleo.",
         thumb=f"{N}/estado_sustancia/estado_sustancia_fa2.png",
         variants=[v("ForceAtlas2 · Gephi Toolkit", f"{N}/estado_sustancia/estado_sustancia_fa2.html", f"{N}/estado_sustancia/estado_sustancia_fa2.png",
                     f"{N}/estado_sustancia/estado_sustancia_fa2.pdf", f"{N}/estado_sustancia/estado_sustancia_fa2.gexf")]),
    dict(id="n-municipio-sustancia", scope="Nacional", type="Bipartito", title="Municipio ↔ Sustancia (716 municipios)",
         desc="El grafo más grande: 851 nodos y 10,595 aristas. Un núcleo denso de municipios ligados a las sustancias más reportadas; "
              "los perfiles específicos hacia la periferia. Tooltip en las 2,500 aristas de mayor peso. Página de ~2 MB.",
         thumb=f"{N}/municipio_sustancia/municipio_sustancia_fa2.png",
         variants=[v("ForceAtlas2 · Gephi Toolkit", f"{N}/municipio_sustancia/municipio_sustancia_fa2.html", f"{N}/municipio_sustancia/municipio_sustancia_fa2.png",
                     f"{N}/municipio_sustancia/municipio_sustancia_fa2.pdf", f"{N}/municipio_sustancia/municipio_sustancia_fa2.gexf")]),
    dict(id="n-mapa", scope="Nacional", type="Mapa", title="Mapa: estados por perfil de emisiones",
         desc="La red de similitud entre estados colocada en las capitales sobre el mapa de México. Muestra si un perfil de emisiones "
              "parecido coincide con la cercanía geográfica.",
         thumb=f"{N}/geografico/estado_geo_toolkit.png",
         variants=[v("Coordenadas reales · Gephi Toolkit", f"{N}/geografico/estado_geo.html", f"{N}/geografico/estado_geo_toolkit.png",
                     f"{N}/geografico/estado_geo_toolkit.pdf", f"{N}/geografico/estado_geo_toolkit.gexf")]),
    # ------------------------------------------------------------------ Tamaulipas
    dict(id="t-bipartito", scope="Tamaulipas", type="Bipartito", title="Municipio ↔ Sustancia",
         desc="Los 20 municipios de Tamaulipas y las 71 sustancias que reportan, en dos columnas ordenadas por emisión acumulada. "
              "La versión de Gephi Toolkit usa el mismo diseño con tamaño y color por atributo.",
         thumb=f"{G}/tamaulipas_graph.png",
         variants=[v("Dos columnas · Plotly", f"{G}/tamaulipas_graph.html", f"{G}/tamaulipas_graph.png"),
                   v("Dos columnas · Gephi Toolkit", None, f"{TK}/tamaulipas_graph_toolkit.png", f"{TK}/tamaulipas_graph_toolkit.pdf",
                     f"{TK}/tamaulipas_graph_toolkit_layout.gexf")]),
    dict(id="t-sustancias", scope="Tamaulipas", type="Similitud", title="Sustancias que se reportan juntas",
         desc="Dos sustancias se conectan si sus municipios coinciden (Jaccard ≥ 0.7). Aparecen los grupos químicos: solventes clorados, "
              "hidrocarburos aromáticos policíclicos, metales pesados, aldehídos y gases refrigerantes.",
         thumb=f"{R}/sustancia_sustancia/sustancia_sustancia_fa2.png",
         variants=[v("ForceAtlas2 · Gephi + Modularity", f"{R}/sustancia_sustancia/sustancia_sustancia_fa2.html", f"{R}/sustancia_sustancia/sustancia_sustancia_fa2.png",
                     f"{R}/sustancia_sustancia/sustancia_sustancia_fa2.pdf", f"{R}/sustancia_sustancia/sustancia_sustancia_fa2.gexf"),
                   v("Layout jerárquico · Plotly + Louvain", f"{P}/sustancia_sustancia.html", f"{P}/sustancia_sustancia.png")]),
    dict(id="t-municipios", scope="Tamaulipas", type="Similitud", title="Municipios con perfil parecido",
         desc="Los municipios se conectan por la similitud coseno de su perfil de emisiones (≥ 0.7). Salen tres grupos: el corredor "
              "industrial (Altamira, Reynosa…), uno intermedio y los municipios rurales.",
         thumb=f"{R}/municipio_municipio/municipio_municipio_fa2.png",
         variants=[v("ForceAtlas2 · Gephi + Modularity", f"{R}/municipio_municipio/municipio_municipio_fa2.html", f"{R}/municipio_municipio/municipio_municipio_fa2.png",
                     f"{R}/municipio_municipio/municipio_municipio_fa2.pdf", f"{R}/municipio_municipio/municipio_municipio_fa2.gexf"),
                   v("Layout jerárquico · Plotly + Louvain", f"{P}/municipio_municipio.html", f"{P}/municipio_municipio.png")]),
    dict(id="t-temporal", scope="Tamaulipas", type="Temporal", title="Evolución por año, 2004–2022",
         desc="El bipartito municipio ↔ sustancia año por año, con botón de reproducir y slider. Las posiciones son fijas, así que "
              "los nodos no saltan; el tamaño es el Kg de ese año (escala log común) y el gris marca lo que no reportó.",
         thumb=f"{R}/temporal/temporal_snapshots_fa2.png",
         variants=[v("ForceAtlas2 · Gephi Toolkit", f"{R}/temporal/temporal_fa2.html", f"{R}/temporal/temporal_snapshots_fa2.png",
                     extra=[(f"PDF {y}", f"{R}/temporal/temporal_{y}_fa2.pdf") for y in (2004, 2010, 2016, 2022)]),
                   v("Dos columnas · Plotly", f"{TT}/tamaulipas_temporal.html", f"{TT}/tamaulipas_temporal_snapshots.png")]),
    dict(id="t-centralidad", scope="Tamaulipas", type="Centralidad", title="Centralidad: quién conecta más",
         desc="Betweenness y PageRank calculados por Gephi. Altamira, Matamoros y Reynosa son los grandes puentes; el Bióxido de "
              "carbono concentra el PageRank. En el HTML, el tamaño de los nodos sigue la centralidad.",
         thumb=f"{T}/centralidad/centralidad_toolkit_fa2.png",
         variants=[v("ForceAtlas2 · Gephi Toolkit", f"{T}/centralidad/centralidad_fa2.html", f"{T}/centralidad/centralidad_toolkit_fa2.png",
                     f"{T}/centralidad/centralidad_toolkit_fa2.pdf", f"{T}/centralidad/centralidad_toolkit_fa2.gexf"),
                   v("Dos columnas · Gephi Toolkit", f"{T}/centralidad/centralidad.html", f"{T}/centralidad/centralidad_toolkit.png",
                     f"{T}/centralidad/centralidad_toolkit.pdf", f"{T}/centralidad/centralidad_toolkit.gexf")]),
    dict(id="t-huella", scope="Tamaulipas", type="Temporal", title="Huella temporal de cada nodo",
         desc="Color: año en que un municipio o sustancia aparece por primera vez (azul oscuro = desde 2004). Tamaño: cuántos años ha "
              "reportado. Muestra quién es constante y quién se incorporó después.",
         thumb=f"{T}/timeline/timeline_toolkit_fa2.png",
         variants=[v("ForceAtlas2 · Gephi Toolkit", f"{T}/timeline/timeline_fa2.html", f"{T}/timeline/timeline_toolkit_fa2.png",
                     f"{T}/timeline/timeline_toolkit_fa2.pdf", f"{T}/timeline/timeline_toolkit_fa2.gexf"),
                   v("Dos columnas · Gephi Toolkit", None, f"{T}/timeline/timeline_toolkit.png", f"{T}/timeline/timeline_toolkit.pdf",
                     f"{T}/timeline/timeline_toolkit.gexf")]),
    dict(id="t-mapa", scope="Tamaulipas", type="Mapa", title="Mapa: municipios por perfil de emisiones",
         desc="La red de similitud entre municipios sobre el mapa real. Los industriales de la frontera están lejos entre sí pero "
              "conectados por su perfil; el grupo rural es compacto en el mapa.",
         thumb=f"{T}/geografico/municipio_geo_toolkit.png",
         variants=[v("Coordenadas reales · Gephi Toolkit", f"{T}/geografico/municipio_geo.html", f"{T}/geografico/municipio_geo_toolkit.png",
                     f"{T}/geografico/municipio_geo_toolkit.pdf", f"{T}/geografico/municipio_geo_toolkit.gexf")]),
    dict(id="t-ego", scope="Tamaulipas", type="Ego-network", title="Ego-network de Altamira",
         desc="El mayor emisor del estado: sus 15 sustancias principales y los 8 municipios que comparten ese perfil. Tres sustancias "
              "son exclusivas de Altamira y cuelgan como hojas en la versión ForceAtlas2.",
         thumb=f"{T}/ego_network/ego_altamira_toolkit_fa2.png",
         variants=[v("ForceAtlas2 · Gephi Toolkit", f"{T}/ego_network/ego_altamira_fa2.html", f"{T}/ego_network/ego_altamira_toolkit_fa2.png",
                     f"{T}/ego_network/ego_altamira_toolkit_fa2.pdf", f"{T}/ego_network/ego_altamira_toolkit_fa2.gexf"),
                   v("Concéntrico · Gephi Toolkit", f"{T}/ego_network/ego_altamira.html", f"{T}/ego_network/ego_altamira_toolkit.png",
                     f"{T}/ego_network/ego_altamira_toolkit.pdf", f"{T}/ego_network/ego_altamira_toolkit.gexf")]),
    dict(id="t-medio", scope="Tamaulipas", type="Medio", title="Municipio ↔ Medio de descarga",
         desc="Las sustancias colapsadas en su medio de descarga (aire, agua, suelo, alcantarillado…): 31 nodos en lugar de 91. "
              "«aire» concentra casi todo el volumen.",
         thumb=f"{T}/contraccion_medio/municipio_medio_toolkit_fa2.png",
         variants=[v("ForceAtlas2 · Gephi Toolkit", f"{T}/contraccion_medio/municipio_medio_fa2.html", f"{T}/contraccion_medio/municipio_medio_toolkit_fa2.png",
                     f"{T}/contraccion_medio/municipio_medio_toolkit_fa2.pdf", f"{T}/contraccion_medio/municipio_medio_toolkit_fa2.gexf"),
                   v("Dos columnas · Gephi Toolkit", f"{T}/contraccion_medio/municipio_medio.html", f"{T}/contraccion_medio/municipio_medio_toolkit.png",
                     f"{T}/contraccion_medio/municipio_medio_toolkit.pdf", f"{T}/contraccion_medio/municipio_medio_toolkit.gexf")]),
]
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
            btns.append(f'<a class="btn primary" href="{esc(x["html"])}">Interactivo' + (f" <small>{weight}</small>" if weight else "") + "</a>")
        for key, name in (("png", "PNG"), ("pdf", "PDF"), ("gexf", "GEXF")):
            if x[key]:
                btns.append(f'<a class="btn" href="{esc(x[key])}" title="{name} · {size_txt(x[key])}">{name}</a>')
        for label, path in x["extra"]:
            btns.append(f'<a class="btn" href="{esc(path)}" title="{size_txt(path)}">{esc(label)}</a>')
        rows.append(f'<div class="variant"><span class="vlabel">{esc(x["label"])}</span><div class="btns">{"".join(btns)}</div></div>')
    frames = ""
    if c["id"] == "t-temporal":
        links = "".join(f'<a href="{esc(p)}">{y}</a>' for y, p in FRAMES)
        frames = f'<details class="frames"><summary>Cuadros por año (PNG de Gephi)</summary><div class="yrs">{links}</div></details>'
    text = f'{c["title"]} {c["desc"]} {c["type"]} {c["scope"]} ' + " ".join(x["label"] for x in c["variants"])
    return f'''<article class="card" data-scope="{esc(c["scope"])}" data-type="{esc(c["type"])}" data-text="{esc(text.lower())}">
  <a class="thumb" href="{esc(href)}" tabindex="-1" aria-hidden="true"><img src="assets/thumbs/{c["id"]}.jpg" alt="" width="640" height="400" loading="lazy"></a>
  <div class="body">
    <div class="tags"><span class="tag scope-{esc(c["scope"].lower())}">{esc(c["scope"])}</span><span class="tag">{esc(c["type"])}</span></div>
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
.tag.scope-nacional{background:var(--blue);color:#fff}.tag.scope-tamaulipas{background:var(--orange);color:#fff}
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
  var st={scope:'Todos',type:'Todos'};
  function norm(s){return s.normalize('NFD').replace(/[\\u0300-\\u036f]/g,'').toLowerCase();}
  var texts=cards.map(function(c){return norm(c.getAttribute('data-text'));});
  function apply(){
    var t=norm(q.value.trim()).split(/\\s+/).filter(Boolean), n=0;
    cards.forEach(function(c,i){
      var ok=(st.scope==='Todos'||c.dataset.scope===st.scope)&&(st.type==='Todos'||c.dataset.type===st.type)&&t.every(function(w){return texts[i].indexOf(w)>=0;});
      c.hidden=!ok; if(ok)n++;
    });
    out.textContent=n+' de '+cards.length+' gráficos'; empty.hidden=n>0;
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
    chips = lambda key, vals: (f'<div class="chips" data-key="{key}"><span class="lbl">{"Alcance" if key == "scope" else "Tipo"}:</span>' +
                               "".join(f'<button class="chip" data-v="{esc(x)}" aria-pressed="{"true" if x == "Todos" else "false"}">{esc(x)}</button>' for x in ["Todos"] + vals) + "</div>")
    total_txt = f'{s["total"] / 1e12:.2f} billones de Kg' if s["total"] >= 1e12 else f'{s["total"] / 1e9:,.0f} mil millones de Kg'
    today = datetime.date.today().strftime("%d/%m/%Y")
    page = f'''<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>PRTR México — grafos interactivos</title>
<meta name="description" content="Redes de estados, municipios y sustancias del Registro de Emisiones y Transferencia de Contaminantes (PRTR) de México, 2004–2022: bipartitos, similitud, evolución por año, mapas y centralidad.">
<meta name="theme-color" content="#2a78d6">
<style>{CSS}</style>
</head>
<body>
<header class="top"><div class="wrap">
  <h1>PRTR México — grafos interactivos</h1>
  <p class="lead">El Registro de Emisiones y Transferencia de Contaminantes ({s["y0"]}–{s["y1"]}) visto como redes: qué estados y municipios
  reportan qué sustancias, cuáles se parecen entre sí y cómo cambian año con año. Cada gráfico se puede abrir interactivo, con buscador, o descargar en PNG, PDF y GEXF (para Gephi).</p>
  <ul class="stats">
    <li><b>{s["estados"]}</b><span>estados</span></li>
    <li><b>{s["municipios"]:,}</b><span>municipios</span></li>
    <li><b>{s["sustancias"]}</b><span>sustancias</span></li>
    <li><b>{s["y0"]}–{s["y1"]}</b><span>{s["y1"] - s["y0"] + 1} años</span></li>
    <li><b>{s["rows"]:,}</b><span>reportes</span></li>
    <li><b>{total_txt.split(" de ")[0]}</b><span>de Kg acumulados</span></li>
  </ul>
</div></header>
<main class="wrap">
<section id="graficos" aria-labelledby="h-graf">
  <h2 id="h-graf">Gráficos</h2>
  <div class="tools">
    {chips("scope", ["Nacional", "Tamaulipas"])}
    {chips("type", types)}
    <input id="q" type="search" placeholder="Buscar (ej. temporal, metales, Altamira)…" aria-label="Buscar gráficos">
    <span id="count" aria-live="polite"></span>
  </div>
  <div class="grid">
{chr(10).join(card_html(c) for c in CARDS)}
  </div>
  <p id="empty" class="empty" hidden>Ningún gráfico coincide con el filtro.</p>
</section>

<section aria-labelledby="h-leer">
  <h2 id="h-leer">Cómo leer los gráficos</h2>
  <details class="doc" open><summary>Colores, tamaños y conexiones</summary><div class="in"><ul>
    <li><span class="dot b"></span>Azul: estados o municipios. <span class="dot o"></span>Naranja: sustancias. En las redes de similitud, el color indica la comunidad detectada; en la ego-network, el rojo es el municipio foco.</li>
    <li><b>Tamaño</b> del nodo: emisión acumulada {s["y0"]}–{s["y1"]} (suma de todos los reportes), casi siempre en escala logarítmica porque los totales difieren en más de diez órdenes de magnitud.</li>
    <li><b>Aristas</b>: hay una arista cuando un municipio o estado reportó esa sustancia. En las redes de similitud, cuando sus perfiles se parecen por encima de un umbral (coseno o Jaccard ≥ 0.7).</li>
  </ul></div></details>
  <details class="doc"><summary>Qué se puede hacer en las páginas interactivas</summary><div class="in"><ul>
    <li><b>Tooltip</b> sobre cualquier nodo: total y porcentaje del país o estado, ranking, años con reporte, medio y sector principales, sustancias o municipios con más Kg. Sobre el punto medio de una arista aparece el detalle de esa relación.</li>
    <li><b>Buscador</b> (arriba a la izquierda): por nombre o símbolo químico, sin importar acentos. Al elegir un resultado hace zoom, muestra su ficha y resalta sus conexiones.</li>
    <li><b>Botones y leyenda</b>: ocultar o atenuar un tipo de nodo (o una comunidad). Al atenuarlo también se ocultan sus etiquetas y tooltips.</li>
    <li>En las páginas <b>animadas</b>: reproducir o mover el slider de año; la búsqueda y el modo de atenuar se conservan al cambiar de año.</li>
    <li>Rueda o cuadro de selección para hacer zoom; doble clic para restablecer.</li>
  </ul></div></details>
</section>

<section aria-labelledby="h-notas">
  <h2 id="h-notas">Notas metodológicas</h2>
  <details class="doc"><summary>Datos y unidades</summary><div class="in">
    <p>La base es el PRTR de México con {s["rows"]:,} reportes. Cada reporte trae un valor en Kg/año; los totales que se muestran son la <b>suma de todos los reportes de {s["y0"]} a {s["y1"]}</b>, no una tasa anual.
    Estados, municipios y sustancias se toman de las columnas <code>spatial</code> e <code>interest</code>. Algunas sustancias aparecen en varias formas químicas (por ejemplo «Plomo (compuestos)» y «Plomo (Compuestos solubles)») y se tratan como sustancias distintas.</p></div></details>
  <details class="doc"><summary>Métodos</summary><div class="in"><ul>
    <li><b>Similitud entre municipios o estados</b>: coseno del vector de <code>log(1 + Kg)</code> por sustancia. <b>Entre sustancias</b>: índice de Jaccard sobre los municipios que las reportan (corrige que las sustancias muy comunes coincidan por azar).</li>
    <li><b>ForceAtlas2</b> (Gephi Toolkit) con la influencia del peso de aristas en 0 en los bipartitos: unos pocos emisores enormes (Altamira, Bióxido de carbono) pesan ~1000 veces más que el resto y colapsaban el layout. En las redes de similitud sí se usa el peso.</li>
    <li><b>Comunidades</b>: Louvain (Python) o Modularity (Gephi), según el gráfico. Centralidad: betweenness y PageRank de Gephi.</li>
    <li><b>Mapas</b>: coordenadas aproximadas de las cabeceras (esquemáticas, no para uso cartográfico).</li>
  </ul></div></details>
</section>

<section aria-labelledby="h-repro">
  <h2 id="h-repro">Reproducir</h2>
  <details class="doc"><summary>Estructura del proyecto y comandos</summary><div class="in">
    <p>Cada carpeta contiene los scripts y los resultados de su gráfico. Los módulos compartidos están en la raíz: <code>prtr_hover.py</code> (tooltips), <code>prtr_ui.py</code> y <code>ui_snippet.js</code> (buscador y botones) y <code>prtr_fa2_html.py</code>.
    El dataset <code>prtr_raw_for_stori_stori.csv</code> no se versiona: colócalo en la raíz para regenerar.</p>
<pre>pip install networkx plotly matplotlib numpy scipy pillow
python tamaulipas_graph/build_graph.py            # y los demás build_*.py, fa2_html.py, assemble_temporal.py
python nacional_gephi/nacional_html.py
python build_index.py                             # esta página</pre>
    <p>Las imágenes de Gephi (ForceAtlas2, Modularity, PDF/PNG) se generan con los programas Java de cada carpeta y el <code>gephi-toolkit-0.10.1-all.jar</code>. Más detalles en el <code>README.md</code> del proyecto.</p></div></details>
</section>
</main>
<footer><div class="wrap">Generado el {today}. Los gráficos interactivos cargan Plotly desde un CDN y necesitan conexión a internet.</div></footer>
<script>{JS}</script>
</body>
</html>
'''
    with open(os.path.join(HERE, "index.html"), "w", encoding="utf-8") as f:
        f.write(page)
    print(f"Written index.html ({len(CARDS)} cards) and {len(CARDS)} thumbnails")


if __name__ == "__main__":
    main()
