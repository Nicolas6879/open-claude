"""Tamano en la frontera: nulo de signo aleatorio SIN costes ni financiacion.
Con costes, todas las configuraciones tienen media negativa y el test es conservador
(hipotesis compuesta). Sin costes, la configuracion menos favorable tiene media exactamente 0.
Escribe out/calibracion_frontera.json."""
import json
import os
import sys
import time
from multiprocessing import Pool

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import numpy as np  # noqa: E402

from cazador import mundos as MU  # noqa: E402
from cazador import pipeline as PL  # noqa: E402
from cazador import protocolo as P  # noqa: E402
from calibrar import resumen  # noqa: E402

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out")
N = 120

if __name__ == "__main__":
    PL.SPEC["sp500"]["coste"] = 0.0
    PL.SPEC["sp500"]["spread"] = 0.0
    base = MU.base_seleccion()
    fechas = PL.d_sp500()["fechas"]
    args = [("nulo", P.SEMILLA + 500000 + i, 0.0, fechas, base, 20, "signo") for i in range(N)]
    t0 = time.time()
    with Pool(4) as pool:
        res = pool.map(MU.ejecutar_mundo, args, chunksize=4)
    out = dict(
        descripcion="nulo signo aleatorio, costes=0, financiacion=0 (frontera de la hipotesis compuesta)",
        resumen=resumen(res, "nulo_signo_sin_costes"),
        segundos=round(time.time() - t0, 1),
    )
    with open(os.path.join(OUT, "calibracion_frontera.json"), "w") as f:
        json.dump(out, f, indent=1, default=str)
    print(json.dumps(out["resumen"], default=str))
