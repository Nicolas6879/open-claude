"""Hubs y cuellos de botella sensoriomotores: uso de caminos mas cortos ORN -> DN.

Coste de arista = 1 / n_sinapsis (sinapsis fuertes = caminos cortos). Para una muestra de ORN, se calcula el
camino mas corto a cada DN y se cuenta cuantas veces pasa cada neurona (conteo de uso, no betweenness exacta).
"""
import numpy as np
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import dijkstra


def path_usage(G, n_src=40, seed=0):
    N = G["ids"].shape[0]
    M = csr_matrix((1.0 / G["syn"].astype(np.float64), G["indices"].astype(np.int32), G["indptr"]), shape=(N, N))
    types = G["types"].astype(str)
    supers = G["superclasses"].astype(str)
    orn = np.nonzero(np.char.startswith(types, "ORN_"))[0]
    dn = np.nonzero(supers == "descending_neuron")[0]
    rng = np.random.default_rng(seed)
    src = rng.choice(orn, size=min(n_src, len(orn)), replace=False)
    dist, pred = dijkstra(M, directed=True, indices=src, return_predecessors=True)
    usage = np.zeros(N, dtype=np.int64)
    reach = 0
    for si, s in enumerate(src):
        pr = pred[si]
        for t in dn:
            if not np.isfinite(dist[si, t]):
                continue
            reach += 1
            v = t
            guard = 0
            while v != s and v >= 0 and guard < N:
                usage[v] += 1
                v = pr[v]
                guard += 1
    return usage, dict(n_src=int(len(src)), n_dn=int(len(dn)), pairs_reachable=int(reach),
                       pairs_total=int(len(src) * len(dn)))


def rank_hubs(G, usage, top=50):
    types = G["types"].astype(str)
    classes = G["classes"].astype(str)
    supers = G["superclasses"].astype(str)
    excl = np.char.startswith(types, "ORN_") | (supers == "descending_neuron")
    u = usage.copy()
    u[excl] = 0
    order = np.argsort(-u)[:top]
    out = []
    outdeg = np.diff(G["indptr"])
    for i in order:
        if u[i] == 0:
            break
        out.append(dict(id=int(G["ids"][i]), type=types[i], cls=classes[i], superclass=supers[i],
                        usage=int(u[i]), out_degree=int(outdeg[i])))
    return out
