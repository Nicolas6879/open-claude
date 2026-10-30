"""Mundos de control para calibrar el instrumento antes de tocar la muestra final.

- Mundo nulo: retornos en exceso del tramo de SELECCION (1990-2013) remuestreados con
  bootstrap estacionario y desmediados. Ninguna estrategia debe ganar de verdad.
  Solo se usa el tramo de seleccion: la muestra final real no entra en ningun mundo.
- Mundo plantado: como el nulo, mas un efecto conocido: el retorno del dia t recibe
  a * S_{t-1}, donde S es la senal de tendencia 60 dias (LS). Su SR bruto anual es s.
  El instrumento debe encontrarlo (potencia).
"""
import numpy as np
import pandas as pd

from . import datos as D
from . import pipeline as PL
from . import protocolo as P


def _indices_extendidos(S, n, L, rng):
    """Bootstrap estacionario de longitud n sobre una muestra de tamano S."""
    restart = rng.random(n) < (1.0 / L)
    restart[0] = True
    arranque = rng.integers(0, S, size=n)
    t = np.arange(n)
    ultimo = np.maximum.accumulate(np.where(restart, t, 0))
    return (arranque[ultimo] + (t - ultimo)) % S


def base_seleccion():
    """Retornos y tipo sin riesgo del tramo de seleccion del S&P 500 (unica fuente real usada)."""
    d = PL.d_sp500()
    fin = pd.Timestamp(P.PRIMARIO["fin_seleccion"])
    mask = (d["fechas"] <= fin)
    R = d["R"][0][mask]
    rf = d["rf"][mask]
    return R, rf


def mundo(tipo, rng, s_plantado=0.0, base=None, fechas=None, bloque=None, modo="signo"):
    """tipo: 'nulo' o 'plantado'. modo:
      'iid'    : remuestreo iid de excesos desmediados (nulo estricto; pierde clustering de vol)
      'bloques': remuestreo por bloques de los excesos (DIAGNOSTICO: filtra estructura de la muestra)
      'signo'  : magnitudes |exceso| remuestreadas por bloques x signo iid +-1 (nulo recomendado:
                 cero retorno esperado para toda estrategia, conserva el clustering de volatilidad)
    Devuelve dict compatible con PL.d_sp500(sint)."""
    R_sel, rf_sel = base if base is not None else base_seleccion()
    exc = R_sel - rf_sel
    exc = exc - exc.mean()                         # sin deriva
    n = len(fechas)
    if modo == "iid":
        idx = _indices_extendidos(len(exc), n, 1, rng)
        R = exc[idx] + rf_sel[idx]
    elif modo == "bloques":
        L = P.BLOQUE["diario"] if bloque is None else bloque
        idx = _indices_extendidos(len(exc), n, L, rng)
        R = exc[idx] + rf_sel[idx]
    elif modo == "signo":
        L = P.BLOQUE["diario"] if bloque is None else bloque
        idx = _indices_extendidos(len(exc), n, L, rng)
        eps = rng.choice([-1.0, 1.0], size=n)
        R = eps * np.abs(exc[idx]) + rf_sel[idx]
    else:
        raise ValueError(modo)
    if tipo == "nulo":
        pass
    elif tipo == "plantado":
        sigma = exc.std(ddof=1)
        a = s_plantado * sigma / np.sqrt(252.0)    # alfa diario bruto que da SR = s_plantado
        lps = np.empty(n)
        lps[0] = 0.0
        R = R.copy()
        for t in range(1, n):
            # senal TSMOM 60 dias en t-1 (solo info <= t-1), aplicada al retorno de t
            sg = np.sign(lps[t - 1] - lps[t - 1 - 60]) if t - 1 >= 60 else 0.0
            R[t] = R[t] + a * sg
            lps[t] = lps[t - 1] + np.log1p(R[t])
    else:
        raise ValueError(tipo)
    precio = 100.0 * np.cumprod(np.r_[1.0, 1.0 + R[1:]])
    return dict(fechas=fechas, precio=precio, R=R, rf=rf_sel[idx])


def ejecutar_mundo(args):
    """Funcion para multiprocessing: un mundo completo (seleccion + muestra final)."""
    tipo, semilla, s_plant, fechas, base, bloque, modo = args
    rng = np.random.default_rng(semilla)
    sint = mundo(tipo, rng, s_plantado=s_plant, base=base, fechas=fechas, bloque=bloque, modo=modo)
    d = PL.d_sp500(sint)
    res = PL.correr("sp500", d, semilla=semilla, real=False)
    sel = res["seleccion"]
    # Control naive: mejor SR de seleccion, p crudo en la muestra final (sin BH ni puerta)
    mejor = sel["mejor_sr_seleccion"]["config"]
    fin_naive = PL.etapa_muestra_final("sp500", d, PL.SPEC["sp500"], [mejor],
                                       sel["ebar_todas"], semilla + 1)
    r0 = fin_naive["finalistas"][0]
    fin = res["muestra_final"]
    return dict(
        tipo=tipo, modo=modo, s=float(s_plant), bloque=(P.BLOQUE["diario"] if bloque is None else bloque),
        semilla=int(semilla), n_configs=sel["n_configs"],
        puerta=bool(sel["puerta"]), p_spa_alfa=sel["p_spa_alfa"], p_rc_alfa=sel["p_rc_alfa"],
        campeon=res["campeon"],
        familia_campeon=(next((t["familia"] for t in sel["tabla"] if t["config"] == res["campeon"]), None)
                         if res["campeon"] else None),
        pasa_finalistas=(None if fin is None else [r["config"] for r in fin["finalistas"]
                                                    if r["es_finalista"] and r["pasa"]]),
        naive=dict(config=mejor, p_dinero=r0["p_dinero"], p_alfa=r0["p_alfa"], sr=r0["sr_anual"]),
        sr_campeon_seleccion=(None if not res["campeon"] else
                              next(t["sr_anual"] for t in sel["tabla"] if t["config"] == res["campeon"])),
    )
