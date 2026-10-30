"""E01: Physarum de un par s-t contra Dijkstra. Barridos de gamma, forma de f y paso dt."""
import os as _o
for _k in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    _o.environ.setdefault(_k, "1")
import sys, os, json, time
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import numpy as np
from multiprocessing import Pool
from micelio.physarum import Physarum, single_pair_flow
from micelio.graphs import dijkstra, delaunay_edges, edge_lengths, grid_maze
import networkx as nx

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "out")


def make_case(kind, seed):
    rng = np.random.default_rng(1000 + seed)
    if kind == "delaunay":
        n = int(rng.integers(25, 61))
        pts = rng.random((n, 2))
        edges = delaunay_edges(pts)
        L = edge_lengths(pts, edges)
        d = np.linalg.norm(pts[:, None] - pts[None], axis=2)
        s, t = np.unravel_index(np.argmax(d), d.shape)
        return n, edges, L, int(s), int(t)
    n, edges, L, pts = grid_maze(15, 0.15, rng)
    s, t = 0, n - 1
    return n, edges, L, s, t


def judge(n, edges, L, s, t, D):
    thr = 0.1 * D.max()
    sel = D > thr
    g = nx.Graph()
    for (a, b), x, ok in zip(edges, L, sel):
        if ok:
            g.add_edge(int(a), int(b), w=x)
    dist = dijkstra(n, edges, L, s)
    if s not in g or t not in g or not nx.has_path(g, s, t):
        return dict(ok=False, nedges=int(sel.sum()), conn=False, excess=np.nan)
    is_path = (g.number_of_edges() == g.number_of_nodes() - 1 and max(dict(g.degree()).values()) <= 2
               and nx.is_connected(g))
    tot = sum(d["w"] for *_, d in g.edges(data=True))
    exact = is_path and abs(tot - dist[t]) < 1e-6 * dist[t]
    # caso 'camino pero no minimo' o 'con bucles'
    return dict(ok=bool(exact), nedges=int(sel.sum()), conn=True, excess=float(tot / dist[t] - 1))


def winner_is_shortest(n, edges, L, s, t, D):
    """Camino 'mas ancho' (maximiza el minimo D) == camino de Dijkstra? (separa 'sin converger del todo' de 'bloqueado en otro camino')"""
    g = nx.Graph()
    for (a, b), x, d in zip(edges, L, D):
        g.add_edge(int(a), int(b), w=float(x), d=float(d))
    sp = nx.dijkstra_path(g, s, t, weight="w")
    # widest path: Dijkstra modificado (coste = -min D)
    import heapq
    best = {s: np.inf}
    prev = {}
    pq = [(-np.inf, s)]
    while pq:
        b, u = heapq.heappop(pq)
        b = -b
        if b < best.get(u, -1):
            continue
        for v in g[u]:
            nb = min(b, g[u][v]["d"])
            if nb > best.get(v, -1):
                best[v] = nb
                prev[v] = u
                heapq.heappush(pq, (-nb, v))
    path = [t]
    while path[-1] != s:
        path.append(prev[path[-1]])
    return path[::-1] == sp or path == sp


def run_one(args):
    kind, seed, gamma, f, dt, T = args
    n, edges, L, s, t = make_case(kind, seed)
    ph = Physarum(n, edges, L, [s, t], gamma=gamma, kind=f, dt=dt)
    D_prev = None
    tconv = np.nan
    nsteps = int(T / dt)
    for k in range(nsteps):
        Dold = ph.D.copy()
        Q = ph.step_pair(s, t)
        ph.D = np.maximum(ph.D, 0.0)   # evita D<0 con dt grande
        if np.max(np.abs(ph.D - Dold)) / dt < 1e-6:
            tconv = ph.t
            break
    r = judge(n, edges, L, s, t, ph.D)
    r["win_ok"] = winner_is_shortest(n, edges, L, s, t, ph.D)
    # brecha relativa entre el mejor y el segundo mejor camino simple
    g = nx.Graph()
    for (a, b), x in zip(edges, L):
        g.add_edge(int(a), int(b), weight=float(x))
    it = nx.shortest_simple_paths(g, s, t, weight="weight")
    p1 = next(it); p2 = next(it, None)
    pl = lambda p: sum(g[a][b]["weight"] for a, b in zip(p[:-1], p[1:]))
    r["gap"] = float(pl(p2) / pl(p1) - 1) if p2 else np.nan
    r.update(kind=kind, seed=seed, gamma=gamma, f=f, dt=dt, tconv=float(tconv), n=n)
    return r


if __name__ == "__main__":
    quick = len(sys.argv) > 1 and sys.argv[1] == "quick"
    nd, nm = (6, 3) if quick else (60, 20)
    T = 200.0
    jobs = []
    for kind, ns in (("delaunay", nd), ("maze", nm)):
        for seed in range(ns):
            for f, gam in [("pow", 1.0), ("pow", 0.7), ("pow", 1.5), ("sat", 1.0), ("sat", 2.0), ("sat", 3.0), ("sat", 0.7)]:
                jobs.append((kind, seed, gam, f, 0.25, T))
            for dt in (0.05, 0.25, 1.0, 2.0):
                jobs.append((kind, seed, 1.0, "pow", dt, T))
    for kind, ns in (("delaunay", nd), ("maze", nm)):
        for seed in range(ns):
            jobs.append((kind, seed, 1.0, "pow", 1.0, 3000.0))
    t0 = time.time()
    with Pool(2) as p:
        res = p.map(run_one, jobs, chunksize=4)
    print("tiempo", time.time() - t0)
    json.dump(res, open(os.path.join(OUT, "e01_quick.json" if quick else "e01_validacion.json"), "w"))
    import pandas as pd
    df = pd.DataFrame(res)
    df["Tmax"] = [j[5] for j in jobs]
    g = df.groupby(["f", "gamma", "dt", "Tmax", "kind"]).agg(n=("ok", "size"), exito=("ok", "mean"), ganador=("win_ok", "mean"), nedges=("nedges", "mean"),
                                                     tconv=("tconv", "median"), noconv=("tconv", lambda x: x.isna().mean()))
    print(g.to_string())
