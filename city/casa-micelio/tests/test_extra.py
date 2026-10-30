"""Tests de datos, reservorio y competencia. Ejecutar con el python del venv:  python tests/test_extra.py"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import numpy as np
from micelio.data import load_cities
from micelio.graphs import delaunay_edges, edge_lengths, overlap, bottleneck_threshold, greedy_spanner, mst_edges, city_metrics
from micelio.reservoir import PhysarumReservoir, ESN, narma10, ridge_fit, ridge_pred
from micelio.compete import compete


def test_city_data():
    for reg, n in (("kanto", 37), ("espana", 40)):
        names, lat, lon, pop, xy, c = load_cities(reg)
        assert len(names) == n and xy.shape == (n, 2) and (pop > 50000).all()
    names, lat, lon, pop, xy, c = load_cities("kanto")
    assert names[0] == "Tokyo" and abs(lat[0] - 35.6895) < 1e-3     # coincide con Wikidata Q1490 (medido)
    assert "Suginami" not in load_cities("kanto")[0]               # coordenada erronea de GeoNames, excluida


def test_spanner_property():
    rng = np.random.default_rng(0)
    pts = rng.random((25, 2))
    t = 1.5
    e = greedy_spanner(pts, t)
    m = city_metrics(pts, e, len(pts))
    # el spanner voraz garantiza dist_red <= t * recta para TODO par => razon media <= t
    assert m["MD"] <= t + 1e-9 and m["connected"]


def test_overlap_and_bottleneck():
    pts = np.array([[0, 0], [10, 0], [20, 0.0]])
    e = np.array([[0, 1], [1, 2]])
    a, b = overlap(pts, e, pts, e, tol=1.0)
    assert a == 1.0 and b == 1.0
    a, b = overlap(pts, e, pts + np.array([0, 50.0]), e, tol=1.0)
    assert a == 0.0
    D = np.array([0.9, 0.2])
    assert abs(bottleneck_threshold(3, e, D, [0, 2]) - 0.2) < 1e-12


def test_reservoir_shapes_and_determinism():
    r1 = PhysarumReservoir(n=15, gamma=0.5, r_dt=0.1, gain=0.1, bias=1.0, seed=1, spread=1.0)
    r2 = PhysarumReservoir(n=15, gamma=0.5, r_dt=0.1, gain=0.1, bias=1.0, seed=1, spread=1.0)
    u = np.random.default_rng(0).uniform(-1, 1, 50)
    P1, D1 = r1.run(u)
    P2, D2 = r2.run(u)
    assert P1.shape == (50, 15) and np.allclose(P1, P2) and np.all(np.isfinite(D1))
    X = ESN(N=20, seed=2).run(u)
    assert X.shape == (50, 20) and np.abs(X).max() <= 1.0


def test_narma_and_ridge():
    u, y = narma10(500, np.random.default_rng(0))
    assert np.all(np.isfinite(y)) and y.max() < 1.5
    X = np.random.default_rng(1).normal(size=(200, 3))
    w = ridge_fit(X, X @ np.array([1.0, -2.0, 0.5]) + 3, 1e-9)
    assert np.allclose(w, [1, -2, 0.5, 3], atol=1e-5)


def test_compete_symmetry_and_independence():
    rng = np.random.default_rng(0)
    pts = rng.random((30, 2))
    e = delaunay_edges(pts)
    L = edge_lengths(pts, e)
    A, B = [0, 1, 2], [3, 4, 5]
    # lam=0: cada especie evoluciona como si estuviera sola (mismos D que una corrida con las mismas comidas)
    DA, DB, _ = compete(len(pts), e, L, A, B, 1.5, 0.0, 0.0, T=20, dt=0.25)
    DA2, DB2, _ = compete(len(pts), e, L, A, B, 1.5, 0.0, 1.0, T=20, dt=0.25)   # mu no debe importar si lam=0
    assert np.allclose(DA, DA2) and np.allclose(DB, DB2)
    # simetria: mismas comidas para A y B y misma CI => D^A == D^B
    DA3, DB3, _ = compete(len(pts), e, L, A, A, 1.5, 1.0, 0.5, T=20, dt=0.25)
    assert np.allclose(DA3, DB3, atol=1e-9)


if __name__ == "__main__":
    n = 0
    for k, f in list(globals().items()):
        if k.startswith("test_"):
            f()
            n += 1
            print("ok", k)
    print(n, "tests ok")
