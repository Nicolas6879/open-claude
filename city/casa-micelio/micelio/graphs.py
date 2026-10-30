"""Generadores de grafos, controles y metricas de red."""
import heapq
import numpy as np
import networkx as nx
from scipy.spatial import Delaunay


def dijkstra(n, edges, w, s):
    adj = [[] for _ in range(n)]
    for (a, b), x in zip(edges, w):
        adj[a].append((b, x))
        adj[b].append((a, x))
    dist = np.full(n, np.inf)
    dist[s] = 0
    pq = [(0.0, s)]
    while pq:
        d, a = heapq.heappop(pq)
        if d > dist[a]:
            continue
        for b, x in adj[a]:
            nd = d + x
            if nd < dist[b]:
                dist[b] = nd
                heapq.heappush(pq, (nd, b))
    return dist


def delaunay_edges(pts):
    tri = Delaunay(pts)
    es = set()
    for s in tri.simplices:
        for i in range(3):
            a, b = int(s[i]), int(s[(i + 1) % 3])
            es.add((min(a, b), max(a, b)))
    return np.array(sorted(es), dtype=int)


def edge_lengths(pts, edges):
    return np.linalg.norm(pts[edges[:, 0]] - pts[edges[:, 1]], axis=1)


def grid_maze(k, braid, rng, jitter=0.2):
    """Laberinto k x k de celdas: arbol aleatorio (DFS) + 'braid' fraccion de paredes extra abiertas.
    Devuelve n, edges, L (longitud 1+jitter*U, sin empates), pts."""
    G = nx.grid_2d_graph(k, k)
    idx = {c: i for i, c in enumerate(sorted(G.nodes()))}
    # arbol de expansion aleatorio con pesos aleatorios
    for a, b in G.edges():
        G[a][b]["w"] = rng.random()
    T = nx.minimum_spanning_tree(G, weight="w")
    keep = set(map(frozenset, T.edges()))
    extra = [e for e in G.edges() if frozenset(e) not in keep]
    rng.shuffle(extra)
    nb = int(braid * len(extra))
    keep |= set(map(frozenset, extra[:nb]))
    edges = np.array([[idx[a], idx[b]] for a, b in map(tuple, keep)], dtype=int)
    L = 1.0 + jitter * rng.random(len(edges))
    pts = np.array([c for c, _ in sorted(idx.items(), key=lambda kv: kv[1])], dtype=float)
    return len(idx), edges, L, pts


# ---------------------------------------------------------------- controles
def mst_edges(pts):
    """Arbol de expansion minimo euclidiano (sobre Delaunay, que lo contiene)."""
    de = delaunay_edges(pts)
    L = edge_lengths(pts, de)
    g = nx.Graph()
    for (a, b), x in zip(de, L):
        g.add_edge(int(a), int(b), w=float(x))
    T = nx.minimum_spanning_tree(g, weight="w")
    return np.array(sorted((min(a, b), max(a, b)) for a, b in T.edges()), dtype=int)


def gabriel_edges(pts):
    de = delaunay_edges(pts)
    keep = []
    for a, b in de:
        m = (pts[a] + pts[b]) / 2
        r = np.linalg.norm(pts[a] - pts[b]) / 2
        d = np.linalg.norm(pts - m, axis=1)
        d[[a, b]] = np.inf
        if np.all(d >= r - 1e-12):
            keep.append((a, b))
    return np.array(keep, dtype=int)


def rng_edges(pts):
    de = delaunay_edges(pts)
    keep = []
    for a, b in de:
        dab = np.linalg.norm(pts[a] - pts[b])
        d = np.maximum(np.linalg.norm(pts - pts[a], axis=1), np.linalg.norm(pts - pts[b], axis=1))
        d[[a, b]] = np.inf
        if np.all(d >= dab - 1e-12):
            keep.append((a, b))
    return np.array(keep, dtype=int)


def greedy_spanner(pts, t):
    """Spanner voraz (Althofer et al.): aristas por longitud; se anade (a,b) si la distancia actual > t*|ab|."""
    n = len(pts)
    ii, jj = np.triu_indices(n, 1)
    d = np.linalg.norm(pts[ii] - pts[jj], axis=1)
    order = np.argsort(d)
    g = nx.Graph()
    g.add_nodes_from(range(n))
    edges = []
    for k in order:
        a, b = int(ii[k]), int(jj[k])
        try:
            cur = nx.dijkstra_path_length(g, a, b, weight="w", ) if nx.has_path(g, a, b) else np.inf
        except nx.NetworkXNoPath:
            cur = np.inf
        if cur > t * d[k]:
            g.add_edge(a, b, w=float(d[k]))
            edges.append((a, b))
    return np.array(edges, dtype=int)


