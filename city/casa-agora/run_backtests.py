"""Ejecuta todos los backtests, imprime tablas y escribe out/results.json (contrato).

Uso:  PYTHONDONTWRITEBYTECODE=1 python3 run_backtests.py

Diseno:
- Evaluacion: 500 trayectorias (semillas 0..499) por escenario. Mismas trayectorias
  y mismas semillas de ruido para todas las estrategias (numeros aleatorios comunes).
- Sintonizacion del umbral de la guardia: 200 trayectorias de OTRAS semillas
  (100000..100199). La evaluacion no se usa para elegir parametros.
- Sensibilidad: LP pasivo, escenario GBM, volatilidad x comision, 500 trayectorias.
"""
import csv
import json
import math
import os
import statistics as stats
import sys
import time

RAIZ = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, RAIZ)

from mercado import ESCENARIOS, generar_precios  # noqa: E402
import simulacion as S  # noqa: E402
from estrategias import GuardiaVolatilidad  # noqa: E402

FEE = 0.003
N_EVAL = 500
SEMILLA_EVAL = 0
N_ENTRENA = 200
SEMILLA_ENTRENA = 100_000
GRID_SALIDA = [0.3, 0.4, 0.5, 0.7, 0.9]  # vol. anual para retirar la liquidez
GRID_FACTOR = [0.5, 0.75, 1.0]           # reentrada = salida * factor (1.0 = sin histeresis)
VOLS_SENS = [0.2, 0.4, 0.6, 0.8, 1.0]
FEES_SENS = [0.0005, 0.003, 0.01]
CAPITAL_TOTAL = 2 * S.CAP_Y              # valor inicial del capital de Tendera
SEMILLA_RUIDO = 10_000_000               # semilla de ruido = semilla_trayectoria + esto


def precios_de(esc, semilla, sigma=None):
    cfg = ESCENARIOS[esc]
    sg = cfg["sigma"] if sigma is None else sigma
    return generar_precios(S.P0, sg, S.PASOS, semilla, cfg["lam_anual"], cfg["sigma_salto"])


def evaluar(esc, semillas, estrategia, fee=FEE, umbral=None, sigma=None,
            factor=0.75, tam_ruido=S.TAM_RUIDO):
    """estrategia: 'pasivo', 'guardia' o 'hodl'. Devuelve una fila por trayectoria."""
    filas = []
    for s in semillas:
        pr = precios_de(esc, s, sigma)
        if estrategia == "hodl":
            h = S.hodl(pr)
            filas.append({"vf": h["valor_final"], "hodl": h["valor_final"],
                          "fees": 0.0, "mdd": h["mdd"], "salidas": 0})
            continue
        g = (GuardiaVolatilidad(salida=umbral, factor_entrada=factor)
             if estrategia == "guardia" else None)
        r = S.correr(pr, fee, s + SEMILLA_RUIDO, guardia=g, tam_ruido=tam_ruido)
        filas.append({"vf": r["valor_final"], "hodl": r["hodl_final"],
                      "fees": r["fees"], "mdd": r["mdd"], "salidas": r["salidas"]})
    return filas


def resumen(filas):
    vf = [f["vf"] for f in filas]
    hd = [f["hodl"] for f in filas]
    fees = [f["fees"] for f in filas]
    dif = [a - b for a, b in zip(vf, hd)]
    il = [d - c for d, c in zip(dif, fees)]  # LP - HODL = comisiones + perdida impermanente
    return {
        "final_value_mean": stats.fmean(vf),
        "final_value_median": stats.median(vf),
        "hodl_final_mean": stats.fmean(hd),
        "max_drawdown_mean": stats.fmean(f["mdd"] for f in filas),
        "beats_hodl_prob": sum(1 for d in dif if d > 0) / len(dif),
        "fees_mean": stats.fmean(fees),
        "impermanent_loss_mean": stats.fmean(il),
        "lp_minus_hodl_mean": stats.fmean(dif),
        "salidas_mean": stats.fmean(f["salidas"] for f in filas),
    }


def vol_referencia():
    """Volatilidad anual de un dato REAL publico (MSFT mensual 2000-2010, vega_datasets)."""
    ruta = os.path.join(RAIZ, "data", "msft_mensual_2000_2010.csv")
    with open(ruta, newline="") as f:
        precios = [float(r["price"]) for r in csv.DictReader(f)]
    rets = [math.log(b / a) for a, b in zip(precios, precios[1:])]
    return stats.stdev(rets) * math.sqrt(12)


def tabla(titulo, cabecera, filas):
    print(f"\n{titulo}")
    print(" | ".join(f"{c:>16}" for c in cabecera))
    for fila in filas:
        print(" | ".join(f"{v:>16}" for v in fila))


