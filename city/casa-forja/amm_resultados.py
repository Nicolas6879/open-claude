"""Umbral de comisiones de un LP tipo Uniswap v2 sobre precios reales. Escribe out/amm_umbral.json.
Uso: python3 amm_resultados.py"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cazador import amm as A  # noqa: E402
from cazador import datos as D  # noqa: E402

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out")

if __name__ == "__main__":
    res = {}
    casos = [("GOOG_diario_2004_2013", D.goog()["Close"].to_numpy(), 252.0),
             ("EURUSD_horario_2017_2018", D.eurusd_h1()["Close"].to_numpy(), 252 * 24.0)]
    for nombre, s, per in casos:
        r = A.umbral_rotacion(s, A.FEE, per)
        r["tau_por_periodo_segun_comision"] = A.curva_comisiones(s, periodos_anuales=per)
        res[nombre] = r
    with open(os.path.join(OUT, "amm_umbral.json"), "w") as f:
        json.dump(res, f, indent=1)
    for k, v in res.items():
        print(k, {a: (round(b, 4) if isinstance(b, float) else b) for a, b in v.items()
                  if a != "tau_por_periodo_segun_comision"})
