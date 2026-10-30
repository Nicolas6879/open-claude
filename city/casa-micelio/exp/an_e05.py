import os as _o
_o.environ.setdefault("OMP_NUM_THREADS", "1")
import os, json
import numpy as np, pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "out")
df = pd.read_csv(os.path.join(OUT, "e05_competencia.csv"))
# referencia: sin interaccion (lam=0) de la misma configuracion (CI no importa salvo B_first que a veces no converge)
ref = df[(df.lam == 0) & (df.ic == "sym")].set_index("cfg")
df["U0"] = df.cfg.map(ref.union)
df["lenA0"] = df.cfg.map(ref.lenA)
df["lenB0"] = df.cfg.map(ref.lenB)
df["ratio_union"] = df.union / df.U0
df["mono"] = (np.minimum(df.lenA, df.lenB) < 0.1 * np.maximum(df.lenA, df.lenB)).astype(float)
df["asym"] = (df.lenA - df.lenB) / (df.lenA + df.lenB)
g = df.groupby(["ic", "lam", "mu"]).agg(n=("mono", "size"), mono=("mono", "mean"), ratio_union=("ratio_union", "mean"),
                                         ru_sd=("ratio_union", "std"), asym_abs=("asym", lambda x: np.abs(x).mean()),
                                         lenA_rel=("lenA", "mean"), lenB_rel=("lenB", "mean"), conv=("converged", "mean")).round(3)
g.to_csv(os.path.join(OUT, "e05_resumen.csv"))
pd.set_option("display.width", 200)
print(g.to_string())
# dependencia de la historia: en cada (cfg, lam, mu) con lam>0, la CI cambia el estado (mono distinto) ?
h = df[df.lam > 0].pivot_table(index=["cfg", "lam", "mu"], columns="ic", values="mono")
dep = ((h.max(axis=1) - h.min(axis=1)) > 0.5)
print("dependencia de la CI por (lam,mu):")
print(dep.groupby(["lam", "mu"]).mean().unstack().round(2).to_string())
print("dependencia global (lam=1, mu=1):", float(dep.xs((1.0, 1.0), level=("lam", "mu")).mean()))
# figura
fig, axs = plt.subplots(1, 4, figsize=(16, 3.6))
lams = sorted(df.lam.unique()); mus = sorted(df.mu.unique())
for ax, (ic, what, title) in zip(axs, (("sym", "mono", "monopolio, inicio simetrico"), ("A_first", "mono", "monopolio, A primero"),
                                       ("sym", "ratio_union", "infraestructura / sin interaccion (simetrico)"), ("A_first", "ratio_union", "infraestructura / sin interaccion (A primero)"))):
    M = np.full((len(lams), len(mus)), np.nan)
    for i, l in enumerate(lams):
        for j, m in enumerate(mus):
            s = g.loc[(ic, l, m)] if (ic, l, m) in g.index else None
            if s is not None:
                M[i, j] = s[what]
    im = ax.imshow(M, origin="lower", cmap="viridis", vmin=0 if what == "mono" else 0.6, vmax=1 if what == "mono" else 1.05, aspect="auto")
    ax.set_xticks(range(len(mus))); ax.set_xticklabels(mus); ax.set_yticks(range(len(lams))); ax.set_yticklabels(lams)
    ax.set_xlabel("mu (reciprocidad)"); ax.set_ylabel("lam (permeabilidad)"); ax.set_title(title, fontsize=9)
    for i in range(len(lams)):
        for j in range(len(mus)):
            if not np.isnan(M[i, j]):
                ax.text(j, i, f"{M[i,j]:.2f}", ha="center", va="center", fontsize=7, color="w" if M[i, j] < (0.5 if what == "mono" else 0.85) else "k")
    plt.colorbar(im, ax=ax, fraction=0.046)
plt.tight_layout()
plt.savefig(os.path.join(OUT, "fig_e05_competencia.png"), dpi=105)
