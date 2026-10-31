"""Motor LIF con espigas (numba) para el cuerpo fungiforme real, con plasticidad de tres factores KC->MBON.

Neurona (parametros de Shiu et al. 2024, verificados en PMC11446845): dv/dt = (g - v)/tau_m, dg/dt = -g/tau_s,
cada espiga presinaptica suma w (mV) a g de la postsinaptica tras un retardo; v en mV sobre el reposo; umbral 7 mV
(-52 -> -45), reset a 0, refractario 2.2 ms (aqui 2 ms con dt=0.5), tau_m 20 ms, tau_s 5 ms, retardo 1.8 ms (aqui 2 ms).
La escala sinaptica (mV por sinapsis) NO viene de Shiu (usa 0.275 para cerebro completo): se calibra (ver calibrate.py).

Plasticidad (Hige 2015, verificado): depresion de KC->MBON cuando una KC esta "activa" (traza e_k >= theta) mientras
llega dopamina D_j al compartimento del MBON j:  f_kj <- f_kj * (1 - eta * D_j * dt).  Solo depresion, sin
dependencia de la espiga del MBON.  Los PN y los DAN estimulados son generadores de Poisson.
"""
import os

import numpy as np

os.environ.setdefault("NUMBA_CACHE_DIR", os.path.join(os.path.expanduser("~"), ".cache", "neuro2-numba"))  # fuera del repo
try:
    import numba
    from numba import njit
except Exception:                      # pragma: no cover - sin numba el codigo corre (muy lento) en Python puro
    numba = None

    def njit(*a, **k):
        if len(a) == 1 and callable(a[0]):
            return a[0]
        return lambda f: f

DT = 0.5            # ms
DELAY = 4           # pasos (2 ms)
REF_STEPS = 4       # pasos (2 ms)
TAU_M = 20.0        # ms
TAU_S = 5.0         # ms
VTH = 7.0           # mV
PSTEP = 4           # pasos por actualizacion de plasticidad (2 ms)


@njit(cache=True)
def run_trial(seed, nsteps, n, lif_lo, lif_hi, silenced,
              ptr, post, w,
              kc_lo, nkc, kptr, kpost, kw0, kf,
              g_idx, g_r0, g_r1, g_on, g_off, ramp,
              win_on, win_off,
              dan_lo, ndan, dptr, dpost, dg, dan_ref_hz,
              plastic, eta, theta, tau_e_ms, tau_da_ms,
              counts, kc_peak, mbon_lo, nmbon):
    """Una prueba. counts[i] = espigas de i en [win_on, win_off).  kc_peak[k] = max de la traza e_k.
    Devuelve el numero total de espigas."""
    np.random.seed(seed)
    v = np.zeros(n, np.float32)
    g = np.zeros(n, np.float32)
    ref = np.zeros(n, np.int32)
    inbuf = np.zeros((DELAY, n), np.float32)
    dec_s = np.float32(np.exp(-DT / TAU_S))
    kv = np.float32(DT / TAU_M)
    ngen = g_idx.shape[0]
    e = np.zeros(nkc, np.float32)
    kc_new = np.zeros(nkc, np.int32)
    a = np.zeros(ndan, np.float32)
    dan_new = np.zeros(ndan, np.int32)
    D = np.zeros(nmbon, np.float32)
    dtp = DT * PSTEP
    dec_e = np.float32(np.exp(-dtp / tau_e_ms))
    dec_a = np.float32(np.exp(-dtp / tau_da_ms))
    total = 0
    for t in range(nsteps):
        slot = t % DELAY
        # --- fase 0: absorber lo que llega ahora (las espigas de este paso se escriben en el mismo slot: llegan en t+DELAY)
        for i in range(lif_lo, lif_hi):
            g[i] += inbuf[slot, i]
        for i in range(n):
            inbuf[slot, i] = 0.0
        # --- generadores (PN, DAN estimulados)
        for q in range(ngen):
            r = g_r0[q]
            if t >= g_on[q] and t < g_off[q]:
                fr = (t - g_on[q]) / ramp
                if fr > 1.0:
                    fr = 1.0
                r = g_r0[q] + (g_r1[q] - g_r0[q]) * fr
            if r > 0.0 and np.random.random() < r * DT * 1e-3:
                i = g_idx[q]
                if silenced[i]:
                    continue
                # propagacion
                total += 1
                if t >= win_on and t < win_off:
                    counts[i] += 1
                for p in range(ptr[i], ptr[i + 1]):
                    inbuf[slot, post[p]] += w[p]
                if i >= dan_lo and i < dan_lo + ndan:
                    dan_new[i - dan_lo] += 1
        # --- neuronas LIF
        for i in range(lif_lo, lif_hi):
            if silenced[i]:
                g[i] = 0.0
                v[i] = 0.0
                continue
            v[i] += kv * (g[i] - v[i])
            g[i] *= dec_s
            if ref[i] > 0:
                ref[i] -= 1
                v[i] = 0.0
            elif v[i] >= VTH:
                v[i] = 0.0
                ref[i] = REF_STEPS
                total += 1
                if t >= win_on and t < win_off:
                    counts[i] += 1
                for p in range(ptr[i], ptr[i + 1]):
                    inbuf[slot, post[p]] += w[p]
                if i >= kc_lo and i < kc_lo + nkc:
                    k = i - kc_lo
                    kc_new[k] += 1
                    for p in range(kptr[k], kptr[k + 1]):
                        inbuf[slot, kpost[p]] += kw0[p] * kf[p]
                if i >= dan_lo and i < dan_lo + ndan:
                    dan_new[i - dan_lo] += 1
        # --- plasticidad / trazas cada PSTEP pasos
        if (t + 1) % PSTEP == 0:
            for k in range(nkc):
                e[k] = e[k] * dec_e + kc_new[k]
                kc_new[k] = 0
                if e[k] > kc_peak[k]:
                    kc_peak[k] = e[k]
            for d in range(ndan):
                a[d] = a[d] * dec_a + dan_new[d] * (1000.0 / tau_da_ms)
                dan_new[d] = 0
            if plastic:
                anyd = False
                for j in range(nmbon):
                    D[j] = 0.0
                for d in range(ndan):
                    if a[d] > 0.5:
                        for p in range(dptr[d], dptr[d + 1]):
                            D[dpost[p]] += dg[p] * a[d] / dan_ref_hz
                            anyd = True
                if anyd:
                    for k in range(nkc):
                        if e[k] >= theta:
                            for p in range(kptr[k], kptr[k + 1]):
                                dj = D[kpost[p] - mbon_lo]
                                if dj > 0.0:
                                    fac = 1.0 - eta * dj * dtp * 1e-3
                                    if fac < 0.0:
                                        fac = 0.0
                                    kf[p] *= fac
    return total
