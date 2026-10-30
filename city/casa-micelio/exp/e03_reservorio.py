"""E03: reservorio Physarum vs ESN. Busqueda aleatoria de hiperparametros (misma presupuesto), 5 semillas finales."""
import os as _o
for _k in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    _o.environ.setdefault(_k, "1")
import sys, os, json, time
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import numpy as np
from multiprocessing import Pool
from micelio.reservoir import PhysarumReservoir, ESN, ridge_fit, ridge_pred, narma10, mackey_glass, nrmse

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "out")
V2 = os.environ.get("E03_V2", "1") == "1"
METHODS = ("phys", "physhet", "esn")
WASH, NTR, NVA, NTE = 200, 2000, 500, 1000
LAMS = [1e-6, 1e-4, 1e-2, 1, 1e2]


def make_task(task, seed):
    rng = np.random.default_rng(10_000 + seed)
    T = WASH + NTR + NVA + NTE
    if task == "narma10":
        u, y = narma10(T, rng)
        return u, {"y": y}
    if task == "mc":
        u = rng.uniform(-1, 1, T)
        return u, {f"d{k}": np.roll(u, k) for k in range(1, 61)}
    if task == "mg":
        x = mackey_glass(T + 40, rng=rng)
        return x[:T], {"h1": x[1:T + 1], "h25": x[25:T + 25]}


def split(X):
    a = WASH
    return X[a:a + NTR], X[a + NTR:a + NTR + NVA], X[a + NTR + NVA:]


def feats(method, params, seed, u):
    if method in ("phys", "physhet"):
        res = PhysarumReservoir(n=40, gamma=params["gamma"], r_dt=params["r_dt"], gain=params["gain"],
                                bias=params["bias"], seed=seed, spread=params.get("spread", 0.0))
        P, D = res.run(u)
        X = np.c_[P, D] if params.get("useD", True) else P
        return X
    if method == "esn":
        esn = ESN(N=params["N"], rho=params["rho"], in_scale=params["in_scale"], leak=params["leak"], seed=seed)
        return esn.run(u)
    if method == "delay":
        K = 10
        return np.stack([np.roll(u, k) for k in range(K)], axis=1)


def evaluate(method, params, task, seed):
    u, ys = make_task(task, seed)
    X = feats(method, params, seed, u)
    Xtr, Xva, Xte = split(X)
    mu, sd = Xtr.mean(0), Xtr.std(0) + 1e-9
    Xtr, Xva, Xte = (Xtr - mu) / sd, (Xva - mu) / sd, (Xte - mu) / sd
    out = {}
    for name, y in ys.items():
        ytr, yva, yte = split(y)
        best = None
        for lam in LAMS:
            w = ridge_fit(Xtr, ytr, lam)
            e = nrmse(yva, ridge_pred(Xva, w))
            if best is None or e < best[0]:
                best = (e, lam, w)
        e, lam, w = best
        yh = ridge_pred(Xte, w)
        out[name] = (e, nrmse(yte, yh), 1 - float(np.mean((yte - yh) ** 2) / np.var(yte)))
    if task == "mc":
        return dict(val=float(np.mean([v[0] for v in out.values()])), test=float(np.mean([v[1] for v in out.values()])),
                    MC=float(sum(max(0.0, v[2]) for v in out.values())))
    key = list(out)[0]
    r = dict(val=float(np.mean([v[0] for v in out.values()])), test=float(np.mean([v[1] for v in out.values()])))
    for k, v in out.items():
        r["test_" + k] = float(v[1])
    return r


def sample_params(method, rng):
    if method in ("phys", "physhet"):
        if V2:      # v2: incluye el regimen contractivo (gamma<1) que v1 no exploraba
            d = dict(gamma=float(rng.uniform(0.1, 1.2)), r_dt=float(10 ** rng.uniform(-2, -0.2)),
                     gain=float(10 ** rng.uniform(-2, 0)), bias=float(10 ** rng.uniform(-0.5, 0.3)))
        else:
            d = dict(gamma=float(rng.uniform(1.0, 3.0)), r_dt=float(10 ** rng.uniform(-2.3, -0.5)),
                     gain=float(10 ** rng.uniform(-1, 0.5)), bias=float(10 ** rng.uniform(-1, 0.3)))
        if method == "physhet":
            d["spread"] = float(rng.uniform(0.5, 3.0 if V2 else 2.5))
        return d
    if method == "esn":
        return dict(N=140, rho=float(rng.uniform(0.3, 1.3)), in_scale=float(10 ** rng.uniform(-2, 0)),
                    leak=float(rng.uniform(0.1, 1.0)))
    return {}


def search_job(args):
    method, task, k = args
    rng = np.random.default_rng(777 + k)
    params = sample_params(method, rng)
    r = evaluate(method, params, task, seed=900 + k % 3)   # semillas de busqueda distintas de las finales
    return dict(method=method, task=task, k=k, params=params, **r)


def final_job(args):
    method, task, params, seed = args
    r = evaluate(method, params, task, seed)
    return dict(method=method, task=task, seed=seed, params=params, **r)


if __name__ == "__main__":
    quick = len(sys.argv) > 1 and sys.argv[1] == "quick"
    tasks = ["narma10", "mc", "mg"]
    nsearch = 4 if quick else 30
    nseed = 2 if quick else 5
    t0 = time.time()
    with Pool(2) as p:
        sj = [(m, t, k) for m in METHODS for t in tasks for k in range(nsearch)]
        sres = p.map(search_job, sj, chunksize=1)
        print("busqueda", time.time() - t0)
        finals = []
        for m in METHODS:
            for t in tasks:
                cand = [r for r in sres if r["method"] == m and r["task"] == t and np.isfinite(r["val"])]
                best = min(cand, key=lambda r: r["val"])
                for s in range(nseed):
                    finals.append((m, t, best["params"], s))
        for t in tasks:
            for s in range(nseed):
                finals.append(("delay", t, {}, s))
        fres = p.map(final_job, finals, chunksize=1)
    json.dump(dict(search=sres, final=fres), open(os.path.join(OUT, "e03_quick.json" if quick else ("e03_reservorio.json" if V2 else "e03_reservorio_v1.json")), "w"))
    import pandas as pd
    df = pd.DataFrame(fres)
    cols = [c for c in df.columns if c.startswith("test") or c == "MC"]
    print(df.groupby(["task", "method"])[cols].agg(["mean", "std"]).round(3).to_string())
    print("tiempo", time.time() - t0)
