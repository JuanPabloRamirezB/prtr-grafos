"""Interactive HTML for every *_fa2.gexf under this folder (Gephi Toolkit, ForceAtlas2):
see prtr_fa2_html.py. Run: python fa2_html.py"""
import os
import sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.normpath(os.path.join(HERE, "..")))
import prtr_fa2_html as F

F.render_folder(HERE, {
    "centralidad_toolkit_fa2": "Tamaulipas — centrality (betweenness), ForceAtlas2",
    "timeline_toolkit_fa2": "Tamaulipas — temporal fingerprint (first year / years active), ForceAtlas2",
    "municipio_medio_toolkit_fa2": "Tamaulipas — Municipality ↔ Release medium, ForceAtlas2",
    "ego_altamira_toolkit_fa2": "Ego-network of Altamira, ForceAtlas2",
})
