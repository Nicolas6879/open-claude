"""Pruebas de casa-mb-real.  Ejecutar:  PYTHONDONTWRITEBYTECODE=1 python tests/test_mb_real.py
(con el venv que tenga numpy y numba; sin numba corre en Python puro, lento pero valido para las pruebas unitarias).
Las pruebas con datos reales se saltan si faltan los feather o pyarrow."""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "src"))
import numpy as np

import compartments as comp
import engine as eng
import network as nw

PASS, SKIP = [], []


def ok(name):
    PASS.append(name)
    print("OK  ", name)


def tiny_net(w_pn=40.0, w_kc=8.0):
    """0 = PN (generador), 1-2 = KC, 3 = MBON, 4 = DAN (generador)."""
    n = 5
    ptr = np.array([0, 1, 1, 1, 1, 1], np.int64)           # PN -> KC1
    post = np.array([1], np.int64)
    w = np.array([w_pn], np.float32)
    kptr = np.array([0, 1, 2], np.int64)                    # KC1->MBON, KC2->MBON
    kpost = np.array([3, 3], np.int64)
    kw0 = np.array([w_kc, w_kc], np.float32)
    dptr = np.array([0, 1], np.int64); dpost = np.array([0], np.int64); dg = np.array([1.0], np.float32)
    return n, ptr, post, w, kptr, kpost, kw0, dptr, dpost, dg


def run(net, pn_on, pn_off, dan_on, dan_off, plastic, eta=2.0, theta=0.3, seed=1, nsteps=3000, silenced=None, pn_hz=100.0):
    n, ptr, post, w, kptr, kpost, kw0, dptr, dpost, dg = net
    kf = np.ones(2, np.float32)
    g_idx = np.array([0, 4], np.int64)
    g_r0 = np.zeros(2, np.float32); g_r1 = np.array([pn_hz, 50.0], np.float32)
    g_on = np.array([pn_on, dan_on], np.int64); g_off = np.array([pn_off, dan_off], np.int64)
    counts = np.zeros(n, np.int32); kcp = np.zeros(2, np.float32)
    sil = np.zeros(n, np.bool_) if silenced is None else silenced
    eng.run_trial(seed, nsteps, n, 1, 4, sil, ptr, post, w, 1, 2, kptr, kpost, kw0, kf, g_idx, g_r0, g_r1, g_on, g_off, 10.0,
                  0, nsteps, 4, 1, dptr, dpost, dg, 50.0, plastic, eta, theta, 500.0, 150.0, counts, kcp, 3, 1)
    return counts, kf, kcp


def test_parse_instance():
    assert comp.parse_instance("MBON01(y5B'2a)_R") == (("g5", "b'2"), ())
    assert comp.parse_instance("MBON05(y4>y1y2)_R") == (("g4",), ("g1", "g2"))
    assert comp.parse_instance("PAM07(y4<y1y2)_L") == (("g4",), ("g1", "g2"))
    assert comp.parse_instance("MBON26(b'2d)_R") == (("b'2",), ())
    assert comp.parse_instance("MBON19(a2p3p)_R") == (("a2", "a3"), ())
    assert comp.parse_instance("PPL106_R") == ((), ())
    assert comp.parse_instance("MBON22(calyx)_R") == (("calyx",), ())
    ok("parse_instance")


def test_swap_degrees():
    rng = np.random.default_rng(0)
    E = 3000
    pre = rng.integers(0, 200, E); post = rng.integers(0, 40, E)
    key = np.unique(pre * 1000 + post, return_index=True)[1]
    pre, post = pre[key], post[key]
    w = rng.integers(1, 30, len(pre)).astype(np.float32)
    groups = (post % 2).astype(int)
    new = nw.swap_edges(pre, post, w, groups, rng)
    assert (np.bincount(new, minlength=200) == np.bincount(pre, minlength=200)).all()      # grado de salida
    assert (np.bincount(post, minlength=40) == np.bincount(post, minlength=40)).all()      # grado de entrada (post intacto)
    assert len(set(zip(new.tolist(), post.tolist()))) == len(new)                          # sin duplicados
    assert (new != pre).mean() > 0.5                                                      # realmente mezcla
    # un grupo no mezcla con otro: el multiconjunto de presinapticos de cada grupo se conserva
    for g in (0, 1):
        assert sorted(new[groups == g].tolist()) == sorted(pre[groups == g].tolist())
    ok("swap_edges conserva grados, sin duplicados, respeta grupos")


def test_engine_basic():
    net = tiny_net()
    c, kf, _ = run(net, 0, 3000, 99999, 99999, False)
    assert c[1] > 5, c                    # KC1 recibe PN fuerte y dispara
    assert c[2] == 0                      # KC2 sin entradas
    assert c[3] > 0                       # MBON dispara por KC1
    c2, _, _ = run(net, 0, 3000, 99999, 99999, False)
    assert (c == c2).all()                # reproducible con la misma semilla
    c3, _, _ = run(net, 0, 3000, 99999, 99999, False, seed=2)
    assert not (c == c3).all()            # semilla distinta, resultado distinto
    sil = np.zeros(5, np.bool_); sil[1] = True
    c4, _, _ = run(net, 0, 3000, 99999, 99999, False, silenced=sil)
    assert c4[1] == 0 and c4[3] == 0      # KC1 silenciada: el MBON calla
    ok("motor LIF: disparo, semilla, silenciamiento")


