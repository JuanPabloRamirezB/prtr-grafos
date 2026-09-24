"""Interactive HTML for the two projected networks (Gephi Toolkit, ForceAtlas2 + Modularity):
see prtr_fa2_html.py. The temporal graph has its own script (assemble_temporal.py)."""
import os
import sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.normpath(os.path.join(HERE, "..")))
import prtr_fa2_html as F

F.render_folder(HERE, {
    "sustancia_sustancia_fa2": "Tamaulipas — coocurrencia de sustancias (Jaccard), ForceAtlas2 + Modularity de Gephi",
    "municipio_municipio_fa2": "Tamaulipas — similitud de perfil entre municipios, ForceAtlas2 + Modularity de Gephi",
}, skip=("temporal",), placeholders={"sustancia_sustancia_fa2": "Buscar sustancia (nombre o símbolo)…",
                                    "municipio_municipio_fa2": "Buscar municipio…"})
