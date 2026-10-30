"""Simulador LIF sintetico del cuerpo fungiforme (mushroom body) de Drosophila.

Circuito modelado (la conectividad es SINTETICA, ver README.md):
  ORN (50) -> PN (50, 1:1 por glomerulo) -> KC (2000, 6 PN al azar) -> MBON (4)
  KC -> APL (1) -> KC  (inhibicion global)
  DAN (2 de recompensa + 2 de castigo) modula las sinapsis KC->MBON mediante
  una traza de elegibilidad de las KC activas.

Las neuronas son integrate-and-fire con fuga y corriente sinaptica exponencial,
con espigas explicitas. Solo depende de numpy. Reproducible con la semilla.

Uso minimo:
    from fly_mb import MushroomBody, Params
    mb = MushroomBody(seed=7)
    res = mb.run([{"name": "A", "t0": 0, "t1": 1000, "odor": "A"}])
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field

import numpy as np

POP_NAMES = ("ORN", "PN", "KC", "APL", "MBON", "DAN")
ODOR_NAMES = ("A", "B", "C")


@dataclass
class Params:
    """Parametros del modelo. Tiempos en ms; voltajes adimensionales (umbral = 1)."""
    dt_ms: float = 0.25
    tau_m: float = 10.0          # constante de membrana (todas las poblaciones)
    tau_syn: float = 5.0         # decaimiento de la corriente sinaptica
    t_ref: float = 2.0           # periodo refractario absoluto
    v_thr: float = 1.0
    v_reset: float = 0.0
    noise: float = 0.08          # ruido blanco: sigma de la OU ~ noise*sqrt(tau_m/2)
    n_orn: int = 50
    n_kc: int = 2000
    k_pn_per_kc: int = 6         # cada KC recibe 6 PN elegidas al azar
    n_mbon: int = 4
    n_dan_rew: int = 2           # DAN de recompensa (reducen KC->MBON)
    n_dan_pun: int = 2           # DAN de castigo (potencian KC->MBON)
    bias_orn: float = 0.6        # actividad espontanea de ORN (subumbral)
    gain_orn: float = 1.2        # corriente por unidad de afinidad del olor
    w_orn_pn: float = 0.8        # ORN -> PN 1:1
    bias_pn: float = 0.5
    w_pn_kc: float = 2.0         # PN -> KC (excitatorio)
    w_pn_kc_jitter: float = 0.2  # +-20% de variabilidad en cada sinapsis PN->KC
    bias_kc: float = 0.0
    bias_kc_sd: float = 0.10     # heterogeneidad de umbrales de KC
    w_kc_apl: float = 0.2        # KC -> APL
    w_apl_kc: float = 1.5        # APL -> KC (inhibicion global)
    w_kc_mbon: float = 0.03      # KC -> MBON, media inicial
    bias_mbon: float = 0.5
    dan_drive: float = 1.5       # corriente externa de los DAN durante la US
    tau_da: float = 50.0         # decaimiento de la senal de dopamina
    tau_elig: float = 1000.0     # traza de elegibilidad de las KC
    eta_dep: float = 3e-5        # tasa de depresion KC->MBON por recompensa
    eta_pot: float = 3e-5        # tasa de potenciacion KC->MBON por castigo
    elig_thr: float = 4.0        # umbral de la traza de elegibilidad (coincidencia)
    w_max: float = 0.2           # cota superior de los pesos plasticos


@dataclass
class Result:
    seed: int
    params: Params
    dt_ms: float
    n_steps: int
    schedule: list
    spike_step: np.ndarray       # paso de simulacion de cada espiga
    spike_id: np.ndarray         # id global de la neurona que dispara
    W_init: np.ndarray           # KC->MBON antes de la simulacion (n_mbon, n_kc)
    W_final: np.ndarray          # KC->MBON al final
    offset: dict = field(default_factory=dict)
    sizes: dict = field(default_factory=dict)
    xy: dict = field(default_factory=dict)

    def window_counts(self, pop: str, t0: float, t1: float) -> np.ndarray:
        """Numero de espigas de cada neurona de `pop` en la ventana [t0, t1) ms."""
        s0 = int(round(t0 / self.dt_ms))
        s1 = int(round(t1 / self.dt_ms))
        m = (self.spike_step >= s0) & (self.spike_step < s1)
        lo, sz = self.offset[pop], self.sizes[pop]
        ids = self.spike_id[m]
        ids = ids[(ids >= lo) & (ids < lo + sz)] - lo
        return np.bincount(ids, minlength=sz)

    def stim(self, name: str) -> dict:
        for s in self.schedule:
            if s["name"] == name:
                return s
        raise KeyError(name)


def _layout(p: Params, rng: np.random.Generator) -> dict:
    """Coordenadas en [0,1]: ORN izquierda, PN, nube de KC, APL, MBON y DAN a la derecha."""
    xy = {}
    yo = np.linspace(0.04, 0.96, p.n_orn)
    xy["ORN"] = np.column_stack([np.full(p.n_orn, 0.06), yo])
    xy["PN"] = np.column_stack([np.full(p.n_orn, 0.25), yo])
    kc_x = np.clip(0.58 + 0.09 * rng.standard_normal(p.n_kc), 0.40, 0.76)
    kc_y = np.clip(0.50 + 0.30 * rng.standard_normal(p.n_kc), 0.02, 0.98)
    xy["KC"] = np.column_stack([kc_x, kc_y])
    xy["APL"] = np.array([[0.80, 0.50]])
    xy["MBON"] = np.column_stack([np.full(p.n_mbon, 0.88), np.linspace(0.30, 0.70, p.n_mbon)])
    n_dan = p.n_dan_rew + p.n_dan_pun
    xy["DAN"] = np.column_stack([np.full(n_dan, 0.97), np.linspace(0.10, 0.90, n_dan)])
    return xy


class MushroomBody:
    """Red sintetica del cuerpo fungiforme. La anatomia y los olores dependen solo de la semilla."""

    def __init__(self, seed: int = 0, params: Params | None = None):
        self.seed = int(seed)
        self.p = p = params or Params()
        rng = np.random.default_rng(self.seed)

        self.sizes = {"ORN": p.n_orn, "PN": p.n_orn, "KC": p.n_kc, "APL": 1,
                      "MBON": p.n_mbon, "DAN": p.n_dan_rew + p.n_dan_pun}
        self.offset, off = {}, 0
        for name in POP_NAMES:
            self.offset[name] = off
            off += self.sizes[name]
        self.N = off

        # Anatomia sintetica: cada KC recibe k PN al azar (sin repetir)
        self.pn_of_kc = np.stack([rng.choice(p.n_orn, p.k_pn_per_kc, replace=False)
                                  for _ in range(p.n_kc)])
        self.W_pn_kc = np.zeros((p.n_kc, p.n_orn))
        jit = rng.uniform(1 - p.w_pn_kc_jitter, 1 + p.w_pn_kc_jitter, self.pn_of_kc.shape)
        np.put_along_axis(self.W_pn_kc, self.pn_of_kc, p.w_pn_kc * jit, axis=1)
        self.bias_kc = p.bias_kc + p.bias_kc_sd * rng.standard_normal(p.n_kc)
        self.W_kc_mbon0 = p.w_kc_mbon * rng.uniform(0.5, 1.5, (p.n_mbon, p.n_kc))

        # Olores sinteticos: 12 de 50 glomerulos fuertes, resto ruido bajo
        self.odor_names = ODOR_NAMES
        self.aff = np.zeros((len(ODOR_NAMES), p.n_orn))
        for i in range(len(ODOR_NAMES)):
            a = rng.uniform(0.0, 0.15, p.n_orn)
            on = rng.choice(p.n_orn, 12, replace=False)
            a[on] = rng.uniform(0.5, 1.0, 12)
            self.aff[i] = a

        self.xy = _layout(p, np.random.default_rng(self.seed + 1000))

    def run(self, schedule: list, t_end_ms: float | None = None) -> Result:
        """Simula el protocolo. `schedule` es una lista de dicts:
        {name, t0, t1, odor (A/B/C o None), reward (bool), punish (bool)}."""
        p = self.p
        dt = p.dt_ms
        t_end = t_end_ms if t_end_ms is not None else max(s["t1"] for s in schedule)
        n = int(round(t_end / dt))

        odor_of_step = np.full(n, -1, dtype=np.int64)
        rew = np.zeros(n, dtype=bool)
        pun = np.zeros(n, dtype=bool)
        for seg in schedule:
            a = int(round(seg["t0"] / dt))
            b = min(int(round(seg["t1"] / dt)), n)
            if seg.get("odor") is not None:
                odor_of_step[a:b] = ODOR_NAMES.index(seg["odor"])
            if seg.get("reward"):
                rew[a:b] = True
            if seg.get("punish"):
                pun[a:b] = True

        off, sz = self.offset, self.sizes
        sl = {k: slice(off[k], off[k] + sz[k]) for k in POP_NAMES}
        dan_rew = slice(off["DAN"], off["DAN"] + p.n_dan_rew)
        dan_pun = slice(off["DAN"] + p.n_dan_rew, off["DAN"] + sz["DAN"])

        leak = dt / p.tau_m
        sig = p.noise * np.sqrt(dt)
        dec_syn = np.exp(-dt / p.tau_syn)
        dec_da = np.exp(-dt / p.tau_da)
        dec_el = np.exp(-dt / p.tau_elig)
        ref_steps = int(round(p.t_ref / dt))

        W = self.W_kc_mbon0.copy()
        W_init = W.copy()
        rng = np.random.default_rng(self.seed + 2)  # ruido de la simulacion

        v = np.zeros(self.N)
        refr = np.zeros(self.N, dtype=np.int64)
        syn = np.zeros(self.N)
        base = np.zeros(self.N)
        base[sl["ORN"]] = p.bias_orn
        base[sl["PN"]] = p.bias_pn
        base[sl["KC"]] = self.bias_kc
        base[sl["MBON"]] = p.bias_mbon
        ext = base.copy()

        da_rew = da_pun = 0.0
        elig = np.zeros(p.n_kc)
        rec_s, rec_i = [], []

        for k in range(n):
            o = odor_of_step[k]
            if o >= 0:
                ext[sl["ORN"]] = base[sl["ORN"]] + p.gain_orn * self.aff[o]
            else:
                ext[sl["ORN"]] = base[sl["ORN"]]
            ext[dan_rew] = p.dan_drive if rew[k] else 0.0
            ext[dan_pun] = p.dan_drive if pun[k] else 0.0

            # 1) integracion de voltaje (las neuronas refractarias quedan en reset)
            I = ext + syn
            free = refr == 0
            z = sig * rng.standard_normal(self.N)
            v = np.where(free, v + leak * (I - v) + z, p.v_reset)
            spk = free & (v >= p.v_thr)
            v[spk] = p.v_reset
            refr[spk] = ref_steps
            refr[~free] -= 1

            # 2) propagacion sináptica (efecto en el paso siguiente)
            syn *= dec_syn
            s_orn = spk[sl["ORN"]]
            s_pn = spk[sl["PN"]].astype(np.float64)
            s_kc = spk[sl["KC"]].astype(np.float64)
            s_apl = spk[sl["APL"]]
            syn[sl["PN"]] += p.w_orn_pn * s_orn
            syn[sl["KC"]] += self.W_pn_kc @ s_pn
            syn[off["APL"]] += p.w_kc_apl * s_kc.sum()
            if s_apl[0]:
                syn[sl["KC"]] -= p.w_apl_kc
            syn[sl["MBON"]] += W @ s_kc

            # 3) dopamina y elegibilidad -> plasticidad KC->MBON
            s_rew = float(spk[dan_rew].sum())
            s_pun = float(spk[dan_pun].sum())
            da_rew = da_rew * dec_da + s_rew
            da_pun = da_pun * dec_da + s_pun
            elig = elig * dec_el + s_kc
            if da_rew > 1e-4 or da_pun > 1e-4:
                # Coincidencia no lineal: solo cuentan las KC fuertemente activas
                # (traza por encima de elig_thr, al cuadrado).
                coinc = np.maximum(elig - p.elig_thr, 0.0) ** 2
                W += dt * (-p.eta_dep * da_rew + p.eta_pot * da_pun) * coinc
                np.clip(W, 0.0, p.w_max, out=W)

            if spk.any():
                idx = np.flatnonzero(spk)
                rec_s.append(np.full(idx.size, k, dtype=np.int64))
                rec_i.append(idx)

        steps = np.concatenate(rec_s) if rec_s else np.zeros(0, dtype=np.int64)
        ids = np.concatenate(rec_i) if rec_i else np.zeros(0, dtype=np.int64)
        return Result(seed=self.seed, params=p, dt_ms=dt, n_steps=n, schedule=list(schedule),
                      spike_step=steps, spike_id=ids, W_init=W_init, W_final=W.copy(),
                      offset=dict(self.offset), sizes=dict(self.sizes), xy=self.xy)


def to_contract(res: Result, description: str) -> dict:
    """Convierte el resultado al formato CONTRATO de out/activity.json."""
    neurons = []
    for name in POP_NAMES:
        lo, xy = res.offset[name], res.xy[name]
        for i in range(res.sizes[name]):
            neurons.append({"id": int(lo + i), "type": name,
                            "x": round(float(xy[i, 0]), 4), "y": round(float(xy[i, 1]), 4)})
    spikes = [[round(float(s) * res.dt_ms, 1), int(i)]
              for s, i in zip(res.spike_step, res.spike_id)]
    stimuli = [{"name": s["name"], "t_start": round(float(s["t0"]), 1),
                "t_end": round(float(s["t1"]), 1)} for s in res.schedule]
    return {
        "meta": {"description": description, "synthetic": True, "seed": int(res.seed),
                 "dt_ms": float(res.dt_ms),
                 "duration_ms": round(res.n_steps * res.dt_ms, 1)},
        "neurons": neurons,
        "spikes": spikes,
        "stimuli": stimuli,
    }


def write_contract(d: dict, path: str) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(d, f, separators=(",", ":"))
