"""Tests del pipeline con cielos SINTETICOS (no usan datos descargados).
Incluye la prueba de potencia: se inyecta una estructura conocida y la evaluacion debe detectarla;
con estructura aleatoria (control negativo) NO debe declarar ventaja.
Uso: python3 tests/test_pipeline.py   (necesita numpy/scipy: usar el venv)
"""
import os
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))
import numpy as np
import modelo as M
import evaluacion as E


def cielo_sintetico(n, rng, base=1000):
    v = rng.normal(size=(n, 3))
    v /= np.linalg.norm(v, axis=1, keepdims=True)
    mag = 1.0 + rng.exponential(1.6, size=n)  # muchas debiles, pocas brillantes
    hips = base + np.arange(n)
    return hips, v, mag


def cultura_plantada(nombre, q, params, rng, n=250, base=1000):
    """q = fraccion de aristas que son las del modelo (estructura inyectada); el resto, parejas al azar."""
    hips, v, mag = cielo_sintetico(n, rng, base)
    h2v = {h: x for h, x in zip(hips, v)}
    h2m = {h: x for h, x in zip(hips, mag)}
    lam, R, r = params
    # punto fijo: el modelo se aplica sobre las estrellas que la propia estructura toca (como en el
    # regimen A, donde el modelo solo ve las estrellas usadas por la cultura)
    idx = np.arange(n)
    for _ in range(6):
        cand = M.Candidatas(v[idx], mag[idx])
        e = idx[cand.top_k(lam, R, round(r * len(idx)))]
        idx = np.unique(e)
    cand = M.Candidatas(v[idx], mag[idx])
    e = idx[cand.top_k(lam, R, round(r * len(idx)))]
    nplant = int(round(q * len(e)))
    plant = e[rng.permutation(len(e))[:nplant]]
    nrand = len(e) - nplant
    ra = idx[rng.integers(0, len(idx), size=(nrand * 3, 2))]
    ra = ra[ra[:, 0] != ra[:, 1]][:nrand]
    todo = np.unique(np.sort(np.concatenate([plant, ra]), axis=1), axis=0)
    ar = [(int(hips[a]), int(hips[b]), i % 8) for i, (a, b) in enumerate(todo)]
    return E.Cultura(nombre, nombre, ar, h2v, h2m)


def test_f1_basico():
    a = np.array([1, 2, 3], dtype=np.int64)
    b = np.array([2, 3, 4], dtype=np.int64)
    assert abs(M.f1_claves(a, a) - 1.0) < 1e-12
    assert M.f1_claves(a, np.array([9, 10], dtype=np.int64)) == 0.0
    assert abs(M.f1_claves(a, b) - 2 * 2 / 6) < 1e-12


def test_delaunay_euler():
    rng = np.random.default_rng(1)
    v = rng.normal(size=(100, 3))
    v /= np.linalg.norm(v, axis=1, keepdims=True)
    e = M.delaunay_aristas(v)
    assert len(e) == 3 * 100 - 6  # triangulacion de la esfera: E = 3V-6


def test_grado_aleatorio_conserva_grados():
    rng = np.random.default_rng(2)
    g = rng.integers(1, 4, size=60)
    e = M.grado_aleatorio(g, np.arange(60), rng)
    gg = np.bincount(e.ravel(), minlength=60)
    assert gg.sum() >= 0.9 * g.sum()  # el modelo 'borrado' pierde pocos lazos/duplicados
    assert (gg <= g).all()


def test_inyeccion_estructura_detectada_y_control_negativo():
    """Potencia: estructura 100 % gestaltica se detecta; 0 % (aristas al azar) no da ventaja."""
    rng = np.random.default_rng(3)
    par = (2.0, 60, 0.8)
    res = {}
    for q in (1.0, 0.5, 0.0):
        f_mod, f_nn, f_a, f_c = [], [], [], []
        for s in range(4):
            c = cultura_plantada(f"s{s}", q, par, np.random.default_rng(100 + s), n=250)
            v, m = c.estrellas(c.hips)
            o = E.nulos_A(c.keys, c.hips, v, m, par, 0.6, rng, nsem=30)
            f_mod.append(o["modelo"]); f_nn.append(o["nn"]); f_a.append(o["aleatorio_grado"]); f_c.append(o["sub_aleatorio"])
        res[q] = (np.mean(f_mod), np.mean(f_nn), np.mean(f_a), np.mean(f_c))
        print(f"  q={q}: F1 modelo={res[q][0]:.3f} NN={res[q][1]:.3f} aleatorio_grado={res[q][2]:.3f} sub_aleatorio={res[q][3]:.3f}")
    assert res[1.0][0] > 0.85                    # recupera la estructura inyectada
    assert res[1.0][0] > 2 * res[1.0][2]         # x2 sobre el nulo de grados (se detecta)
    assert res[1.0][0] > 1.5 * res[1.0][3]       # y sobre un subconjunto aleatorio de candidatas
    assert res[0.0][0] < 2 * max(res[0.0][2], 0.02) + 0.05  # control negativo: sin ventaja x2
    assert res[1.0][0] > res[0.5][0] > res[0.0][0]          # monotonia con la fraccion inyectada


def test_lofo_recupera_parametros_plantados():
    """Con varias 'culturas' que comparten los parametros plantados, el ajuste en N-1 los recupera."""
    par = (2.0, 60, 0.8)
    cult = [cultura_plantada(f"s{s}", 1.0, par, np.random.default_rng(200 + s), n=200, base=1000 + 300 * s)
            for s in range(5)]
    Mg = np.stack([E.f1_grid_A(c) for c in cult])
    nombres = [c.nombre for c in cult]
    fam = {n: n for n in nombres}
    el = np.ones(len(cult), dtype=bool)
    ch = E.lofo_indices(Mg, nombres, fam, el, modo="familia")
    for c, idx in enumerate(ch):
        f1_heldout = Mg[c][idx]
        assert f1_heldout > 0.9, (idx, f1_heldout)


def test_fugas_familia():
    """Leave-family-out debe excluir a todos los parientes del conjunto de entrenamiento."""
    nombres = ["a1", "a2", "b"]
    fam = {"a1": "A", "a2": "A", "b": "B"}
    Mg = np.zeros((3, 2, 1, 1))
    Mg[0, 0] = 1  # a1 prefiere parametro 0
    Mg[1, 0] = 1  # a2 (pariente) tambien; b prefiere el 1
    Mg[2, 1] = 1
    el = np.ones(3, dtype=bool)
    ch_f = E.lofo_indices(Mg, nombres, fam, el, "familia")
    ch_c = E.lofo_indices(Mg, nombres, fam, el, "cultura")
    assert ch_f[0][0] == 1   # sin a2 en el entrenamiento, solo queda b -> parametro 1
    assert ch_c[0][0] == 0   # LOCO si deja a a2 (fuga): demuestra por que se usa la familia


if __name__ == "__main__":
    for nm, fn in sorted(globals().items()):
        if nm.startswith("test_") and callable(fn):
            print(nm)
            fn()
    print("TODOS LOS TESTS OK")