def fmt(x, dec=0):
    return f"{x:,.{dec}f}"


def main():
    t0 = time.time()
    eval_semillas = range(SEMILLA_EVAL, SEMILLA_EVAL + N_EVAL)
    entr_semillas = range(SEMILLA_ENTRENA, SEMILLA_ENTRENA + N_ENTRENA)

    print("== 0. Referencia con datos reales (solo calibracion, no entra en el modelo)")
    print(f"Vol. anual MSFT mensual 2000-2010 (dato real, 123 meses): {vol_referencia():.1%}")
    print(f"Capital de Tendera: {CAPITAL_TOTAL:,.0f} y (valor inicial). Comision base: {FEE:.2%}")

    print("\n== 1. Sintonizacion de la guardia (semillas de entrenamiento)")
    filas_t = []
    base_t = resumen(evaluar("gbm", entr_semillas, "pasivo"))["lp_minus_hodl_mean"]
    base_s = resumen(evaluar("saltos", entr_semillas, "pasivo"))["lp_minus_hodl_mean"]
    filas_t.append(["LP pasivo", "-", "-", fmt(base_t), fmt(base_s), fmt((base_t + base_s) / 2)])
    mejor, mejor_val = None, -math.inf
    for u in GRID_SALIDA:
        for fct in GRID_FACTOR:
            g = resumen(evaluar("gbm", entr_semillas, "guardia", umbral=u, factor=fct))
            s_ = resumen(evaluar("saltos", entr_semillas, "guardia", umbral=u, factor=fct))
            media = (g["lp_minus_hodl_mean"] + s_["lp_minus_hodl_mean"]) / 2
            filas_t.append([f"guardia", f"{u:.0%}", f"{fct}", fmt(g["lp_minus_hodl_mean"]),
                            fmt(s_["lp_minus_hodl_mean"]), fmt(media)])
            if media > mejor_val:
                mejor, mejor_val = (u, fct), media
    tabla("LP - HODL medio en entrenamiento (valor final, y)",
          ["estrategia", "salida", "reentrada x", "GBM", "saltos", "media"], filas_t)
    mejor_u, mejor_f = mejor
    print(f"Parametros elegidos por entrenamiento: salida={mejor_u:.0%}, reentrada x{mejor_f}")

    print(f"\n== 2. Evaluacion principal ({N_EVAL} trayectorias por escenario)")
    ev = {}
    for esc, cfg in ESCENARIOS.items():
        ev[esc] = {
            "LP pasivo": resumen(evaluar(esc, eval_semillas, "pasivo")),
            "Tendera guardia": resumen(evaluar(esc, eval_semillas, "guardia",
                                               umbral=mejor_u, factor=mejor_f)),
            "HODL": resumen(evaluar(esc, eval_semillas, "hodl")),
        }
        filas = []
        for nombre, r in ev[esc].items():
            if nombre == "HODL":
                prob = "-"
                il = "-"
                fees = "-"
            else:
                prob = f"{r['beats_hodl_prob']:.1%}"
                il = fmt(r["impermanent_loss_mean"])
                fees = fmt(r["fees_mean"])
            filas.append([nombre, fmt(r["final_value_mean"]), fmt(r["final_value_median"]),
                          f"{r['max_drawdown_mean']:.1%}", prob, fees, il,
                          fmt(r["lp_minus_hodl_mean"]), fmt(r["salidas_mean"], 2)])
        tabla(f"Escenario '{esc}': {cfg['nombre']}",
              ["estrategia", "valor medio", "mediana", "MDD medio", "P(>HODL)",
               "comisiones", "perd.imperm.", "LP-HODL medio", "salidas/med"], filas)

    print(f"\n== 3. Sensibilidad (LP pasivo, GBM, {N_EVAL} trayectorias): LP - HODL medio")
    sens = []
    filas_s = []
    for v in VOLS_SENS:
        fila = [f"vol {v:.0%}"]
        for f in FEES_SENS:
            r = resumen(evaluar("gbm", eval_semillas, "pasivo", fee=f, sigma=v))
            sens.append({"volatility": float(v), "fee": float(f),
                         "lp_minus_hodl_mean": float(r["lp_minus_hodl_mean"])})
            fila.append(fmt(r["lp_minus_hodl_mean"]))
        filas_s.append(fila)
    tabla("Filas: volatilidad anual. Columnas: comision " + ", ".join(f"{f:.2%}" for f in FEES_SENS),
          ["volatilidad"] + [f"fee {f:.2%}" for f in FEES_SENS], filas_s)

    print("\n== 4. Tendera frente a LP pasivo por volatilidad (GBM, comision 0.30%)")
    filas_g = []
    for v in VOLS_SENS:
        rp = resumen(evaluar("gbm", eval_semillas, "pasivo", sigma=v))
        rg = resumen(evaluar("gbm", eval_semillas, "guardia", umbral=mejor_u,
                             factor=mejor_f, sigma=v))
        filas_g.append([f"vol {v:.0%}", fmt(rp["lp_minus_hodl_mean"]),
                        fmt(rg["lp_minus_hodl_mean"]), fmt(rg["salidas_mean"], 2)])
    tabla("LP - HODL medio", ["volatilidad", "LP pasivo", "Tendera", "salidas/med"], filas_g)

    print("\n== 5. Sensibilidad al volumen del trader de ruido (LP pasivo, comision 0.30%)")
    filas_r = []
    for v in (0.4, 0.6):
        for escala in (0.5, 1.0, 2.0):
            r = resumen(evaluar("gbm", eval_semillas, "pasivo", sigma=v,
                                tam_ruido=S.TAM_RUIDO * escala))
            filas_r.append([f"vol {v:.0%}", f"x{escala}", fmt(r["fees_mean"]),
                            fmt(r["impermanent_loss_mean"]), fmt(r["lp_minus_hodl_mean"]),
                            f"{r['beats_hodl_prob']:.1%}"])
    tabla("Volumen de ruido x escala de referencia",
          ["volatilidad", "ruido", "comisiones", "perd.imperm.", "LP-HODL medio", "P(>HODL)"],
          filas_r)

    # Trayectoria representativa: GBM, semilla 0, LP pasivo, con series completas.
    pr0 = precios_de("gbm", SEMILLA_EVAL)
    rep = S.correr(pr0, FEE, SEMILLA_EVAL + SEMILLA_RUIDO, serie=True)

    def redondear(xs):
        return [round(float(x), 6) for x in xs]

    base = ev["gbm"]
    hodl_m = base["HODL"]["final_value_mean"]
    descripcion = (
        "Laboratorio simulado de un AMM x*y=k (estilo Uniswap v2, comision 0.30%) con un "
        "arbitrajista optimo, un trader de ruido y el resto del mercado como LP pasivo. "
        f"Escenario base: {ESCENARIOS['gbm']['nombre']}; {N_EVAL} trayectorias de "
        f"{S.PASOS} pasos horarios (semillas 0-{N_EVAL - 1}). Capital inicial "
        f"{CAPITAL_TOTAL:,.0f} y; HODL de referencia: valor final medio {hodl_m:,.0f} y "
        f"(mediana {base['HODL']['final_value_median']:,.0f}). Datos sinteticos."
    )
    resultado = {
        "meta": {
            "description": descripcion,
            "simulated": True,
            "seed": int(SEMILLA_EVAL),
            "steps": int(S.PASOS),
        },
        "price_path": redondear(pr0),
        "pool_path": {
            "reserve_x": redondear(rep["reserve_x"]),
            "reserve_y": redondear(rep["reserve_y"]),
        },
        "strategies": [
            {
                "name": "LP pasivo (comision 0.30%)",
                "final_value_mean": float(base["LP pasivo"]["final_value_mean"]),
                "final_value_median": float(base["LP pasivo"]["final_value_median"]),
                "max_drawdown_mean": float(base["LP pasivo"]["max_drawdown_mean"]),
                "beats_hodl_prob": float(base["LP pasivo"]["beats_hodl_prob"]),
                "fees_mean": float(base["LP pasivo"]["fees_mean"]),
                "impermanent_loss_mean": float(base["LP pasivo"]["impermanent_loss_mean"]),
            },
            {
                "name": (f"Tendera: guardia de volatilidad (salida {mejor_u:.0%}, "
                         f"reentrada {mejor_u * mejor_f:.0%} anual)"),
                "final_value_mean": float(base["Tendera guardia"]["final_value_mean"]),
                "final_value_median": float(base["Tendera guardia"]["final_value_median"]),
                "max_drawdown_mean": float(base["Tendera guardia"]["max_drawdown_mean"]),
                "beats_hodl_prob": float(base["Tendera guardia"]["beats_hodl_prob"]),
                "fees_mean": float(base["Tendera guardia"]["fees_mean"]),
                "impermanent_loss_mean": float(base["Tendera guardia"]["impermanent_loss_mean"]),
            },
        ],
        "sensitivity": sens,
    }
    ruta = os.path.join(RAIZ, "out", "results.json")
    os.makedirs(os.path.dirname(ruta), exist_ok=True)
    with open(ruta, "w") as f:
        json.dump(resultado, f, separators=(",", ":"))
    print(f"\nEscrito: {ruta}  ({os.path.getsize(ruta) / 1024:.0f} KB)")
    print(f"Tiempo total: {time.time() - t0:.1f} s")


if __name__ == "__main__":
    main()
