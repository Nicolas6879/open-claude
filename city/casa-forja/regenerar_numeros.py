"""Regenera TODOS los numeros citados en README.md y en el bus, desde out/*.json y out/*.csv.

Uso: python3 regenerar_numeros.py   -> imprime la tabla y escribe out/numeros.json
Intervalos: Clopper-Pearson exacto (bilateral 95 %). Correccion global: Benjamini-Hochberg q=0.05
sobre los finalistas (dos variantes: con todos los conjuntos del pre-registro, y sin acciones20,
cuyos resultados quedaron invalidados por el bug de NaN corregido en senales.py).
"""
import json
import os

import numpy as np
import pandas as pd
from scipy.stats import beta

from cazador import motor as M
from cazador import protocolo as P

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out")


def clopper_pearson(k, n, alfa=0.05):
    lo = 0.0 if k == 0 else beta.ppf(alfa / 2, k, n - k + 1)
    hi = 1.0 if k == n else beta.ppf(1 - alfa / 2, k + 1, n - k)
    return float(lo), float(hi)


def proporcion(nombre, k, n):
    lo, hi = clopper_pearson(k, n)
    return {"mundo": nombre, "k": int(k), "n": int(n), "tasa": round(k / n, 4),
            "IC95_exacto": [round(lo, 4), round(hi, 4)]}


def main():
    out = {}
    cal = json.load(open(os.path.join(OUT, "calibracion.json")))["resumen"]
    filas = []
    for clave in ["nulo_signo", "nulo_iid", "diagnostico_nulo_bloques", "plantado_s0.3", "plantado_s0.6"]:
        r = cal[clave]
        k = int(round(r["tasa_campeon"] * r["n_mundos"]))
        filas.append(proporcion(clave + " (campeon)", k, r["n_mundos"]))
        g = int(round(r["tasa_puerta_seleccion"] * r["n_mundos"]))
        filas.append(proporcion(clave + " (puerta de seleccion)", g, r["n_mundos"]))
    fr = json.load(open(os.path.join(OUT, "calibracion_frontera.json")))["resumen"]
    k = int(round(fr["tasa_campeon"] * fr["n_mundos"]))
    filas.append(proporcion("frontera sin costes (campeon)", k, fr["n_mundos"]))
    g = int(round(fr["tasa_puerta_seleccion"] * fr["n_mundos"]))
    filas.append(proporcion("frontera sin costes (puerta)", g, fr["n_mundos"]))
    out["calibracion"] = filas

    real = json.load(open(os.path.join(OUT, "resultados_reales.json")))
    out["seleccion"] = {k: dict(configs=v["seleccion"]["n_configs"], puerta=bool(v["seleccion"]["puerta"]),
                                p_spa_alfa=round(v["seleccion"]["p_spa_alfa"], 4),
                                campeon=v["campeon"]) for k, v in real.items()}

    fin = pd.read_csv(os.path.join(OUT, "muestra_final_finalistas.csv"))
    p_all = np.concatenate([fin.p_alfa.values, fin.p_dinero.values])
    rech_all = M.benjamini_hochberg(p_all, P.Q_BH)
    n = len(fin)
    fin["pasa_BH_todos"] = rech_all[:n] & rech_all[n:]
    valido = fin[fin.conjunto != "acciones20"].reset_index(drop=True)
    p_val = np.concatenate([valido.p_alfa.values, valido.p_dinero.values])
    rech_val = M.benjamini_hochberg(p_val, P.Q_BH)
    m = len(valido)
    valido["pasa_BH_sin_acciones20"] = rech_val[:m] & rech_val[m:]
    out["finalistas_muestra_final"] = fin[["conjunto", "config", "p_alfa", "p_dinero", "sr_muestra_final",
                                           "cagr", "alfa_anual", "maxdd", "pasa_BH_todos"]].round(4).to_dict("records")
    out["familias_pruebas_BH_todos"] = int(2 * n)
    out["familias_pruebas_BH_sin_acciones20"] = int(2 * m)
    out["pasan_BH_todos"] = fin.loc[fin.pasa_BH_todos, ["conjunto", "config"]].values.tolist()
    out["pasan_BH_sin_acciones20"] = valido.loc[valido.pasa_BH_sin_acciones20, ["conjunto", "config"]].values.tolist()
    out["n_configs_total_preregistro"] = int(sum(v["seleccion"]["n_configs"] for v in real.values()))

    with open(os.path.join(OUT, "numeros.json"), "w") as f:
        json.dump(out, f, indent=1, ensure_ascii=False)
    print("CALIBRACION (Clopper-Pearson 95 %)")
    for f_ in filas + [] :
        print(f"  {f_['mundo']:38s} {f_['k']:3d}/{f_['n']:<4d} = {100*f_['tasa']:5.2f} %  IC [{100*f_['IC95_exacto'][0]:.2f}, {100*f_['IC95_exacto'][1]:.2f}] %")
    print("SELECCION (puerta SPA alfa p<0,10)")
    for k_, v in out["seleccion"].items():
        print(f"  {k_:12s} configs={v['configs']:4d} puerta={v['puerta']} p_spa={v['p_spa_alfa']} campeon={v['campeon']}")
    print("PASAN BH con todos los conjuntos:", out["pasan_BH_todos"])
    print("PASAN BH sin acciones20 (validos):", out["pasan_BH_sin_acciones20"])


if __name__ == "__main__":
    main()
