"""Motor LIF de todo el SNC (numba, paralelo por neuronas). Unidades: ms, mV.

dV/dt = (V_L - V + g + b_i + e_i) / tau_m        (b_i: sesgo fijo por neurona; e_i: entrada sensorial)
g decae con tau_s; cada espiga presinaptica suma w_ij = signo_pre * n_sinapsis * w_syn a g_post (retardo 1 paso).
Espiga si V >= V_thr; reset V_reset; periodo refractario t_ref. Sin ruido gaussiano (coste demasiado alto a 2e5 neuronas
por paso): la variabilidad sale de la red y de las condiciones iniciales aleatorias.
"""
import numpy as np
import numba as nb

PARAMS = dict(dt=0.5, tau_m=20.0, tau_s=5.0, V_L=-52.0, V_thr=-45.0, V_reset=-52.0, t_ref=2.0, w_syn=0.275)


@nb.njit(parallel=True, cache=False)
def _update(V, g, refr, bias, ext, alive, dt, tau_m, V_L, V_thr, V_reset, ref_steps, decay, spk):
    N = V.shape[0]
    for i in nb.prange(N):
        spk[i] = 0
        if alive[i] == 0:
            continue
        if refr[i] > 0:
            refr[i] -= 1
            V[i] = V_reset
            g[i] *= decay
            continue
        V[i] += dt / tau_m * (V_L - V[i] + g[i] + bias[i] + ext[i])
        g[i] *= decay
        if V[i] >= V_thr:
            spk[i] = 1
            V[i] = V_reset
            refr[i] = ref_steps


@nb.njit(cache=False)
def _scatter(spk, g, indptr, indices, ws):
    n_spk = 0
    N = spk.shape[0]
    for i in range(N):
        if spk[i]:
            n_spk += 1
            for e in range(indptr[i], indptr[i + 1]):
                g[indices[e]] += ws[e]
    return n_spk


@nb.njit(cache=False)
def run_chunk(V, g, refr, bias, ext, alive, spk, counts, indptr, indices, ws,
              n_steps, dt, tau_m, V_L, V_thr, V_reset, ref_steps, decay, rec_mask, rec_t, rec_i, rec_n, t0):
    for k in range(n_steps):
        _update(V, g, refr, bias, ext, alive, dt, tau_m, V_L, V_thr, V_reset, ref_steps, decay, spk)
        N = spk.shape[0]
        for i in range(N):
            if spk[i]:
                counts[i] += 1
                if rec_mask[i] and rec_n[0] < rec_t.shape[0]:
                    rec_t[rec_n[0]] = t0 + k * dt
                    rec_i[rec_n[0]] = i
                    rec_n[0] += 1
        _scatter(spk, g, indptr, indices, ws)
    return 0


class Network:
    """Estado de la red completa. ws = signo * n_sinapsis * w_syn por arista (float32)."""

    def __init__(self, graph, bias_mV_per_ms=None, w_syn=None, seed=0, dt=None):
        p = dict(PARAMS)
        if w_syn is not None:
            p["w_syn"] = w_syn
        if dt is not None:
            p["dt"] = dt
        self.p = p
        self.N = graph["ids"].shape[0]
        self.indptr = graph["indptr"]
        self.indices = graph["indices"].astype(np.int32)
        pre_sign = graph["sign"].astype(np.float32)
        counts_e = np.diff(self.indptr)
        src_sign = np.repeat(pre_sign, counts_e)
        self.ws = (src_sign * graph["syn"] * p["w_syn"]).astype(np.float32)
        rng = np.random.default_rng(seed)
        self.V = rng.uniform(p["V_L"], p["V_thr"], self.N).astype(np.float64)
        self.g = np.zeros(self.N, dtype=np.float64)
        self.refr = np.zeros(self.N, dtype=np.int64)
        self.bias = np.zeros(self.N, dtype=np.float64) if bias_mV_per_ms is None else np.asarray(bias_mV_per_ms, np.float64)
        self.ext = np.zeros(self.N, dtype=np.float64)
        self.alive = np.ones(self.N, dtype=np.uint8)
        self.spk = np.zeros(self.N, dtype=np.uint8)
        self.counts = np.zeros(self.N, dtype=np.int64)
        self.t = 0.0
        self.decay = float(np.exp(-p["dt"] / p["tau_s"]))
        self.ref_steps = int(round(p["t_ref"] / p["dt"]))
        self.rec_mask = np.zeros(self.N, dtype=np.uint8)
        self.rec_t = np.zeros(1, dtype=np.float64)
        self.rec_i = np.zeros(1, dtype=np.int64)
        self.rec_n = np.zeros(1, dtype=np.int64)

    def set_recording(self, mask, capacity):
        self.rec_mask = mask.astype(np.uint8)
        self.rec_t = np.zeros(capacity, dtype=np.float64)
        self.rec_i = np.zeros(capacity, dtype=np.int64)
        self.rec_n[0] = 0

    def advance(self, t_ms):
        p = self.p
        n_steps = int(round(t_ms / p["dt"]))
        run_chunk(self.V, self.g, self.refr, self.bias, self.ext, self.alive, self.spk, self.counts,
                  self.indptr, self.indices, self.ws, n_steps, p["dt"], p["tau_m"], p["V_L"], p["V_thr"],
                  p["V_reset"], self.ref_steps, self.decay, self.rec_mask, self.rec_t, self.rec_i, self.rec_n, self.t)
        self.t += n_steps * p["dt"]
        return n_steps
