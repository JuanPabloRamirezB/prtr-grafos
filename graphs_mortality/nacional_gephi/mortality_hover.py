"""Lightweight hover-text module for the national mortality graphs (separate from
prtr_hover.py, which is PRTR-specific). Units: CONTEO is a death COUNT (additive),
aggregated 2000-2022, excluding aggregate rows (ENT_CVE/MUN_CVE/SEXO/RANGO_EDAD ==
"Total"). Cause names/descriptions are kept in Spanish (as reported in the source),
matching the site's convention of leaving proper nouns/source-language text
untranslated; only UI chrome (titles, buttons, units) is in English.
"""
import pickle

CACHE = "/tmp/mortality_agg/agg.pkl"
_agg = None


def _load():
    global _agg
    if _agg is None:
        _agg = pickle.load(open(CACHE, "rb"))
    return _agg


def n(v):
    return f"{v:,.0f} deaths"


def _pct(v, total):
    if not total:
        return "0%"
    p = 100 * v / total
    return f"{p:.1f}%" if p >= 0.1 else ("<0.1%" if p > 0 else "0%")


def hover_location(key, level, extra=None):
    """key: state name, or 'Estado.Municipio' string."""
    a = _load()
    if level == "estado":
        totals, unit = a["ent_total"], ("state", "states")
        rank = 1 + sum(1 for v in totals.values() if v > totals.get(key, 0))
        lines = [f"<b>{key}</b> · state",
                 f"Total deaths 2000–2022: {n(totals.get(key, 0))}",
                 f"#{rank} of {len(totals)} states"]
    else:
        totals, unit = a["mun_total"], ("municipality", "municipalities")
        ent, mun = key.split(".", 1)
        tk = (ent, mun)
        rank = 1 + sum(1 for v in totals.values() if v > totals.get(tk, 0))
        lines = [f"<b>{mun}</b> ({ent}) · municipality",
                 f"Total deaths 2000–2022: {n(totals.get(tk, 0))}",
                 f"#{rank} of {len(totals)} municipalities"]
    if extra:
        lines += list(extra)
    return "<br>".join(lines)


def hover_causa(cd, chapter, desc=None, national_total=None, extra=None):
    a = _load()
    label = cd if chapter else (desc or a["causa_desc"].get(cd, cd))
    kind = "ICD chapter" if chapter else "specific cause (ICD code)"
    lines = [f"<b>{label}</b>" + (f" ({cd})" if not chapter and label != cd else "") + f" · {kind}"]
    if national_total is not None:
        lines.append(f"Total deaths nationally 2000–2022: {n(national_total)}")
    if extra:
        lines += list(extra)
    return "<br>".join(lines)


def edge_hover_loc_causa(loc_key, level, cd, chapter, weight, desc=None):
    a = _load()
    causa_label = cd if chapter else (desc or a["causa_desc"].get(cd, cd))
    if level == "estado":
        loc_label = loc_key
        total = a["ent_total"].get(loc_key, 0)
    else:
        ent, mun = loc_key.split(".", 1)
        loc_label = f"{mun} ({ent})"
        total = a["mun_total"].get((ent, mun), 0)
    return "<br>".join([
        f"<b>{loc_label} ↔ {causa_label}</b>",
        f"Deaths 2000–2022: {n(weight)}",
        f"That's {_pct(weight, total)} of {loc_label}'s total deaths (all causes)",
    ])


def sim_edge_hover(a_state, b_state, sim, granularity):
    return "<br>".join([
        f"<b>{a_state} ↔ {b_state}</b>",
        f"Cosine similarity of the mortality-cause profile ({granularity}): {sim:.2f}",
    ])


HOVERLABEL = dict(bgcolor="white", font_color="#0b0b0b", font_size=12, align="left", namelength=-1)
