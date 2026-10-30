"""Motor de simulacion (vectorizado) y estadistica de pruebas multiples.

Convenciones:
- W[n, i, t]: peso objetivo del activo i decidido al cierre de t (solo informacion <= t).
- Se aplica al periodo t+1: Wh[:, :, t+1] = W[:, :, t]. Ningun peso ve su propio retorno.
- R[i, t]: retorno del activo i en el periodo t (de t-1 a t). rf[t]: tipo sin riesgo del periodo t.
- Peso restante (1 - sum_i w_i) gana rf (efectivo); sum_i w_i > 1 o < 0 paga financiacion.

Formulas de Bailey & Lopez de Prado (PSR, DSR), White (2000) Reality Check, Hansen (2005)
SPA y Benjamini-Hochberg (1995) se implementan de memoria; ver README.
"""
import math

import numpy as np
from scipy.stats import kurtosis, norm, skew

GAMMA_EULER = 0.5772156649015329


# --------------------------------------------------------------------- simulacion

def retornos_netos(W, R, rf, anual, coste_bps, spread_anual, coste_fijo_bps=0.0):
    """W: (N, I, T); R: (I, T); rf: (T,). Devuelve net (N, T) y Wh (N, I, T)."""
    N, I, T = W.shape
    Wh = np.zeros_like(W)
    Wh[:, :, 1:] = W[:, :, :-1]
    suma = Wh.sum(axis=1)                                   # (N, T)
    gross = (Wh * R[None]).sum(axis=1) + (1.0 - suma) * rf[None, :]
    prev = np.zeros_like(Wh)
    prev[:, :, 1:] = Wh[:, :, :-1]
    turnover = np.abs(Wh - prev).sum(axis=1)                # (N, T)
    financiacion = spread_anual / anual * (np.maximum(suma - 1.0, 0) + np.maximum(-suma, 0))
    net = gross - coste_bps / 1e4 * turnover - financiacion - coste_fijo_bps / 1e4
    net[:, 0] = 0.0
    return net, Wh


def exposicion_media(Wh):
    """Exposicion neta media por configuracion (N, I) -> (N,) sumando activos."""
    return Wh.sum(axis=1).mean(axis=1)


def rotacion_anual(Wh, anual):
    prev = np.zeros_like(Wh)
    prev[:, :, 1:] = Wh[:, :, :-1]
    return np.abs(Wh - prev).sum(axis=1).mean(axis=1) * anual


# ------------------------------------------------------------------- metricas

def sharpe_anual(x, anual):
    """x: (N, T) excesos. Sharpe anualizado (sin correccion)."""
    sd = x.std(axis=-1, ddof=1)
    return x.mean(axis=-1) / np.where(sd > 0, sd, np.nan) * math.sqrt(anual)


def sharpe_por_periodo(x):
    sd = x.std(axis=-1, ddof=1)
    return x.mean(axis=-1) / np.where(sd > 0, sd, np.nan)


def max_drawdown(x):
    """x: (T,) retornos por periodo. Drawdown maximo (fraccion negativa)."""
    eq = np.cumprod(1.0 + x)
    peak = np.maximum.accumulate(eq)
    return float((eq / peak - 1.0).min())


def psr(sr, T, g3, g4, sr_ref=0.0):
    """Probabilistic Sharpe Ratio (Bailey & Lopez de Prado 2012). sr por periodo."""
    denom = np.sqrt(np.maximum(1.0 - g3 * sr + (g4 - 1.0) / 4.0 * sr ** 2, 1e-12))
    return norm.cdf((sr - sr_ref) * math.sqrt(T - 1) / denom)


def sr_umbral_dsr(var_sr_trials, N):
    """SR esperado del mejor de N ensayos sin habilidad (Deflated SR, de memoria)."""
    if N < 2:
        return 0.0
    return math.sqrt(var_sr_trials) * (
        (1 - GAMMA_EULER) * norm.ppf(1 - 1.0 / N)
        + GAMMA_EULER * norm.ppf(1 - 1.0 / (N * math.e))
    )


