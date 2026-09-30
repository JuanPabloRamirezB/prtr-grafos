# prtr-grafos — grafos interactivos del PRTR de México

Redes de **estados, municipios y sustancias** del Registro de Emisiones y Transferencia de Contaminantes (2004–2022),
con páginas interactivas (Plotly), imágenes (PNG/PDF) y archivos GEXF para abrir en Gephi.
La página central es [`index.html`](index.html): lista los 13 gráficos, con filtros, buscador, miniaturas y enlaces.

## Estructura

| Carpeta | Contenido |
|---|---|
| `index.html`, `assets/thumbs/` | Página central (GitHub Pages) y sus miniaturas. Se genera con `build_index.py`. |
| `graphs_pollutants/` | Todos los grafos del PRTR (contaminantes), organizados en las subcarpetas de abajo. |
| `graphs_pollutants/nacional_gephi/` | Nivel nacional: estados↔estados, estado↔sustancia, municipio↔sustancia (716 municipios) y mapa de estados. |
| `graphs_pollutants/tamaulipas_graph/` | Municipio↔sustancia de Tamaulipas en dos columnas (Plotly). |
| `graphs_pollutants/tamaulipas_graph_toolkit/` | La misma red renderizada con Gephi Toolkit. |
| `graphs_pollutants/tamaulipas_projected_networks/` | Redes proyectadas (sustancias y municipios) con layout jerárquico y Louvain (Plotly). |
| `graphs_pollutants/tamaulipas_gephi_fa2_redes/` | Redes proyectadas y evolución por año con ForceAtlas2 y Modularity de Gephi. |
| `graphs_pollutants/tamaulipas_temporal_graph/` | Evolución por año en dos columnas (Plotly). |
| `graphs_pollutants/tamaulipas_gephi_extra/` | Centralidad, huella temporal, mapa, ego-network de Altamira y municipio↔medio (dos columnas y ForceAtlas2). |

Módulos compartidos (raíz, fuera de `graphs_pollutants/` porque los usan todos los grafos): `prtr_hover.py` (tooltips descriptivos),
`prtr_ui.py` + `ui_snippet.js` (buscador, botones y leyenda por grupo), `prtr_fa2_html.py` (HTML a partir de los GEXF que exporta Gephi),
`build_prtr_graph.py` (GEXF inicial), `ui_smoke_test.py` (prueba en Edge headless).

`graphs_pollutants/tamaulipas_gephi_extra/timeline/timeline.html` es una copia de `tamaulipas_temporal.html` (con el enlace de regreso ajustado).
`graphs_pollutants/nacional_gephi/municipio_sustancia/municipio_sustancia_fa2_buscador.html` es idéntico a `municipio_sustancia_fa2.html`; se conserva por compatibilidad.

## Publicar en GitHub Pages

Este repositorio (`prtr-grafos`, raíz = esta carpeta) tiene dos formas de publicarse:

**Opción A — GitHub Actions (flujo incluido).** El archivo `.github/workflows/prtr-grafos-pages.yml` publica solo los archivos públicos
(sin scripts, código Java ni dataset). En el repositorio: *Settings → Pages → Source: GitHub Actions*; el despliegue corre al hacer push a
`main` con cualquier cambio, o a mano desde *Actions → Run workflow*.

**Opción B — Deploy from branch (más simple).** *Settings → Pages → Source: Deploy from a branch → main / (root)*. El archivo `.nojekyll`
ya está incluido. (El `.gitignore` mantiene fuera el CSV, el `.jar` y los `.class`.) No necesita Actions ni build: sirve los archivos tal cual.

La página queda en `https://<usuario>.github.io/<repositorio>/`.

Todos los enlaces son relativos, así que funciona bajo cualquier URL. Los gráficos cargan Plotly desde un CDN (necesitan internet).

## Regenerar

Requisitos: Python 3.10+ con `pip install networkx plotly matplotlib numpy scipy pillow`. Coloca `prtr_raw_for_stori_stori.csv` en esta carpeta (no se versiona: 39 MB).

```bash
cd prtr-grafos
python graphs_pollutants/tamaulipas_graph/build_graph.py
python graphs_pollutants/tamaulipas_projected_networks/build_projected_networks.py
python graphs_pollutants/tamaulipas_temporal_graph/build_temporal_graph.py
for d in centralidad contraccion_medio ego_network geografico; do python graphs_pollutants/tamaulipas_gephi_extra/$d/build_html.py; done
python graphs_pollutants/tamaulipas_gephi_extra/fa2_html.py
python graphs_pollutants/tamaulipas_gephi_fa2_redes/fa2_html.py
python graphs_pollutants/tamaulipas_gephi_fa2_redes/assemble_temporal.py
python graphs_pollutants/nacional_gephi/nacional_html.py
python build_index.py            # página central y miniaturas
```

Los HTML de los pasos con Gephi (`*_fa2.html`) se construyen a partir de los `*_fa2.gexf` ya incluidos, así que **no** hace falta Gephi para regenerarlos.
Para volver a calcular layouts, comunidades, centralidad o los PNG/PDF de Gephi se usan los programas Java de cada carpeta (`Gephi*.java`) con
[`gephi-toolkit-0.10.1-all.jar`](https://repo1.maven.org/maven2/org/gephi/gephi-toolkit/0.10.1/gephi-toolkit-0.10.1-all.jar) y un JDK 21:

```bash
javac -cp gephi-toolkit-0.10.1-all.jar -d . GephiProyectada.java
java  -cp ".:gephi-toolkit-0.10.1-all.jar" GephiProyectada entrada.gexf salida/ base tamano_col peso_fa2 escala gravedad normal tamano_max pack
```

(en Windows el separador del classpath es `;`; los argumentos de cada programa están documentados en su comentario inicial). El PNG de Gephi necesita un
entorno gráfico del sistema (no funciona con `-Djava.awt.headless=true`).

## Prueba de las páginas interactivas

`python ui_smoke_test.py <archivo.html> ...` abre cada página en Edge headless, escribe una búsqueda, elige el primer resultado, recorre todos los botones
(comprobando tooltips y visibilidad) y, en las animadas, cambia de año con una selección activa. Imprime un JSON por archivo y debe mostrar `"errs": []`.
Ajusta la ruta de `EDGE` en el script si usas otro navegador o sistema.

## Notas

- Los totales son la **suma de todos los reportes 2004–2022** (el CSV trae Kg/año por reporte), no una tasa anual.
- Similitud entre municipios/estados: coseno de `log(1+Kg)` por sustancia (≥ 0.7 en Tamaulipas; percentil 70 a nivel nacional). Entre sustancias: Jaccard ≥ 0.7.
- ForceAtlas2 con influencia del peso de aristas en 0 en los bipartitos (unos pocos emisores enormes colapsaban el layout).
- Las coordenadas de los mapas son aproximadas (cabeceras), no aptas para uso cartográfico.
