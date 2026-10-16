#!/usr/bin/env bash
# Builds the full 9-graph-type PRTR set for one Mexican state, mirroring the
# graphs_pollutants/estados/{mexico,baja_california_sur} pilot layout exactly.
# Usage: ./build_state.sh "Nuevo León"
set -euo pipefail
STATE="$1"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$HERE/.."  # build_prtr_graph.py reads prtr_raw_for_stori_stori.csv relative to cwd
VENV=$(ls -d /tmp/claude-1000/*/*/scratchpad/viz_venv 2>/dev/null | head -1)
PY="${VENV:-}/bin/python"
[ -x "$PY" ] || { python3 -m venv /tmp/viz_venv && /tmp/viz_venv/bin/pip install -q networkx plotly matplotlib numpy scipy pillow && PY=/tmp/viz_venv/bin/python; }
JAVAC="/mnt/c/Program Files/Java/jdk-21/bin/javac.exe"
JAVA="/mnt/c/Program Files/Java/jdk-21/bin/java.exe"
JARW=$(wslpath -w "$HERE/../gephi-toolkit-0.10.1-all.jar")
SLUG=$("$PY" -c "import unicodedata,sys; print(unicodedata.normalize('NFKD',sys.argv[1]).encode('ascii','ignore').decode().lower().replace(' ','_'))" "$STATE")
BASE="$HERE/estados/$SLUG"
mkdir -p "$BASE"/{"${SLUG}_graph","${SLUG}_graph_toolkit","${SLUG}_projected_networks","${SLUG}_temporal_graph"}
mkdir -p "$BASE/${SLUG}_gephi_fa2_redes"/{sustancia_sustancia,municipio_municipio,temporal/frames}
mkdir -p "$BASE/${SLUG}_gephi_extra"/{centralidad,contraccion_medio,ego_network,geografico,timeline}

jrun() { # jrun ClassDir ClassName input.gexf outDir [extra args...]
  local cdir="$1" cls="$2" input="$3" outdir="$4"; shift 4
  "$JAVA" -cp "$JARW;$(wslpath -w "$HERE/$cdir")" "$cls" "$(wslpath -w "$input")" "$(wslpath -w "$outdir")" "$@"
}

echo "== $STATE ($SLUG) : base GEXFs + Plotly =="
"$PY" "$HERE/../build_prtr_graph.py" "$STATE" "$BASE/${SLUG}_graph_toolkit" "$SLUG"
"$PY" "$HERE/tamaulipas_graph/build_graph.py" "$STATE" "$BASE/${SLUG}_graph" "$SLUG"
"$PY" "$HERE/tamaulipas_projected_networks/build_projected_networks.py" "$STATE" "$BASE/${SLUG}_projected_networks"
"$PY" "$HERE/tamaulipas_temporal_graph/build_temporal_graph.py" "$STATE" "$BASE/${SLUG}_temporal_graph" "$SLUG"
"$PY" "$HERE/tamaulipas_gephi_fa2_redes/build_projected_gexf.py" "$STATE" "$BASE/${SLUG}_gephi_fa2_redes"
"$PY" "$HERE/tamaulipas_gephi_fa2_redes/build_temporal_gexf.py" "$STATE" "$BASE/${SLUG}_gephi_fa2_redes"
"$PY" "$HERE/tamaulipas_gephi_extra/contraccion_medio/build_gexf.py" "$STATE" "$BASE/${SLUG}_gephi_extra/contraccion_medio"
"$PY" "$HERE/tamaulipas_gephi_extra/contraccion_medio/build_html.py" "$STATE" "$BASE/${SLUG}_gephi_extra/contraccion_medio"
"$PY" "$HERE/tamaulipas_gephi_extra/centralidad/build_html.py" "$STATE" "$BASE/${SLUG}_gephi_extra/centralidad"
"$PY" "$HERE/tamaulipas_gephi_extra/timeline/build_gexf.py" "$STATE" "$BASE/${SLUG}_gephi_extra/timeline"
"$PY" "$HERE/tamaulipas_gephi_extra/ego_network/build_gexf.py" "$STATE" "$BASE/${SLUG}_gephi_extra/ego_network"
FOCAL_SLUG=$(tail -1 "$BASE/${SLUG}_gephi_extra/ego_network/focal.txt")
"$PY" "$HERE/tamaulipas_gephi_extra/ego_network/build_html.py" "$STATE" "$BASE/${SLUG}_gephi_extra/ego_network"
"$PY" "$HERE/tamaulipas_gephi_extra/geografico/build_gexf.py" "$STATE" "$BASE/${SLUG}_gephi_extra/geografico"
"$PY" "$HERE/tamaulipas_gephi_extra/geografico/build_html.py" "$STATE" "$BASE/${SLUG}_gephi_extra/geografico"