def deflated_sharpe(x_excess):
    """x_excess: (N, T) excesos. Devuelve (sr_periodo, psr0, dsr) para cada configuracion."""
    N, T = x_excess.shape
    sr = sharpe_por_periodo(x_excess)
    g3 = skew(x_excess, axis=-1, bias=False)
    g4 = kurtosis(x_excess, axis=-1, fisher=False, bias=False)
    var_trials = np.nanvar(sr, ddof=1) if N > 1 else 0.0
    ref = sr_umbral_dsr(var_trials, N)
    p0 = psr(sr, T, g3, g4, 0.0)
    dsr = psr(sr, T, g3, g4, ref)
    return sr, p0, dsr, ref


# ---------------------------------------------------------------- bootstrap

def indices_bootstrap(T, B, L, rng):
    """Bootstrap estacionario de Politis-Romano: bloques con longitud geometrica media L.
    Devuelve (B, T) indices. Vectorizado: restart + ultimo inicio."""
    restart = rng.random((B, T)) < (1.0 / L)
    restart[:, 0] = True
    arranque = rng.integers(0, T, size=(B, T))
    t = np.broadcast_to(np.arange(T), (B, T))
    ultimo = np.maximum.accumulate(np.where(restart, t, 0), axis=1)
    base = arranque[np.arange(B)[:, None], ultimo]
    return (base + (t - ultimo)) % T


def medias_bootstrap(D, idx):
    """D: (N, T). Medias de cada remuestra: (N, B). Usa conteos (un matmul)."""
    B, T = idx.shape
    flat = (idx.T * B + np.arange(B)[None, :]).ravel()
    C = np.bincount(flat, minlength=T * B).reshape(T, B).astype(np.float64)
    return D @ C / T


def pval_media_positiva(x, idx):
    """Test unilateral H1: media > 0, con bootstrap centrado. x: (N, T). Devuelve (N,) p."""
    obs = x.mean(axis=1)
    xc = x - obs[:, None]
    M = medias_bootstrap(xc, idx)
    return (M >= obs[:, None]).mean(axis=1)


def reality_check_y_spa(D, idx):
    """D: (N, T) diferencias frente al benchmark (positivas = mejor que benchmark).

    Devuelve dict con p de White (Reality Check, estudentizado sin recentrar) y p de
    Hansen (SPA, estudentizado con recentrado consistente), y los t de cada configuracion.
    """
    N, T = D.shape
    dbar = D.mean(axis=1)
    M = medias_bootstrap(D, idx)                        # (N, B) medias remuestreadas
    se = M.std(axis=1, ddof=1)
    se = np.where(se > 1e-12, se, 1e-12)
    t = dbar / se
    # White RC (estudentizado, sin recentrar)
    T_obs_rc = t.max()
    T_star_rc = ((M - dbar[:, None]) / se[:, None]).max(axis=0)
    p_rc = float((T_star_rc >= T_obs_rc).mean())
    # Hansen SPA: recentrado consistente (mu_hat = dbar si el t es muy negativo)
    lam = math.sqrt(2.0 * math.log(max(math.log(T), 1.0001)))
    mu = np.where(t <= -lam, dbar, 0.0)
    T_obs_spa = max(t.max(), 0.0)
    T_star_spa = np.maximum(((M - dbar[:, None] + mu[:, None]) / se[:, None]).max(axis=0), 0.0)
    p_spa = float((T_star_spa >= T_obs_spa).mean())
    return {"p_rc": p_rc, "p_spa": p_spa, "t": t, "dbar": dbar}


def benjamini_hochberg(p, q):
    """Devuelve mascara booleana de rechazos al nivel q (BH 1995)."""
    p = np.asarray(p, dtype=float)
    m = len(p)
    orden = np.argsort(p)
    umbral = q * (np.arange(1, m + 1) / m)
    cumple = p[orden] <= umbral
    rechazo = np.zeros(m, dtype=bool)
    if cumple.any():
        k = np.max(np.where(cumple)[0])
        rechazo[orden[: k + 1]] = True
    return rechazo
