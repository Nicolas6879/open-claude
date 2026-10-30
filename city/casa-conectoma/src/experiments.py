"""Experimentos de la mosca virtual sobre el SNC completo.

Cada prueba usa la misma semilla (posicion inicial) en todas las condiciones (diseno apareado).
Subcomandos: tune | main | lesions | hubs
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
import hubs as hb  # noqa: E402
import lif_engine  # noqa: E402
import rewire  # noqa: E402

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BIAS = 0.0  # Shiu et al.: linea base 0 Hz; sin sesgo intrinseco (v2 usaba 7.5 mV: ver LOG)
W_SYN = 0.275  # Shiu et al. 2024 (valor fijo de su modelo)
DT = 1.0
STATE = {}


def setup_variants(variants):
    """Construye las redes necesarias en el proceso padre (se heredan por fork)."""
    G = cns_graph.load_graph()
    N = G["ids"].shape[0]
    bias = np.full(N, BIAS)
    nets = {}
    if "connectome" in variants or "lesion" in variants:
        nets["connectome"] = lif_engine.Network(G, bias_mV_per_ms=bias, seed=1, w_syn=W_SYN, dt=DT)
    if "rewired" in variants:
        G2 = dict(G)
        idx, done = rewire.swap_targets(G, factor=10, seed=7)
        G2["indices"] = idx
        nets["rewired"] = lif_engine.Network(G2, bias_mV_per_ms=bias, seed=1, w_syn=W_SYN, dt=DT)
        STATE["rewire_done"] = int(done)
        STATE["rewire_dup_frac"] = float(rewire.duplicate_fraction(G["indptr"], idx))
    if "signshuffle" in variants:
        G3 = dict(G)
        G3["sign"] = rewire.shuffle_signs(G["sign"], seed=11)
        nets["signshuffle"] = lif_engine.Network(G3, bias_mV_per_ms=bias, seed=1, w_syn=W_SYN, dt=DT)
    base = nets.get("connectome") or next(iter(nets.values()))
    world = fa.FlyWorld(G, base)
    STATE.update(G=G, nets=nets, world=world, base_net=base)
    return G, world, nets


def use_variant(name):
    world = STATE["world"]
    world.net = STATE["nets"][name]
    return world


def job(spec):
    cond, seed, K_T, forward = spec["cond"], spec["seed"], spec.get("K_T", 0.0), spec.get("forward", "const")
    world = STATE["world"]
    variant = spec.get("variant", "connectome")
    if cond in ("connectome", "connectome_mirror", "lesion_DN_all", "lesion_DN_L", "lesion_DN_R", "lesion_ORN_all",
                "lesion_hubs", "lesion_random", "rewired", "signshuffle", "forward_dn"):
        world = use_variant(variant)
        base = STATE["baseline"][variant]
        off = spec.get("off_idx")
        off = np.asarray(off, dtype=np.int64) if off is not None else None
        if cond == "lesion_ORN_all":
            off = world.orn
        if cond == "lesion_DN_all":
            off = np.concatenate([world.dn_L, world.dn_R])
        if cond == "lesion_DN_L":
            off = world.dn_L
        if cond == "lesion_DN_R":
            off = world.dn_R
        sign = -1.0 if cond == "connectome_mirror" else 1.0
        mode = "connectome"
        fwd = forward
        rb = None
        r = fa.run_trial(world, seed, mode=mode, K_T=K_T, turn_sign=sign, forward=fwd, off_idx=off,
                         rate_base=rb, baseline=base)
    elif cond == "direct":
        r = fa.run_trial(world, seed, mode="direct", K_T=K_T, baseline=(0, 0))
    elif cond == "randomwalk":
        r = fa.run_trial(world, seed, mode="randomwalk", K_T=0.0, baseline=(0, 0))
    else:
        raise ValueError(cond)
    r["cond"] = cond
    r["K_T"] = K_T
    return r


def init_baselines(variants):
    STATE["baseline"], STATE["rate_base"] = {}, {}
    world = STATE["world"]
    for v in variants:
        world.net = STATE["nets"][v]
        b = fa.measure_baseline(world)
        STATE["baseline"][v] = (b[0].tolist(), b[1].tolist())
        STATE["rate_base"][v] = (b[0] + b[1])
    STATE["world"].net = STATE["nets"][variants[0]]


def _init_worker(variants):
    # spawn: cada proceso carga el grafo y construye sus redes (fork se bloquea con hilos de numba)
    import os as _os
    _os.environ.setdefault("NUMBA_NUM_THREADS", "1")
    setup_variants(variants)
    init_baselines(variants)


def run_pool(specs, variants, procs=4):
    ctx = mp.get_context("spawn")
    with ctx.Pool(procs, initializer=_init_worker, initargs=(variants,)) as pool:
        return pool.map(job, specs, chunksize=1)


def summarize(res):
    succ = np.array([r["success"] for r in res], dtype=float)
    n = len(succ)
    p = succ.mean() if n else float("nan")
    z = 1.96
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    ts = [r["t_s"] for r in res if r["success"]]
    return dict(n=n, success=round(p, 3), ci95=[round(centre - half, 3), round(centre + half, 3)],
                t_success_median_s=round(float(np.median(ts)), 2) if ts else None,
                t_success_mean_s=round(float(np.mean(ts)), 2) if ts else None,
                final_dist_median_mm=round(float(np.median([r["final_dist_mm"] for r in res])), 2))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["tune", "main", "lesions", "hubs"])
    ap.add_argument("--K_hub", type=int, default=0)
    ap.add_argument("--procs", type=int, default=4)
    ap.add_argument("--n", type=int, default=40)
    ap.add_argument("--K", type=float, default=None)
    ap.add_argument("--Kd", type=float, default=None)
    a = ap.parse_args()
    out = os.path.join(HERE, "out")
    os.makedirs(out, exist_ok=True)
    t0 = time.time()
    if a.cmd == "tune":
        variants = ["connectome"]
        specs = []
        for K in [K_ for K_ in ([a.K] if a.K else [5.0, 15.0, 40.0])]:
            for s in range(100, 100 + a.n):
                specs.append(dict(cond="connectome", seed=s, K_T=K, variant="connectome"))
        for K in ([a.Kd] if a.Kd else [10.0, 30.0, 90.0]):
            for s in range(100, 100 + a.n):
                specs.append(dict(cond="direct", seed=s, K_T=K))
        res = run_pool(specs, variants, a.procs)
        rows = {}
        for r in res:
            rows.setdefault((r["cond"], r["K_T"]), []).append(r)
        table = {f"{c}|K={k}": summarize(v) for (c, k), v in rows.items()}
        for k, v in table.items():
            print(k, v, flush=True)
        with open(os.path.join(out, "tuning.json"), "w", encoding="utf-8") as fh:
            json.dump(dict(seeds="100-%d" % (99 + a.n), table=table,
                           wall_s=round(time.time() - t0, 1)), fh, indent=1)
    elif a.cmd == "main":
        variants = ["connectome", "rewired", "signshuffle"]
        K, Kd = a.K, a.Kd
        if K is None or Kd is None:
            raise SystemExit("main requiere --K (ganancia de giro de la red) y --Kd (controlador directo), elegidos en tune")
        specs = []
        seeds = range(200, 200 + a.n)
        for s_ in seeds:
            specs.append(dict(cond="connectome", seed=s_, K_T=K, variant="connectome"))
            specs.append(dict(cond="connectome_mirror", seed=s_, K_T=K, variant="connectome"))
            specs.append(dict(cond="rewired", seed=s_, K_T=K, variant="rewired"))
            specs.append(dict(cond="signshuffle", seed=s_, K_T=K, variant="signshuffle"))
            specs.append(dict(cond="direct", seed=s_, K_T=Kd))
            specs.append(dict(cond="randomwalk", seed=s_))
        res = run_pool(specs, variants, a.procs)
        rows = {}
        for r in res:
            rows.setdefault(r["cond"], []).append(r)
        summ = {c: summarize(v) for c, v in rows.items()}
        for c, v in summ.items():
            print(c, v, flush=True)
        with open(os.path.join(out, "chemotaxis_summary.json"), "w", encoding="utf-8") as fh:
            json.dump(dict(seeds="200-%d" % (199 + a.n), K_T=K, K_direct=Kd, dt_ms=DT, w_syn=W_SYN, bias_mV=BIAS,
                           rewire=STATE.get("rewire_stats", {}), condiciones=summ,
                           wall_s=round(time.time() - t0, 1)), fh, indent=1)
        # trayectorias de muestra (3 semillas) para la animacion
        samp = {c: [dict(seed=r["seed"], success=r["success"], traj=r["traj"]) for r in rows[c] if r["seed"] in (200, 201, 202)]
                for c in ["connectome", "rewired", "direct", "randomwalk"]}
        with open(os.path.join(out, "trajectories_sample.json"), "w", encoding="utf-8") as fh:
            json.dump(samp, fh, separators=(",", ":"))
    elif a.cmd == "lesions":
        import hubs_io
        variants = ["connectome"]
        K = a.K
        hub_idx = hubs_io.load_hub_indices()
        specs = []
        seeds = range(200, 200 + a.n)
        rand_idx = hubs_io.matched_random(hub_idx)
        conds = {"lesion_DN_all": None, "lesion_DN_L": None, "lesion_ORN_all": None,
                 "lesion_hubs": hub_idx, "lesion_random": rand_idx}
        for c, off in conds.items():
            for s_ in seeds:
                specs.append(dict(cond=c, seed=s_, K_T=K, variant="connectome",
                                  off_idx=None if off is None else [int(x) for x in off]))
        res = run_pool(specs, variants, a.procs)
        rows = {}
        for r in res:
            rows.setdefault(r["cond"], []).append(r)
        summ = {c: summarize(v) for c, v in rows.items()}
        for c, v in summ.items():
            print(c, v, flush=True)
        with open(os.path.join(out, "lesions_summary.json"), "w", encoding="utf-8") as fh:
            json.dump(dict(seeds="200-%d" % (199 + a.n), K_T=K, n_hubs=int(len(hub_idx)),
                           n_random=int(len(rand_idx)), condiciones=summ, wall_s=round(time.time() - t0, 1)), fh, indent=1)
    elif a.cmd == "hubs":
        import hubs as hb
        G = cns_graph.load_graph()
        usage, info = hb.path_usage(G, n_src=a.n, seed=0)
        top = hb.rank_hubs(G, usage, top=60)
        with open(os.path.join(out, "hubs.json"), "w", encoding="utf-8") as fh:
            json.dump(dict(info=info, top=top), fh, ensure_ascii=False, indent=1)
        np.save(os.path.join(os.environ.get("CONECTOMA_DATA", "."), "hub_usage.npy"), usage)
        print(json.dumps(info), flush=True)
        for t_ in top[:15]:
            print(t_, flush=True)
    print("wall", round(time.time() - t0, 1), flush=True)


if __name__ == "__main__":
    main()
