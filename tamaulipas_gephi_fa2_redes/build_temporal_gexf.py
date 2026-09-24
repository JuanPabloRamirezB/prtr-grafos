"""Union Municipio<->Sustancia graph (all years) with per-year columns:
node kg_<year> (Kg/ano that year, 0 if absent) and edge y_<year> (same)."""
import csv, os
import networkx as nx

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "..", "prtr_raw_for_stori_stori.csv")

edge_year, loc_year, sub_year = {}, {}, {}
years = set()
with open(SRC, encoding="utf-8") as f:
    for row in csv.DictReader(f):
        sp = row["spatial"].split(".")
        if sp[0] != "Tamaulipas":
            continue
        loc = ".".join(sp[:2])
        ip = row["interest"].split(".")
        sub = ip[-3] if len(ip) >= 3 else row["interest"]
        try:
            v = float(row["observation"]); y = int(row["temporal"])
        except ValueError:
            continue
        years.add(y)
        edge_year[(loc, sub, y)] = edge_year.get((loc, sub, y), 0.0) + v
        loc_year[(loc, y)] = loc_year.get((loc, y), 0.0) + v
        sub_year[(sub, y)] = sub_year.get((sub, y), 0.0) + v
years = sorted(years)

G = nx.Graph()
locs = sorted({k[0] for k in loc_year}); subs = sorted({k[0] for k in sub_year})
for l in locs:
    a = dict(label=l, type="location", total_kg=sum(loc_year.get((l, y), 0.0) for y in years))
    a.update({f"kg_{y}": loc_year.get((l, y), 0.0) for y in years})
    G.add_node("LOC::" + l, **a)
for s in subs:
    a = dict(label=s, type="substance", total_kg=sum(sub_year.get((s, y), 0.0) for y in years))
    a.update({f"kg_{y}": sub_year.get((s, y), 0.0) for y in years})
    G.add_node("SUB::" + s, **a)
pairs = {(l, s) for (l, s, y) in edge_year}
for l, s in pairs:
    a = dict(weight=sum(edge_year.get((l, s, y), 0.0) for y in years))
    a.update({f"y_{y}": edge_year.get((l, s, y), 0.0) for y in years})
    G.add_edge("LOC::" + l, "SUB::" + s, **a)
print("years", years[0], years[-1], len(years), "nodes", G.number_of_nodes(), "edges", G.number_of_edges())
nx.write_gexf(G, os.path.join(HERE, "temporal", "temporal_union.gexf"))
with open(os.path.join(HERE, "temporal", "years.txt"), "w") as f:
    f.write(",".join(map(str, years)))
