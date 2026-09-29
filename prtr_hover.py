"""Descriptive hover text (English, plotly HTML) for the PRTR graphs.

Everything is derived from prtr_raw_for_stori_stori.csv so every HTML shows the same
figures. Units: `observation` is Kg/year per report; "cumulative" below is the SUM of
those reports over 2004-2022 (not an annual rate). Substance/medium/sector category
values are translated for display via prtr_i18n; place names (states/municipalities)
are kept as-is.

    import prtr_hover as H
    H.hover("Tamaulipas.Altamira")                # municipio (place names untranslated)
    H.hover("Cromo (Compuestos solubles)")        # substance -> shown as "Chromium (soluble compounds)"
    H.hover("aire")                               # release medium -> shown as "air"
    H.edge_hover("Tamaulipas.Altamira", "Bióxido de carbono")
    H.edge_midpoints(edges, pos)                  # invisible hover targets on edges

Internal aggregation keys stay the ORIGINAL SPANISH strings from the CSV throughout
(so lookups always match); `display()` is the only place English text is produced,
and `resolve()` accepts either the Spanish key or its English translation (needed
because Gephi-rendered pages re-import the already-translated node "label").
"""
import csv
import os
from collections import Counter, defaultdict

import plotly.graph_objects as go

from prtr_i18n import MEDIO_EN, SECTOR_EN, SUBSTANCE_EN

_HERE = os.path.dirname(os.path.abspath(__file__))
_SRC = os.path.join(_HERE, "prtr_raw_for_stori_stori.csv")
STATE = "Tamaulipas"     # None = whole country
LEVEL = "municipio"      # "municipio" (State.Municipality) or "estado" (state)
ALL_YEARS = set()
_loaded = False

_SUBSTANCE_ES = {v: k for k, v in SUBSTANCE_EN.items()}
_MEDIO_ES = {v: k for k, v in MEDIO_EN.items()}


def configure(state="Tamaulipas", level="municipio"):
    """Switch scope: configure("Tamaulipas","municipio") (default) or
    configure(None,"estado") / configure(None,"municipio") for the national data."""
    global STATE, LEVEL, _loaded
    STATE, LEVEL, _loaded = state, level, False


def _unit():
    return ("state", "states") if LEVEL == "estado" else ("municipality", "municipalities")


def _share_of():
    return "of the state" if STATE else "of the national total"