def greedy_augment(pts, k_extra, base=None):
    """MST + k aristas de Delaunay elegidas vorazmente por mayor reduccion de la distancia media por unidad de longitud."""
    n = len(pts)
    de = delaunay_edges(pts)
    L = edge_lengths(pts, de)
    cur = set(map(tuple, (mst_edges(pts) if base is None else base).tolist()))
    straight = np.linalg.norm(pts[:, None] - pts[None], axis=2) + np.eye(n)

    def meanratio(es):
        g = nx.Graph()
        g.add_nodes_from(range(n))
        for a, b in es:
            g.add_edge(a, b, w=float(np.linalg.norm(pts[a] - pts[b])))
        d = dict(nx.all_pairs_dijkstra_path_length(g, weight="w"))
        M = np.array([[d[i].get(j, np.inf) for j in range(n)] for i in range(n)])
        iu = np.triu_indices(n, 1)
        return float(np.mean(M[iu] / straight[iu]))

    base_val = meanratio(cur)
    for _ in range(k_extra):
        best, be = None, 0
        cand = [(tuple(e), l) for e, l in zip(de.tolist(), L) if tuple(e) not in cur]
        for e, l in cand:
            val = meanratio(cur | {e})
            gain = (base_val - val) / l
            if gain > be:
                best, be, bv = e, gain, val
        if best is None:
            break
        cur.add(best)
        base_val = bv
    return np.array(sorted(cur), dtype=int)


# ---------------------------------------------------------------- metricas
def contract(pts, edges, terminals):
    """Contrae cadenas de nodos de grado 2 no terminales en 'enlaces'. Devuelve lista de (a,b,longitud) entre
    nodos terminales/junciones (indices originales)."""
    g = nx.Graph()
    for a, b in edges:
        g.add_edge(int(a), int(b), w=float(np.linalg.norm(pts[a] - pts[b])))
    term = set(int(t) for t in terminals)
    key = {v for v in g.nodes if g.degree(v) != 2 or v in term}
    seen = set()
    links = []
    for v in key:
        for nb in g.neighbors(v):
            if (v, nb) in seen:
                continue
            path = [v, nb]
            tot = g[v][nb]["w"]
            while path[-1] not in key:
                cur, prev = path[-1], path[-2]
                nxt = [x for x in g.neighbors(cur) if x != prev]
                if not nxt:
                    break
                path.append(nxt[0])
                tot += g[cur][nxt[0]]["w"]
            seen.add((path[0], path[1]))
            seen.add((path[-1], path[-2]))
            if path[-1] in key and path[0] != path[-1]:
                links.append((path[0], path[-1], tot))
    # quitar enlaces duplicados (se recorren dos veces)
    uniq = {}
    for a, b, l in links:
        k = (min(a, b), max(a, b), round(l, 9))
        uniq[k] = (k[0], k[1], l)
    return list(uniq.values())


def city_metrics(pts, edges, nc, rng=None, nsamp=300, qs=(0.05, 0.10, 0.20), thr_note=None):
    """pts: todos los nodos (las primeras nc filas son ciudades). edges: aristas del grafo.
    Todo se calcula sobre el grafo de *enlaces* (cadenas de grado 2 contraidas).
    Devuelve dict: TL (longitud total), MD (razon media camino/recta entre pares de ciudades conectadas),
    FT1 (fraccion de enlaces cuya perdida deja a todas las ciudades conectadas), conn_qXX (fraccion media de pares
    de ciudades conectados cuando cada enlace falla con prob. q), nlinks, njunc (junciones de Steiner), cycles."""
    edges = np.asarray(edges, dtype=int)
    cities = list(range(nc))
    if len(edges) == 0:
        return dict(TL=0.0, MD=np.inf, FT1=np.nan, nlinks=0, njunc=0, connected=False, cycles=0)
    links = contract(pts, edges, cities)
    nl = len(links)
    TL = float(sum(l for _, _, l in links))
    g = nx.Graph()
    g.add_nodes_from(cities)
    for a, b, l in links:
        if not g.has_edge(a, b) or g[a][b]["w"] > l:
            g.add_edge(a, b, w=l)
    straight = np.linalg.norm(pts[:nc, None] - pts[None, :nc], axis=2)
    ratios = []
    for i in range(nc):
        d = nx.single_source_dijkstra_path_length(g, i, weight="w")
        for j in range(i + 1, nc):
            if j in d:
                ratios.append(d[j] / straight[i, j])
    npairs = nc * (nc - 1) / 2
    MD = float(np.mean(ratios)) if len(ratios) == npairs else (float(np.mean(ratios)) if ratios else np.inf)
    junc = len({v for a, b, _ in links for v in (a, b)} - set(cities))
    ncomp = nx.number_connected_components(g)
    cycles = nl - g.number_of_nodes() + ncomp

    def conn_pairs(keep_mask):
        h = nx.Graph()
        h.add_nodes_from(cities)
        for (a, b, _), k in zip(links, keep_mask):
            if k:
                h.add_edge(a, b)
        lab = {}
        for ci, comp in enumerate(nx.connected_components(h)):
            for v in comp:
                lab[v] = ci
        cnt = np.bincount([lab[c] for c in cities])
        return float((cnt * (cnt - 1) / 2).sum() / npairs)

    ok1 = 0
    for k in range(nl):
        m = np.ones(nl, bool)
        m[k] = False
        ok1 += conn_pairs(m) >= 1.0 - 1e-12
    out = dict(TL=TL, MD=MD, nlinks=nl, njunc=junc, connected=bool(len(ratios) == npairs), cycles=int(cycles),
               FT1=float(ok1 / max(nl, 1)))
    rng = rng or np.random.default_rng(0)
    for q in qs:
        v = [conn_pairs(rng.random(nl) > q) for _ in range(nsamp)]
        out[f"conn_q{int(round(q*100)):02d}"] = float(np.mean(v))
    return out


