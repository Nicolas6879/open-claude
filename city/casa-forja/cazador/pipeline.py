"""Canalizacion completa: universo -> seleccion (con puerta) -> finalistas -> muestra final.

Flujo (congelado en protocolo.py):
1. Seleccion: se generan todas las configuraciones usando solo datos <= fin_seleccion.
   Se calculan retornos netos de costes, Sharpe deflactado (DSR, N = numero de configs),
   y SPA de Hansen sobre el alfa frente a un B&H con la misma exposicion media.
2. Puerta: si SPA (alfa) >= PUERTA_SPA, no hay candidato. Se para. Sin muestra final.
3. Finalistas: los K mejores por DSR (desempate por SR). Se congelan nombres y exposiciones.
4. Muestra final: se regenera el universo con todos los datos (causal), se evalua solo el
   tramo final y se aplica BH (q = Q_BH) a las 2K pruebas (alfa y dinero) de los finalistas.
   Un finalista pasa solo si rechaza en ambas.
"""
import math

import numpy as np
import pandas as pd

from . import datos as D
from . import motor as M
from . import protocolo as P
from . import senales as S


# ----------------------------------------------------------------- datasets

def _rendim(precio):
    R = np.zeros_like(precio, dtype=float)
    R[..., 1:] = precio[..., 1:] / precio[..., :-1] - 1.0
    return R


def d_sp500(sint=None):
    if sint is None:
        s = D.sp500()
        fechas = s.index
        precio = s.to_numpy()[None, :]
        R = _rendim(precio)
        rf = D.rf_real_diaria(fechas, P.RF_RELLENO_ANUAL)
    else:
        fechas, precio, R, rf = sint["fechas"], sint["precio"], sint["R"], sint["rf"]
        precio = np.atleast_2d(np.asarray(precio, float))
        R = np.asarray(R, float)
    return dict(fechas=pd.DatetimeIndex(fechas), precio=precio, R=np.atleast_2d(R),
                refs=np.atleast_2d(R), rf=np.asarray(rf, float))


def d_wti():
    s = D.wti()
    precio = s.to_numpy()[None, :]
    R = _rendim(precio)
    return dict(fechas=s.index, precio=precio, R=R, refs=R, rf=np.zeros(len(s)))


def d_acciones20():
    df = D.acciones20()
    precio = df.to_numpy().T
    R = _rendim(precio)
    ew = R.mean(axis=0, keepdims=True)
    rf = D.rf_real_diaria(df.index, P.RF_RELLENO_ANUAL)
    return dict(fechas=df.index, precio=precio, R=R, refs=ew, rf=rf,
                nombres=list(df.columns))


def d_franceses():
    fr = D.french_mensual()
    F = fr[["Mkt-RF", "SMB", "HML"]].to_numpy().T
    return dict(fechas=fr.index, precio=None, R=F, refs=F, rf=np.zeros(len(fr)))


def d_momentum():
    m = D.momentum_mensual()
    F = m["Mom"].to_numpy()[None, :]
    return dict(fechas=m.index, precio=None, R=F, refs=F, rf=np.zeros(len(m)))


def d_overnight():
    ohlc = D.sp500_ohlc()
    op, cl = ohlc["Open"].to_numpy(), ohlc["Close"].to_numpy()
    o = np.zeros_like(cl)
    o[1:] = op[1:] / cl[:-1] - 1.0
    i_ = cl / op - 1.0
    cc = _rendim(cl[None, :])
    return dict(fechas=ohlc.index, precio=cl[None, :], R=np.vstack([o, i_]), refs=cc,
                rf=np.zeros(len(cl)))


def d_spy_tr():
    s = D.spy_ajustado()
    fechas = s.index
    precio = s.to_numpy()[None, :]
    R = _rendim(precio)
    return dict(fechas=fechas, precio=precio, R=R, refs=R, rf=D.rf_dtb3_diaria(fechas))


def d_btc():
    s = D.btc()
    precio = s.to_numpy()[None, :]
    R = _rendim(precio)
    return dict(fechas=s.index, precio=precio, R=R, refs=R, rf=np.zeros(len(s)))


