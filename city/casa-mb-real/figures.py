"""Figuras SVG pequenas a partir de out/*.json y out/raw/*.npz.  Uso: python figures.py"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "src"))
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

import analysis as an
import experiments as ex
sys.path.insert(0, HERE)
import mbdata as md

OUT = os.path.join(HERE, "out")
BLUE, ORANGE, GRAY, INK, INK2, BG = "#2a78d6", "#eb6834", "#9a9992", "#0b0b0b", "#52514e", "#fcfcfb"
plt.rcParams.update({"svg.fonttype": "none", "font.family": "sans-serif", "font.size": 9, "axes.edgecolor": INK2, "axes.labelcolor": INK,
                     "xtick.color": INK2, "ytick.color": INK2, "text.color": INK, "figure.facecolor": BG, "axes.facecolor": BG,
                     "savefig.facecolor": BG, "axes.spines.top": False, "axes.spines.right": False})


def fig_anatomy():
    a = json.load(open(os.path.join(OUT, "anatomy.json")))
    lines = open(os.path.join(OUT, "dan_mbon_types.csv")).read().strip().split("\n")
    mb = lines[0].split(",")[1:]
    dan = [l.split(",")[0] for l in lines[1:]]
    W = np.array([[float(x) for x in l.split(",")[1:]] for l in lines[1:]])
    keep = [i for i, d in enumerate(dan) if W[i].sum() > 0]
    dan = [dan[i] for i in keep]; W = W[keep]
    # orden de MBON: valencia (evitacion primero) y luego por DAN principal
    val = np.array([a["MBON_tipos"][m]["valence"] for m in mb])
    top = W.argmax(0)
    order = sorted(range(len(mb)), key=lambda j: (val[j], top[j]))
    fig, ax = plt.subplots(figsize=(10.5, 4.8))
    M = np.log10(1 + W[:, order])
    im = ax.imshow(M, aspect="auto", cmap="Blues", vmin=0, vmax=3.7)
    ax.set_xticks(range(len(order))); ax.set_xticklabels([mb[j].replace("MBON", "") for j in order], rotation=90, fontsize=7)
    ax.set_yticks(range(len(dan))); ax.set_yticklabels(dan, fontsize=7)
    for k, j in enumerate(order):
        ax.add_patch(plt.Rectangle((k - .5, -1.6), 1, 1, color=(ORANGE if val[j] < 0 else BLUE), clip_on=False))
    ax.text(-0.9, -1.1, "valencia MBON (NT)", ha="right", va="center", fontsize=7, color=INK2)
    ax.set_xlabel("tipo de MBON (naranja: glutamato, evitacion; azul: GABA/ACh, atraccion)")
    ax.set_title("DAN -> MBON medido (sinapsis, log10(1+n)); los DAN contactan los MBON de su compartimento", fontsize=9, loc="left", pad=22)
    cb = fig.colorbar(im, ax=ax, fraction=0.03, pad=0.01); cb.set_label("log10(1+sinapsis)", fontsize=7)
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "fig1_anatomia.svg"))
    plt.close(fig)


def per_type_effect(raw, v, ci_idx=0):
    d, stims = ex.dli(raw, v)
    return d, stims


def fig_types():
    nodes, _ = md.load()
    v = an.valence_vector(nodes)
    raw = ex.load_raw(os.path.join(OUT, "raw", "main.npz"))
    d, stims = ex.dli(raw, v)
    ty = [i for i, s in enumerate(stims) if s.startswith("type:")]
    names = [stims[i][5:] for i in ty]
    A = d[0][:, ty, 0]
    m = A.mean(0); se = 1.96 * A.std(0, ddof=1) / np.sqrt(A.shape[0])
    fig, ax = plt.subplots(figsize=(8.2, 3.6))
    x = np.arange(len(names))
    exp = np.array([+1 if n.startswith("PAM") else (-1 if n.startswith("PPL1") else 0) for n in names])
    col = [GRAY if e == 0 else (BLUE if np.sign(mm) == e else ORANGE) for e, mm in zip(exp, m)]
    ax.axhline(0, color=INK2, lw=0.8)
    ax.bar(x, m, color=col, width=0.6)
    ax.errorbar(x, m, yerr=se, fmt="none", ecolor=INK2, lw=0.8)
    import summarize as sm
    rc = sm.load_controls()
    if rc is not None and "comp_shuf_type" in [str(c) for c in rc["conds"]]:
        dc, sc = ex.dli(rc, v)
        cn = [str(c) for c in rc["conds"]]
        ci_ = cn.index("comp_shuf_type")
        have = [k for k, n in enumerate(names) if "type:" + n in sc]
        idx = [sc.index("type:" + names[k]) for k in have]
        ax.plot(x[have], dc[ci_][:, idx, 0].mean(0), "s", mfc="none", mec=INK, ms=4.5, lw=0, label="compartimentos barajados (control)")
        ax.legend(frameon=False, fontsize=7, loc="upper center", bbox_to_anchor=(0.5, -0.32))
    ax.set_xticks(x); ax.set_xticklabels(names, rotation=90, fontsize=7)
    ax.set_ylabel("dLI(A) = cambio de valencia\n(+ acercamiento, - evitacion)")
    ax.set_title("Un tipo de DAN a la vez, cableado real. Azul: signo esperado (PAM +, PPL1 -); naranja: signo contrario; gris: sin clase", fontsize=8, loc="left")
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "fig2_tipos.svg"))
    plt.close(fig)


def fig_controls():
    R = json.load(open(os.path.join(OUT, "results.json")))
    if "controls" not in R:
        return
    c = R["controls"]["resultados"]
    names = list(c.keys())
    names = [n for n in names if "tipos" in c[n]]
    sep = [c[n]["tipos"]["separacion_PAM_menos_PPL1"] for n in names]
    acc = [c[n]["tipos"]["acierta_signo"] for n in names]
    fig, ax = plt.subplots(figsize=(7.6, 3.4))
    y = np.arange(len(names))[::-1]
    for yy, s, n, a in zip(y, sep, names, acc):
        col = BLUE if n == "real" else (ORANGE if n.startswith("comp_") else GRAY)
        ax.errorbar(s[0], yy, xerr=[[s[0] - s[1]], [s[2] - s[0]]], fmt="o", color=col, ms=5, lw=1.2)
        ax.text(max(sep[0][2], max(x[2] for x in sep)) * 1.12, yy, f"{a}/23", va="center", fontsize=7, color=INK2)
    ax.axvline(0, color=INK2, lw=0.8)
    ax.axvline(sep[names.index("real")][0], color=BLUE, lw=0.6, ls=":")
    ax.set_yticks(y); ax.set_yticklabels(names, fontsize=8)
    ax.set_xlabel("separacion PAM - PPL1 en dLI(A), por tipo (IC95 entre semillas); a la derecha: tipos con signo correcto")
    ax.set_title("Controles de cableado: azul real, gris cableado aleatorio con grados, naranja compartimentos", fontsize=8, loc="left")
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "fig3_controles.svg"))
    plt.close(fig)


def fig_sweeps():
    p = os.path.join(OUT, "raw", "sweeps.npz")
    if not os.path.exists(p):
        return
    nodes, _ = md.load()
    v = an.valence_vector(nodes)
    raw = ex.load_raw(p)
    d, st = ex.dli(raw, v)
    cn = [str(c) for c in raw["conds"]]
    etas = sorted({float(c.split("_")[0][3:]) for c in cn if c.startswith("eta")})
    ths = sorted({float(c.split("_th")[1]) for c in cn if c.startswith("eta")})
    fig, axs = plt.subplots(1, 2, figsize=(7.6, 3.0))
    for ax, s, tt in zip(axs, ("PAM", "PPL1"), ("PAM-todos (esperado +)", "PPL1-todos (esperado -)")):
        M = np.full((len(etas), len(ths)), np.nan)
        for i, e in enumerate(etas):
            for j, t in enumerate(ths):
                k = cn.index(f"eta{e}_th{t}")
                M[i, j] = d[k][:, st.index(s), 0].mean()
        lim = np.nanmax(np.abs(M))
        im = ax.imshow(M, cmap="RdBu", vmin=-lim, vmax=lim, aspect="auto", origin="lower")
        for i in range(M.shape[0]):
            for j in range(M.shape[1]):
                ax.text(j, i, f"{M[i,j]:+.2f}", ha="center", va="center", fontsize=6.5, color=("white" if abs(M[i, j]) > 0.55 * lim else INK))
        ax.set_xticks(range(len(ths))); ax.set_xticklabels(ths); ax.set_yticks(range(len(etas))); ax.set_yticklabels(etas)
        ax.set_xlabel("umbral de KC activa (theta)"); ax.set_title(tt, fontsize=8, loc="left")
    axs[0].set_ylabel("tasa de aprendizaje eta (1/s)")
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "fig4_barrido.svg"))
    plt.close(fig)


def fig_lesions():
    R = json.load(open(os.path.join(OUT, "results.json")))
    if "lesions_mbon" not in R:
        return
    L = R["lesions_mbon"]["silenciar_tipo_MBON"]
    names = sorted(L, key=lambda t: L[t]["PPL1"]["cambio_vs_intacto"][0])
    fig, axs = plt.subplots(1, 2, figsize=(8.2, 4.0), sharey=True)
    for ax, s, col in zip(axs, ("PPL1", "PAM"), (ORANGE, BLUE)):
        y = np.arange(len(names))
        m = [L[t][s]["cambio_vs_intacto"][0] for t in names]
        lo = [L[t][s]["cambio_vs_intacto"][1] for t in names]; hi = [L[t][s]["cambio_vs_intacto"][2] for t in names]
        ax.barh(y, m, color=col, height=0.6)
        ax.errorbar(m, y, xerr=[np.array(m) - np.array(lo), np.array(hi) - np.array(m)], fmt="none", ecolor=INK2, lw=0.7)
        ax.axvline(0, color=INK2, lw=0.8); ax.set_title(f"silenciar tipo de MBON: cambio en dLI(A), {s}-todos", fontsize=8, loc="left")
    axs[0].set_yticks(np.arange(len(names))); axs[0].set_yticklabels(names, fontsize=6.5)
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "fig5_lesiones_mbon.svg"))
    plt.close(fig)


if __name__ == "__main__":
    fig_anatomy(); fig_types(); fig_controls(); fig_sweeps(); fig_lesions()
    print("figuras listas")
