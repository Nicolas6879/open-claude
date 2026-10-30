"""Carga de ciudades y ferrocarril (ver datos/descargar.py)."""
import csv, json, os
import numpy as np
import networkx as nx

DATOS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "datos")
R = 6371.0


def load_cities(region):
    rows = list(csv.DictReader(open(os.path.join(DATOS, f"ciudades_{region}.csv"))))
    lat = np.array([float(r["lat"]) for r in rows])
    lon = np.array([float(r["lon"]) for r in rows])
    names = [r["nombre"] for r in rows]
    pop = np.array([int(r["poblacion"]) for r in rows])
    lat0 = np.deg2rad(lat.mean())
    xy = np.c_[np.deg2rad(lon - lon.mean()) * np.cos(lat0) * R, np.deg2rad(lat - lat.mean()) * R]
    return names, lat, lon, pop, xy, (lat.mean(), lon.mean())


def to_xy(lon, lat, center):
    lat0 = np.deg2rad(center[0])
    return np.c_[np.deg2rad(np.asarray(lon) - center[1]) * np.cos(lat0) * R, np.deg2rad(np.asarray(lat) - center[0]) * R]


def rail_backbone(region, snap_km=20.0):
    """Red ferroviaria (Natural Earth 10m) reducida a lo que une ciudades: union de caminos minimos entre pares de
    ciudades conectadas. Devuelve (pts, edges, nc, info) con las primeras nc filas = ciudades (las que enganchan a la red)."""
    names, lat, lon, pop, xy, center = load_cities(region)
    lines = json.load(open(os.path.join(DATOS, f"ferrocarril_{region}.json")))
    idx = {}
    coords = []
    def nid(p):
        if p not in idx:
            idx[p] = len(coords)
            coords.append(p)
        return idx[p]
    g = nx.Graph()
    ll = []
    for pl in lines:
        ids = [nid(tuple(p)) for p in pl]
        ll.append(ids)
    coords = np.array(coords)
    P = to_xy(coords[:, 0], coords[:, 1], center)
    for ids in ll:
        for a, b in zip(ids[:-1], ids[1:]):
            if a != b:
                w = float(np.linalg.norm(P[a] - P[b]))
                if not g.has_edge(a, b) or g[a][b]["w"] > w:
                    g.add_edge(a, b, w=w)
    # separar la componente conexa mayor de cada ciudad
    nc = len(names)
    snap, dist_snap = [], []
    for i in range(nc):
        d = np.linalg.norm(P - xy[i], axis=1)
        j = int(np.argmin(d))
        snap.append(j)
        dist_snap.append(float(d[j]))
    comp_of = {}
    for ci, comp in enumerate(nx.connected_components(g)):
        for v in comp:
            comp_of[v] = ci
    ok = [i for i in range(nc) if dist_snap[i] <= snap_km]
    # mayor componente entre las ciudades enganchadas
    from collections import Counter
    cnt = Counter(comp_of[snap[i]] for i in ok)
    main = cnt.most_common(1)[0][0]
    ok = [i for i in ok if comp_of[snap[i]] == main]
    # union de caminos minimos
    used = set()
    for a in range(len(ok)):
        dist, path = nx.single_source_dijkstra(g, snap[ok[a]], weight="w")
        for b in range(a + 1, len(ok)):
            p = path[snap[ok[b]]]
            for u, v in zip(p[:-1], p[1:]):
                used.add((min(u, v), max(u, v)))
    # construir pts: ciudades enganchadas primero, luego nodos de la via
    nodes = sorted({x for e in used for x in e})
    loc = {v: k + len(ok) for k, v in enumerate(nodes)}
    pts = np.vstack([xy[ok], P[nodes]])
    edges = [(loc[u], loc[v]) for u, v in used]
    for k, i in enumerate(ok):          # tramo de acceso ciudad -> via
        edges.append((k, loc[snap[i]]))
    info = dict(n_ciudades=nc, enganchadas=len(ok), excluidas=[names[i] for i in range(nc) if i not in ok],
                acceso_medio_km=float(np.mean([dist_snap[i] for i in ok])), acceso_max_km=float(max(dist_snap[i] for i in ok)),
                idx_ciudades=ok)
    return pts, np.array(edges, dtype=int), len(ok), info
