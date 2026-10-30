"""Calibracion del instrumento con mundos de control (solo seleccion real + sintetico).

Uso: python3 calibrar.py  (con el python del venv). Escribe out/calibracion.json.
Mundos:
  nulo_iid      : bootstrap iid de excesos desmediados (sin ninguna dependencia)
  nulo_bloques  : bootstrap por bloques de 20 dias (conserva clustering de volatilidad y
                  dependencia corta real del S&P 500 de 1990-2013)
  plantado_s    : nulo_bloques + TSMOM60 con SR bruto s inyectado (potencia)
"""
import json
import os
import sys
import time
from multiprocessing import Pool

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from cazador import mundos as MU  # noqa: E402
from cazador import pipeline as PL  # noqa: E402
from cazador import protocolo as P  # noqa: E402

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out")


def clopper_pearson(k, n, alfa=0.05):
    """Intervalo exacto de Clopper-Pearson para una proporcion k/n (bilateral 95 %)."""
    from scipy.stats import beta
    lo = 0.0 if k == 0 else beta.ppf(alfa / 2, k, n - k + 1)
    hi = 1.0 if k == n else beta.ppf(1 - alfa / 2, k + 1, n - k)
    return float(lo), float(hi)


def resumen(res, etiqueta):
    n = len(res)
    gate = np.mean([r["puerta"] for r in res])
    camp = np.mean([r["campeon"] is not None for r in res])
    naive_p05 = np.mean([r["naive"]["p_dinero"] < 0.05 for r in res])
    naive_alfa = np.mean([r["naive"]["p_alfa"] < 0.05 for r in res])
    fam = {}
    for r in res:
        if r["campeon"]:
            fam[r["familia_campeon"]] = fam.get(r["familia_campeon"], 0) + 1
    k = int(round(camp * n))
    lo, hi = clopper_pearson(k, n)
    return dict(
        mundo=etiqueta, n_mundos=n, n_configs=res[0]["n_configs"],
        tasa_puerta_seleccion=float(gate),
        tasa_campeon=float(camp), campeones=k,
        campeon_ic95_exacto=[float(lo), float(hi)],
        familias_campeon=fam,
        naive_tasa_p_dinero_menor_05=float(naive_p05),
        naive_tasa_p_alfa_menor_05=float(naive_alfa),
    )


N_SIGNO = 300
N_IID = 200
N_BLOQUES = 100
N_PLANT = 150


def main():
    t0 = time.time()
    base = MU.base_seleccion()
    fechas = PL.d_sp500()["fechas"]
    tareas = []
    for i in range(N_SIGNO):
        tareas.append(("nulo", P.SEMILLA + 100000 + i, 0.0, fechas, base, 20, "signo", "nulo_signo"))
    for i in range(N_IID):
        tareas.append(("nulo", P.SEMILLA + 200000 + i, 0.0, fechas, base, 1, "iid", "nulo_iid"))
    for i in range(N_BLOQUES):
        tareas.append(("nulo", P.SEMILLA + 300000 + i, 0.0, fechas, base, 20, "bloques",
                       "diagnostico_nulo_bloques"))
    for s in P.SR_PLANTADOS:
        for i in range(N_PLANT):
            tareas.append(("plantado", P.SEMILLA + 400000 + i + int(1000 * s), s, fechas, base, 20,
                           "signo", f"plantado_s{s}"))
    args = [t[:7] for t in tareas]
    etiq = [t[7] for t in tareas]
    with Pool(4) as pool:
        res = pool.map(MU.ejecutar_mundo, args, chunksize=4)
    grupos = {}
    for e, r in zip(etiq, res):
        grupos.setdefault(e, []).append(r)
    salida = dict(
        protocolo=dict(n_signo=N_SIGNO, n_iid=N_IID, n_bloques=N_BLOQUES, n_plantados=N_PLANT,
                       sr_plantados=list(P.SR_PLANTADOS), alfa=P.ALFA, puerta=P.PUERTA_SPA,
                       q_bh=P.Q_BH, k=P.K_FINALISTAS, B=P.B_BOOTSTRAP, coste_bps=P.COSTE_IDA_BPS),
        resumen={e: resumen(r, e) for e, r in grupos.items()},
        segundos=round(time.time() - t0, 1),
    )
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, "calibracion.json"), "w") as f:
        json.dump(salida, f, indent=2, default=str)
    print(json.dumps(salida["resumen"], indent=1, default=str))


if __name__ == "__main__":
    main()
