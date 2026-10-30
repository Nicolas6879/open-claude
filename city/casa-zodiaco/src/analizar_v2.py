"""Analiza el test sellado de v2 (familias SELLADO) y las compara con v1. Escribe out/resumen_v2.json."""
import os, sys, json
sys.dont_write_bytecode = True
import numpy as np, pandas as pd
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "out")
DISENO = ['potawatomi', 'romanian', 'nordica', 'belarusian', 'navajo', 'tukano', 'seri', 'balinese', 'tupi', 'polinesia',
          'mongolian', 'arabe_popular', 'tibetan', 'sardinian', 'lokono']
SUF = sys.argv[1] if len(sys.argv) > 1 else ""  # "" o "_kmatch"
v = pd.read_csv(os.path.join(OUT, f"resultados_v2_sellado_hgb{SUF}.csv"))
b = pd.read_csv(os.path.join(OUT, "resultados_B.csv"))[["cultura", "f1_modelo", "f1_nn"]].rename(columns={"f1_modelo": "f1_v1", "f1_nn": "f1_nn_v1"})
v = v.merge(b, on="cultura")
res = {}
rng = np.random.default_rng(3)
for nombre, d in (("sellado", v[~v.familia.isin(DISENO)]), ("diseno", v[v.familia.isin(DISENO)]), ("todo", v)):
    d = d.copy()
    d["g1"] = d.f1_modelo >= 2 * d.f1_aleatorio_grado
    d["g2"] = d.f1_modelo > d.f1_nn
    d["g2_ic"] = d.dif_nn_lo > 0
    d["g2_v1"] = d.f1_v1 > d.f1_nn_v1
    d["g2_cons"] = d.f1_consenso > d.f1_nn
    d["v2_gt_v1"] = d.f1_modelo > d.f1_v1
    d["v2_gt_cons"] = d.f1_modelo > d.f1_consenso
    ff = lambda col: d.assign(_x=d[col].astype(float)).groupby("familia")["_x"].mean().values
    o = dict(n_culturas=int(len(d)), n_familias=int(d.familia.nunique()))
    for col in ("g1", "g2", "g2_ic", "g2_v1", "g2_cons", "v2_gt_v1", "v2_gt_cons"):
        f = ff(col)
        bs = f[rng.integers(0, len(f), size=(5000, len(f)))].mean(1)
        o[col] = dict(por_cultura=float(d[col].mean()), por_familia=float(f.mean()), ic_fam=[float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))])
    for col in ("f1_modelo", "f1_v1", "f1_nn", "f1_consenso", "f1_aleatorio_grado"):
        o["mediana_" + col] = float(d[col].median())
        o["media_fam_" + col] = float(d.groupby("familia")[col].mean().mean())
    res[nombre] = o
    if nombre == "sellado":
        pd.set_option("display.width", 200)
        print(d[["cultura", "familia", "n_aristas", "K_modelo", "f1_modelo", "f1_v1", "f1_nn", "f1_consenso", "f1_aleatorio_grado", "g2", "dif_nn_lo", "dif_nn_hi"]].round(3).to_string())
json.dump(res, open(os.path.join(OUT, f"resumen_v2{SUF}.json"), "w"), indent=1)
print(json.dumps(res["sellado"], indent=1))
