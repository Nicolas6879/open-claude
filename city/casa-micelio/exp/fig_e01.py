import os as _o
_o.environ.setdefault("OMP_NUM_THREADS", "1")
import sys, os, json
import numpy as np, pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "out")
df = pd.DataFrame(json.load(open(os.path.join(OUT, "e01_validacion.json"))))
# T se reconstruye: los trabajos largos son pow gamma=1 dt=1.0 con tconv posible > 200
jobs_T = []
# marcar T=3000: segunda aparicion de (kind,seed,pow,1.0,dt=1.0)
seen = {}
T = []
for r in df.itertuples():
    k = (r.kind, r.seed, r.f, r.gamma, r.dt)
    seen[k] = seen.get(k, 0) + 1
    T.append(3000.0 if (r.f == "pow" and r.gamma == 1.0 and r.dt == 1.0 and seen[k] == 2) else 200.0)
df["Tmax"] = T
d = df[(df.Tmax == 200) & ((df.dt == 0.25) | ((df.f == "pow") & (df.gamma == 1.0)))].drop_duplicates(["kind", "seed", "f", "gamma", "dt"])
fig, ax = plt.subplots(1, 3, figsize=(13, 3.6))
labs = [("pow", 0.7), ("pow", 1.0), ("pow", 1.5), ("sat", 1.0), ("sat", 2.0), ("sat", 3.0)]
for ki, (kind, c) in enumerate((("delaunay", "#2a6f97"), ("maze", "#bc6c25"))):
    v = [d[(d.kind == kind) & (d.f == f) & (d.gamma == g) & (d.dt == 0.25)].ok.mean() for f, g in labs]
    ax[0].bar(np.arange(len(labs)) + 0.4 * ki - 0.2, v, 0.4, label=kind, color=c)
ax[0].set_xticks(range(len(labs)))
ax[0].set_xticklabels([f"{f}\n$\\gamma$={g}" for f, g in labs], fontsize=8)
ax[0].set_ylabel("camino = Dijkstra (T=200)")
ax[0].set_title("A. exito vs forma de f y gamma (dt=0.25)")
ax[0].legend(fontsize=8)
# B dt
dts = [0.05, 0.25, 1.0, 2.0]
for ki, (kind, c) in enumerate((("delaunay", "#2a6f97"), ("maze", "#bc6c25"))):
    ok = [df[(df.Tmax == 200) & (df.kind == kind) & (df.f == "pow") & (df.gamma == 1.0) & (df.dt == x)].win_ok.mean() for x in dts]
    ax[1].plot(range(4), ok, "o-", color=c, label=f"{kind}: ganador correcto")
ax[1].set_xticks(range(4)); ax[1].set_xticklabels(dts)
ax[1].set_xlabel("paso dt (gamma=1)"); ax[1].set_ylim(0, 1.05)
ax[1].set_title("B. paso: dt=2 rompe la garantia")
ax[1].legend(fontsize=8)
# C tconv vs gap
g = df[(df.Tmax == 3000) & (df.kind == "delaunay")].dropna(subset=["tconv", "gap"])
ax[2].loglog(g.gap, g.tconv, "o", color="#2a6f97", ms=4)
ax[2].set_xlabel("brecha relativa 2o/1er camino"); ax[2].set_ylabel("tiempo de convergencia")
ax[2].set_title("C. gamma=1: T_conv vs brecha")
plt.tight_layout()
plt.savefig(os.path.join(OUT, "fig_e01_validacion.png"), dpi=110)
cc = g[g.gap > 0]
print("corr loglog tconv~gap", np.corrcoef(np.log(cc.gap), np.log(cc.tconv))[0, 1], "pendiente", np.polyfit(np.log(cc.gap), np.log(cc.tconv), 1)[0], len(cc))
