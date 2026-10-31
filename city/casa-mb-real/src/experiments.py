"""Experimentos de aprendizaje: condiciones, trabajos paralelos y resumen estadistico.

Un TRABAJO = (condicion de red, semilla).  La semilla fija: el triplete de olores (A,B,C), el ruido y el sorteo de los
controles aleatorios (misma semilla => mismos olores en todas las condiciones: comparacion pareada).
Para cada trabajo se corre un control sin DAN ('nous') y uno por cada conjunto de DAN estimulados; el efecto de
aprendizaje es  dLI = LI(emparejado) - LI(control sin DAN),  que descuenta la deriva y el ruido de prueba-reprueba.
"""
import dataclasses
import json
import multiprocessing as mp
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import analysis as an
import mbdata as md
import network as nw
import protocol as pr

_G = {}


def _init():
    nodes, edges = md.load()
    _G["nodes"], _G["edges"] = nodes, edges
    dan = np.flatnonzero(nodes["cls"] == md.DAN)
    _G["dan"] = dan
    _G["dtype"] = nodes["type"][dan]
    mb = np.flatnonzero(nodes["cls"] == md.MBON)
    _G["mb"] = mb
    _G["mtype"] = nodes["type"][mb]


def dan_set(name):
    """'PAM' | 'PPL1' | 'type:PAM08' | 'types:PAM01,PAM02' | 'PAM-minus:PAM08' | 'none'."""
    dan, dt = _G["dan"], _G["dtype"]
    if name == "none":
        return np.array([], np.int64)
    if name == "PAM":
        return dan[[t.startswith("PAM") for t in dt]]
    if name == "PPL1":
        return dan[[t.startswith("PPL1") for t in dt]]
    if name.startswith("type:"):
        return dan[dt == name[5:]]
    if name.startswith("types:"):
        ts = set(name[6:].split(","))
        return dan[[t in ts for t in dt]]
    if name.startswith("PAM-minus:") or name.startswith("PPL1-minus:"):
        base, rm = name.split("-minus:")
        s = dan_set(base)
        return np.array([i for i in s if _G["nodes"]["type"][i] != rm], np.int64)
    raise ValueError(name)


def mbon_idx(types):
    nodes = _G["nodes"]
    return np.flatnonzero(np.isin(nodes["type"], list(types)) & (nodes["cls"] == md.MBON))


@dataclasses.dataclass
class Cond:
    name: str
    params: dict = dataclasses.field(default_factory=dict)
    rewire: dict = dataclasses.field(default_factory=dict)      # {'kcmbon': 'global'|'lobe', 'pnkc': True}
    stims: tuple = ("PAM", "PPL1")
    silence: dict = dataclasses.field(default_factory=dict)     # {'apl': True, 'mbon_types': [...]}
    us_mode: str = "forward"
    eta: float = None
    theta: float = None
    n_pairs: int = None
    ntest: int = None


def run_job(args):
    cond, seed = args
    if not _G:
        _init()
    nodes, edges = _G["nodes"], _G["edges"]
    p = nw.Params(**cond.params)
    rw = dict(cond.rewire)
    rng_w = np.random.default_rng([seed, 4242])
    if rw.get("kcmbon") == "lobe":
        # lobulo del MBON = subtipo de KC dominante (por neurona MBON)
        kcm = (nodes["cls"][edges["pre"]] == md.KC) & (nodes["cls"][edges["post"]] == md.MBON)
        cl = np.array([0 if t.startswith("KCg") else (1 if t.startswith("KCa'b'") else 2) for t in nodes["type"][edges["pre"][kcm]]])
        acc = np.zeros((len(nodes["id"]), 3))
        np.add.at(acc, (edges["post"][kcm], cl), edges["w"][kcm])
        rw["mbon_lobe"] = acc.argmax(1)
    net = nw.build(nodes, edges, p, rng=rng_w, rewire=rw or None)
    v = an.valence_vector(nodes, "nt")
    sil = []
    if cond.silence.get("apl"):
        sil += list(range(*net.ranges["APL"]))
    if cond.silence.get("mbon_types"):
        sil += list(mbon_idx(cond.silence["mbon_types"]))
    eta = cond.eta if cond.eta is not None else p.eta
    theta = cond.theta if cond.theta is not None else p.theta
    npairs = cond.n_pairs if cond.n_pairs is not None else p.n_pairs
    ntest = cond.ntest if cond.ntest is not None else p.ntest
    rng_o = np.random.default_rng([seed, 1717])
    odors = [pr.make_odor(net, rng_o) for _ in range(3)]
    out = {}
    names = ["none"] + [s for s in cond.stims if s != "none"]
    for nm in names:
        R = pr.Runner(net, silence=sil, dan_stim=dan_set(nm))
        o = R.conditioning(odors, seed=seed, eta=eta, theta=theta, n_pairs=npairs, ntest=ntest, us_mode=cond.us_mode)
        out[nm] = dict(pre=(o["mb_pre"] * ntest).round().astype(np.uint16), post=(o["mb_post"] * ntest).round().astype(np.uint16),
                       kc_bits=np.packbits(o["kc_pre"] > 0, axis=1), f_mean=o["f_mean"])
    return cond.name, seed, out


