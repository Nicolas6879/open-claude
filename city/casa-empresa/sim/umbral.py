"""Umbral de rentabilidad: cuantas veces la demanda base hace falta para no perder
(y para ganar una cantidad objetivo al mes en el anio 3).

Multiplica a la vez la demanda (instalaciones organicas, aceptacion del regalo,
conversion a Laboratorio, compra de cosmeticos y ventas de aulas) por un factor m.
Escenario C (aula y regalo, equipo cero). Monte Carlo con n trayectorias por factor.

Uso: PYTHONDONTWRITEBYTECODE=1 python3 umbral.py [--n 1000]
"""
import argparse
import json
import math
import os

import numpy as np

import simulador as S

HERE = os.path.dirname(os.path.abspath(__file__))
# Demanda lineal: su efecto es proporcional. El regalo (bucle viral) se trata aparte porque
# es un proceso de ramificacion: por encima de k = 1 crece sin tope en este modelo.
DEMANDA = ["instalaciones_organicas_semana", "lab_conversion_semana",
           "cosmeticos_compra_semana", "aula_ventas_semana"]
FACTORES = [1, 2, 3, 5, 10, 20, 30, 50, 100, 200, 500]


def margen_mes_anio3(par, aula, seed):
    res = S.simula(par, 0, aula, T=156, seed=seed)
    ult = res["margen_semanal"][:, -52:].sum(axis=1)
    return ult / 12.0                          # USD por mes, media del anio 3


def barre(sup, n, seed, aula, claves, factores):
    out = []
    for m in factores:
        R = np.random.default_rng(seed)
        par = S.muestra_parametros(sup, n, R)
        for k in claves:
            par[k] = par[k] * m
        mm = margen_mes_anio3(par, aula, seed)
        out.append({"m": m, "margen_mes_mediana": float(np.median(mm)),
                    "p_negativo": float(np.mean(mm < 0))})
    return out


def mediana_mes(sup, n, seed, claves, m):
    R = np.random.default_rng(seed)
    par = S.muestra_parametros(sup, n, R)
    for k in claves:
        par[k] = par[k] * m
    return float(np.median(margen_mes_anio3(par, True, seed)))


def bisecta(sup, n, seed, claves, objetivo, lo=1.0, hi=200.0, iters=18):
    """Cruce exacto del margen mensual mediano con objetivo (el margen crece con m).
    Biseccion en escala logaritmica sobre la misma muestra de supuestos (misma semilla)."""
    if mediana_mes(sup, n, seed, claves, lo) >= objetivo:
        return lo
    for _ in range(iters):
        mid = math.sqrt(lo * hi)
        if mediana_mes(sup, n, seed, claves, mid) >= objetivo:
            hi = mid
        else:
            lo = mid
    return round(hi, 2)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=1000)
    args = ap.parse_args()
    sup = S.cargar_supuestos()
    seed = sup["semilla"]
    tabla_todo = barre(sup, args.n, seed, True, DEMANDA, FACTORES)
    tabla_inst = barre(sup, args.n, seed, True, ["instalaciones_organicas_semana"], FACTORES)
    # Bucle viral: instalaciones que genera cada usuaria a lo largo de su vida (valores medianos).
    med = {k: float(v["moda"]) for k, v in sup["parametros"].items() if v.get("dist") == "tri"}
    b, c = med["retencion_b"], med["retencion_c"]
    semanas = np.arange(156)
    L = float(np.sum(c * (1.0 + semanas) ** (-b)))          # semanas-usuaria activas por instalacion
    k_vida = med["regalo_prob"] * med["regalo_aceptacion"] * med["abandono_final"] * L
    viral = {
        "instalaciones_generadas_por_usuaria_media": k_vida,
        "semanas_activas_por_instalacion_medianas": L,
        "aceptacion_critica_para_k_igual_1": (1.0 / (med["regalo_prob"] * med["abandono_final"] * L)),
        "nota": "k = P(regalo) x P(acepta) x h x L. Con k < 1 el regalo solo suma una fraccion; k >= 1 exige aceptacion mayor que 1 con los medianos.",
    }
    res = {
        "bucle_viral": viral,
        "descripcion": "Umbral: factor m sobre la demanda base (escenario C, equipo cero). Margen mensual mediano del anio 3.",
        "demanda_multiplicada": DEMANDA,
        "tabla_toda_la_demanda": tabla_todo,
        "tabla_solo_adquisicion": tabla_inst,
        "umbral_1000_mes_cuatro_palancas": bisecta(sup, args.n, seed, DEMANDA, 1000.0),
        "umbral_1000_mes_solo_instalaciones": bisecta(sup, args.n, seed, ["instalaciones_organicas_semana"], 1000.0),
        "umbral_no_perder_cuatro_palancas": bisecta(sup, args.n, seed, DEMANDA, 0.0),
        "definicion": "m multiplica a la vez instalaciones organicas, conversion a Laboratorio, cosmeticos y ventas de aulas (cuatro palancas). En la fila 'solo instalaciones' solo se multiplican las instalaciones organicas.",
        "nota": "Monte Carlo con los supuestos de sim/supuestos.json; el factor se aplica a la mediana de cada supuesto de demanda.",
    }
    ruta = os.path.join(HERE, "out", "umbral.json")
    with open(ruta, "w", encoding="utf-8") as f:
        json.dump(res, f, ensure_ascii=False, indent=1)
    for fila in tabla_todo:
        print("m=%4d  margen mensual mediano anio 3 = %10.1f  P(<0)=%.2f" % (fila["m"], fila["margen_mes_mediana"], fila["p_negativo"]))
    print("umbral 1000 USD/mes, cuatro palancas:", res["umbral_1000_mes_cuatro_palancas"])
    print("umbral 1000 USD/mes, solo instalaciones:", res["umbral_1000_mes_solo_instalaciones"])
    print("umbral 0 USD/mes, cuatro palancas:", res["umbral_no_perder_cuatro_palancas"])


if __name__ == "__main__":
    main()
