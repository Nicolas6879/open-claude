"""E02: redes entre ciudades reales: Physarum (completo y malla) vs controles y ferrocarril real."""
import os as _o
for _k in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    _o.environ.setdefault(_k, "1")
import sys, os, json, time, itertools
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import numpy as np
import pandas as pd
from multiprocessing import Pool
from micelio.data import load_cities, rail_backbone
from micelio.graphs import (mst_edges, delaunay_edges, gabriel_edges, rng_edges, greedy_spanner, greedy_augment,
                            edge_lengths, city_metrics)
from micelio.mesh import make_mesh
from micelio.physarum import run_mean_field
from micelio.graphs import overlap, bottleneck_threshold

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "out")
GAMMAS = [1.1, 1.2, 1.35, 1.5, 2.0, 3.0]
KAPPAS = [1.0, 0.3, 0.1, 0.03]       # umbral = kappa * umbral de cuello de botella (el mayor que mantiene todo conectado)


def controls(xy):
    res = {}
    res["MST"] = mst_edges(xy)
    res["Delaunay"] = delaunay_edges(xy)
    res["Gabriel"] = gabriel_edges(xy)
    res["RNG"] = rng_edges(xy)
    for t in (1.15, 1.3, 1.5, 2.0, 3.0):
        res[f"spanner_t{t}"] = greedy_spanner(xy, t)
    for k in (2, 5, 10, 15, 20, 30):
        res[f"MST+{k}"] = greedy_augment(xy, k)
    return res


def load_rail(region):
    f = os.path.join(OUT, f"rail_{region}.npz")
    if not os.path.exists(f):
        return None
    z = np.load(f)
    return z["pts"], z["edges"]


def phys_job(args):
    region, variant, gamma, seed = args
    names, lat, lon, pop, xy, center = load_cities(region)
    nc = len(xy)
    rng = np.random.default_rng(seed)
    ii, jj = np.triu_indices(nc, 1)
    weights = None
    if variant == "A":            # grafo completo de ciudades (sin Steiner)
        pts = xy
        edges = np.c_[ii, jj]
        L = edge_lengths(pts, edges)
    else:                         # malla con puntos de Steiner (B: pares uniformes; G: pares con peso gravitatorio)
        extent = (xy.max(0) - xy.min(0))
        spacing = np.sqrt(np.prod(extent) / 330.0)
        pts, edges, L = make_mesh(xy, spacing, rng)
        if variant == "G":
            d = np.linalg.norm(xy[ii] - xy[jj], axis=1)
            weights = pop[ii] * pop[jj] / d
    n = len(pts)
    t0 = time.time()
    e, Ls, D, info = run_mean_field(n, edges, L, np.arange(nc), gamma, kind="sat", dt=0.2, T=250.0, tol=1e-6, rng=rng,
                                    weights=weights)
    tstar = bottleneck_threshold(n, e, D, np.arange(nc))
    rail = load_rail(region)
    rows = []
    for kap in KAPPAS:
        sel = D >= kap * tstar - 1e-15
        m = city_metrics(pts, e[sel], nc, rng=np.random.default_rng(seed + 7), nsamp=200)
        if rail is not None:
            a, b = overlap(pts, e[sel], rail[0], rail[1])
            m.update(near_rail=a, rail_covered=b)
        m.update(region=region, kind="physarum" + variant, gamma=gamma, kappa=kap, thr=kap * tstar, thr_star=tstar,
                 seed=seed, t_end=info["t"], converged=info["converged"], secs=time.time() - t0, n_edges=int(sel.sum()))
        rows.append(m)
    if seed == 0:
        np.savez_compressed(os.path.join(OUT, f"net_{region}_{variant}_g{gamma}.npz"), pts=pts.astype(np.float32),
                            edges=e, D=D.astype(np.float32), tstar=tstar)
    return rows


def ctrl_job(region):
    names, lat, lon, pop, xy, center = load_cities(region)
    nc = len(xy)
    rows = []
    pts, e, ncr, info = rail_backbone(region)
    np.savez_compressed(os.path.join(OUT, f"rail_{region}.npz"), pts=pts.astype(np.float32), edges=e)
    m = city_metrics(pts, e, ncr, rng=np.random.default_rng(1), nsamp=400)
    m.update(region=region, kind="rail", name="ferrocarril_NE", info=json.dumps(info), near_rail=1.0, rail_covered=1.0)
    rows.append(m)
    for name, ed in controls(xy).items():
        m = city_metrics(xy, ed, nc, rng=np.random.default_rng(1), nsamp=400)
        a, b = overlap(xy, ed, pts, e)
        m.update(region=region, kind="control", name=name, near_rail=a, rail_covered=b)
        rows.append(m)
    return rows


if __name__ == "__main__":
    quick = len(sys.argv) > 1 and sys.argv[1] == "quick"
    regions = ["kanto", "espana"]
    seeds = range(2) if quick else range(6)
    jobs = [(r, v, g, s) for r in regions for v in "ABG" for g in GAMMAS for s in (range(3) if v == "A" else seeds)]
    if quick:
        jobs = [(r, v, g, s) for r in regions for v in "BG" for g in (1.0, 2.0) for s in range(1)]
    with Pool(2) as p:
        c = p.map(ctrl_job, regions)
        ctrl = pd.DataFrame([x for r in c for x in r])
        print(ctrl.drop(columns=["info"], errors="ignore").to_string())
        ctrl.to_csv(os.path.join(OUT, "e02_controles.csv"), index=False)
        res = p.map(phys_job, jobs, chunksize=1)
    df = pd.DataFrame([x for r in res for x in r])
    df.to_csv(os.path.join(OUT, "e02_quick.csv" if quick else "e02_physarum.csv"), index=False)
    print(df.groupby(["region", "kind", "gamma", "kappa"])[["TL", "MD", "FT1", "conn_q10", "n_edges", "njunc", "near_rail", "secs"]].mean().round(3).to_string())
