"""Paso 1 de la ronda de cierre: igualar el regimen basal de DN del cableado aleatorizado al del conectoma real.

Mide la tasa media de DN (Hz) a olor simetrico de intensidad c = 1 (izquierda y derecha por separado, 1 s tras
300 ms de calentamiento) para el conectoma real y para el aleatorizado con varios W_syn. Luego se elige el W_syn
del aleatorizado cuya tasa media de DN iguala la del conectoma. Solo se barre W_syn; nada mas se ajusta.

Uso: python3 src/match_rate.py [--wsyn-grid 0.275,0.2,0.15,0.1,0.05]
Salida: out/rate_match.json
"""
import argparse
import json
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
DT = 1.0


def dn_rate(variant_graph, w_syn, seeds=(1,), c=1.0, win_ms=1000.0, warm_ms=300.0):
    G = variant_graph
    N = G["ids"].shape[0]
    net = lif_engine.Network(G, bias_mV_per_ms=np.zeros(N), seed=1, w_syn=w_syn, dt=DT)
    w = fa.FlyWorld(G, net)
    sideL = w.orn_side == "L"
    rates = []
    for sd in seeds:
        for side in ("L", "R"):
            rng = np.random.default_rng(1000 * sd + (0 if side == "L" else 1))
            net.V[:] = rng.uniform(-52.0, -45.0, N)
            net.g[:] = 0.0
            net.refr[:] = 0
            net.counts[:] = 0
            net.alive[:] = 1
            cL, cR = (c, 0.0) if side == "L" else (0.0, c)
            net.ext[:] = 0.0
            net.ext[w.orn] = fa.orn_drive(np.where(sideL, cL, cR)) * w.orn_aff
            net.advance(warm_ms)
            net.counts[:] = 0
            net.advance(win_ms)
            cnt = net.counts.astype(float) / (win_ms / 1000.0)
            dn = np.concatenate([w.dn_L, w.dn_R])
            rates.append(float(cnt[dn].mean()))
            rates_by_side = rates
    return float(np.mean(rates)), rates_by_side


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--wsyn-grid", default="0.275,0.2,0.15,0.1,0.05")
    a = ap.parse_args()
    t0 = time.time()
    grid = [float(x) for x in a.wsyn_grid.split(",")]
    G = cns_graph.load_graph()
    res = {"connectome": {}, "rewired": {}}
    rate_c, _ = dn_rate(G, 0.275)
    res["connectome"]["0.275"] = round(rate_c, 3)
    print("connectome W=0.275 DN media Hz", round(rate_c, 3), flush=True)
    Gr = dict(G)
    Gr["indices"], done = rewire.swap_targets(G, factor=10, seed=7)
    res["rewired_swaps"] = int(done)
    for ws in grid:
        r, _ = dn_rate(Gr, ws)
        res["rewired"][str(ws)] = round(r, 3)
        print("rewired W", ws, "DN media Hz", round(r, 3), flush=True)
    best = min(grid, key=lambda ws: abs(res["rewired"][str(ws)] - rate_c))
    res["target_rate_Hz"] = round(rate_c, 3)
    res["W_rewired_matched"] = best
    res["wall_s"] = round(time.time() - t0, 1)
    os.makedirs(os.path.join(HERE, "out"), exist_ok=True)
    with open(os.path.join(HERE, "out", "rate_match.json"), "w", encoding="utf-8") as fh:
        json.dump(res, fh, indent=1)
        fh.write("\n")
    print("W aleatorizado elegido", best, "wall", res["wall_s"], flush=True)


if __name__ == "__main__":
    main()
