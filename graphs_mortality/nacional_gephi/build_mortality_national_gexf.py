"""National-level GEXF inputs for the mortality dataset (mirrors
graphs_pollutants/nacional_gephi/build_national_gexf.py), at two "cause"
granularities:
  capitulo   : the 23 single-letter ICD chapter codes (A, B, C...), used as-is.
  especifico : the top 100 specific ICD codes nationally by total CONTEO (death
               count), with municipio<->causa edges additionally dropped when
               their own summed CONTEO <= 100 over 2000-2022 (top-N alone isn't
               enough to bound size at municipio level: the highest-volume
               causes occur in nearly every municipality).

Uses CONTEO (death count, additive) rather than TASA (a rate - not valid to sum
across sex/age strata), aggregated from the raw Database_mortality/*.csv with
ENT_CVE/MUN_CVE resolved to real names via ../../data/inegi_catalogo_municipios.csv
(the source's own ENT_NAME/MUN_NAME text has irrecoverably corrupted accents).
Reuses the cached aggregation at /tmp/mortality_agg/agg.pkl when present.

Produces (all under this folder):
  estado_estado/estado_estado_{capitulo,especifico}.gexf   - state similarity (cosine)
  estado_causa/estado_causa_{capitulo,especifico}.gexf     - bipartite
  municipio_causa/municipio_causa_{capitulo,especifico}.gexf - bipartite
  geografico/estado_geo_{capitulo,especifico}.gexf         - copy of estado_estado, +lat/lon

All node "type"/"total_kg"/"lat"/"lon" attribute names are kept exactly as the
existing compiled Gephi Toolkit classes (GephiBipartito/GephiGeoNacional/
GephiProyectada) expect them, even though semantically here total_kg holds a
death count, not kilograms - only the internal Gephi column name is reused, not
its display meaning (the HTML rendering layer labels it correctly).
"""
import csv
import glob
import math
import os
import pickle

import networkx as nx
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "..", "..", "data")
CATALOG = os.path.join(DATA, "inegi_catalogo_municipios.csv")
SRC_DIR = os.path.join(DATA, "Database_mortality")
CACHE = "/tmp/mortality_agg/agg.pkl"
TOP_N = 100
MUN_ESP_MIN = 100  # drop municipio<->causa-especifica edges at or below this total CONTEO

# same state-capital coordinates as graphs_pollutants/nacional_gephi/build_national_gexf.py
COORDS = {
 "Aguascalientes": (21.8853, -102.2916), "Baja California": (32.6245, -115.4523),
 "Baja California Sur": (24.1426, -110.3128), "Campeche": (19.8301, -90.5349),
 "Chiapas": (16.7528, -93.1152), "Chihuahua": (28.6353, -106.0889),
 "Ciudad de México": (19.4326, -99.1332), "Coahuila de Zaragoza": (25.4232, -100.9924),
 "Colima": (19.2433, -103.7250), "Durango": (24.0277, -104.6532),
 "Guanajuato": (21.0190, -101.2574), "Guerrero": (17.5506, -99.5058),
 "Hidalgo": (20.1011, -98.7591), "Jalisco": (20.6597, -103.3496),
 "México": (19.2826, -99.6557), "Michoacán de Ocampo": (19.7060, -101.1950),
 "Morelos": (18.9186, -99.2342), "Nayarit": (21.5058, -104.8946),
 "Nuevo León": (25.6866, -100.3161), "Oaxaca": (17.0732, -96.7266),
 "Puebla": (19.0414, -98.2063), "Querétaro": (20.5888, -100.3899),
 "Quintana Roo": (18.5001, -88.2961), "San Luis Potosí": (22.1565, -100.9855),
 "Sinaloa": (24.8091, -107.3940), "Sonora": (29.0729, -110.9559),
 "Tabasco": (17.9895, -92.9475), "Tamaulipas": (23.7369, -99.1411),
 "Tlaxcala": (19.3182, -98.2375), "Veracruz de Ignacio de la Llave": (19.5438, -96.9102),
 "Yucatán": (20.9674, -89.5926), "Zacatecas": (22.7709, -102.5832),
}


