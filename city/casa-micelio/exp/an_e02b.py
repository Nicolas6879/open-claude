"""E02b: jerarquia: correlacion (Spearman) entre poblacion y centralidad de intermediacion/grado por ciudad,
red real (NE) vs controles vs Physarum (semilla 0)."""
import os as _o
_o.environ.setdefault("OMP_NUM_THREADS", "1")
import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import numpy as np, networkx as nx
from scipy.stats import spearmanr
from micelio.data import load_cities, rail_backbone
from micelio.graphs import contract, mst_edges, delaunay_edges, rng_edges
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "out")


def cent(pts, edges, nc, pop):
    links = contract(pts, edges, list(range(nc)))
    g = nx.Graph()
    g.add_nodes_from(range(nc))
    for a, b, l in links:
        if not g.has_edge(a, b) or g[a][b]["w"] > l:
            g.add_edge(a, b, w=l)
    bc = nx.betweenness_centrality(g, weight="w")
    bb, dd = [], []
    for i in range(nc):
        j = i
        if g.degree(i) == 1:                       # ciudad colgada de una junción (ferrocarril): usar la junción
            nb = next(iter(g[i]))
            if nb >= nc:
                j = nb
        bb.append(bc[j]); dd.append(g.degree(j))
    b, d = np.array(bb), np.array(dd)
    return dict(rho_bet=float(spearmanr(pop[:nc], b)[0]), rho_deg=float(spearmanr(pop[:nc], d)[0]),
                madrid_or_tokyo_deg=int(d[0]), maxdeg=int(d.max()))


res = {}
for region in ("kanto", "espana"):
    names, lat, lon, pop, xy, center = load_cities(region)
    nc = len(xy)
    z = np.load(os.path.join(OUT, f"rail_{region}.npz"))
    ok = rail_backbone  # noqa (los indices de las ciudades enganchadas se recalculan abajo)
    info = None
    pts, e, ncr, info = rail_backbone(region)
    popr = pop[info["idx_ciudades"]]
    r = {"ferrocarril_NE": cent(pts, e, ncr, popr)}
    r["MST"] = cent(xy, mst_edges(xy), nc, pop)
    r["RNG"] = cent(xy, rng_edges(xy), nc, pop)
    for var in "ABG":
        for g in ("1.5", "2.0"):
            f = os.path.join(OUT, f"net_{region}_{var}_g{g}.npz")
            zz = np.load(f)
            P, E, D, ts = zz["pts"].astype(float), zz["edges"], zz["D"], float(zz["tstar"])
            sel = D >= 0.3 * ts
            r[f"Physarum{var}_g{g}"] = cent(P, E[sel], nc, pop)
    res[region] = r
    print(region)
    for k, v in r.items():
        print(f"  {k:18s} rho(pop,intermediacion)={v['rho_bet']:+.2f} rho(pop,grado)={v['rho_deg']:+.2f} grado_ciudad_mayor={v['madrid_or_tokyo_deg']} gradomax={v['maxdeg']}")
json.dump(res, open(os.path.join(OUT, "e02b_jerarquia.json"), "w"), indent=1)
