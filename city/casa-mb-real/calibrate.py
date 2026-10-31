"""Calibracion de los parametros libres (supuestos) y comprobacion contra Hige 2015.  Escribe out/calibration.json.

1. Escalas PN->KC, KC->APL, APL->KC: se eligieron en una rejilla previa (ver LOG) para ~7 % de KC con >=1 espiga en 1 s
   de olor con APL y ~4x mas sin APL; aqui se re-evalua el punto elegido y vecinos (no se re-optimiza).
2. S_mbon: ganancia KC->MBON (normalizada por MBON) para ~25 Hz de tasa media de MBON con olor.
3. eta: tasa de depresion; se fija para que UN emparejamiento con PPL1-g1pedc (PPL101) deprima la respuesta de MBON-g1pedc
   (MBON11) al CS+ un ~80 % (Hige 2015: 118 -> 24 espigas).  El CS- (-25 % en Hige: 110 -> 83) NO se ajusta: es una validacion.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "src"))
import numpy as np

import mbdata as md
import network as nw
import protocol as pr


def kc_stats(nodes, edges, p, nodd=8, silence_apl=False, seed=5):
    net = nw.build(nodes, edges, p)
    R = pr.Runner(net, silence=(np.arange(*net.ranges["APL"]) if silence_apl else None))
    rng = np.random.default_rng(seed)
    a1, a2, a5, apl = [], [], [], []
    for i in range(nodd):
        o = pr.make_odor(net, rng)
        c, _ = R.trial(o, test=True, seed=10 + i)
        kc = c[R.kc_lo:R.kc_hi]
        a1.append((kc >= 1).mean()); a2.append((kc >= 2).mean()); a5.append((kc >= 5).mean())
        apl.append(c[R.apl_lo:R.apl_hi].mean())
    c, _ = R.trial(np.zeros(len(net.gen_pn)), test=True, seed=99)
    base = (c[R.kc_lo:R.kc_hi] >= 1).mean()
    return dict(kc_ge1=float(np.mean(a1)), kc_ge2=float(np.mean(a2)), kc_ge5=float(np.mean(a5)), apl_hz=float(np.mean(apl)),
                kc_reposo_ge1=float(base))


def main():
    nodes, edges = md.load()
    out = {"nota": "supuestos calibrados; ver docstring"}
    p0 = nw.Params()
    out["escalas_elegidas"] = {k: getattr(p0, k) for k in ("s_pn", "s_kcapl", "s_aplkc", "S_mbon", "eta", "theta", "tau_e_ms")}
    out["kc_con_APL"] = kc_stats(nodes, edges, p0)
    out["kc_sin_APL"] = kc_stats(nodes, edges, p0, silence_apl=True)
    vec = {}
    for kcapl, aplkc in ((0.03, 0.3), (0.03, 1.0), (0.1, 0.3), (0.1, 1.0), (0.1, 3.0)):
        p = nw.Params(s_kcapl=kcapl, s_aplkc=aplkc)
        vec[f"kcapl={kcapl},aplkc={aplkc}"] = kc_stats(nodes, edges, p, nodd=4)
    out["vecinos_APL"] = vec
    # MBON
    mb = {}
    for S in (3000.0, 7000.0, 12000.0):
        net = nw.build(nodes, edges, nw.Params(S_mbon=S))
        R = pr.Runner(net)
        rng = np.random.default_rng(2)
        rr = []
        for i in range(4):
            o = pr.make_odor(net, rng)
            c, _ = R.trial(o, test=True, seed=i)
            rr.append(c[R.mb_lo:R.mb_hi])
        rr = np.array(rr)
        c, _ = R.trial(np.zeros(len(net.gen_pn)), test=True, seed=9)
        mb[str(S)] = dict(media_hz=float(rr.mean()), mediana=float(np.median(rr)), p10=float(np.percentile(rr, 10)),
                          p90=float(np.percentile(rr, 90)), frac_mudos=float((rr.mean(0) < 1).mean()),
                          reposo_hz=float(c[R.mb_lo:R.mb_hi].mean()))
    out["MBON_ganancia"] = mb
    # eta (Hige 2015)
    net = nw.build(nodes, edges, nw.Params())
    dan = np.flatnonzero(nodes["cls"] == md.DAN)
    mbi = np.flatnonzero(nodes["cls"] == md.MBON)
    ppl101 = dan[nodes["type"][dan] == "PPL101"]
    m11 = np.flatnonzero(nodes["type"][mbi] == "MBON11")
    R = pr.Runner(net, dan_stim=ppl101)
    res = {}
    for eta in (0.3, 1.0, 2.0, 2.3, 3.0, 5.0):
        ch = []
        for s in range(24):
            rng = np.random.default_rng(100 + s)
            odors = [pr.make_odor(net, rng) for _ in range(3)]
            o = R.conditioning(odors, seed=s + 1, eta=eta, theta=0.3, n_pairs=1, ntest=4)
            pre = o["mb_pre"][:, m11].mean(1); post = o["mb_post"][:, m11].mean(1)
            ch.append(post / np.maximum(pre, 1e-9) - 1)
        ch = np.array(ch)
        res[str(eta)] = dict(cs_mas=float(ch[:, 0].mean()), cs_menos=float(ch[:, 1].mean()), nuevo=float(ch[:, 2].mean()))
    out["eta_vs_Hige2015_MBON11"] = dict(objetivo_cs_mas=-0.80, objetivo_cs_menos_NO_ajustado=-0.25, resultados=res)
    json.dump(out, open(os.path.join(HERE, "out", "calibration.json"), "w"), indent=1)
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
