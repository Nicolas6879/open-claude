"""Intervalos de confianza (IC95) y desglose de comisiones. Reproducible.

Uso:  PYTHONDONTWRITEBYTECODE=1 python3 intervalos.py     (unos 30 s)

Que significa el "±" del README: el semiancho del IC95 de la media,
    h = 1,96 * sd / sqrt(n),
con sd la desviacion muestral de la diferencia (LP - HODL) por trayectoria y n = 500.
Las trayectorias estan emparejadas (LP y HODL usan el mismo precio), asi que el error
es el de la diferencia. Para una probabilidad p: h = 1,96 * sqrt(p(1-p)/n).
Con esto, el IC de la media es [m - h, m + h].

La guardia usa los parametros que elige run_backtests.py en su seccion 1
(salida 30%, reentrada x0,5); si se cambian alli, cambiar aqui.
"""
import math
import os
import statistics as st
import sys

RAIZ = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, RAIZ)

import run_backtests as R  # noqa: E402
import simulacion as S  # noqa: E402

EVAL = range(R.SEMILLA_EVAL, R.SEMILLA_EVAL + R.N_EVAL)
UMBRAL, FACTOR = 0.3, 0.5


def intervalo_media(xs):
    m = st.fmean(xs)
    return m, 1.96 * st.stdev(xs) / math.sqrt(len(xs))


def resumen_ic(esc, estrategia):
    if estrategia == "guardia":
        filas = R.evaluar(esc, EVAL, "guardia", umbral=UMBRAL, factor=FACTOR)
    else:
        filas = R.evaluar(esc, EVAL, "pasivo")
    dif = [f["vf"] - f["hodl"] for f in filas]
    m, h = intervalo_media(dif)
    p = sum(1 for d in dif if d > 0) / len(dif)
    hp = 1.96 * math.sqrt(p * (1 - p) / len(dif))
    return m, h, p, hp


def desglose(sigma):
    """Comisiones medias de LP pasivo (fee 0,30%, GBM) separadas por origen."""
    tot, ruido, arb, dif = [], [], [], []
    for s in EVAL:
        pr = R.precios_de("gbm", s, sigma)
        r = S.correr(pr, R.FEE, s + R.SEMILLA_RUIDO)
        tot.append(r["fees"])
        ruido.append(r["fees_ruido"])
        arb.append(r["fees_arb"])
        dif.append(r["valor_final"] - r["hodl_final"])
    return st.fmean(tot), st.fmean(ruido), st.fmean(arb), st.fmean(dif)


def main():
    print("== A. Diferencia LP - HODL con IC95 (valor final, y; 500 trayectorias)")
    print("   ± = semiancho del IC95 (ver docstring)")
    for esc in ["gbm", "saltos"]:
        for est, nombre in (("pasivo", "LP pasivo"), ("guardia", "Tendera guardia")):
            m, h, p, hp = resumen_ic(esc, est)
            print(f"{esc:>7} | {nombre:<16} | LP-HODL {m:>8.1f} ± {h:5.1f} "
                  f"(IC95 [{m - h:.1f}, {m + h:.1f}]) | P(>HODL) {p:.1%} ± {hp:.1%}")

    print("\n== B. Comisiones por origen vs volatilidad (LP pasivo, GBM, fee 0,30%)")
    print(f"{'vol':>6} | {'comisiones':>10} | {'ruido':>8} | {'arbitraje':>9} | {'LP-HODL':>8}")
    for v in (0.2, 0.4, 0.6, 0.8, 1.0):
        t, rn, ra, d = desglose(v)
        print(f"{v:>6.0%} | {t:>10.1f} | {rn:>8.1f} | {ra:>9.1f} | {d:>8.1f}")



if __name__ == "__main__":
    main()
