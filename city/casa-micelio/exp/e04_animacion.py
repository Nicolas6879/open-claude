"""E04: genera out/crecimiento.html (pagina autonoma, sin dependencias) con la animacion del crecimiento de la red."""
import os as _o
for _k in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    _o.environ.setdefault(_k, "1")
import sys, os, json, base64
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import numpy as np
from micelio.data import load_cities
from micelio.mesh import make_mesh
from micelio.physarum import run_mean_field

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "out")
SCEN = [("g12", "gamma=1.2 (red con bucles)", 1.2, False), ("g20", "gamma=2 (red casi arbol)", 2.0, False),
        ("g20w", "gamma=2 + flujos gravitatorios (poblacion)", 2.0, True)]


def build(region):
    names, lat, lon, pop, xy, center = load_cities(region)
    nc = len(xy)
    rng = np.random.default_rng(0)
    ext = xy.max(0) - xy.min(0)
    sp = np.sqrt(np.prod(ext) / 330.0)
    pts, edges, L = make_mesh(xy, sp, rng)
    key = {(int(a), int(b)): i for i, (a, b) in enumerate(edges)}
    ii, jj = np.triu_indices(nc, 1)
    res = {}
    for sid, label, gamma, grav in SCEN:
        w = (pop[ii] * pop[jj] / np.linalg.norm(xy[ii] - xy[jj], axis=1)) if grav else None
        e, Ls, D, info = run_mean_field(len(pts), edges, L, np.arange(nc), gamma, kind="sat", dt=0.2, T=250.0, tol=1e-6,
                                        rng=np.random.default_rng(0), snapshots=3, weights=w, compact_every=10)
        frames = []
        for t, ee, DD in info["snaps"]:
            arr = np.zeros(len(edges), np.uint8)
            for (a, b), d in zip(ee, DD):
                arr[key[(min(int(a), int(b)), max(int(a), int(b)))]] = int(min(255, round(255 * np.sqrt(min(d, 1.0)))))
            frames.append((float(t), base64.b64encode(arr.tobytes()).decode()))
        res[sid] = dict(label=label, frames=frames)
        print(region, sid, len(frames), "frames", flush=True)
    z = np.load(os.path.join(OUT, f"rail_{region}.npz"))
    rp, re_ = z["pts"], z["edges"]
    # ferrocarril: segmentos redondeados a 0.5 km, sin duplicados
    seg = set()
    for a, b in re_:
        p, q = np.round(rp[a] * 2).astype(int), np.round(rp[b] * 2).astype(int)
        if (p != q).any():
            seg.add((tuple(p), tuple(q)) if tuple(p) < tuple(q) else (tuple(q), tuple(p)))
    rail = [int(v) for s in seg for pt in s for v in pt]
    return dict(names=names, pop=[int(x) for x in pop], xy=np.round(xy, 1).tolist(), pts=np.round(pts, 1).tolist(),
                edges=edges.tolist(), nc=nc, scen=res, rail=rail)


if __name__ == "__main__":
    data = {r: build(r) for r in ("kanto", "espana")}
    tpl = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "crecimiento.template.html")).read()
    html = tpl.replace("/*DATA*/null", json.dumps(data, separators=(",", ":")))
    open(os.path.join(OUT, "crecimiento.html"), "w").write(html)
    print("html", len(html) / 1e6, "MB")
