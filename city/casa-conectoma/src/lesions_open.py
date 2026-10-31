"""Lesiones virtuales en bucle abierto sobre la ganancia sensoriomotora (paso 2 de la ronda de cierre).

Para cada lesion se silencian las neuronas indicadas (alive = 0: no disparan) en la red del conectoma real
(W_syn = 0.275, linea base 0 Hz, como en transfer.py). Se mide G (ganancia ipsilateral) y la tasa media de DN
a c = 1 con 5 semillas, igual que en transfer.py.

Lesiones:
  none            control sin lesion
  DN_all          silenciar todas las DN (lectura motora)           -> G = 0 por construccion (lectura nula)
  DN_L            silenciar DN izquierdas
  ORN_all         silenciar todas las ORN (sin olor)                -> G = 0 por construccion (sin entrada)
  hubs_top10      silenciar los 10 hubs ORN->DN de out/hubs.json (no ORN, no DN)
  random_top10    10 neuronas al azar con grado de salida emparejado a esos hubs (control de cualquier neurona)

Uso: python3 src/lesions_open.py --seeds 5 [--procs 4]
Salida: out/lesions_open.json
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
import hubs_io  # noqa: E402
import lif_engine  # noqa: E402
import transfer  # noqa: E402

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
W_SYN = transfer.W_SYN
DT = transfer.DT


def lesion_indices(name, G, w):
    if name == "none":
        return np.array([], dtype=np.int64)
    if name == "DN_all":
        return np.concatenate([w.dn_L, w.dn_R])
    if name == "DN_L":
        return w.dn_L
    if name == "ORN_all":
        return w.orn
    if name == "hubs_top10":
        return hubs_io.load_hub_indices(n=10)
    if name == "random_top10":
        return hubs_io.matched_random(hubs_io.load_hub_indices(n=10))
    raise ValueError(name)


def run_lesion(name, seeds, win_ms=1000.0, warm_ms=300.0):
    G = cns_graph.load_graph()
    N = G["ids"].shape[0]
    net = lif_engine.Network(G, bias_mV_per_ms=np.zeros(N), seed=1, w_syn=W_SYN, dt=DT)
    w = fa.FlyWorld(G, net)
    off = lesion_indices(name, G, w)
    sideL = w.orn_side == "L"
    rows = []
    for sd in seeds:
        A, R_ = {}, {}
        for side in ("L", "R"):
            rng = np.random.default_rng(1000 * sd + (0 if side == "L" else 1))
            net.V[:] = rng.uniform(-52.0, -45.0, N)
            net.g[:] = 0.0
            net.refr[:] = 0
            net.counts[:] = 0
            net.alive[:] = 1
            if len(off):
                net.alive[off] = 0
            cL, cR = (1.0, 0.0) if side == "L" else (0.0, 1.0)
            net.ext[:] = 0.0
            net.ext[w.orn] = fa.orn_drive(np.where(sideL, cL, cR)) * w.orn_aff
            net.advance(warm_ms)
            net.counts[:] = 0
            net.advance(win_ms)
            cnt = net.counts.astype(float) / (win_ms / 1000.0)
            A[side] = float(cnt[w.dn_L].mean() - cnt[w.dn_R].mean())
            R_[side] = float(0.5 * (cnt[w.dn_L].mean() + cnt[w.dn_R].mean()))
        rows.append(dict(seed=sd, G=(A["L"] - A["R"]) / 2.0, M=(A["L"] + A["R"]) / 2.0,
                         DN_media_Hz=(R_["L"] + R_["R"]) / 2.0))
    return name, len(off), rows


def _job(args):
    return run_lesion(*args)


def ci(x, n=2000, seed=0):
    x = np.asarray(x, float)
    rng = np.random.default_rng(seed)
    m = [rng.choice(x, size=len(x), replace=True).mean() for _ in range(n)]
    return [round(float(np.percentile(m, 2.5)), 4), round(float(np.percentile(m, 97.5)), 4)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=5)
    ap.add_argument("--procs", type=int, default=4)
    a = ap.parse_args()
    t0 = time.time()
    names = ["none", "DN_all", "DN_L", "ORN_all", "hubs_top10", "random_top10"]
    seeds = list(range(1, a.seeds + 1))
    ctx = mp.get_context("spawn")
    with ctx.Pool(a.procs) as pool:
        res = pool.map(_job, [(n, seeds) for n in names], chunksize=1)
    out = {}
    for name, n_off, rows in res:
        G_ = [r["G"] for r in rows]
        D_ = [r["DN_media_Hz"] for r in rows]
        out[name] = dict(neuronas_silenciadas=int(n_off),
                         G_media=round(float(np.mean(G_)), 4), G_ic95=ci(G_),
                         DN_media_Hz=round(float(np.mean(D_)), 3), DN_ic95=ci(D_),
                         G_por_semilla=[round(g, 4) for g in G_])
        print(name, json.dumps(out[name]), flush=True)
    doc = dict(descripcion="Lesiones virtuales en bucle abierto (c=1, W_syn 0.275, 5 semillas). G = ganancia "
                           "ipsilateral; DN_media_Hz = tasa media de DN.", seeds=seeds, resultados=out,
               wall_s=round(time.time() - t0, 1))
    with open(os.path.join(HERE, "out", "lesions_open.json"), "w", encoding="utf-8") as fh:
        json.dump(doc, fh, indent=1)
        fh.write("\n")
    print("wall", doc["wall_s"], flush=True)


if __name__ == "__main__":
    main()
