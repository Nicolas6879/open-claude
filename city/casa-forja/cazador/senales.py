"""Familias de hipotesis. Cada funcion devuelve lista de (familia, nombre, W).

Causalidad: W[t] usa solo informacion hasta t (los calendarios usan t+1 porque el calendario
es conocido de antemano; el peso se aplica a t+1 en el motor, nunca antes). Tests en
tests/test_causalidad.py.
"""
import math

import numpy as np
import pandas as pd
from numba import njit

from . import protocolo as P

KS_TSMOM = [2, 3, 5, 8, 10, 15, 20, 30, 40, 50, 60, 80, 100, 120, 150, 200, 252]
FS_MA = [5, 10, 15, 20, 30, 40, 50]
SS_MA = [60, 100, 150, 200, 250]
NS_Z = [5, 10, 20, 40, 60, 120, 250]
TH_Z = [0.5, 1.0, 1.5, 2.0]
NN_DON = [20, 40, 60, 100, 150, 200]
SIG_VT = [0.05, 0.08, 0.10, 0.12, 0.15, 0.20]
L_VT = [10, 20, 40, 60, 120, 250]
KS_REG = [60, 120, 252]
Q_REG = [0.5, 0.7, 0.9]
L_VOL = [10, 20, 60]
MULT_VOL = [0.8, 1.0, 1.2]
L_FAC = [1, 3, 6, 12, 24, 36]


def _nan0(x):
    return np.where(np.isfinite(x), x, 0.0)


def media_movil(x, n):
    s = pd.Series(x).rolling(n, min_periods=n).mean().to_numpy()
    return s


def desv_movil(x, n):
    return pd.Series(x).rolling(n, min_periods=n).std(ddof=1).to_numpy()


def _calendario(fechas):
    fechas = pd.DatetimeIndex(fechas)
    clave = fechas.strftime("%Y-%m")
    serie = pd.Series(np.arange(len(fechas)), index=fechas)
    pos = serie.groupby(clave).cumcount().to_numpy()
    tam = pd.Series(1, index=fechas).groupby(clave).transform("size").to_numpy()
    return {
        "dias_fin": tam - pos - 1,     # 0 en el ultimo dia habil del mes
        "dias_ini": pos,               # 0 en el primer dia habil del mes
        "mes": fechas.month.to_numpy(),
        "dia_sem": fechas.day_of_week.to_numpy(),
    }


def _siguiente(x):
    """Desplaza un calendario un dia hacia delante: W[t] = f(t+1)."""
    y = np.zeros_like(x, dtype=float)
    y[:-1] = x[1:]
    return y


# ------------------------------------------------------------ familias diarias

def tsmom(lp, r, anual):
    out = []
    T = len(lp)
    vol = desv_movil(r, 20) * math.sqrt(anual)
    escala = np.clip(P.ANCLA_VOL_TSMOM / np.where(vol > 0, vol, np.nan), 0, 2.0)
    escala = _nan0(escala)
    for k in KS_TSMOM:
        R = np.full(T, np.nan)
        R[k:] = lp[k:] - lp[:-k]
        s = _nan0(np.sign(R))
        out.append(("tsmom", f"LS_k{k}", s))
        out.append(("tsmom", f"LO_k{k}", np.maximum(s, 0)))
        out.append(("tsmom", f"volLS_k{k}", s * escala))
        out.append(("tsmom", f"volLO_k{k}", np.maximum(s, 0) * escala))
    return out


def cruce_medias(lp):
    out = []
    for f in FS_MA:
        mf = media_movil(lp, f)
        for s_ in SS_MA:
            ms = media_movil(lp, s_)
            sig = _nan0(np.sign(mf - ms))
            out.append(("cruce", f"LS_{f}_{s_}", sig))
            out.append(("cruce", f"LO_{f}_{s_}", np.maximum(sig, 0)))
    return out


def reversion_tendencia(lp, r):
    out = []
    for n in NS_Z:
        m = media_movil(lp, n)
        sd = desv_movil(r, n) * math.sqrt(n)
        z = _nan0((lp - m) / np.where(sd > 0, sd, np.nan))
        for th in TH_Z:
            rev = np.where(z > th, -1.0, np.where(z < -th, 1.0, 0.0))
            out.append(("zscore", f"rev_n{n}_th{th}", rev))
            out.append(("zscore", f"tend_n{n}_th{th}", -rev))
    return out


