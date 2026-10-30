"""Graficos SVG pequenos a partir de out/*.json y out/*.csv. Uso: python3 graficos.py"""
import json
import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

RAIZ = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(RAIZ, "out")
GR = os.path.join(RAIZ, "graficos")


def _estilo():
    plt.rcParams.update({"font.size": 10, "axes.spines.top": False, "axes.spines.right": False,
                         "figure.dpi": 100})


def calibracion():
    ruta = os.path.join(OUT, "numeros.json")
    if not os.path.exists(ruta):
        return
    with open(ruta) as f:
        filas = {r["mundo"]: r for r in json.load(f)["calibracion"]}
    pares = [("nulo_signo (campeon)", "nulo signo\n(estricto)"), ("nulo_iid (campeon)", "nulo iid"),
             ("diagnostico_nulo_bloques (campeon)", "nulo bloques\n(diagnostico)"),
             ("frontera sin costes (campeon)", "frontera\nsin costes"),
             ("plantado_s0.3 (campeon)", "plantado\nSR 0.3"), ("plantado_s0.6 (campeon)", "plantado\nSR 0.6")]
    etiquetas, tasas, ics = [], [], []
    for clave, lab in pares:
        if clave in filas:
            r = filas[clave]
            etiquetas.append(lab)
            tasas.append(r["tasa"])
            ics.append(r["IC95_exacto"])
    if not tasas:
        return
    _estilo()
    fig, ax = plt.subplots(figsize=(7.5, 3.8))
    err = np.array([[t - lo, hi - t] for t, (lo, hi) in zip(tasas, ics)]).T
    colores = ["#2b6cb0" if "nulo" in e or "frontera" in e else "#2f855a" for e in etiquetas]
    ax.bar(range(len(tasas)), tasas, color=colores, yerr=err, capsize=4)
    ax.axhline(0.05, color="#c53030", ls="--", lw=1)
    ax.text(len(tasas) - 0.5, 0.055, "5 % (referencia)", color="#c53030", ha="right", fontsize=8)
    ax.set_xticks(range(len(tasas)), etiquetas, fontsize=8)
    ax.set_ylabel("fraccion con campeon (IC95 exacto)")
    ax.set_title("Calibracion: falsos positivos (azul) y potencia (verde)")
    fig.tight_layout()
    fig.savefig(os.path.join(GR, "calibracion_falsos_positivos_potencia.svg"))
    plt.close(fig)


def curva_capital():
    ruta = os.path.join(OUT, "curva_capital.csv")
    if not os.path.exists(ruta):
        return
    df = pd.read_csv(ruta, parse_dates=["fecha"])
    _estilo()
    fig, ax = plt.subplots(figsize=(7, 3.6))
    ax.plot(df.fecha, df.capital_estrategia, label="estrategia (Kelly 0,5)", color="#2b6cb0")
    ax.plot(df.fecha, df.capital_bh, label="B&H indice", color="#718096", ls="--")
    ax.set_ylabel("capital simulado")
    ax.set_title("Muestra final 2014-2022 (paper trading, capital simulado)")
    ax.legend(frameon=False)
    fig.tight_layout()
    fig.savefig(os.path.join(GR, "curva_capital_muestra_final.svg"))
    plt.close(fig)


if __name__ == "__main__":
    os.makedirs(GR, exist_ok=True)
    calibracion()
    curva_capital()
    print("graficos listos")
