"""Interactive HTML for every *_fa2.gexf under this folder (Gephi Toolkit, ForceAtlas2):
see prtr_fa2_html.py. Run: python fa2_html.py"""
import os
import sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.normpath(os.path.join(HERE, "..", "..")))
import prtr_fa2_html as F
import prtr_hover as H

STATE_FILTER = sys.argv[1] if len(sys.argv) > 1 else "Tamaulipas"
OUT_DIR = sys.argv[2] if len(sys.argv) > 2 else HERE
FOCAL_SLUG = sys.argv[3] if len(sys.argv) > 3 else "altamira"
H.configure(STATE_FILTER, "municipio")

F.render_folder(OUT_DIR, {
    "centralidad_toolkit_fa2": f"{STATE_FILTER} — centrality (betweenness), ForceAtlas2",
    "timeline_toolkit_fa2": f"{STATE_FILTER} — temporal fingerprint (first year / years active), ForceAtlas2",
    "municipio_medio_toolkit_fa2": f"{STATE_FILTER} — Municipality ↔ Release medium, ForceAtlas2",
    f"ego_{FOCAL_SLUG}_toolkit_fa2": f"Ego-network of {FOCAL_SLUG.title()}, ForceAtlas2",
})