@njit(cache=False)
def _donchian(p, n, m, permitir_corto):
    T = p.shape[0]
    w = np.zeros(T)
    pos = 0.0
    for t in range(T):
        if t >= n:
            hi = -1e300
            lo = 1e300
            for j in range(t - n, t):
                if p[j] > hi:
                    hi = p[j]
                if p[j] < lo:
                    lo = p[j]
            hi_m = -1e300
            lo_m = 1e300
            for j in range(t - m, t):
                if p[j] > hi_m:
                    hi_m = p[j]
                if p[j] < lo_m:
                    lo_m = p[j]
            # salidas primero, despues entradas (orden fijo, sin mirar el futuro)
            if pos == 1.0 and p[t] < lo_m:
                pos = 0.0
            if pos == -1.0 and p[t] > hi_m:
                pos = 0.0
            if pos == 0.0 and p[t] > hi:
                pos = 1.0
            elif pos == 0.0 and permitir_corto and p[t] < lo:
                pos = -1.0
        w[t] = pos
    return w


def canal_donchian(lp):
    out = []
    for n in NN_DON:
        m = max(n // 2, 2)
        out.append(("donchian", f"LO_n{n}", _donchian(lp, n, m, False)))
        out.append(("donchian", f"LS_n{n}", _donchian(lp, n, m, True)))
    return out


def volatilidad_objetivo(r, anual):
    out = []
    for sig in SIG_VT:
        for L in L_VT:
            vol = desv_movil(r, L) * math.sqrt(anual)
            w = _nan0(np.clip(sig / np.where(vol > 0, vol, np.nan), 0, 1.5))
            out.append(("volobj", f"s{sig}_L{L}", w))
    return out


def regimen_volatilidad_tendencia(lp, r, anual):
    out = []
    vol = pd.Series(desv_movil(r, 20) * math.sqrt(anual))
    cuant = {q: vol.rolling(1000, min_periods=250).quantile(q).to_numpy() for q in Q_REG}
    v = vol.to_numpy()
    T = len(lp)
    for k in KS_REG:
        R = np.full(T, np.nan)
        R[k:] = lp[k:] - lp[:-k]
        tend = np.maximum(_nan0(np.sign(R)), 0)
        for q in Q_REG:
            calma = _nan0(np.where(np.isfinite(cuant[q]), (v <= cuant[q]).astype(float), 0.0))
            out.append(("regimen", f"calma_k{k}_q{q}", tend * calma))
            out.append(("regimen", f"tension_k{k}_q{q}", tend * (1 - calma)))
    return out


def estacionalidad(fechas):
    out = []
    cal = _calendario(fechas)
    fin, ini = cal["dias_fin"], cal["dias_ini"]
    for b in range(0, 4):
        for a in range(1, 5):
            en = ((fin < b) | (ini < a)).astype(float)
            out.append(("estacional", f"fin_mes_b{b}_a{a}", _siguiente(en)))
    for d in range(5):
        out.append(("estacional", f"dia_sem_{d}", _siguiente((cal["dia_sem"] == d).astype(float))))
    mes = cal["mes"]
    for m in range(1, 13):
        out.append(("estacional", f"mes_{m}", _siguiente((mes == m).astype(float))))
    nov_abr = np.isin(mes, [11, 12, 1, 2, 3, 4]).astype(float)
    out.append(("estacional", "nov_abr", _siguiente(nov_abr)))
    return out


def timing_volatilidad(r, anual):
    out = []
    for L in L_VOL:
        sig = pd.Series(desv_movil(r, L) * math.sqrt(anual))
        med = sig.rolling(252, min_periods=126).median().to_numpy()
        s = sig.to_numpy()
        for mult in MULT_VOL:
            umbral = mult * med
            ok = np.isfinite(umbral) & np.isfinite(s)
            calma = _nan0(np.where(ok, (s < umbral).astype(float), 0.0))
            tension = _nan0(np.where(ok, (s > umbral).astype(float), 0.0))
            out.append(("volrel", f"calma_L{L}_m{mult}", calma))
            out.append(("volrel", f"tension_L{L}_m{mult}", tension))
    return out


def familias_diarias(precio, fechas, r=None):
    """Todas las familias de un activo diario. precio: (T,), fechas: DatetimeIndex."""
    precio = np.asarray(precio, dtype=float)
    lp = np.log(precio)
    if r is None:
        r = np.diff(lp, prepend=lp[0])
    anual = P.PERIODOS_ANUALES["diario"]
    out = []
    out += tsmom(lp, r, anual)
    out += cruce_medias(lp)
    out += reversion_tendencia(lp, r)
    out += canal_donchian(precio)
    out += volatilidad_objetivo(r, anual)
    out += regimen_volatilidad_tendencia(lp, r, anual)
    out += estacionalidad(fechas)
    out += timing_volatilidad(r, anual)
    return out


def familias_tsmom_ma(precio, fechas=None):
    """Subconjunto para series de materias primas (WTI)."""
    precio = np.asarray(precio, dtype=float)
    lp = np.log(precio)
    r = np.diff(lp, prepend=lp[0])
    return tsmom(lp, r, P.PERIODOS_ANUALES["diario"]) + cruce_medias(lp)


# ---------------------------------------------------------------- mensuales

def factor_mensual(F):
    """Factor de senal de tendencia por media movil de L meses (LS y LO)."""
    out = []
    s = pd.Series(F)
    for L in L_FAC:
        m = s.rolling(L, min_periods=L).mean().to_numpy()
        sig = _nan0(np.sign(m))
        out.append(("factor", f"LS_L{L}", sig))
        out.append(("factor", f"LO_L{L}", np.maximum(sig, 0)))
    return out


# -------------------------------------------------------- machine learning

def _features(r, lp, anual):
    T = len(r)
    cols = []
    for lag in [0, 1, 2, 4, 9, 19]:
        x = np.full(T, np.nan)
        x[lag:] = r[: T - lag] if lag else r
        cols.append(x)
    vol = desv_movil(r, 20) * math.sqrt(anual)
    cols.append(vol)
    mom = np.full(T, np.nan)
    mom[20:] = lp[20:] - lp[:-20]
    cols.append(mom)
    return np.column_stack(cols)


def ml_configs(precio, fechas, r=None):
    """Clasificadores de direccion con validacion walk-forward purgada (purga = 5 dias)."""
    from sklearn.ensemble import HistGradientBoostingClassifier
    from sklearn.linear_model import LogisticRegression
    from sklearn.preprocessing import StandardScaler

    precio = np.asarray(precio, dtype=float)
    lp = np.log(precio)
    if r is None:
        r = np.diff(lp, prepend=lp[0])
    anual = P.PERIODOS_ANUALES["diario"]
    T = len(lp)
    X = _features(r, lp, anual)
    y = np.full(T, np.nan)
    y[:-1] = (r[1:] > 0).astype(float)
    anios = np.asarray(fechas.year)
    primero = {a: np.where(anios == a)[0][0] for a in np.unique(anios)}
    purga = 5
    cfgs = {
        "logit_A": (X[:, :6], "logit"),
        "logit_B": (X, "logit"),
        "hgb_A": (X[:, :6], "hgb"),
    }
    salida = []
    for nombre_mod, (Xm, tipo) in cfgs.items():
        probs = np.full(T, np.nan)
        mdl = None
        anio_ajuste = None
        for a in np.unique(anios):
            if a < anios[0] + 3:
                continue
            fin_train = primero[a] - purga - 1
            if fin_train < 250:
                continue
            tr = np.arange(0, fin_train + 1)
            tr = tr[np.isfinite(Xm[tr]).all(axis=1) & np.isfinite(y[tr])]
            te = np.where(anios == a)[0]
            te = te[np.isfinite(Xm[te]).all(axis=1)]
            if len(tr) < 100 or len(te) == 0:
                continue
            if tipo == "logit":
                sc = StandardScaler().fit(Xm[tr])
                mdl = LogisticRegression(max_iter=200, C=1.0).fit(sc.transform(Xm[tr]), y[tr])
                probs[te] = mdl.predict_proba(sc.transform(Xm[te]))[:, 1]
            else:
                # HGB: reentrenamiento cada 2 anios (cada ajuste usa solo datos pasados y purgados)
                if mdl is None or anio_ajuste is None or a - anio_ajuste >= 2:
                    mdl = HistGradientBoostingClassifier(
                        max_depth=2, max_iter=60, learning_rate=0.05, random_state=P.SEMILLA
                    ).fit(Xm[tr], y[tr])
                    anio_ajuste = a
                probs[te] = mdl.predict_proba(Xm[te])[:, 1]
        pesos = _nan0(2 * probs - 1)
        salida.append(("ml", f"{nombre_mod}_LS", pesos))
        salida.append(("ml", f"{nombre_mod}_LO", np.maximum(pesos, 0)))
    return salida


# ------------------------------------------------------- cross-section (acciones)

PARES = [("KO", "PEP"), ("XOM", "CVX"), ("JPM", "BAC"), ("MRK", "PFE"), ("PG", "JNJ")]


def _fin_de_mes(fechas):
    mes = pd.DatetimeIndex(fechas).to_period("M")
    ultimo = np.zeros(len(fechas), dtype=bool)
    ultimo[:-1] = mes[:-1] != mes[1:]
    ultimo[-1] = True
    return ultimo


def _rellenar_hacia_delante(D):
    """D: (I, T) con NaN salvo en fechas de decision. Propaga la ultima decision."""
    out = D.copy()
    for t in range(1, out.shape[1]):
        mask = np.isnan(out[:, t])
        out[mask, t] = out[mask, t - 1]
    # antes de la primera decision mensual no hay posicion (corrige un NaN que contaminaba acciones20)
    return np.where(np.isnan(out), 0.0, out)


@njit(cache=False)
def _estado_par(z, th, salida):
    T = z.shape[0]
    w = np.zeros(T)
    pos = 0.0
    for t in range(T):
        if np.isnan(z[t]):
            w[t] = 0.0
            continue
        if pos == 0.0:
            if z[t] > th:
                pos = -1.0
            elif z[t] < -th:
                pos = 1.0
        elif abs(z[t]) < salida:
            pos = 0.0
        w[t] = pos
    return w


def cross_seccion(lps, R, fechas):
    """lps: (I, T) log-precios; R: (I, T) retornos. Devuelve lista (familia, nombre, W (I, T))."""
    I, T = lps.shape
    fin_mes = _fin_de_mes(fechas)
    out = []
    for k in [21, 63, 126, 252]:
        S = np.full((I, T), np.nan)
        S[:, k:] = lps[:, k:] - lps[:, :-k]
        dec_lo = np.full((I, T), np.nan)
        dec_ls = np.full((I, T), np.nan)
        for t in np.where(fin_mes)[0]:
            s = S[:, t]
            if np.isnan(s).any():
                dec_lo[:, t] = 0.0
                dec_ls[:, t] = 0.0
                continue
            orden = np.argsort(s)
            w_lo = np.zeros(I)
            w_lo[orden[-4:]] = 0.25
            w_ls = w_lo.copy()
            w_ls[orden[:4]] = -0.25
            dec_lo[:, t] = w_lo
            dec_ls[:, t] = w_ls
        out.append(("cs_mom", f"LO_top4_k{k}", _rellenar_hacia_delante(dec_lo)))
        out.append(("cs_mom", f"LS_top4_k{k}", _rellenar_hacia_delante(dec_ls)))
    for k in [21]:
        S = np.full((I, T), np.nan)
        S[:, k:] = lps[:, k:] - lps[:, :-k]
        dec_lo = np.full((I, T), np.nan)
        dec_ls = np.full((I, T), np.nan)
        for t in np.where(fin_mes)[0]:
            s = S[:, t]
            if np.isnan(s).any():
                dec_lo[:, t] = 0.0
                dec_ls[:, t] = 0.0
                continue
            orden = np.argsort(s)
            w_lo = np.zeros(I)
            w_lo[orden[:4]] = 0.25
            w_ls = w_lo.copy()
            w_ls[orden[-4:]] = -0.25
            dec_lo[:, t] = w_lo
            dec_ls[:, t] = w_ls
        out.append(("cs_rev", f"LO_bot4_k{k}", _rellenar_hacia_delante(dec_lo)))
        out.append(("cs_rev", f"LS_rev_k{k}", _rellenar_hacia_delante(dec_ls)))
    return out


def pares(nombres, lps, cols_a_b=PARES):
    """Pares pre-registrados. nombres: lista de tickers en el mismo orden que filas de lps."""
    idx = {n: i for i, n in enumerate(nombres)}
    out = []
    I, T = lps.shape
    for a, b in cols_a_b:
        ia, ib = idx[a], idx[b]
        spread = lps[ia] - lps[ib]
        s_ser = pd.Series(spread)
        for n in [20, 60]:
            m = s_ser.rolling(n, min_periods=n).mean().to_numpy()
            sd = s_ser.rolling(n, min_periods=n).std(ddof=1).to_numpy()
            z = (spread - m) / np.where(sd > 0, sd, np.nan)
            for th in [1.5, 2.0]:
                st = _estado_par(z, th, 0.5)
                W = np.zeros((I, T))
                W[ia] = 0.5 * st
                W[ib] = -0.5 * st
                out.append(("par", f"{a}_{b}_n{n}_th{th}", W))
    return out
