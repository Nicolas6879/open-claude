import os as _o
_o.environ.setdefault("OMP_NUM_THREADS", "1")
import os
import numpy as np, pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "out")
c = pd.read_csv(os.path.join(OUT, "e02c_controles_enrutados.csv"))
p = pd.read_csv(os.path.join(OUT, "e02_physarum.csv"))
fig, axs = plt.subplots(2, 2, figsize=(12, 8))
for ri, region in enumerate(("kanto", "espana")):
    cc = c[c.region == region].groupby("name")[["TL", "MD", "conn_q10"]].mean()
    for ai, (yk, yl) in enumerate((("MD", "detour medio (camino/recta)"), ("conn_q10", "pares conectados (fallo 10% enlaces)"))):
        ax = axs[ri, ai]
        for fam, mk, lab in (("spanner", "s", "control enrutado: spanner voraz"), ("MST+", "^", "control enrutado: MST+k voraz")):
            d = cc[[i.startswith(fam) for i in cc.index]].sort_values("TL")
            ax.plot(d.TL, d[yk], mk + "-", color="#888", ms=3.5, lw=1, label=lab)
        for nm, m2 in (("MST", "*"), ("Delaunay", "D"), ("Gabriel", "P"), ("RNG", "X")):
            ax.plot(cc.loc[nm, "TL"], cc.loc[nm, yk], m2, color="k", ms=8, label=nm + " enrutado")
        for kind, col in (("physarumB", "#1f77b4"), ("physarumG", "#2ca02c")):
            g = p[(p.region == region) & (p.kind == kind) & (p.kappa == 1.0)].groupby("gamma")[["TL", yk]].mean()
            ax.plot(g.TL, g[yk], "o-", color=col, ms=6, lw=1.2, label="Physarum " + ("B" if kind.endswith("B") else "G (gravedad)") + " (gamma 1.1 a 3)")
            for gm, r in g.iterrows():
                if gm in (1.1, 1.5, 3.0):
                    ax.annotate(f"{gm}", (r.TL, r[yk]), fontsize=7, xytext=(3, 3), textcoords="offset points")
        ax.set_xscale("log"); ax.set_xlabel("longitud total TL (km)"); ax.set_ylabel(yl)
        ax.set_title(("Kanto" if region == "kanto" else "Espana") + ": controles enrutados por la MISMA malla", fontsize=9)
        if ri == 0 and ai == 0:
            ax.legend(fontsize=7)
plt.tight_layout()
plt.savefig(os.path.join(OUT, "fig_e02c_malla_justa.png"), dpi=105)
