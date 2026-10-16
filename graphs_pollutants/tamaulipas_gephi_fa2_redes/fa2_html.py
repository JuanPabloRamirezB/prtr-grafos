"""Interactive HTML for the two projected networks (Gephi Toolkit, ForceAtlas2 + Modularity):
see prtr_fa2_html.py. The temporal graph has its own script (assemble_temporal.py)."""
import os
import sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.normpath(os.path.join(HERE, "..", "..")))
import prtr_fa2_html as F
import prtr_hover as H

STATE_FILTER = sys.argv[1] if len(sys.argv) > 1 else "Tamaulipas"
OUT_DIR = sys.argv[2] if len(sys.argv) > 2 else HERE
H.configure(STATE_FILTER, "municipio")

F.render_folder(OUT_DIR, {
    "sustancia_sustancia_fa2": f"{STATE_FILTER} — substance co-occurrence (Jaccard), ForceAtlas2 + Gephi Modularity",
    "municipio_municipio_fa2": f"{STATE_FILTER} — profile similarity between municipalities, ForceAtlas2 + Gephi Modularity",
}, skip=("temporal",), placeholders={"sustancia_sustancia_fa2": "Search substance (name or symbol)…",
                                    "municipio_municipio_fa2": "Search municipality…"})