def test_delay():
    net = tiny_net(w_pn=60.0)
    n = net[0]
    # una espiga unica de PN forzada: tasa enorme durante 1 paso
    c, _, _ = run(net, 0, 3, 99999, 99999, False, pn_hz=1e6, nsteps=60)
    assert c[1] >= 1
    ok("retardo sinaptico: la KC responde tras la espiga del PN")


def test_plasticity_rules():
    net = tiny_net()
    # coincidencia: PN activa KC1 y el DAN llega 200 ms (400 pasos) despues
    c, kf, _ = run(net, 0, 2000, 400, 2000, True)
    assert kf[0] < 0.5, kf                # KC1 activa + DAN: deprime
    assert kf[1] == 1.0                   # KC2 inactiva: intacta (especificidad de olor)
    # sin DAN: nada cambia
    c, kf, _ = run(net, 0, 2000, 99999, 99999, True)
    assert kf[0] == 1.0 and kf[1] == 1.0
    # hacia atras (DAN antes y sin solape): sin plasticidad (Hige 2015)
    c, kf, _ = run(net, 3000, 5000, 0, 1000, True, nsteps=6000)
    assert kf[0] > 0.98, kf
    # plasticidad desactivada aunque haya coincidencia
    c, kf, _ = run(net, 0, 2000, 400, 2000, False)
    assert kf[0] == 1.0
    # gating por umbral: theta enorme => KC nunca 'activa'
    c, kf, _ = run(net, 0, 2000, 400, 2000, True, theta=1e6)
    assert kf[0] == 1.0
    ok("plasticidad: coincidencia, especificidad, orden temporal, gating por umbral")


def test_data():
    try:
        import mbdata as md
        nodes, edges = md.load()
    except Exception as e:                # sin datos / pyarrow
        SKIP.append("datos reales (%s)" % type(e).__name__)
        print("SKIP datos reales:", type(e).__name__, str(e)[:80])
        return
    n = {k: int((nodes["cls"] == i).sum()) for i, k in enumerate(md.CLASS_NAMES)}
    assert n["KC"] == 4064 and n["MBON"] == 97 and n["DAN"] == 340 and n["APL"] == 2, n
    kc = nodes["cls"] == md.KC
    assert (nodes["nt_consensus"][kc] == "acetylcholine").all()
    assert (nodes["nt_predicted"][kc] == "dopamine").sum() == 4058       # el problema de datos del Alcalde
    import analysis as an
    v = an.valence_vector(nodes)
    assert (v < 0).sum() == 26 and (v > 0).sum() == 71
    net = nw.build(nodes, edges, nw.Params())
    assert net.info["n_edges_kcmbon"] == 61210 and net.info["n_channels"] == 88
    ok("datos reales: conteos, consensus_nt vs predicted_nt, valencia 26/71, red")
    # reproducibilidad de la construccion con controles
    n1 = nw.build(nodes, edges, nw.Params(), rng=np.random.default_rng(3), rewire={"kcmbon": "global"})
    n2 = nw.build(nodes, edges, nw.Params(), rng=np.random.default_rng(3), rewire={"kcmbon": "global"})
    assert (n1.kw0 == n2.kw0).all() and (n1.kpost == n2.kpost).all()
    ok("control kcmbon_global reproducible y conserva numero de aristas")


def test_outputs():
    p = os.path.join(ROOT, "out", "anatomy.json")
    if not os.path.exists(p):
        SKIP.append("anatomy.json"); return
    a = json.load(open(p))
    v = a["DAN_a_MBON_validacion"]
    assert v["frac_media_observada"] > 0.8 and v["nulo_permutando_etiquetas_MBON"]["max"] < 0.5
    assert a["KC_subtipo_coincidencia"]["coinciden"] == a["KC_subtipo_coincidencia"]["total"]
    ok("out/anatomy.json: compartimentos validados con conectividad")
    r = os.path.join(ROOT, "out", "results.json")
    if os.path.exists(r):
        R = json.load(open(r))
        if "main" in R:
            m = R["main"]["resultados"]["real"]
            assert m["PPL1"]["A"][0] < 0
            ok("out/results.json: PPL1 con cableado real da dLI(A) < 0")


if __name__ == "__main__":
    test_parse_instance(); test_swap_degrees(); test_engine_basic(); test_delay(); test_plasticity_rules(); test_data(); test_outputs()
    print(f"\n{len(PASS)} pruebas OK, {len(SKIP)} saltadas {SKIP}")
