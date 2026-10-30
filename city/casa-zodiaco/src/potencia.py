"""Potencia del pipeline (regimen B, parametros fijos de v1): se inyecta en el cielo REAL una 'cultura' sintetica
con una fraccion q de aristas gestalticas (muestreadas entre las mejor puntuadas por el modelo) y el resto aristas
Delaunay al azar, con los tamaños de las 56 culturas reales. Se mide que fraccion supera G1 (x2 al nulo de grados) y G2 (> NN).
q=0 es el control negativo. Uso: python potencia.py -> out/potencia.csv"""
import os, sys
sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, pandas as pd
import datos, modelo as M, evaluacion as E
from correr_A import cargar_culturas, OUT

cult = [c for c in cargar_culturas() if c.eligible]
df = datos.cargar_hyg(); d = df[df.hip.notna()].copy(); d["hip"] = d.hip.astype(int)
vec = datos.radec_a_vec(d.ra.values * 15.0, d.dec.values)
univ = E.Universo(d.hip.values.astype(np.int64), vec, d.mag.values, mag_max=6.5)
ML, LAM, R, RAT = 3.5, 0.5, 30, 0.45
pred = univ.pred(ML, LAM, R, RAT)
nn = univ.nn(ML)
idx55, cand55 = univ.candidatas(5.5)
hips55 = univ.hips[idx55]
score = cand55.puntuacion(LAM, R)
orden = np.argsort(-score)
keys55 = M.claves_de(cand55.e, hips55)
rng = np.random.default_rng(99)
filas = []
for q in (0.0, 0.05, 0.1, 0.2, 0.3, 0.5, 0.75, 1.0):
    for c in cult:
        for rep in range(3):
            E_c = c.n_aristas
            n_pl = int(round(q * E_c))
            top = orden[: max(2 * E_c, 50)]
            pl = rng.choice(top, size=min(n_pl, len(top)), replace=False) if n_pl else np.zeros(0, dtype=int)
            resto = rng.choice(len(keys55), size=E_c - len(pl), replace=False)
            truth = np.unique(np.concatenate([keys55[pl], keys55[resto]]))
            fm = M.f1_claves(pred, truth)
            fn = M.f1_claves(nn, truth)
            nulo = np.mean([M.f1_claves(univ.aleatorio_grado(ML, pred, rng), truth) for _ in range(30)])
            filas.append(dict(q=q, cultura=c.nombre, familia=c.familia, n_aristas=E_c, rep=rep, f1_modelo=fm, f1_nn=fn, f1_nulo=nulo))
t = pd.DataFrame(filas)
t["g1"] = t.f1_modelo >= 2 * t.f1_nulo
t["g2"] = t.f1_modelo > t.f1_nn
t.to_csv(os.path.join(OUT, "potencia_detalle.csv"), index=False)
g = t.groupby("q").agg(F1_modelo=("f1_modelo", "median"), F1_NN=("f1_nn", "median"), F1_nulo=("f1_nulo", "median"),
                       G1=("g1", "mean"), G2=("g2", "mean")).round(3)
g.to_csv(os.path.join(OUT, "potencia.csv"))
print(g)