SPEC = {
    "sp500": dict(fn=d_sp500, anual=252, bloque=20, spread=P.SPREAD_FINANCIACION_ANUAL, fijo=0.0,
                  seg=P.PRIMARIO),
    "spy_tr": dict(fn=d_spy_tr, anual=252, bloque=20, spread=P.SPREAD_FINANCIACION_ANUAL, fijo=0.0,
                   coste=P.COSTE_IDA_BPS, seg=P.SECUNDARIOS["spy_tr"]),
    "btc": dict(fn=d_btc, anual=252, bloque=20, spread=0.0, fijo=0.0,
                coste=P.COSTE_BTC_BPS, seg=P.SECUNDARIOS["btc"]),
    "acciones20": dict(fn=d_acciones20, anual=252, bloque=20, spread=P.SPREAD_FINANCIACION_ANUAL,
                       fijo=0.0, seg=P.SECUNDARIOS["acciones20"]),
    "franceses": dict(fn=d_franceses, anual=12, bloque=3, spread=0.0, fijo=0.0,
                      seg=P.SECUNDARIOS["franceses"]),
    "momentum": dict(fn=d_momentum, anual=12, bloque=3, spread=0.0, fijo=0.0,
                     seg=P.SECUNDARIOS["momentum"]),
    "wti": dict(fn=d_wti, anual=252, bloque=20, spread=0.0, fijo=0.0, seg=P.SECUNDARIOS["wti"]),
    "overnight": dict(fn=d_overnight, anual=252, bloque=20, spread=0.0,
                      fijo=2 * P.COSTE_IDA_BPS, seg=P.SECUNDARIOS["overnight"]),
}


# ---------------------------------------------------------- universo de configs

def recortar(d, mascara):
    T = len(d["fechas"])
    out = {}
    for k, v in d.items():
        if k == "fechas":
            out[k] = d["fechas"][mascara]
        elif isinstance(v, np.ndarray) and v.shape[-1] == T:
            out[k] = v[..., mascara]
        else:
            out[k] = v
    return out


def _mezclar(lista_cfgs, I, T):
    nombres = [f"{f}:{n}" for f, n, _, _ in lista_cfgs]
    fams = [f for f, _, _, _ in lista_cfgs]
    W = np.zeros((len(lista_cfgs), I, T))
    ref = np.zeros(len(lista_cfgs), dtype=int)
    for k, (_, _, w, rr) in enumerate(lista_cfgs):
        W[k] = w
        ref[k] = rr
    return nombres, fams, W, ref


def _universo_base(nombre, d):
    """Configuraciones que no dependen de retornos netos (sin selector)."""
    T = len(d["fechas"])
    fechas = d["fechas"]
    out = []
    if nombre in ("sp500", "spy_tr"):
        precio = d["precio"][0]
        r = np.diff(np.log(precio), prepend=np.log(precio[0]))
        for f, n, w in S.familias_diarias(precio, fechas, r):
            out.append((f, n, w[None, :], 0))
        for f, n, w in S.ml_configs(precio, fechas, r):
            out.append((f, n, w[None, :], 0))
        I = 1
    elif nombre in ("wti", "btc"):
        for f, n, w in S.familias_tsmom_ma(d["precio"][0], fechas):
            out.append((f, n, w[None, :], 0))
        I = 1
    elif nombre == "acciones20":
        lps = np.log(d["precio"])
        for f, n, w in S.cross_seccion(lps, d["R"], fechas):
            out.append((f, n, w, 0))
        for f, n, w in S.pares(d["nombres"], lps):
            out.append((f, n, w, 0))
        I = d["R"].shape[0]
    elif nombre == "franceses":
        for j in range(3):
            for f, n, w in S.factor_mensual(d["R"][j]):
                W = np.zeros((3, T))
                W[j] = w
                out.append((f, f"{['MktRF','SMB','HML'][j]}_{n}", W, j))
        I = 3
    elif nombre == "momentum":
        for f, n, w in S.factor_mensual(d["R"][0]):
            out.append((f, f"Mom_{n}", w[None, :], 0))
        I = 1
    elif nombre == "overnight":
        out.append(("overnight", "largo_overnight", np.array([np.ones(T), np.zeros(T)]), 0))
        out.append(("overnight", "largo_intradia", np.array([np.zeros(T), np.ones(T)]), 0))
        I = 2
    else:
        raise ValueError(nombre)
    return out, I


