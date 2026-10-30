"""Resume resultados_{A,B}.csv: medianas, compuerta G1/G2 (por cultura y ponderada por familia), IC de las fracciones
(bootstrap por familias). Uso: python analizar.py A|B"""
import os, sys, json
sys.dont_write_bytecode = True
import numpy as np, pandas as pd

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "out")
which = sys.argv[1]  # p. ej. A, B, A_v1b
d = pd.read_csv(os.path.join(OUT, f"resultados_{which}.csv"))
e = d[d.elegible].copy()
e["g1"] = e.f1_modelo >= 2 * e.f1_aleatorio_grado
e["g2"] = e.f1_modelo > e.f1_nn
e["g2_ic"] = e.dif_nn_lo > 0          # estrictamente mejor con IC95 % de la diferencia por encima de 0
e["g1_ic"] = e.ratio_lo > 1
e["g2_prox"] = e.f1_modelo > e.f1_prox
e["peor_nn_ic"] = e.dif_nn_hi < 0
e["g2_sub"] = e.f1_modelo > e.f1_sub_aleatorio
w = 1.0 / e.groupby("familia")["cultura"].transform("count")


def frac(col):
    x = e[col].astype(float).values
    cult = x.mean()
    ff = e.assign(_x=x).groupby("familia")["_x"].mean().values  # fraccion por familia
    fam = ff.mean()                                              # = peso 1/|familia| por cultura
    rng = np.random.default_rng(1)
    bs = ff[rng.integers(0, len(ff), size=(5000, len(ff)))].mean(axis=1)
    return dict(por_cultura=float(cult), por_familia=float(fam), ic_fam=[float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))])


res = dict(n_elegibles=int(len(e)), n_familias=int(e.familia.nunique()))
for col in ("g1", "g2", "g1_ic", "g2_ic", "g2_prox", "g2_sub", "peor_nn_ic"):
    res[col] = frac(col)
for col in ("f1_modelo", "f1_nn", "f1_prox", "f1_aleatorio_grado", "f1_sub_aleatorio", "f1_loco"):
    res["mediana_" + col] = float(e[col].median())
    res["media_fam_" + col] = float((e[col] * w).sum() / w.sum())
res["rel_mediana_vs_nn"] = float(np.median(e.f1_modelo / e.f1_nn - 1))
res["ratio_mediano_vs_aleatorio"] = float(np.median(e.f1_modelo / np.maximum(e.f1_aleatorio_grado, 1e-9)))
res["f1_loco_menos_lofo_media"] = float((e.f1_loco - e.f1_modelo).mean())
cols = [c for c in ("lam", "R", "r") if c in e] + (["m_lim"] if "m_lim" in e else [])
res["hiperparametros_modales"] = {c: {str(k): int(v) for k, v in e[c].value_counts().items()} for c in cols}
json.dump(res, open(os.path.join(OUT, f"resumen_{which}.json"), "w"), indent=1)
print(json.dumps(res, indent=1))
pd.set_option("display.width", 220); pd.set_option("display.max_rows", 100)
cols = ["cultura", "n_aristas", "n_estrellas" if "n_estrellas" in e else "n_pred", "lam", "R", "r", "f1_modelo", "f1_nn", "f1_prox", "f1_sub_aleatorio", "f1_aleatorio_grado", "g1", "g2", "dif_nn_lo", "dif_nn_hi"]
print(e[cols].round(3).to_string())
