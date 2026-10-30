"""Ejecucion sobre datos reales. Requiere el protocolo congelado (ver congelar()).

Uso: python3 run_real.py congelar   -> escribe out/protocolo_congelado.json (hash de protocolo.py)
     python3 run_real.py correr     -> seleccion + puerta + muestra final (una vez) por conjunto
"""
import hashlib
import json
import os
import sys
import time
from datetime import datetime

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from cazador import datos as D  # noqa: E402
from cazador import motor as M  # noqa: E402
from cazador import pipeline as PL  # noqa: E402
from cazador import protocolo as P  # noqa: E402

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out")
CONJUNTOS = ["sp500", "spy_tr", "btc", "acciones20", "franceses", "momentum", "wti", "overnight"]


def congelar():
    if os.path.exists(D.ARCHIVO_PROTOCOLO):
        print("Ya estaba congelado:", open(D.ARCHIVO_PROTOCOLO).read())
        return
    os.makedirs(OUT, exist_ok=True)
    info = dict(sha256=D.hash_protocolo(), congelado_en=datetime.now().isoformat(timespec="seconds"),
                nota="Protocolo fijado antes de ejecutar seleccion sobre datos reales.")
    with open(D.ARCHIVO_PROTOCOLO, "w") as f:
        json.dump(info, f, indent=2)
    print(json.dumps(info, indent=2))


def correr():
    D.exigir_protocolo_congelado("run_real.correr")  # registra la entrada; la muestra final la exige correr()
    res_global = {}
    for nombre in CONJUNTOS:
        t = time.time()
        d = PL.SPEC[nombre]["fn"]()
        res = PL.correr(nombre, d, semilla=P.SEMILLA, real=True)
        res["segundos"] = round(time.time() - t, 1)
        res_global[nombre] = res
        tab = pd.DataFrame(res["seleccion"]["tabla"])
        tab.to_csv(os.path.join(OUT, f"seleccion_{nombre}.csv"), index=False, float_format="%.6g")
        print(nombre, "configs", res["seleccion"]["n_configs"],
              "puerta", res["seleccion"]["puerta"], "p_spa", res["seleccion"]["p_spa_alfa"],
              "campeon", res["campeon"], flush=True)
    # Correccion global BH sobre todos los finalistas evaluados en muestra final
    filas = []
    for nombre, r in res_global.items():
        fin = r["muestra_final"]
        if fin is None:
            continue
        for f in fin["finalistas"]:
            if f["es_finalista"]:
                filas.append(dict(conjunto=nombre, config=f["config"], p_alfa=f["p_alfa"],
                                  p_dinero=f["p_dinero"], sr_muestra_final=f["sr_anual"],
                                  cagr=f["cagr"], alfa_anual=f["alfa_anual"], maxdd=f["maxdd"],
                                  n_dias=f["n_dias"]))
    if filas:
        df = pd.DataFrame(filas)
        p = np.concatenate([df.p_alfa.values, df.p_dinero.values])
        rech = M.benjamini_hochberg(p, P.Q_BH)
        n = len(df)
        df["rechazo_global_alfa"] = rech[:n]
        df["rechazo_global_dinero"] = rech[n:]
        df["pasa_global"] = df.rechazo_global_alfa & df.rechazo_global_dinero
        df.to_csv(os.path.join(OUT, "muestra_final_finalistas.csv"), index=False, float_format="%.6g")
    with open(os.path.join(OUT, "resultados_reales.json"), "w") as f:
        json.dump(res_global, f, indent=1, default=str)
    print("hecho")


if __name__ == "__main__":
    if sys.argv[1:] == ["congelar"]:
        congelar()
    elif sys.argv[1:] == ["correr"]:
        correr()
    else:
        print(__doc__)