def build_agg():
    ent_names, mun_names = {}, {}
    with open(CATALOG, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            ent_names[row["cve_ent"]] = row["ent_name"]
            mun_names[(row["cve_ent"], row["cve_mun"])] = row["mun_name"]

    est_chap, mun_chap, est_esp, mun_esp = {}, {}, {}, {}
    causa_nat_esp, causa_desc, ent_total, mun_total = {}, {}, {}, {}
    for path in sorted(glob.glob(os.path.join(SRC_DIR, "*_Rates.csv"))):
        with open(path, newline="", encoding="utf-8") as f:
            r = csv.reader(f)
            header = next(r)
            idx = {c: header.index(c) for c in
                   ["CAUSA_DEF", "ENT_CVE", "MUN_CVE", "SEXO", "RANGO_EDAD", "CONTEO", "Descripcion"]}
            for row in r:
                if not row:
                    continue
                ent_cve, mun_cve = row[idx["ENT_CVE"]], row[idx["MUN_CVE"]]
                sexo, edad = row[idx["SEXO"]], row[idx["RANGO_EDAD"]]
                cd = row[idx["CAUSA_DEF"]]
                if "Total" in (ent_cve, mun_cve, sexo, edad, cd):
                    continue
                try:
                    conteo = float(row[idx["CONTEO"]])
                except ValueError:
                    continue
                ent = ent_names.get(ent_cve, ent_cve)
                mun = mun_names.get((ent_cve, mun_cve), mun_cve)
                ent_total[ent] = ent_total.get(ent, 0.0) + conteo
                mun_total[(ent, mun)] = mun_total.get((ent, mun), 0.0) + conteo
                if len(cd) == 1:
                    est_chap[(ent, cd)] = est_chap.get((ent, cd), 0.0) + conteo
                    mun_chap[(ent, mun, cd)] = mun_chap.get((ent, mun, cd), 0.0) + conteo
                else:
                    desc = row[idx["Descripcion"]].strip()
                    if desc == "Total":
                        continue  # specific code with no real description text: skip
                    est_esp[(ent, cd)] = est_esp.get((ent, cd), 0.0) + conteo
                    mun_esp[(ent, mun, cd)] = mun_esp.get((ent, mun, cd), 0.0) + conteo
                    causa_nat_esp[cd] = causa_nat_esp.get(cd, 0.0) + conteo
                    if desc and cd not in causa_desc:
                        causa_desc[cd] = desc
    return dict(est_chap=est_chap, mun_chap=mun_chap, est_esp=est_esp, mun_esp=mun_esp,
                causa_nat_esp=causa_nat_esp, causa_desc=causa_desc, ent_total=ent_total, mun_total=mun_total)


if os.path.exists(CACHE):
    agg = pickle.load(open(CACHE, "rb"))
    print(f"Loaded cached aggregation from {CACHE}")
else:
    print("No cache found, aggregating from raw Database_mortality/*.csv (several minutes)...")
    agg = build_agg()
    os.makedirs(os.path.dirname(CACHE), exist_ok=True)
    pickle.dump(agg, open(CACHE, "wb"))

est_chap, mun_chap = agg["est_chap"], agg["mun_chap"]
est_esp_all, mun_esp_all = agg["est_esp"], agg["mun_esp"]
causa_nat_esp, causa_desc = agg["causa_nat_esp"], agg["causa_desc"]
ent_total, mun_total = agg["ent_total"], agg["mun_total"]

TOP = set(sorted(causa_nat_esp, key=causa_nat_esp.get, reverse=True)[:TOP_N])
est_esp = {k: v for k, v in est_esp_all.items() if k[1] in TOP}
mun_esp = {k: v for k, v in mun_esp_all.items() if k[2] in TOP and v > MUN_ESP_MIN}
print(f"Top-{TOP_N} specific causes selected. estado x causa-especifica: {len(est_esp)} edges "
      f"(before prune: {sum(1 for k in est_esp_all if k[1] in TOP)}); "
      f"municipio x causa-especifica: {len(mun_esp)} edges (before >{MUN_ESP_MIN} prune: "
      f"{sum(1 for k in mun_esp_all if k[2] in TOP)})")


def causa_label(cd, chapter):
    if chapter:
        return cd
    return causa_desc.get(cd, cd)


def estado_estado(pairs, ents_needed):
    """pairs: dict (ent, causa) -> conteo, over the full set of causes for this granularity."""
    causas = sorted({cd for (_, cd) in pairs})
    idx = {c: i for i, c in enumerate(causas)}
    ents = sorted(ents_needed)
    vec = {}
    for e in ents:
        v = np.zeros(len(causas))
        for (ee, cd), conteo in pairs.items():
            if ee == e:
                v[idx[cd]] = math.log1p(conteo)
        vec[e] = v
    sims = {}
    for i in range(len(ents)):
        for j in range(i + 1, len(ents)):
            a, b = ents[i], ents[j]
            na, nb = np.linalg.norm(vec[a]), np.linalg.norm(vec[b])
            sims[(a, b)] = float(vec[a] @ vec[b] / (na * nb)) if na > 0 and nb > 0 else 0.0
    thr = float(np.percentile(list(sims.values()), 70))
    G = nx.Graph()
    n_causas = {}
    for (e, cd) in pairs:
        n_causas.setdefault(e, set()).add(cd)
    for e in ents:
        la, lo = COORDS[e]
        G.add_node(e, label=e, total_kg=ent_total.get(e, 0.0), n_causas=len(n_causas.get(e, ())),
                   lat=la, lon=lo)
    for (a, b), sim in sims.items():
        if sim >= thr:
            G.add_edge(a, b, weight=sim)
    print(f"estado_estado: cosine >= {thr:.3f} -> {G.number_of_nodes()} nodes, {G.number_of_edges()} edges, "
          f"isolates={len(list(nx.isolates(G)))}")
    return G


def bipartite(pairs, level, chapter, causa_totals):
    """pairs: dict (loc..., cd) -> conteo, level = 'estado' or 'municipio'."""
    B = nx.Graph()
    causa_tot_local = {}
    loc_keys = set()
    for key, conteo in pairs.items():
        cd = key[-1]
        loc = key[0] if level == "estado" else f"{key[0]}.{key[1]}"
        loc_keys.add(loc)
        causa_tot_local[cd] = causa_tot_local.get(cd, 0.0) + conteo
    loc_total_src = ent_total if level == "estado" else mun_total
    for loc in loc_keys:
        lookup = loc if level == "estado" else tuple(loc.split(".", 1))
        total = loc_total_src.get(lookup, sum(v for k, v in pairs.items()
                                                if (k[0] if level == "estado" else f"{k[0]}.{k[1]}") == loc))
        label = loc if level == "estado" else f"{loc.split('.', 1)[1]} ({loc.split('.', 1)[0]})"
        B.add_node("LOC::" + loc, label=label, type="location", total_kg=total)
    for cd, tot in causa_tot_local.items():
        national = causa_totals.get(cd, tot)
        B.add_node("CAU::" + cd, label=causa_label(cd, chapter), type="causa", total_kg=national)
    for key, conteo in pairs.items():
        cd = key[-1]
        loc = key[0] if level == "estado" else f"{key[0]}.{key[1]}"
        B.add_edge("LOC::" + loc, "CAU::" + cd, weight=conteo)
    for n, d in B.nodes(data=True):
        d["log_total"] = math.log10(1 + d["total_kg"])
    print(f"{level}_causa ({'capitulo' if chapter else 'especifico'}): "
          f"{B.number_of_nodes()} nodes, {B.number_of_edges()} edges")
    return B


def write(G, *paths):
    for p in paths:
        os.makedirs(os.path.dirname(p), exist_ok=True)
        nx.write_gexf(G, p)
        print("Written", p)


# ---- estado <-> estado (+ geografico copy), both granularities
ents_all = sorted(ent_total)
G_chap = estado_estado(est_chap, ents_all)
write(G_chap, os.path.join(HERE, "estado_estado", "estado_estado_capitulo.gexf"),
      os.path.join(HERE, "geografico", "estado_geo_capitulo.gexf"))

G_esp = estado_estado(est_esp, ents_all)
write(G_esp, os.path.join(HERE, "estado_estado", "estado_estado_especifico.gexf"),
      os.path.join(HERE, "geografico", "estado_geo_especifico.gexf"))

# ---- estado <-> causa, both granularities
write(bipartite(est_chap, "estado", True, {cd: sum(v for (e, c), v in est_chap.items() if c == cd) for cd in {c for _, c in est_chap}}),
      os.path.join(HERE, "estado_causa", "estado_causa_capitulo.gexf"))
write(bipartite(est_esp, "estado", False, causa_nat_esp),
      os.path.join(HERE, "estado_causa", "estado_causa_especifico.gexf"))

# ---- municipio <-> causa, both granularities
mun_chap_totals = {cd: sum(v for (e, m, c), v in mun_chap.items() if c == cd) for cd in {c for _, _, c in mun_chap}}
write(bipartite(mun_chap, "municipio", True, mun_chap_totals),
      os.path.join(HERE, "municipio_causa", "municipio_causa_capitulo.gexf"))
write(bipartite(mun_esp, "municipio", False, causa_nat_esp),
      os.path.join(HERE, "municipio_causa", "municipio_causa_especifico.gexf"))

print("ALL GEXF WRITTEN")
