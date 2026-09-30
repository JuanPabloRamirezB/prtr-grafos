"""Lightweight hover-text module for the national mortality graphs (separate from
prtr_hover.py, which is PRTR-specific). Units: CONTEO is a death COUNT (additive),
aggregated 2000-2022, excluding aggregate rows (ENT_CVE/MUN_CVE/SEXO/RANGO_EDAD ==
"Total"). Cause names/descriptions are kept in Spanish (as reported in the source),
matching the site's convention of leaving proper nouns/source-language text
untranslated; only UI chrome (titles, buttons, units) is in English.

"Leading causes" / "Highest burden in" lists are drawn from the FULL underlying
dataset (all 1,511 specific causes, all locations), not just whatever subset of
edges a particular graph variant happens to draw - same convention as prtr_hover.py,
whose hover stats are dataset-wide rather than scoped to the rendered subgraph.
"""
import pickle

CACHE = "/tmp/mortality_agg/agg.pkl"
_agg = None


def _load():
    global _agg
    if _agg is not None:
        return _agg
    a = pickle.load(open(CACHE, "rb"))
    a["causa_nat_chap"] = {}
    for (ent, cd), v in a["est_chap"].items():
        a["causa_nat_chap"][cd] = a["causa_nat_chap"].get(cd, 0.0) + v
    a["grand_total"] = sum(a["ent_total"].values())

    def group(src, key_fn, loc_fn):
        loc_to_causas, causa_to_locs = {}, {}
        for k, v in src.items():
            cd, loc = key_fn(k), loc_fn(k)
            loc_to_causas.setdefault(loc, []).append((cd, v))
            causa_to_locs.setdefault(cd, []).append((loc, v))
        for d in (loc_to_causas, causa_to_locs):
            for key in d:
                d[key].sort(key=lambda t: -t[1])
        return loc_to_causas, causa_to_locs

    a["est_chap_by_loc"], a["est_chap_by_causa"] = group(a["est_chap"], lambda k: k[1], lambda k: k[0])
    a["est_esp_by_loc"], a["est_esp_by_causa"] = group(a["est_esp"], lambda k: k[1], lambda k: k[0])
    a["mun_chap_by_loc"], a["mun_chap_by_causa"] = group(a["mun_chap"], lambda k: k[2], lambda k: (k[0], k[1]))
    a["mun_esp_by_loc"], a["mun_esp_by_causa"] = group(a["mun_esp"], lambda k: k[2], lambda k: (k[0], k[1]))
    _agg = a
    return a


def n(v):
    return f"{v:,.0f} deaths"


def _pct(v, total):
    if not total:
        return "0%"
    p = 100 * v / total
    return f"{p:.1f}%" if p >= 0.1 else ("<0.1%" if p > 0 else "0%")


def _causa_label(a, cd, chapter):
    return cd if chapter else a["causa_desc"].get(cd, cd)


def hover_location(key, level, chapter, extra=None):
    """key: state name, or 'Estado.Municipio' string."""
    a = _load()
    gran = "chap" if chapter else "esp"
    if level == "estado":
        totals = a["ent_total"]
        rank = 1 + sum(1 for v in totals.values() if v > totals.get(key, 0))
        total_here = totals.get(key, 0)
        lines = [f"<b>{key}</b> · state",
                 f"Total deaths 2000–2022: {n(total_here)} ({_pct(total_here, a['grand_total'])} of the national total)",
                 f"#{rank} of {len(totals)} states"]
        top = a[f"est_{gran}_by_loc"].get(key, [])[:5]
    else:
        totals = a["mun_total"]
        ent, mun = key.split(".", 1)
        tk = (ent, mun)
        rank = 1 + sum(1 for v in totals.values() if v > totals.get(tk, 0))
        total_here = totals.get(tk, 0)
        lines = [f"<b>{mun}</b> ({ent}) · municipality",
                 f"Total deaths 2000–2022: {n(total_here)} ({_pct(total_here, a['grand_total'])} of the national total)",
                 f"#{rank} of {len(totals)} municipalities"]
        top = a[f"mun_{gran}_by_loc"].get(tk, [])[:5]
    if top:
        items = "; ".join(f"{_causa_label(a, cd, chapter)} ({n(v)})" for cd, v in top)
        lines.append(f"Leading causes of death here: {items}")
    if extra:
        lines += list(extra)
    return "<br>".join(lines)


def hover_causa(cd, chapter, desc=None, national_total=None, extra=None, loc_level=None):
    a = _load()
    gran = "chap" if chapter else "esp"
    label = cd if chapter else (desc or a["causa_desc"].get(cd, cd))
    kind = "ICD chapter" if chapter else "specific cause (ICD code)"
    lines = [f"<b>{label}</b>" + (f" ({cd})" if not chapter and label != cd else "") + f" · {kind}"]
    nat = national_total if national_total is not None else (a["causa_nat_chap"] if chapter else a["causa_nat_esp"]).get(cd, 0)
    if nat:
        lines.append(f"Total deaths nationally 2000–2022: {n(nat)} ({_pct(nat, a['grand_total'])} of all deaths nationally)")
    if loc_level:
        table = a[f"{'est' if loc_level == 'estado' else 'mun'}_{gran}_by_causa"]
        top = table.get(cd, [])[:5]
        if top:
            if loc_level == "estado":
                items = "; ".join(f"{loc} ({n(v)})" for loc, v in top)
            else:
                items = "; ".join(f"{m} ({e}) ({n(v)})" for (e, m), v in top)
            lines.append(f"Highest burden in: {items}")
    if extra:
        lines += list(extra)
    return "<br>".join(lines)


def edge_hover_loc_causa(loc_key, level, cd, chapter, weight, desc=None):
    a = _load()
    causa_label = cd if chapter else (desc or a["causa_desc"].get(cd, cd))
    nat = (a["causa_nat_chap"] if chapter else a["causa_nat_esp"]).get(cd, 0)
    if level == "estado":
        loc_label = loc_key
        total = a["ent_total"].get(loc_key, 0)
    else:
        ent, mun = loc_key.split(".", 1)
        loc_label = f"{mun} ({ent})"
        total = a["mun_total"].get((ent, mun), 0)
    lines = [
        f"<b>{loc_label} ↔ {causa_label}</b>",
        f"Deaths 2000–2022: {n(weight)}",
        f"{_pct(weight, total)} of {loc_label}'s total deaths (all causes)",
    ]
    if nat:
        lines.append(f"{_pct(weight, nat)} of all national deaths from this cause")
    return "<br>".join(lines)


def sim_edge_hover(a_state, b_state, sim, granularity):
    a_agg = _load()
    ta, tb = a_agg["ent_total"].get(a_state, 0), a_agg["ent_total"].get(b_state, 0)
    return "<br>".join([
        f"<b>{a_state} ↔ {b_state}</b>",
        f"Cosine similarity of the mortality-cause profile ({granularity}): {sim:.2f}",
        f"{a_state}: {n(ta)} total deaths · {b_state}: {n(tb)} total deaths",
    ])


HOVERLABEL = dict(bgcolor="white", font_color="#0b0b0b", font_size=12, align="left", namelength=-1)
