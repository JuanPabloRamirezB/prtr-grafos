"""HTML for the FULL municipio<->causa-especifica mortality graph (no top-N /
threshold pruning - all 1,511 specific causes, all 2,378 municipios, 568,317
edges). Reuses mortality_national_html.py's render() conventions directly
(imported, not duplicated) but calls it standalone instead of re-running that
module's other 8 top-level render() calls.
"""
import importlib.util
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.normpath(os.path.join(HERE, "..", "..")))

# Load mortality_national_html.py as a module WITHOUT executing its top-level
# render(...) calls at the bottom (those are guarded by nothing, so import
# would re-run all 8 - instead exec everything up to the first render() call).
src = open(os.path.join(HERE, "mortality_national_html.py"), encoding="utf-8").read()
cut = src.index("render(\"estado_estado\"")
ns = {"__name__": "mortality_national_html", "__file__": os.path.join(HERE, "mortality_national_html.py")}
exec(compile(src[:cut], "mortality_national_html.py", "exec"), ns)

render = ns["render"]

render("municipio_causa", "municipio_causa_especifico_completo_fa2.gexf", "municipio_causa_especifico_completo.gexf",
       "municipio_causa_especifico_completo_fa2.html",
       "Mexico — Municipality ↔ Cause of death (ALL 1,511 specific ICD codes, ALL 2,378 municipalities, no top-N/threshold pruning, ForceAtlas2)",
       label_top=25, mid_top=2500, px=0.5, is_bipartite=True, chapter=False)

print("Written municipio_causa_especifico_completo_fa2.html")
