"""Experimento de control en bucle abierto: transferencia sensoriomotora ORN -> DN.

Para cada red (conectoma real, cableado aleatorizado conservando grados, neurotransmisores barajados):
  olor solo a la izquierda (cL=c, cR=0) y solo a la derecha (cL=0, cR=c), dos niveles c, varias semillas.
  A = rL - rR (Hz) medido en la ventana de olor (tras 300 ms de calentamiento).
  G = (A_izq - A_der) / 2  -> ganancia ipsilateral (Hz por unidad de asimetria de olor).
  M = (A_izq + A_der) / 2  -> sesgo L-R comun (estructura de la red y la reconstruccion).
Cada variante corre en su propio proceso (spawn). Salida: out/transfer.json (IC95 por bootstrap sobre semillas).
"""
import argparse
import json
import multiprocessing as mp
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cns_graph  # noqa: E402
import fly_arena as fa  # noqa: E402
import lif_engine  # noqa: E402
import rewire  # noqa: E402

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
W_SYN = 0.275
DT = 1.0


def build(variant, w_syn=W_SYN):
    G = cns_graph.load_graph()
    N = G["ids"].shape[0]
    if variant.startswith("rewired"):
        G = dict(G)
        G["indices"], _ = rewire.swap_targets(G, factor=10, seed=7)
    elif variant == "signshuffle":
        G = dict(G)
        G["sign"] = rewire.shuffle_signs(G["sign"], seed=11)
    net = lif_engine.Network(G, bias_mV_per_ms=np.zeros(N), seed=1, w_syn=w_syn, dt=DT)
    return G, net


def run_variant(variant, seeds, levels, win_ms=1000.0, warm_ms=300.0, w_syn=W_SYN):
    G, net = build(variant, w_syn)
    w = fa.FlyWorld(G, net)
    N = net.N
    sideL = w.orn_side == "L"
    out = []
    for sd in seeds:
        for c in levels:
            A = {}
            R_ = {}
            for side in ("L", "R"):
                rng = np.random.default_rng(1000 * sd + (0 if side == "L" else 1))
                net.V[:] = rng.uniform(-52.0, -45.0, N)
                net.g[:] = 0.0
                net.refr[:] = 0
                net.counts[:] = 0
                net.alive[:] = 1
                net.ext[:] = 0.0
                cL, cR = (c, 0.0) if side == "L" else (0.0, c)
                net.ext[w.orn] = fa.orn_drive(np.where(sideL, cL, cR)) * w.orn_aff
                net.advance(warm_ms)
                net.counts[:] = 0
                net.advance(win_ms)
                cnt = net.counts.astype(float) / (win_ms / 1000.0)
                A[side] = float(cnt[w.dn_L].mean() - cnt[w.dn_R].mean())
                R_[side] = float(0.5 * (cnt[w.dn_L].mean() + cnt[w.dn_R].mean()))
            out.append(dict(seed=sd, level=c, A_L=A["L"], A_R=A["R"],
                            G=(A["L"] - A["R"]) / 2.0, M=(A["L"] + A["R"]) / 2.0,
                            DN_media_Hz=(R_["L"] + R_["R"]) / 2.0))
    net.ext[:] = 0.0
    return variant, out


def _job(args):
    return run_variant(*args)


def bootstrap_ci(x, n=2000, seed=0):
    x = np.asarray(x, float)
    rng = np.random.default_rng(seed)
    means = [rng.choice(x, size=len(x), replace=True).mean() for _ in range(n)]
    return [float(np.percentile(means, 2.5)), float(np.percentile(means, 97.5))]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=5)
    ap.add_argument("--variants", default="connectome,rewired,signshuffle")
    ap.add_argument("--rewired-wsyn", type=float, default=None,
                    help="W_syn del aleatorizado (si se omite, igual que el conectoma)")
    ap.add_argument("--levels", default="0.25,1.0")
    ap.add_argument("--out", default="transfer.json")
    a = ap.parse_args()
    t0 = time.time()
    variants = a.variants.split(",")
    seeds = list(range(1, a.seeds + 1))
    levels = [float(x) for x in a.levels.split(",")]
    ws = {v: (a.rewired_wsyn if (v.startswith("rewired") and a.rewired_wsyn is not None) else W_SYN) for v in variants}
    ctx = mp.get_context("spawn")
    with ctx.Pool(len(variants)) as pool:
        res = pool.map(_job, [(v, seeds, levels, 1000.0, 300.0, ws[v]) for v in variants], chunksize=1)
    summary = {}
    for v, rows in res:
        summary[v] = {}
        for c in levels:
            r = [x for x in rows if x["level"] == c]
            G_ = [x["G"] for x in r]
            M_ = [x["M"] for x in r]
            D_ = [x["DN_media_Hz"] for x in r]
            summary[v][f"c={c}"] = dict(
                W_syn=ws[v], DN_media_Hz=round(float(np.mean(D_)), 3), DN_media_ic95=[round(v_, 3) for v_ in bootstrap_ci(D_)],
                G_media=round(float(np.mean(G_)), 4), G_ic95=[round(v_, 4) for v_ in bootstrap_ci(G_)],
                M_media=round(float(np.mean(M_)), 4), M_ic95=[round(v_, 4) for v_ in bootstrap_ci(M_)],
                G_por_semilla=[round(g, 4) for g in G_])
    doc = dict(descripcion="Ganancia sensoriomotora ORN->DN en bucle abierto. G = ganancia ipsilateral (Hz por asimetria "
                           "de olor), M = sesgo L-R comun. Controles: cableado aleatorizado conservando grados, "
                           "neurotransmisores barajados.",
               w_syn_conectoma=W_SYN, w_syn_aleatorizado=a.rewired_wsyn, seeds=seeds, levels=levels,
               resultados=summary, wall_s=round(time.time() - t0, 1))
    os.makedirs(os.path.join(HERE, "out"), exist_ok=True)
    with open(os.path.join(HERE, "out", a.out), "w", encoding="utf-8") as fh:
        json.dump(doc, fh, indent=1)
        fh.write("\n")
    for v in summary:
        print(v, json.dumps(summary[v]), flush=True)
    print("wall", doc["wall_s"], flush=True)


if __name__ == "__main__":
    main()
