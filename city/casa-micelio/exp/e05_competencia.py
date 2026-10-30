"""E05: dos plasmodios compitiendo/cooperando por el mismo medio. Barrido (lam, mu) x condicion inicial x configuraciones."""
import os as _o
for _k in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    _o.environ.setdefault(_k, "1")
import sys, os, json, time
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import numpy as np, pandas as pd
from multiprocessing import Pool
from micelio.mesh import make_mesh
from micelio.compete import compete

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "out")
GAMMA = 1.5
THR = 0.05


def setup(cfg):
    rng = np.random.default_rng(5000 + cfg)
    term = rng.random((12, 2)) * 0.8 + 0.1
    perm = rng.permutation(12)
    A, B = perm[:6], perm[6:]
    pts, edges, L = make_mesh(term, np.sqrt(1.0 / 150), rng)
    return pts, edges, L, A, B


def job(args):
    cfg, lam, mu, ic = args
    pts, edges, L, A, B = setup(cfg)
    n = len(pts)
    DA0, DB0 = {"sym": (1.0, 1.0), "A_first": (1.0, 0.02), "B_first": (0.02, 1.0)}[ic]
    DA, DB, info = compete(n, edges, L, A, B, GAMMA, lam, mu, DA0=DA0, DB0=DB0)
    la = float(L[DA > THR].sum()); lb = float(L[DB > THR].sum())
    u = float(L[(DA > THR) | (DB > THR)].sum())
    both = float(L[(DA > THR) & (DB > THR)].sum())
    return dict(cfg=cfg, lam=lam, mu=mu, ic=ic, lenA=la, lenB=lb, union=u, both=both, converged=info["converged"], t=info["t"])


if __name__ == "__main__":
    quick = len(sys.argv) > 1 and sys.argv[1] == "quick"
    ncfg = 2 if quick else 12
    jobs = [(c, lam, mu, ic) for c in range(ncfg) for lam in (0.0, 0.25, 0.5, 0.75, 1.0) for mu in (0.0, 0.25, 0.5, 0.75, 1.0) for ic in ("sym", "A_first", "B_first")
            if not (lam == 0.0 and mu > 0)]
    t0 = time.time()
    with Pool(2) as p:
        res = p.map(job, jobs, chunksize=1)
    df = pd.DataFrame(res)
    df.to_csv(os.path.join(OUT, "e05_quick.csv" if quick else "e05_competencia.csv"), index=False)
    print("tiempo", time.time() - t0)
    g = df.groupby(["lam", "mu", "ic"]).agg(lenA=("lenA", "mean"), lenB=("lenB", "mean"), union=("union", "mean"), both=("both", "mean"), conv=("converged", "mean")).round(3)
    print(g.to_string())
