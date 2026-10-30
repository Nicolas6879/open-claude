"""E02c: control justo para la malla. Los controles (aristas rectas entre ciudades) se *enrutan por la misma malla*
(camino minimo en la malla entre cada par de ciudades unidas) y se comparan con Physarum-B sobre esa misma malla.
Separa el artefacto del mallado del comportamiento de Physarum."""
import os as _o
for _k in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    _o.environ.setdefault(_k, "1")
import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import numpy as np, pandas as pd
import scipy.sparse as sp
import scipy.sparse.csgraph as csg
from micelio.data import load_cities
from micelio.mesh import make_mesh
from micelio.graphs import city_metrics, mst_edges, delaunay_edges, gabriel_edges, rng_edges, greedy_spanner, greedy_augment_sequence
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def controls_dense(xy):
    res = {"MST": mst_edges(xy), "Delaunay": delaunay_edges(xy), "Gabriel": gabriel_edges(xy), "RNG": rng_edges(xy)}
    for t in np.arange(1.1, 3.01, 0.1):
        res[f"spanner_t{t:.1f}"] = greedy_spanner(xy, float(t))
    seq = greedy_augment_sequence(xy, 40)
    base = [tuple(e) for e in mst_edges(xy).tolist()]
    for k in range(1, len(seq) + 1):
        res[f"MST+{k}"] = np.array(base + seq[:k], dtype=int)
    return res

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "out")


def route(n, medges, mL, pairs, cities):
    A = sp.coo_matrix((np.r_[mL, mL], (np.r_[medges[:, 0], medges[:, 1]], np.r_[medges[:, 1], medges[:, 0]])), shape=(n, n)).tocsr()
    srcs = sorted({a for a, b in pairs})
    dist, pred = csg.dijkstra(A, directed=False, indices=srcs, return_predecessors=True)
    row = {s: i for i, s in enumerate(srcs)}
    used = set()
    for a, b in pairs:
        cur = b
        while cur != a:
            p = pred[row[a], cur]
            used.add((min(cur, p), max(cur, p)))
            cur = p
    return np.array(sorted(used), dtype=int)


if __name__ == "__main__":
    rows = []
    for region in ("kanto", "espana"):
        names, lat, lon, pop, xy, center = load_cities(region)
        nc = len(xy)
        ctl = controls_dense(xy)
        print(region, "controles listos", flush=True)
        for seed in range(6):
            rng = np.random.default_rng(seed)
            ext = xy.max(0) - xy.min(0)
            spacing = np.sqrt(np.prod(ext) / 330.0)
            pts, medges, mL = make_mesh(xy, spacing, rng)
            for name, ed in ctl.items():
                routed = route(len(pts), medges, mL, [tuple(map(int, e)) for e in ed], nc)
                m = city_metrics(pts, routed, nc, rng=np.random.default_rng(3), nsamp=200)
                m.update(region=region, seed=seed, name=name)
                rows.append(m)
            print(region, seed, flush=True)
    df = pd.DataFrame(rows)
    df.to_csv(os.path.join(OUT, "e02c_controles_enrutados.csv"), index=False)
    # comparacion con Physarum B/G (misma malla/semilla) a coste igualado
    ph = pd.read_csv(os.path.join(OUT, "e02_physarum.csv"))
    out = []
    for region in ("kanto", "espana"):
        for seed in range(6):
            c = df[(df.region == region) & (df.seed == seed)]
            # envolvente no dominada MD(TL), conn_q10(TL)
            def env(y, better):
                o = c.sort_values("TL")
                kx, ky = [], []
                best = np.inf if better == "low" else -np.inf
                for a, b in zip(o.TL, o[y]):
                    if (better == "low" and b < best - 1e-9) or (better == "high" and b > best + 1e-9):
                        kx.append(a); ky.append(b); best = b
                return np.array(kx), np.array(ky)
            eM, eC = env("MD", "low"), env("conn_q10", "high")
            p = ph[(ph.region == region) & (ph.seed == seed) & (ph.kind.isin(["physarumB", "physarumG"])) & (ph.kappa == 1.0)]
            for r in p.itertuples():
                fm = np.interp(r.TL, *eM) if eM[0][0] <= r.TL <= eM[0][-1] else np.nan
                fc = np.interp(r.TL, *eC) if eC[0][0] <= r.TL <= eC[0][-1] else np.nan
                out.append(dict(region=region, seed=seed, kind=r.kind, gamma=r.gamma, TL=r.TL, MD=r.MD, conn_q10=r.conn_q10,
                                dMD=r.MD - fm, dCQ=r.conn_q10 - fc))
    o = pd.DataFrame(out)
    o.to_csv(os.path.join(OUT, "e02c_physarum_vs_enrutados.csv"), index=False)
    g = o.dropna().groupby(["region", "kind", "gamma"]).agg(n=("dMD", "size"), dMD=("dMD", "mean"), dMD_sd=("dMD", "std"), dCQ=("dCQ", "mean"), dCQ_sd=("dCQ", "std")).round(3)
    print(g.to_string())
    print("fraccion con detour menor que frontera enrutada:", (o.dropna().dMD < 0).mean(), " robustez mayor:", (o.dropna().dCQ > 0).mean(), "n", len(o.dropna()))
    mst = df[df.name == "MST"].groupby("region").TL.mean()
    print("TL MST enrutado medio por region:", mst.to_dict())