def _selector(W_base, net_base, fechas, L_anios, k):
    """Walk-forward: cada anio elige los k mejores (Sharpe neto de costes de los ultimos L anios)."""
    T = len(fechas)
    anios = np.asarray(fechas.year)
    W_out = np.zeros(T)
    primer = anios[0]
    for Y in np.unique(anios):
        if Y < primer + L_anios:
            continue
        ventana = (anios >= Y - L_anios) & (anios < Y)
        sr = M.sharpe_anual(net_base[:, ventana], 252)
        sr = np.where(np.isfinite(sr), sr, -np.inf)
        top = np.argsort(-sr)[:k]
        mY = anios == Y
        W_out[mY] = W_base[top][:, 0, mY].mean(axis=0)
    return W_out


def universo(nombre, d, spec):
    """Devuelve nombres, familias, W (N,I,T) y ref (N,) para el conjunto de datos d."""
    base, I = _universo_base(nombre, d)
    T = len(d["fechas"])
    if nombre in ("sp500", "spy_tr"):
        # Selector walk-forward: necesita retornos netos de las configs base (solo sp500)
        Wb = np.stack([w for _, _, w, _ in base])
        net, _ = M.retornos_netos(Wb, d["R"], d["rf"], spec["anual"], P.COSTE_IDA_BPS,
                                  spec["spread"], spec["fijo"])
        extra = []
        for L in [1, 3, 5]:
            for k in [1, 5]:
                w = _selector(Wb, net, d["fechas"], L, k)
                extra.append(("selector", f"WF_L{L}_top{k}", w[None, :], 0))
        base = base + extra
    nombres, fams, W, ref = _mezclar(base, I, T)
    return nombres, fams, W, ref


# ------------------------------------------------------------- estadisticas

def netos(W, d, spec):
    return M.retornos_netos(W, d["R"], d["rf"], spec["anual"], spec.get("coste", P.COSTE_IDA_BPS),
                            spec["spread"], spec["fijo"])


def referencia(d, ebar, ref):
    """Benchmark con la misma exposicion media (fija ex ante) que cada configuracion."""
    refs = d["refs"][ref]                       # (N, T)
    return ebar[:, None] * refs + (1.0 - ebar[:, None]) * d["rf"][None, :]


def etapa_seleccion(nombre, d_full, spec, semilla):
    fin = pd.Timestamp(spec["seg"]["fin_seleccion"])
    mask = np.asarray(d_full["fechas"] <= fin)
    d = recortar(d_full, mask)
    nombres, fams, W, ref = universo(nombre, d, spec)
    net, Wh = netos(W, d, spec)
    if not np.isfinite(net).all():
        raise RuntimeError(f"NaN en retornos netos ({nombre}): instrumento roto")
    ebar = Wh.sum(axis=1).mean(axis=1)           # (N,) exposicion neta media
    bench = referencia(d, ebar, ref)
    x_dinero = net - d["rf"][None, :]
    D_alfa = net - bench
    sr, p0, dsr, umbral = M.deflated_sharpe(x_dinero)
    rng = np.random.default_rng(semilla)
    T = net.shape[1]
    idx = M.indices_bootstrap(T, P.B_BOOTSTRAP, spec["bloque"], rng)
    spa = M.reality_check_y_spa(D_alfa, idx)
    gate = spa["p_spa"] < P.PUERTA_SPA
    anual = spec["anual"]
    tabla = []
    for k in range(len(nombres)):
        tabla.append(dict(
            config=nombres[k], familia=fams[k], ebar=float(ebar[k]),
            sr_anual=float(M.sharpe_anual(x_dinero[k:k + 1], anual)[0]),
            cagr=float(np.expm1(np.log1p(net[k]).sum() * anual / T)),
            alfa_anual=float(D_alfa[k].mean() * anual),
            t_alfa=float(spa["t"][k]),
            dsr=float(dsr[k]), psr0=float(p0[k]),
            maxdd=float(M.max_drawdown(net[k])),
            rotacion_anual=float(M.rotacion_anual(Wh[k:k + 1], anual)[0]),
        ))
    orden = sorted(range(len(nombres)), key=lambda k: (-dsr[k], -tabla[k]["sr_anual"]))
    finalistas = [nombres[k] for k in orden[: P.K_FINALISTAS]]
    return dict(
        n_configs=len(nombres), umbral_sr_trials=float(umbral),
        p_spa_alfa=spa["p_spa"], p_rc_alfa=spa["p_rc"], puerta=bool(gate),
        finalistas=finalistas if gate else [],
        ebar_todas={nombres[k]: float(ebar[k]) for k in range(len(nombres))},
        mejor_sr_seleccion=tabla[int(np.argmax([t["sr_anual"] for t in tabla]))],
        tabla=tabla,
    )


