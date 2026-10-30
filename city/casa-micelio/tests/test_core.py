"""Tests del nucleo. Ejecutar con el python del venv:  python tests/test_core.py"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import numpy as np
import networkx as nx
from micelio.physarum import Physarum, single_pair_flow, allpairs_flows, run_mean_field
from micelio.graphs import dijkstra, delaunay_edges, edge_lengths, contract, city_metrics, mst_edges


def rand_graph(seed, n=30):
    rng = np.random.default_rng(seed)
    pts = rng.random((n, 2))
    e = delaunay_edges(pts)
    return pts, e, edge_lengths(pts, e)


def test_dijkstra_vs_networkx():
    pts, e, L = rand_graph(1)
    g = nx.Graph()
    for (a, b), x in zip(e, L):
        g.add_edge(int(a), int(b), w=float(x))
    d = dijkstra(len(pts), e, L, 0)
    ref = nx.single_source_dijkstra_path_length(g, 0, weight="w")
    assert all(abs(d[k] - v) < 1e-12 for k, v in ref.items())


def test_kirchhoff_conservation():
    pts, e, L = rand_graph(2)
    D = np.random.default_rng(0).uniform(0.2, 1, len(L))
    Q, p = single_pair_flow(len(pts), e, L, D, 3, 11)
    net = np.zeros(len(pts))
    np.add.at(net, e[:, 0], Q)
    np.add.at(net, e[:, 1], -Q)
    want = np.zeros(len(pts)); want[3] = 1; want[11] = -1
    assert np.allclose(net, want, atol=1e-9)
    assert np.max(np.abs(Q)) <= 1 + 1e-9        # un flujo electrico s-t unitario no supera 1 por arista


def test_allpairs_matches_single_pair():
    pts, e, L = rand_graph(3, 20)
    D = np.random.default_rng(1).uniform(0.2, 1, len(L))
    foods = np.array([2, 5, 9, 14])
    Q = allpairs_flows(len(pts), e, L, D, foods)
    iu, ju = np.triu_indices(4, 1)
    for k, (i, j) in enumerate(zip(iu, ju)):
        q, _ = single_pair_flow(len(pts), e, L, D, int(foods[i]), int(foods[j]))
        assert np.allclose(Q[:, k], q, atol=1e-8), k


def test_two_paths_selects_shorter():
    # dos caminos s->t de longitudes 2.0 y 2.4
    e = np.array([[0, 1], [1, 3], [0, 2], [2, 3]])
    L = np.array([1.0, 1.0, 1.2, 1.2])
    ph = Physarum(4, e, L, [0, 3], gamma=1.0, kind="pow", dt=0.1)
    ph.run_pair(0, 3, 400.0)
    assert ph.D[:2].min() > 0.95 and ph.D[2:].max() < 0.05


def test_mean_field_two_foods_equals_pair():
    pts, e, L = rand_graph(4, 15)
    a = Physarum(len(pts), e, L, [0, 7], gamma=1.0, kind="pow", dt=0.1)
    for _ in range(50):
        a.step_pair(0, 7)
    e2, L2, D2, _ = run_mean_field(len(pts), e, L, [0, 7], 1.0, kind="pow", dt=0.1, T=5.0, prune_below=0.0)
    assert np.allclose(a.D, D2, atol=1e-8)


def test_contract_and_metrics():
    # camino 0-1-2-3 (1,2 intermedios) + atajo 0-3: ciudades = 0 y 3
    pts = np.array([[0, 0], [3, 0.0], [1, 0], [2, 0]])      # las ciudades son las 2 primeras filas
    ed = np.array([[0, 2], [2, 3], [3, 1]])
    links = contract(pts, ed, [0, 1])
    assert len(links) == 1 and abs(links[0][2] - 3.0) < 1e-12
    m = city_metrics(pts, ed, 2)
    assert abs(m["MD"] - 1.0) < 1e-12 and m["FT1"] == 0.0 and m["TL"] == 3.0


def test_mst_is_tree():
    pts, e, L = rand_graph(5, 40)
    m = mst_edges(pts)
    assert len(m) == 39 and nx.is_connected(nx.Graph([tuple(x) for x in m.tolist()]))


if __name__ == "__main__":
    n = 0
    for k, f in list(globals().items()):
        if k.startswith("test_"):
            f()
            n += 1
            print("ok", k)
    print(n, "tests ok")
