"""Figuras SVG pequenas a partir de out/raw. Uso: python -I src/figs.py"""
import os, sys, glob, numpy as np, pandas as pd
import matplotlib; matplotlib.use('svg'); matplotlib.rcParams['svg.fonttype'] = 'none'
import matplotlib.pyplot as plt
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from stats import load, paired
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'out'); RAW = os.path.join(OUT, 'raw')

def forest():
    sets = [('digits proj (E1)', 'E1_*.jsonl', {}), ('MNIST proj (E2)', 'E2_*.jsonl', {}),
            ('MNIST pca', 'E7_mnist_pca.jsonl', {}), ('MNIST select', 'E7_mnist_select.jsonl', {}), ('MNIST glom', 'E7_mnist_glom.jsonl', {}),
            ('MNIST pca_deg', 'E7_mnist_pca_deg.jsonl', {}), ('MNIST pca_rdeg', 'E7_mnist_pca_rdeg.jsonl', {}),
            ('digits select', 'E7_digits_select.jsonl', {}), ('digits glom', 'E7_digits_glom.jsonl', {}),
            ('Fashion proj', 'E2f_*.jsonl', {}), ('news(LSA) proj', 'E2n_*.jsonl', {}),
            ('news pca', 'E7n*_news_pca.jsonl', {}), ('news pca_deg', 'E7n*_news_pca_deg.jsonl', {}), ('news pca_rdeg', 'E7n*_news_pca_rdeg.jsonl', {})]
    fig, axs = plt.subplots(1, 2, figsize=(9.5, 5), sharey=True)
    for ax, (a, b, ttl) in zip(axs, [('real_b', 'null_b', 'real_bin - nulo_bin (MAP, dif. relativa)'), ('real_b', 'f6', 'real_bin - F6 (MAP, dif. relativa)')]):
        y = 0; labels = []
        for lab, pat, _ in sets:
            fs = glob.glob(os.path.join(RAW, pat))
            if not fs: continue
            df = load(os.path.join(RAW, pat)); r = paired(df, a, b, 'MAP')
            if len(r) == 0: continue
            r = r.iloc[0]; ax.errorbar(100 * r.rel, y, xerr=[[100 * (r.rel - r.rel_lo)], [100 * (r.rel_hi - r.rel)]], fmt='o', color='#d95f02', capsize=3, ms=4)
            labels.append(lab + f' (n={int(r.n)})'); y += 1
        ax.axvline(0, color='k', lw=.8); ax.set_yticks(range(len(labels))); ax.set_yticklabels(labels, fontsize=7)
        ax.set_xlabel('% relativo'); ax.set_title(ttl, fontsize=8); ax.grid(alpha=.3)
    axs[0].invert_yaxis()
    fig.tight_layout(); fig.savefig(os.path.join(OUT, 'fig_forest.svg')); plt.close(fig)

def power():
    p = os.path.join(OUT, 'E9_power.csv')
    if not os.path.exists(p): return
    T = pd.read_csv(p); lab = {'real_b': 'real', 'plus10_b': '+10 % KC', 'plus25_b': '+25 %', 'plus50_b': '+50 %', 'plus100_b': '+100 %'}
    fig, ax = plt.subplots(figsize=(4.8, 3.2)); x = np.arange(len(T))
    ax.errorbar(x, 100 * T.dif_rel, yerr=[100 * (T.dif_rel - T.ic_lo), 100 * (T.ic_hi - T.dif_rel)], fmt='o', color='#d95f02', capsize=3)
    for i, r in T.iterrows(): ax.text(i, 100 * r.ic_hi + .08, f"det.{100*r.deteccion_n30:.0f}%", ha='center', fontsize=7)
    ax.set_xticks(x); ax.set_xticklabels([lab[v] for v in T.variante], fontsize=7); ax.axhline(0, color='k', lw=.8)
    ax.set_ylabel('MAP frente al nulo (% relativo)'); ax.set_title('Ventaja inyectada y deteccion (n=30)', fontsize=8); ax.grid(alpha=.3)
    fig.tight_layout(); fig.savefig(os.path.join(OUT, 'fig_power.svg')); plt.close(fig)

if __name__ == '__main__':
    forest(); power()