def etapa_muestra_final(nombre, d_full, spec, finalistas, ebar_sel, semilla, extra=None):
    """Evalua SOLO los finalistas congelados sobre el tramo final.

    extra: configuracion adicional (p. ej. el mejor SR de seleccion, sin correccion) que se
    evalua para el control 'naive', pero NO entra en la familia de BH.
    """
    ini = pd.Timestamp(spec["seg"]["inicio_holdout"])
    nombres, fams, W, ref = universo(nombre, d_full, spec)   # causal: usa historia previa
    net, Wh = netos(W, d_full, spec)
    if not np.isfinite(net).all():
        raise RuntimeError(f"NaN en retornos netos de muestra final ({nombre})")
    mask = np.asarray(d_full["fechas"] >= ini)
    K = len(finalistas)
    todas = list(finalistas) + ([extra] if extra and extra not in finalistas else [])
    filas = [nombres.index(f) for f in todas]
    net_h = net[filas][:, mask]
    ref_h = ref[filas]
    refs_h = d_full["refs"][:, mask]
    rf_h = d_full["rf"][mask]
    eb = np.array([ebar_sel[f] for f in todas])
    bench = eb[:, None] * refs_h[ref_h] + (1 - eb[:, None]) * rf_h[None, :]
    x_din = net_h - rf_h[None, :]
    D_alfa = net_h - bench
    T = net_h.shape[1]
    rng = np.random.default_rng(semilla)
    idx = M.indices_bootstrap(T, P.B_BOOTSTRAP, spec["bloque"], rng)
    p_din = M.pval_media_positiva(x_din, idx)
    p_alf = M.pval_media_positiva(D_alfa, idx)
    # BH solo sobre los K finalistas (2K pruebas): el control naive queda fuera de la familia
    fam = np.concatenate([p_alf[:K], p_din[:K]])
    rech = M.benjamini_hochberg(fam, P.Q_BH)
    res = []
    for k, f in enumerate(todas):
        anual = spec["anual"]
        es_final = k < K
        res.append(dict(
            config=f, es_finalista=es_final, n_dias=int(T),
            sr_anual=float(M.sharpe_anual(x_din[k:k + 1], anual)[0]),
            cagr=float(np.expm1(np.log1p(net_h[k]).sum() * anual / T)),
            alfa_anual=float(D_alfa[k].mean() * anual),
            maxdd=float(M.max_drawdown(net_h[k])),
            p_alfa=float(p_alf[k]), p_dinero=float(p_din[k]),
            rechazo_alfa=bool(rech[k]) if es_final else None,
            rechazo_dinero=bool(rech[K + k]) if es_final else None,
            pasa=bool(rech[k] and rech[K + k]) if es_final else None,
        ))
    pasan = [r for r in res if r["es_finalista"] and r["pasa"]]
    campeon = max(pasan, key=lambda r: r["sr_anual"])["config"] if pasan else None
    return dict(finalistas=res, campeon=campeon, bh_q=P.Q_BH, familia_pruebas=2 * K)


def correr(nombre, d_full, semilla=P.SEMILLA, con_muestra_final=True, real=False):
    """Canalizacion completa sobre un dataset (real o sintetico).

    real=True exige protocolo congelado y registra el acceso a la muestra final.
    """
    spec = SPEC[nombre]
    sel = etapa_seleccion(nombre, d_full, spec, semilla)
    out = dict(dataset=nombre, seleccion=sel, muestra_final=None, campeon=None)
    if not sel["puerta"] or not con_muestra_final:
        return out
    if real:
        D.exigir_protocolo_congelado(f"muestra_final:{nombre}")
    fin = etapa_muestra_final(nombre, d_full, spec, sel["finalistas"], sel["ebar_todas"],
                              semilla + 1, extra=sel["mejor_sr_seleccion"]["config"])
    out["muestra_final"] = fin
    out["campeon"] = fin["campeon"]
    return out
