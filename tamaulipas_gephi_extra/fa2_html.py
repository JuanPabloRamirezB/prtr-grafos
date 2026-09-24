"""Interactive HTML for every *_fa2.gexf under this folder (Gephi Toolkit, ForceAtlas2):
see prtr_fa2_html.py. Run: python fa2_html.py"""
import os
import sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.normpath(os.path.join(HERE, "..")))
import prtr_fa2_html as F

F.render_folder(HERE, {
    "centralidad_toolkit_fa2": "Tamaulipas — centralidad (betweenness), ForceAtlas2",
    "timeline_toolkit_fa2": "Tamaulipas — huella temporal (primer año / años activo), ForceAtlas2",
    "municipio_medio_toolkit_fa2": "Tamaulipas — Municipio ↔ Medio de descarga, ForceAtlas2",
    "ego_altamira_toolkit_fa2": "Ego-network de Altamira, ForceAtlas2",
})
