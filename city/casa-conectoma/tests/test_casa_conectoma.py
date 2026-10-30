"""Pruebas de casa-conectoma. Ejecutar: PYTHONDONTWRITEBYTECODE=1 python3 tests/test_casa_conectoma.py

Las pruebas 1-4 no necesitan datos. Las pruebas 5-6 usan out/ y se saltan con mensaje si falta algo.
"""
import json
import os
import sys
import traceback

import numpy as np

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(HERE, "src"))
import nulls  # noqa: E402
import sim  # noqa: E402


def test_swap_null_keeps_degrees():
    rng = np.random.default_rng(0)
    pairs = [(k, p) for k in range(40) for p in rng.choice(30, size=5, replace=False).tolist()]
    deg_kc = {k: sum(1 for a, _ in pairs if a == k) for k in range(40)}
    deg_pn = {p: sum(1 for _, b in pairs if b == p) for p in range(30)}
    out, done = nulls.swap_null(pairs, 2000, rng)
    assert done > 1000, f"pocos intercambios: {done}"
    new_kc = {k: len(out.get(k, ())) for k in range(40)}
    new_pn = {}
    for k, s in out.items():
        for p in s:
            new_pn[p] = new_pn.get(p, 0) + 1
    assert new_kc == deg_kc, "grados de KC cambiaron"
    assert {p: new_pn.get(p, 0) for p in range(30)} == deg_pn, "grados de PN cambiaron"


def test_pair_overlap_matches_bruteforce():
    M = np.array([[1, 1, 0, 0], [0, 1, 1, 0], [0, 0, 0, 1]], dtype=np.float32)
    mean, frac = nulls.pair_overlap(M)
    # pares: (0,1)=1 compartida, (0,2)=0, (1,2)=0
    assert abs(mean - 1 / 3) < 1e-6 and abs(frac - 1 / 3) < 1e-6, (mean, frac)


def _tiny_net():
    # 1 PN -> 1 KC con APL; N = 4
    return dict(N=4, pn=[101], kc=[201], apl=[301], idx={101: 0, 201: 1, 301: 2}, cls={}, typ={}, pk_mask=None,
                pre=None, post=None, w=None, nt={})


def test_lif_fires_only_with_drive():
    net = _tiny_net()
    W = np.zeros((4, 4), dtype=np.float32)
    W[0, 1] = 10.0  # PN -> KC excitatoria (fuerte: la media de V es rate*w*tau_syn)
    rng = np.random.default_rng(3)
    r0, _ = sim.run_trial(W, net, np.zeros(1, dtype=np.float32), rng)
    assert r0[1] == 0.0, "la KC no debe disparar sin olor"
    r1, _ = sim.run_trial(W, net, np.array([0.6], dtype=np.float32), rng)
    assert r1[0] > 5.0, f"la PN con olor debe disparar: {r1[0]}"
    assert r1[1] > 0.0, "la KC debe recibir y transmitir la PN"


def test_lif_deterministic_with_seed():
    net = _tiny_net()
    W = np.zeros((4, 4), dtype=np.float32)
    W[0, 1] = 10.0
    a, _ = sim.run_trial(W, net, np.array([0.5], dtype=np.float32), np.random.default_rng(7))
    b, _ = sim.run_trial(W, net, np.array([0.5], dtype=np.float32), np.random.default_rng(7))
    assert np.array_equal(a, b)


def test_contract_and_sizes():
    p = os.path.join(HERE, "out", "activity.json")
    if not os.path.exists(p):
        print("  (saltada: falta out/activity.json; ejecutar src/sim.py --export)")
        return
    d = json.load(open(p, encoding="utf-8"))
    assert set(d) >= {"meta", "neurons", "spikes", "stimuli"}
    assert d["meta"]["synthetic"] is False
    ids = {n["id"] for n in d["neurons"]}
    assert all(s[1] in ids for s in d["spikes"][:5000]), "espiga con id desconocido"
    assert all(set(n) == {"id", "type", "x", "y"} for n in d["neurons"])
    total = sum(os.path.getsize(os.path.join(dp, f)) for dp, _, fs in os.walk(HERE) for f in fs if "/.git" not in dp)
    assert total < 10 * 1024 * 1024, f"la casa ocupa {total} bytes (tope 10 MB)"


def test_audit_numbers_if_present():
    p = os.path.join(HERE, "out", "audit.json")
    if not os.path.exists(p):
        print("  (saltada: falta out/audit.json)")
        return
    a = json.load(open(p, encoding="utf-8"))
    assert a["conteos"]["KC_total"] == 4064
    assert a["conteos"]["APL"] == 2
    assert a["PN_KC"]["PN_distintas_por_KC_mediana_(KC_con_PN)"] == 6.0
    o = a["solapamiento_entre_pares_de_KC"]
    assert o["observado_fraccion_pares_con_alguna_PN"] < o["nulo_conserva_grados_fraccion_pares"]


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