def densify(pts, edges, step=2.0):
    out = []
    for a, b in np.asarray(edges, int):
        d = np.linalg.norm(pts[a] - pts[b])
        k = max(int(np.ceil(d / step)), 1)
        t = (np.arange(k + 1) / k)[:, None]
        out.append(pts[a] * (1 - t) + pts[b] * t)
    return np.vstack(out) if out else np.zeros((0, 2))


def overlap(ptsA, edgesA, ptsB, edgesB, tol=7.0, step=2.0):
    """(fraccion de A a menos de tol km de B, fraccion de B a menos de tol km de A), aproximado por muestreo."""
    from scipy.spatial import cKDTree
    A = densify(ptsA, edgesA, step)
    B = densify(ptsB, edgesB, step)
    if len(A) == 0 or len(B) == 0:
        return 0.0, 0.0
    dA = cKDTree(B).query(A)[0]
    dB = cKDTree(A).query(B)[0]
    return float(np.mean(dA <= tol)), float(np.mean(dB <= tol))


def bottleneck_threshold(n, edges, D, terminals):
    """Mayor umbral t tal que {D>=t} mantiene conectados todos los terminales (camino de cuello de botella)."""
    import scipy.sparse as sp
    import scipy.sparse.csgraph as csg
    order = np.sort(np.unique(D))
    lo, hi = 0, len(order) - 1
    def ok(t):
        m = D >= t
        A = sp.coo_matrix((np.ones(m.sum()), (edges[m, 0], edges[m, 1])), shape=(n, n))
        nc_, lab = csg.connected_components(A, directed=False)
        return len(set(lab[terminals])) == 1
    if not ok(order[0]):
        return 0.0
    while lo < hi:
        mid = (lo + hi + 1) // 2
        if ok(order[mid]):
            lo = mid
        else:
            hi = mid - 1
    return float(order[lo])


def greedy_augment_sequence(pts, kmax):
    """Orden de aristas que anade el voraz MST+k (los conjuntos para cada k son prefijos de esta secuencia)."""
    n = len(pts)
    de = delaunay_edges(pts)
    L = edge_lengths(pts, de)
    cur = set(map(tuple, mst_edges(pts).tolist()))
    straight = np.linalg.norm(pts[:, None] - pts[None], axis=2) + np.eye(n)
    iu = np.triu_indices(n, 1)

    def meanratio(es):
        g = nx.Graph()
        g.add_nodes_from(range(n))
        for a, b in es:
            g.add_edge(a, b, w=float(np.linalg.norm(pts[a] - pts[b])))
        d = dict(nx.all_pairs_dijkstra_path_length(g, weight="w"))
        M = np.array([[d[i].get(j, np.inf) for j in range(n)] for i in range(n)])
        return float(np.mean(M[iu] / straight[iu]))

    base = meanratio(cur)
    seq = []
    for _ in range(kmax):
        best, bg, bv = None, 0.0, None
        for e, l in zip(map(tuple, de.tolist()), L):
            if e in cur:
                continue
            v = meanratio(cur | {e})
            gain = (base - v) / l
            if gain > bg:
                best, bg, bv = e, gain, v
        if best is None:
            break
        cur.add(best)
        seq.append(best)
        base = bv
    return seq
