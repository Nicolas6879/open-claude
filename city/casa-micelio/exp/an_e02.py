"""Analisis de E02: frontera de controles, comparacion a coste igualado, figuras."""
import os as _o
_o.environ.setdefault("OMP_NUM_THREADS", "1")
import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import numpy as np, pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from micelio.data import load_cities

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "out")
ph = pd.read_csv(os.path.join(OUT, "e02_physarum.csv"))
ct = pd.read_csv(os.path.join(OUT, "e02_controles.csv"))


def envelope(x, y, better="low"):
    o = np.argsort(x)
    xs, ys = np.asarray(x)[o], np.asarray(y)[o]
    kx, ky = [], []
    best = np.inf if better == "low" else -np.inf
    for a, b in zip(xs, ys):
        if (better == "low" and b < best - 1e-9) or (better == "high" and b > best + 1e-9):
            kx.append(a); ky.append(b); best = b
    return np.array(kx), np.array(ky)


def frontier_at(env, tl):
    kx, ky = env
    if tl < kx[0] or tl > kx[-1]:
        return np.nan
    return float(np.interp(tl, kx, ky))


rows = []
summ = {}
for region in ("kanto", "espana"):
    c = ct[(ct.region == region) & (ct.kind == "control")]
    envMD = envelope(c.TL, c.MD, "low")
    envCQ = envelope(c.TL, c.conn_q10, "high")
    p = ph[ph.region == region].copy()
    p["MD_front"] = [frontier_at(envMD, t) for t in p.TL]
    p["CQ_front"] = [frontier_at(envCQ, t) for t in p.TL]
    p["dMD"] = p.MD - p.MD_front              # <0: Physarum mejor (mas eficiente) a igual coste
    p["dCQ"] = p.conn_q10 - p.CQ_front        # >0: Physarum mejor (mas robusto) a igual coste
    p.to_csv(os.path.join(OUT, f"e02_{region}_vs_frontera.csv"), index=False)
    g = p.dropna(subset=["dMD"]).groupby(["kind", "gamma", "kappa"]).agg(
        n=("dMD", "size"), TL=("TL", "mean"), MD=("MD", "mean"), dMD=("dMD", "mean"), dMD_sd=("dMD", "std"),
        dCQ=("dCQ", "mean"), CQ=("conn_q10", "mean"), FT1=("FT1", "mean"), junc=("njunc", "mean"),
        cyc=("cycles", "mean"), rail=("near_rail", "mean"), conv=("converged", "mean")).round(3)
    g.to_csv(os.path.join(OUT, f"e02_{region}_resumen.csv"))
    summ[region] = g
    print("=====", region)
    print(g.to_string())
    frac = (p.dropna(subset=["dMD"]).dMD < 0).mean()
    print("fraccion de configuraciones Physarum con MD < frontera de controles a igual coste:", round(frac, 3))
    print("ref MST TL", float(c[c.name == "MST"].TL.iloc[0]), "rail", ct[(ct.region == region) & (ct.kind == "rail")][["TL", "MD", "FT1", "conn_q10", "cycles", "njunc"]].round(3).to_dict("records"))

# ---- figura: planos coste-eficiencia y coste-robustez
fig, axs = plt.subplots(2, 2, figsize=(12, 8))
cols = {"physarumA": "#d62728", "physarumB": "#1f77b4", "physarumG": "#2ca02c"}
for ri, region in enumerate(("kanto", "espana")):
    c = ct[(ct.region == region) & (ct.kind == "control")]
    r = ct[(ct.region == region) & (ct.kind == "rail")].iloc[0]
    p = ph[ph.region == region]
    for ai, (yk, yl) in enumerate((("MD", "detour medio (camino/recta)"), ("conn_q10", "pares conectados (fallo 10% enlaces)"))):
        ax = axs[ri, ai]
        for fam, mk in (("spanner", "s"), ("MST+", "^")):
            cc = c[c.name.str.startswith(fam)].sort_values("TL")
            ax.plot(cc.TL, cc[yk], mk + "-", color="#888", ms=5, lw=1, label="control " + ("spanner voraz" if fam == "spanner" else "MST+k voraz"))
        for nm, m2 in (("MST", "*"), ("Delaunay", "D"), ("Gabriel", "P"), ("RNG", "X")):
            cc = c[c.name == nm]
            ax.plot(cc.TL, cc[yk], m2, color="k", ms=8, label=nm)
        ax.plot([r.TL], [r[yk]], "o", color="#e6a100", ms=11, mec="k", label="ferrocarril NE")
        for (kind, gamma, kap), gg in p.groupby(["kind", "gamma", "kappa"]):
            if kap != 1.0:
                continue
            ax.plot(gg.TL.mean(), gg[yk].mean(), "o", color=cols[kind], ms=3 + 2.5 * np.log2(gamma + 0.5), alpha=.8)
        ax.set_xscale("log")
        ax.set_xlabel("longitud total TL (km)"); ax.set_ylabel(yl)
        ax.set_title(("Kanto" if region == "kanto" else "Espana") + ": Physarum A(rojo) B(azul) G(verde)", fontsize=9)
        if ri == 0 and ai == 0:
            ax.legend(fontsize=7)
plt.tight_layout()
plt.savefig(os.path.join(OUT, "fig_e02_frontera.png"), dpi=105)

# ---- figura: mapas
def draw_net(ax, pts, edges, w=None, color="#c0392b", lw=1.5, alpha=1):
    for k, (a, b) in enumerate(edges):
        ax.plot([pts[a, 0], pts[b, 0]], [pts[a, 1], pts[b, 1]], color=color, lw=lw if w is None else lw * (0.3 + 3 * w[k]), alpha=alpha, solid_capstyle="round")

fig, axs = plt.subplots(2, 4, figsize=(17, 8.5))
for ri, region in enumerate(("kanto", "espana")):
    names, lat, lon, pop, xy, center = load_cities(region)
    z = np.load(os.path.join(OUT, f"rail_{region}.npz"))
    rp, re_ = z["pts"], z["edges"]
    panels = [("ferrocarril NE (backbone)", None), ("Physarum B gamma=2", ("B", 2.0)), ("Physarum G (gravedad) gamma=2", ("G", 2.0)), ("Physarum B gamma=1.35", ("B", 1.35))]
    for ci, (title, spec) in enumerate(panels):
        ax = axs[ri, ci]
        if spec is None:
            draw_net(ax, rp, re_, color="#2b5f9e", lw=1.0)
        else:
            f = os.path.join(OUT, f"net_{region}_{spec[0]}_g{spec[1]}.npz")
            if os.path.exists(f):
                zz = np.load(f)
                pts, e, D, ts = zz["pts"], zz["edges"], zz["D"], float(zz["tstar"])
                sel = D >= ts * 0.3
                draw_net(ax, pts, e[sel], w=np.sqrt(np.minimum(D[sel], 1)), color="#b5651d", lw=1.2)
        ax.scatter(xy[:, 0], xy[:, 1], s=8 + 70 * (pop / pop.max()) ** .5, c="k", zorder=5)
        ax.set_aspect("equal"); ax.set_xticks([]); ax.set_yticks([])
        ax.set_title(f"{region}: {title}", fontsize=9)
plt.tight_layout()
plt.savefig(os.path.join(OUT, "fig_e02_mapas.png"), dpi=90)