echo "== $STATE : Java/Gephi (FA2 + Modularity + PNG/PDF) =="
jrun tamaulipas_graph_toolkit GephiTamaulipas "$BASE/${SLUG}_graph_toolkit/prtr_municipio_sustancia_$SLUG.gexf" "$BASE/${SLUG}_graph_toolkit"
for f in tamaulipas_graph_toolkit_layout.gexf tamaulipas_graph_toolkit.pdf tamaulipas_graph_toolkit.png; do
  mv "$BASE/${SLUG}_graph_toolkit/$f" "$BASE/${SLUG}_graph_toolkit/${f/tamaulipas/$SLUG}"
done

jrun tamaulipas_gephi_fa2_redes GephiProyectada "$BASE/${SLUG}_gephi_fa2_redes/sustancia_sustancia/sustancia_sustancia.gexf" "$BASE/${SLUG}_gephi_fa2_redes/sustancia_sustancia" sustancia_sustancia n_municipios 0.0 10 1.0 normal 30 pack
jrun tamaulipas_gephi_fa2_redes GephiProyectada "$BASE/${SLUG}_gephi_fa2_redes/municipio_municipio/municipio_municipio.gexf" "$BASE/${SLUG}_gephi_fa2_redes/municipio_municipio" municipio_municipio total_kg 1.0 10 1.0 normal 30 pack
jrun tamaulipas_gephi_fa2_redes GephiTemporal "$BASE/${SLUG}_gephi_fa2_redes/temporal/temporal_union.gexf" "$BASE/${SLUG}_gephi_fa2_redes/temporal" "$(cat "$BASE/${SLUG}_gephi_fa2_redes/temporal/years.txt")" "2004,2010,2016,2022"

jrun tamaulipas_gephi_extra/centralidad GephiCentralidad "$BASE/${SLUG}_graph_toolkit/prtr_municipio_sustancia_$SLUG.gexf" "$BASE/${SLUG}_gephi_extra/centralidad"
jrun tamaulipas_gephi_extra/centralidad GephiCentralidad "$BASE/${SLUG}_graph_toolkit/prtr_municipio_sustancia_$SLUG.gexf" "$BASE/${SLUG}_gephi_extra/centralidad" fa2

jrun tamaulipas_gephi_extra/contraccion_medio GephiMedio "$BASE/${SLUG}_gephi_extra/contraccion_medio/municipio_medio.gexf" "$BASE/${SLUG}_gephi_extra/contraccion_medio"
jrun tamaulipas_gephi_extra/contraccion_medio GephiMedio "$BASE/${SLUG}_gephi_extra/contraccion_medio/municipio_medio.gexf" "$BASE/${SLUG}_gephi_extra/contraccion_medio" fa2

jrun tamaulipas_gephi_extra/ego_network GephiEgo "$BASE/${SLUG}_gephi_extra/ego_network/ego_$FOCAL_SLUG.gexf" "$BASE/${SLUG}_gephi_extra/ego_network"
jrun tamaulipas_gephi_extra/ego_network GephiEgo "$BASE/${SLUG}_gephi_extra/ego_network/ego_$FOCAL_SLUG.gexf" "$BASE/${SLUG}_gephi_extra/ego_network" fa2
for suf in toolkit.gexf toolkit.pdf toolkit.png toolkit_fa2.gexf toolkit_fa2.pdf toolkit_fa2.png; do
  mv "$BASE/${SLUG}_gephi_extra/ego_network/ego_altamira_$suf" "$BASE/${SLUG}_gephi_extra/ego_network/ego_${FOCAL_SLUG}_$suf"
done

jrun tamaulipas_gephi_extra/geografico GephiGeo "$BASE/${SLUG}_gephi_extra/geografico/municipio_geo.gexf" "$BASE/${SLUG}_gephi_extra/geografico"

jrun tamaulipas_gephi_extra/timeline GephiTimeline "$BASE/${SLUG}_gephi_extra/timeline/temporal_fingerprint.gexf" "$BASE/${SLUG}_gephi_extra/timeline"
jrun tamaulipas_gephi_extra/timeline GephiTimeline "$BASE/${SLUG}_gephi_extra/timeline/temporal_fingerprint.gexf" "$BASE/${SLUG}_gephi_extra/timeline" fa2

echo "== $STATE : FA2 HTML + assemble =="
"$PY" "$HERE/tamaulipas_gephi_fa2_redes/fa2_html.py" "$STATE" "$BASE/${SLUG}_gephi_fa2_redes"
"$PY" "$HERE/tamaulipas_gephi_extra/fa2_html.py" "$STATE" "$BASE/${SLUG}_gephi_extra" "$FOCAL_SLUG"
"$PY" "$HERE/tamaulipas_gephi_fa2_redes/assemble_temporal.py" "$STATE" "$BASE/${SLUG}_gephi_fa2_redes"
echo "== $STATE done: $BASE =="