def _load():
    global _loaded, loc_tot, sub_tot, med_tot, loc_sub, sub_loc, loc_sector, sub_sector, med_sector
    global loc_medio, sub_medio, loc_years, sub_years, med_years, sub_symbol, edge, edge_med
    global edge_year, loc_year, sub_year, state_total, med_loc, med_sub, loc_munis, ALL_YEARS
    if _loaded:
        return
    loc_tot, sub_tot, med_tot = Counter(), Counter(), Counter()
    loc_sub, sub_loc = defaultdict(Counter), defaultdict(Counter)
    loc_sector, sub_sector, med_sector = defaultdict(Counter), defaultdict(Counter), defaultdict(Counter)
    loc_medio, sub_medio = defaultdict(Counter), defaultdict(Counter)
    loc_years, sub_years, med_years = defaultdict(set), defaultdict(set), defaultdict(set)
    sub_symbol = {}
    med_loc, med_sub = defaultdict(Counter), defaultdict(Counter)
    edge = defaultdict(lambda: {"kg": 0.0, "n": 0, "years": set(), "medio": Counter(), "sector": Counter()})
    edge_med = defaultdict(lambda: {"kg": 0.0, "n": 0, "years": set(), "sector": Counter(), "sub": Counter()})
    edge_year = Counter()
    loc_year, sub_year = Counter(), Counter()
    state_total = 0.0
    loc_munis = defaultdict(set)
    ALL_YEARS = set()
    with open(_SRC, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            sp = row["spatial"].split(".")
            if STATE and sp[0] != STATE:
                continue
            loc = sp[0] if LEVEL == "estado" else ".".join(sp[:2])
            loc_munis[loc].add(".".join(sp[:2]))
            p = row["interest"].split(".")
            sub = p[-3] if len(p) >= 3 else row["interest"]
            medio = p[-1]
            sector = p[-5] if len(p) >= 5 else ""
            try:
                v = float(row["observation"])
                y = int(row["temporal"])
            except ValueError:
                continue
            state_total += v
            ALL_YEARS.add(y)
            loc_tot[loc] += v; sub_tot[sub] += v; med_tot[medio] += v
            loc_sub[loc][sub] += v; sub_loc[sub][loc] += v
            loc_sector[loc][sector] += v; sub_sector[sub][sector] += v; med_sector[medio][sector] += v
            loc_medio[loc][medio] += v; sub_medio[sub][medio] += v
            loc_years[loc].add(y); sub_years[sub].add(y); med_years[medio].add(y)
            if len(p) >= 2:
                sub_symbol[sub] = p[-2]
            med_loc[medio][loc] += v; med_sub[medio][sub] += v
            e = edge[(loc, sub)]
            e["kg"] += v; e["n"] += 1; e["years"].add(y); e["medio"][medio] += v; e["sector"][sector] += v
            m = edge_med[(loc, medio)]
            m["kg"] += v; m["n"] += 1; m["years"].add(y); m["sector"][sector] += v; m["sub"][sub] += v
            edge_year[(loc, sub, y)] += v
            edge_year[(loc, medio, y)] += v
            loc_year[(loc, y)] += v; sub_year[(sub, y)] += v
    _loaded = True


def kg(v):
    if v >= 1000:
        return f"{v:,.0f} kg (≈ {v / 1000:,.0f} t)"
    return f"{v:,.2f} kg"


def _pct(v, total):
    if not total:
        return "0%"
    p = 100 * v / total
    if p >= 1:
        return f"{p:.1f}%"
    return f"{p:.3f}%" if p >= 0.001 else ("<0.001%" if p > 0 else "0%")


def display(name):
    """English display text for a category value (substance or release medium);
    place names and anything without a translation entry pass through unchanged."""
    return SUBSTANCE_EN.get(name, MEDIO_EN.get(name, name))


def _top(counter, n=3, total=None, short=False, translate=False):
    total = total if total is not None else sum(counter.values())
    out = []
    for k, v in counter.most_common(n):
        if short:
            name = globals()["short"](k)
        elif translate:
            name = SECTOR_EN.get(k, display(k))
        else:
            name = k
        out.append(f"{name} ({_pct(v, total)})")
    return ", ".join(out) if out else "—"


def _years(ys):
    ys = sorted(ys)
    return f"{len(ys)} of {len(ALL_YEARS)} years ({ys[0]}–{ys[-1]})" if ys else "—"


def short(name):
    if LEVEL == "estado":
        return name
    if STATE and name.startswith(STATE + "."):
        return name.split(".", 1)[1]
    if not STATE and "." in name:
        est, mun = name.split(".", 1)
        return f"{mun} ({est})"
    return name


def _range():
    ys = sorted(ALL_YEARS)
    return f"{ys[0]}–{ys[-1]}"


def resolve(label):
    _load()
    for cand in ((label, f"{STATE}.{label}") if STATE else (label,)):
        if cand in loc_tot:
            return "loc", cand
    for cand in (label, _SUBSTANCE_ES.get(label)):
        if cand and cand in sub_tot:
            return "sub", cand
    for cand in (label, _MEDIO_ES.get(label)):
        if cand and cand in med_tot:
            return "med", cand
    return None, label


def hover(label, extra=None, year=None):
    """Descriptive tooltip for a municipality, substance or release medium. `extra` =
    list of extra lines (e.g. centrality); `year` adds that year's own figure."""
    _load()
    kind, key = resolve(label)
    lines = []
    if kind == "loc":
        rank = 1 + sum(1 for v in loc_tot.values() if v > loc_tot[key])
        u1, u2 = _unit()
        lines += [f"<b>{short(key)}</b> · {u1}",
                  f"Cumulative {_range()}: {kg(loc_tot[key])}",
                  f"{_pct(loc_tot[key], state_total)} {_share_of()} · #{rank} of {len(loc_tot)} {u2}",
                  f"Distinct substances: {len(loc_sub[key])} · reports in {_years(loc_years[key])}",
                  f"Main release medium: {_top(loc_medio[key], 2, translate=True)}",
                  f"Main sector: {_top(loc_sector[key], 2, translate=True)}",
                  f"Top substances (by kg): {_top(loc_sub[key], 3, translate=True)}"]
        if LEVEL == "estado":
            lines.insert(3, f"Municipalities reporting: {len(loc_munis[key])}")
        if year is not None:
            lines.insert(2, f"<b>{year}</b>: {kg(loc_year[(key, year)])}" if loc_year[(key, year)] else f"<b>{year}</b>: no report")
    elif kind == "sub":
        rank = 1 + sum(1 for v in sub_tot.values() if v > sub_tot[key])
        sym = sub_symbol.get(key, "")
        lines += [f"<b>{display(key)}</b>" + (f" · symbol {sym}" if sym else "") + " · substance",
                  f"Cumulative {_range()}: {kg(sub_tot[key])}",
                  f"{_pct(sub_tot[key], state_total)} {_share_of()} · #{rank} of {len(sub_tot)} substances",
                  f"Reported in {len(sub_loc[key])} of {len(loc_tot)} {_unit()[1]} · {_years(sub_years[key])}",
                  f"Release medium: {_top(sub_medio[key], 3, translate=True)}",
                  f"Sector: {_top(sub_sector[key], 2, translate=True)}",
                  f"{_unit()[1].capitalize()} with the most kg: {_top(sub_loc[key], 3, short=True)}"]
        if year is not None:
            lines.insert(2, f"<b>{year}</b>: {kg(sub_year[(key, year)])}" if sub_year[(key, year)] else f"<b>{year}</b>: no report")
    elif kind == "med":
        lines += [f"<b>{display(key)}</b> · release/destination medium",
                  f"Cumulative {_range()}: {kg(med_tot[key])} ({_pct(med_tot[key], state_total)} {_share_of()})",
                  f"{_unit()[1].capitalize()} using it: {len(med_loc[key])} of {len(loc_tot)} · {_years(med_years[key])}",
                  f"Distinct substances: {len(med_sub[key])}",
                  f"Main sector: {_top(med_sector[key], 2, translate=True)}",
                  f"{_unit()[1].capitalize()} with the most kg: {_top(med_loc[key], 3, short=True)}",
                  f"Substances with the most kg: {_top(med_sub[key], 3, translate=True)}"]
    else:
        lines.append(f"<b>{display(label)}</b>")
    if extra:
        lines += list(extra)
    return "<br>".join(lines)


def edge_hover(a, b, year=None, extra=None):
    """Tooltip for a municipality<->substance or municipality<->medium edge."""
    _load()
    ka, a = resolve(a)
    kb, b = resolve(b)
    if ka != "loc":
        a, b, ka, kb = b, a, kb, ka
    b_disp = display(b)
    if kb == "sub":
        e = edge.get((a, b))
        if not e:
            return f"<b>{short(a)} ↔ {b_disp}</b>"
        lines = [f"<b>{short(a)} ↔ {b_disp}</b>",
                 f"Cumulative: {kg(e['kg'])} in {e['n']} reports",
                 f"Years: {_years(e['years'])}",
                 f"Medium: {_top(e['medio'], 2, translate=True)}",
                 f"Sector: {_top(e['sector'], 2, translate=True)}",
                 f"That's {_pct(e['kg'], loc_tot[a])} of what {short(a)} reports"]
    else:
        e = edge_med.get((a, b))
        if not e:
            return f"<b>{short(a)} ↔ {b_disp}</b>"
        lines = [f"<b>{short(a)} ↔ {b_disp}</b>",
                 f"Cumulative: {kg(e['kg'])} in {e['n']} reports",
                 f"Years: {_years(e['years'])}",
                 f"Sector: {_top(e['sector'], 2, translate=True)}",
                 f"Substances with the most kg: {_top(e['sub'], 3, translate=True)}",
                 f"That's {_pct(e['kg'], loc_tot[a])} of what {short(a)} reports"]
    if year is not None:
        v = edge_year.get((a, b, year), 0.0)
        lines.insert(1, f"<b>{year}</b>: {kg(v)}" if v else f"<b>{year}</b>: no report")
    if extra:
        lines += list(extra)
    return "<br>".join(lines)


def muni_pair_hover(a, b, sim):
    """Municipality<->municipality similarity edge."""
    _load()
    _, a = resolve(a)
    _, b = resolve(b)
    sa, sb = set(loc_sub[a]), set(loc_sub[b])
    shared = sa & sb
    top = Counter({s: loc_sub[a][s] + loc_sub[b][s] for s in shared})
    return "<br>".join([
        f"<b>{short(a)} ↔ {short(b)}</b>",
        f"Cosine similarity of the emissions profile: {sim:.2f}",
        f"Shared substances: {len(shared)} of {len(sa | sb)} (union)",
        f"Shared, by kg: {_top(top, 3, translate=True)}",
        f"Only {short(a)}: {len(sa - sb)} · only {short(b)}: {len(sb - sa)}"])


def sub_pair_hover(a, b, jac):
    """Substance<->substance co-occurrence edge."""
    _load()
    a_disp, b_disp = display(a), display(b)
    la, lb = set(sub_loc[a]), set(sub_loc[b])
    both = la & lb
    names = ", ".join(short(m) for m, _ in Counter({m: sub_loc[a][m] + sub_loc[b][m] for m in both}).most_common(4))
    return "<br>".join([
        f"<b>{a_disp} ↔ {b_disp}</b>",
        f"Co-occurrence (Jaccard): {jac:.2f}",
        f"Reported together in {len(both)} {_unit()[1]} (of {len(la | lb)} reporting either)",
        f"Mostly in: {names or '—'}"])


def edge_midpoints(edges, textfn, pos, geo=False, latlon=None, template=False):
    """Invisible hover targets at the midpoint of every edge. `edges` = [(u, v)],
    `textfn(u, v) -> html`, `pos[n] = (x, y)` (or latlon[n] = (lat, lon) when geo).
    template=True uses hovertemplate instead of hoverinfo="text" (needed inside animation
    frames, so a restyled hoverinfo="skip" survives the frame updates)."""
    xs, ys, tx = [], [], []
    for u, v in edges:
        if geo:
            (la, lo), (lb, lob) = latlon[u], latlon[v]
            xs.append((lo + lob) / 2); ys.append((la + lb) / 2)
        else:
            xs.append((pos[u][0] + pos[v][0]) / 2); ys.append((pos[u][1] + pos[v][1]) / 2)
        tx.append(textfn(u, v))
    marker = dict(size=9, color="rgba(0,0,0,0)")
    kw = dict(mode="markers", marker=marker, hovertext=tx, showlegend=False, meta=dict(role="edgehover"))
    if template:
        kw["hovertemplate"] = "%{hovertext}<extra></extra>"
    else:
        kw["hoverinfo"] = "text"
    if geo:
        return go.Scattergeo(lon=xs, lat=ys, **kw)
    return go.Scatter(x=xs, y=ys, **kw)


HOVERLABEL = dict(bgcolor="white", font_color="#0b0b0b", font_size=12, align="left", namelength=-1)