def run_all(conds, seeds, procs=4, log=None):
    jobs = [(c, s) for c in conds for s in seeds]
    t0 = time.time()
    res = {}
    with mp.get_context("fork").Pool(procs, initializer=_init) as pool:
        for k, (name, seed, out) in enumerate(pool.imap_unordered(run_job, jobs, chunksize=1)):
            res.setdefault(name, {})[seed] = out
            if log and (k + 1) % max(1, len(jobs) // 10) == 0:
                print(f"  {k+1}/{len(jobs)} trabajos, {time.time()-t0:.0f}s", file=log, flush=True)
    return res


def effects(res_cond, ntest, nodes, scheme_v):
    """Por semilla y por estimulo: dLI para A, B, C (control sin DAN restado)."""
    out = {}
    seeds = sorted(res_cond)
    names = [k for k in res_cond[seeds[0]] if k != "none"]
    for nm in names:
        arr = []
        for s in seeds:
            r, c = res_cond[s][nm], res_cond[s]["none"]
            li, _, _ = an.learning_index(r["pre"] / ntest, r["post"] / ntest, scheme_v)
            li0, _, _ = an.learning_index(c["pre"] / ntest, c["post"] / ntest, scheme_v)
            arr.append(li - li0)
        out[nm] = np.array(arr)        # [n_seeds, 3]
    return out


def boot_ci(x, n=2000, seed=0):
    x = np.asarray(x, float)
    if len(x) == 0:
        return (np.nan, np.nan, np.nan)
    rng = np.random.default_rng(seed)
    m = x.mean()
    bs = rng.choice(x, size=(n, len(x))).mean(1)
    return (float(m), float(np.quantile(bs, .025)), float(np.quantile(bs, .975)))


# ----------------------------------------------------------------------------------------------------------
def pack_raw(res, conds, seeds):
    """res -> arrays [cond, seed, stim, 3, n_mbon] (uint16, espigas sumadas en ntest pruebas de 1 s)."""
    stims = list(res[conds[0].name][seeds[0]].keys())
    C, S, T = len(conds), len(seeds), len(stims)
    nm = res[conds[0].name][seeds[0]][stims[0]]["pre"].shape[1]
    pre = np.zeros((C, S, T, 3, nm), np.uint16)
    post = np.zeros_like(pre)
    fm = np.zeros((C, S, T), np.float32)
    kb = np.zeros((C, S, 3, 508), np.uint8)
    for ci, c in enumerate(conds):
        for si, sd in enumerate(seeds):
            for ti, st in enumerate(stims):
                r = res[c.name][sd][st]
                pre[ci, si, ti], post[ci, si, ti], fm[ci, si, ti] = r["pre"], r["post"], r["f_mean"]
            kb[ci, si] = res[c.name][sd]["none"]["kc_bits"]
    return dict(pre=pre, post=post, f_mean=fm, kc_bits=kb, conds=np.array([c.name for c in conds]),
                seeds=np.array(seeds), stims=np.array(stims))


def save_raw(path, raw, ntest, meta):
    np.savez_compressed(path, ntest=ntest, meta=json.dumps(meta), **raw)


def load_raw(path):
    z = np.load(path, allow_pickle=False)
    d = {k: z[k] for k in z.files}
    d["ntest"] = int(d["ntest"])
    d["meta"] = json.loads(str(d["meta"]))
    return d


def dli(raw, v):
    """dLI[cond, seed, stim(sin 'none'), odor]  (control sin DAN restado)."""
    ntest = raw["ntest"]
    pre = raw["pre"] / ntest
    post = raw["post"] / ntest
    den = (np.abs(v) * pre).sum(-1)
    li = ((post - pre) @ v) / np.maximum(den, 1e-9)       # [C,S,T,3]
    stims = [str(x) for x in raw["stims"]]
    i0 = stims.index("none")
    out = li - li[:, :, i0:i0 + 1, :]
    keep = [i for i, s in enumerate(stims) if s != "none"]
    return out[:, :, keep, :], [stims[i] for i in keep]
