"""Olores sinteticos y protocolos de condicionamiento (pre-test, emparejamientos, post-test).

Cada olor = subconjunto de canales (tipos de PN con salida) con amplitudes al azar (supuesto: no hay olores medidos).
La valencia se calcula aparte (analysis.py) a partir de las tasas de los 97 MBON guardadas.
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import engine as eng
import mbdata as md

STEP_MS = eng.DT


def make_odor(net, rng, n_active=None):
    """Devuelve tasa (Hz) por PN generador para un olor."""
    p = net.p
    nch = net.info["n_channels"]
    k = n_active or p.n_channels_active
    act = rng.choice(nch, size=k, replace=False)
    amp = np.zeros(nch)
    amp[act] = rng.uniform(0.4, 1.0, size=k)
    u = rng.lognormal(0.0, 0.25, size=len(net.gen_pn))
    return p.pn_odor_hz * amp[net.channels] * u


def _steps(ms):
    return int(round(ms / STEP_MS))


class Runner:
    def __init__(self, net, silence=None, dan_stim=None):
        self.net = net
        n = net.n
        self.silenced = np.zeros(n, np.bool_)
        if silence is not None and len(silence):
            self.silenced[np.asarray(silence)] = True
        self.dan_stim = np.asarray(dan_stim if dan_stim is not None else [], dtype=np.int64)
        r = net.ranges
        self.kc_lo, self.kc_hi = r["KC"]
        self.mb_lo, self.mb_hi = r["MBON"]
        self.dan_lo, self.dan_hi = r["DAN"]
        self.apl_lo, self.apl_hi = r["APL"]
        self.kf = net.kf0.copy()
        self.seed_ctr = 1

    def reset(self):
        self.kf = self.net.kf0.copy()

    def trial(self, odor_rate, us=False, us_mode="forward", plastic=False, eta=0.0, theta=1.0, seed=0, odor_on_ms=500.0,
              odor_ms=1000.0, test=False):
        """Una prueba.  Devuelve (counts_por_neurona_en_ventana_de_olor, kc_peak)."""
        net, p = self.net, self.net.p
        if us and us_mode == "backward":
            odor_on, total = 1300.0, 2400.0
        elif test:
            odor_on, total = 100.0, 1200.0
        else:
            odor_on, total = 100.0, 1200.0
        odor_off = odor_on + odor_ms
        pn = net.gen_pn
        g_idx = [pn]
        g_r0 = [np.full(len(pn), p.pn_base_hz)]
        g_r1 = [odor_rate]
        g_on = [np.full(len(pn), _steps(odor_on))]
        g_off = [np.full(len(pn), _steps(odor_off))]
        if us and len(self.dan_stim):
            if us_mode == "forward":
                u_on, u_off = odor_on + 200.0, odor_off
            else:   # hacia atras: DAN antes del olor, 0.5 s de hueco (Hige 2015)
                u_off = odor_on - 500.0
                u_on = max(0.0, u_off - 800.0)
            d = self.dan_stim
            g_idx.append(d)
            g_r0.append(np.zeros(len(d)))
            g_r1.append(np.full(len(d), p.dan_us_hz))
            g_on.append(np.full(len(d), _steps(u_on)))
            g_off.append(np.full(len(d), _steps(u_off)))
        g_idx = np.concatenate(g_idx).astype(np.int64)
        g_r0 = np.concatenate(g_r0).astype(np.float32)
        g_r1 = np.concatenate(g_r1).astype(np.float32)
        g_on = np.concatenate(g_on).astype(np.int64)
        g_off = np.concatenate(g_off).astype(np.int64)
        counts = np.zeros(net.n, np.int32)
        kc_peak = np.zeros(self.kc_hi - self.kc_lo, np.float32)
        eng.run_trial(seed, _steps(total), net.n, self.kc_lo, self.mb_hi, self.silenced,
                      net.ptr, net.post, net.w,
                      self.kc_lo, self.kc_hi - self.kc_lo, net.kptr, net.kpost, net.kw0, self.kf,
                      g_idx, g_r0, g_r1, g_on, g_off, float(_steps(p.ramp_ms)),
                      _steps(odor_on), _steps(odor_off),
                      self.dan_lo, self.dan_hi - self.dan_lo, net.dptr, net.dpost, net.dg, p.dan_ref_hz,
                      bool(plastic), float(eta), float(theta), float(p.tau_e_ms), float(p.tau_da_ms),
                      counts, kc_peak, self.mb_lo, self.mb_hi - self.mb_lo)
        return counts, kc_peak

    def _test(self, odors, seed, ntest):
        out_mb, out_kc = [], []
        for oi, o in enumerate(odors):
            acc = np.zeros(self.mb_hi - self.mb_lo)
            kc_c = np.zeros(self.kc_hi - self.kc_lo)
            for t in range(ntest):
                c, _ = self.trial(o, test=True, seed=seed * 1000 + oi * 10 + t)
                acc += c[self.mb_lo:self.mb_hi]
                kc_c += c[self.kc_lo:self.kc_hi]
            out_mb.append(acc / ntest / 1.0)            # espigas en 1 s = Hz
            out_kc.append(kc_c / ntest)
        return np.array(out_mb), np.array(out_kc)

    def conditioning(self, odors, seed, eta, theta, n_pairs=4, ntest=2, us_mode="forward", paired=0, control=1):
        """odors = [A, B, C] (tasas por PN).  A se empareja con la activacion de self.dan_stim; B va sin DAN."""
        self.reset()
        mb_pre, kc_pre = self._test(odors, seed, ntest)
        s = seed * 100000 + 7
        for k in range(n_pairs):
            self.trial(odors[paired], us=True, us_mode=us_mode, plastic=True, eta=eta, theta=theta, seed=s + 2 * k)
            self.trial(odors[control], us=False, plastic=True, eta=eta, theta=theta, seed=s + 2 * k + 1)
        mb_post, kc_post = self._test(odors, seed + 50000, ntest)
        # fraccion media del peso restante en las aristas de las KC activas de A
        return dict(mb_pre=mb_pre, mb_post=mb_post, kc_pre=kc_pre, kc_post=kc_post,
                    f_mean=float(self.kf.mean()), f_min=float(self.kf.min()))
