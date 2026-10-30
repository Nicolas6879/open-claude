"""Tests de v2 (rasgos, aprendizaje) y de la extension a otros observadores, con datos SINTETICOS.
Si existe HYG descargado, tambien comprueba la consistencia con las magnitudes terrestres de HYG.
Uso: python3 tests/test_v2_extension.py (venv con numpy/scipy/pandas/sklearn)."""
import os, sys
sys.dont_write_bytecode = True
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))
import numpy as np
import pandas as pd
import modelo as M, v2, extension


def cielo(n, rng):
    v = rng.normal(size=(n, 3)); v /= np.linalg.norm(v, axis=1, keepdims=True)
    return v, 1 + rng.exponential(1.6, n)


def test_rasgos_forma():
    v, m = cielo(300, np.random.default_rng(0))
    cand, X = v2.rasgos(v, m)
    assert X.shape == (len(cand.e), len(v2.NOMBRES)) and np.isfinite(X).all()
    assert (m[cand.i] <= m[cand.j] + 1e-12).all()  # i es el mas brillante


def test_aprendizaje_recupera_regla_plantada():
    """Si las 'culturas' conectan solo aristas sin bloqueadores y cortas, el modelo debe aprenderlo (fuera de muestra)."""
    rng = np.random.default_rng(1)
    v, m = cielo(500, rng)
    cand, X = v2.rasgos(v, m)
    regla = (X[:, v2.NOMBRES.index("bloq_igual")] == 0) & (X[:, 0] < np.percentile(X[:, 0], 40))
    Y = np.stack([regla & (rng.random(len(regla)) < 0.8) for _ in range(6)]).astype(np.uint8)
    w = np.ones(6)
    mdl = v2.ajustar(X, Y[:4], w[:4])
    p = mdl(X)
    from sklearn.metrics import roc_auc_score
    assert roc_auc_score(regla, p) > 0.9


def test_consenso():
    Y = np.array([[1, 0, 1], [1, 1, 0]], dtype=np.uint8)
    assert np.allclose(v2.consenso(Y, np.array([1.0, 1.0])), [1, 0.5, 0.5])


def test_observador_magnitud_y_direccion():
    # estrella de absmag 5 a 10 pc en +x desde el Sol: mag 5; desde un observador en x=5 pc: d=5 -> mag = 5 + 5log10(0.5)
    df = pd.DataFrame(dict(id=[0, 1, 2], hip=[np.nan, 1, 2], ra=[0, 0, 6.0], dec=[0, 0, 0], dist=[0.0, 10.0, 10.0],
                           mag=[-26.7, 5.0, 5.0], absmag=[4.85, 5.0, 5.0], x=[0, 10.0, 0], y=[0, 0, 10.0], z=[0, 0, 0]))
    c = extension.Cielos(df)
    idx, v, mag = c.desde([0, 0, 0], mag_max=99)
    assert set(idx) == {1, 2}  # el Sol (en el origen) no se ve a si mismo
    idx, v, mag = c.desde([5.0, 0, 0], mag_max=99)
    d = dict(zip(idx, mag))
    assert abs(d[1] - (5 + 5 * np.log10(0.5))) < 1e-9
    assert abs(d[0] - (4.85 + 5 * np.log10(5 / 10))) < 1e-9   # el Sol aparece como estrella
    vv = dict(zip(idx, v))
    assert np.allclose(vv[0], [-1, 0, 0])  # desde x=5 el Sol queda en la direccion -x


def test_consistencia_hyg_si_hay_datos():
    import datos
    p = os.path.join(datos.DATOS, "hygdata_v41.csv")
    if not os.path.exists(p):
        print("  (sin HYG descargado: omitido)"); return
    df = datos.cargar_hyg()
    c = extension.Cielos(df)
    idx, v, mag = c.desde([0, 0, 0], mag_max=6.0)
    dm = np.abs(mag - df.mag.values[idx])
    assert np.median(dm) < 0.01 and np.mean(dm < 0.05) > 0.99


if __name__ == "__main__":
    for nm, fn in sorted(globals().items()):
        if nm.startswith("test_") and callable(fn):
            print(nm); fn()
    print("TODOS LOS TESTS OK")
