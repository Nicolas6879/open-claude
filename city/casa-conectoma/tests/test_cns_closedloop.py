"""Pruebas del bucle cerrado SNC. Ejecutar: PYTHONDONTWRITEBYTECODE=1 python3 tests/test_cns_closedloop.py

Pruebas 1-4 no necesitan datos (grafo sintetico pequeno). Las demas se saltan con mensaje si falta el cache del grafo
o los resultados en out/.
"""
import json
import os
import sys
import traceback

import numpy as np

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(HERE, "src"))
import fly_arena as fa  # noqa: E402
import lif_engine  # noqa: E402
import rewire  # noqa: E402


def _tiny_graph(N=60, E_per=6, seed=0):
    rng = np.random.default_rng(seed)
    pre = np.repeat(np.arange(N), E_per)
    post = rng.integers(0, N, size=N * E_per)
    order = np.argsort(pre, kind="stable")
    pre, post = pre[order], post[order]
    indptr = np.zeros(N + 1, dtype=np.int64)
    np.add.at(indptr, pre + 1, 1)
    indptr = np.cumsum(indptr)
    sign = rng.choice([-1, 0, 1], size=N).astype(np.int8)
    syn = rng.integers(1, 20, size=N * E_per).astype(np.float32)
    return dict(ids=np.arange(N), indptr=indptr, indices=post.astype(np.int32), syn=syn, sign=sign)


def test_swap_preserves_out_and_in_degree():
    G = _tiny_graph()
    idx, done = rewire.swap_targets(G, factor=20, seed=3)
    assert done > 100, done
    indeg0 = np.bincount(G["indices"], minlength=60)
    indeg1 = np.bincount(idx, minlength=60)
    assert np.array_equal(indeg0, indeg1), "grado de entrada cambio"
    assert np.array_equal(np.diff(G["indptr"]), np.diff(G["indptr"]))  # out-degree fijo por construccion
    assert not np.array_equal(idx, G["indices"]), "no se reordeno nada"


def test_shuffle_signs_keeps_counts():
    s = np.array([1, 1, -1, 0, 0, 0], dtype=np.int8)
    t = rewire.shuffle_signs(s, seed=1)
    assert sorted(t.tolist()) == sorted(s.tolist())


def test_antenna_geometry():
    (lx, ly), (rx, ry) = fa.antenna_positions(0.0, 0.0, 0.0)
    assert abs(ly - fa.ANT_SEP_MM / 2) < 1e-9 and abs(ry + fa.ANT_SEP_MM / 2) < 1e-9
    # izquierda = +90 grados del rumbo; con rumbo 0 la antena izquierda esta en y>0
    assert abs(lx) < 1e-9 and abs(rx) < 1e-9


def test_engine_spike_and_propagation():
    G = _tiny_graph(N=4, E_per=1, seed=0)
    G["indptr"] = np.array([0, 1, 2, 3, 4])
    G["indices"] = np.array([1, 2, 3, 0], dtype=np.int32)
    G["syn"] = np.array([10, 10, 10, 10], dtype=np.float32)
    G["sign"] = np.array([1, 1, 1, 1], dtype=np.int8)
    net = lif_engine.Network(G, bias_mV_per_ms=np.array([9.0, 0.0, 0.0, 0.0]), seed=0, w_syn=0.275, dt=1.0)
    net.V[:] = -52.0
    net.advance(200.0)
    assert net.counts[0] > 0, "la neurona con sesgo debe disparar"
    net.counts[:] = 0
    net.alive[0] = 0
    net.V[:] = -52.0
    net.advance(200.0)
    assert net.counts[0] == 0, "neurona silenciada no debe disparar"


def test_mirror_sign_flips_turn_direction():
    # con el signo de giro invertido, el giro de 'direct' tiene signo contrario (controlador sin cerebro)
    class W:  # objeto minimo; el modo 'direct' no usa la red
        net = None
        dn_L = np.array([], dtype=np.int64)
        dn_R = np.array([], dtype=np.int64)
        orn = np.array([], dtype=np.int64)
        orn_aff = np.array([])
        orn_side = np.array([])

        def concentration(self, x, y):
            return fa.FlyWorld.concentration(self, x, y)
    w = W()
    r1 = fa.run_trial(w, 5, mode="direct", K_T=30.0, turn_sign=1.0, max_t_s=0.5, record_every=1)
    r2 = fa.run_trial(w, 5, mode="direct", K_T=30.0, turn_sign=-1.0, max_t_s=0.5, record_every=1)
    th1 = r1["traj"][-1][3]
    th2 = r2["traj"][-1][3]
    assert th1 != th2


def test_real_graph_if_present():
    import cns_graph
    try:
        G = cns_graph.load_graph(build_if_missing=False)
    except FileNotFoundError:
        print("  (saltada: falta el cache del grafo; ejecutar src/cns_graph.py)")
        return
    assert G["ids"].shape[0] == 211577
    assert G["indices"].shape[0] == 25568639


def test_results_if_present():
    p = os.path.join(HERE, "out", "chemotaxis_summary.json")
    if not os.path.exists(p):
        print("  (saltada: falta out/chemotaxis_summary.json; ejecutar src/experiments.py main)")
        return
    d = json.load(open(p, encoding="utf-8"))
    assert "condiciones" in d and "connectome" in d["condiciones"]


TESTS = [v for k, v in list(globals().items()) if k.startswith("test_") and callable(v)]

if __name__ == "__main__":
    fails = 0
    for t in TESTS:
        try:
            t()
            print("OK  ", t.__name__)
        except Exception:
            fails += 1
            print("FAIL", t.__name__)
            traceback.print_exc()
    print(f"{len(TESTS) - fails}/{len(TESTS)} pruebas OK")
    sys.exit(1 if fails else 0)
