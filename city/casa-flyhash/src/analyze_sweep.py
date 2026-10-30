"""Barridos: MAP/acc medios por variante y nivel (frac | level | factor ...) + dif pareada real-nulo, F6-SimHash, etc. con IC95; figura SVG.
Uso: python -I src/analyze_sweep.py '<glob>' <columna> <nombre> [metricas]"""
import os, sys, numpy as np, pandas as pd
import matplotlib; matplotlib.use('svg')
import matplotlib.pyplot as plt
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from stats import load, paired
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'out')
COL = {'real_b': '#d95f02', 'null_b': '#7570b3', 'f6': '#1b9e77', 'gauss': '#666666', 'sim_k': '#e7298a', 'sim_m': '#66a61e', 'sim_st': '#a6761d', 'noexp': '#999999', 'raw': '#000000',
       'real_w': '#fc8d62', 'real_like_b': '#d95f02', 'real_like_w': '#fc8d62'}

def run(pattern, col, name, metrics=('MAP', 'acc'), extra=()):
    df = load(pattern)
    if 'tag' in df.columns and name.startswith('E6'): pass
    metrics = [m for m in metrics if m in df.columns]
    g = df.groupby([col, 'variant'])[metrics].agg(['mean', 'sem']); g.columns = ['_'.join(c) for c in g.columns]
    g.to_csv(os.path.join(OUT, f'{name}_means.csv'))
    pairs = [('real_b', 'null_b'), ('real_b', 'f6'), ('f6', 'sim_k'), ('f6', 'sim_m'), ('gauss', 'f6'), ('f6', 'noexp'), ('real_like_b', 'f6'), ('real_like_w', 'real_like_b')] + list(extra)
    rows = []
    for a, b in pairs:
        for m in metrics:
            r = paired(df, a, b, m, by=(col,))
            if len(r): rows.append(r)
    P = pd.concat(rows, ignore_index=True) if rows else pd.DataFrame()
    P.to_csv(os.path.join(OUT, f'{name}_paired.csv'), index=False)
    fig, axs = plt.subplots(1, len(metrics), figsize=(4.2 * len(metrics), 3.4), squeeze=False)
    for ax, m in zip(axs[0], metrics):
        for v, gg in df.groupby('variant'):
            s = gg.groupby(col)[m].agg(['mean', 'sem']).sort_index()
            if len(s) < 2 and v not in ('raw', 'noexp'): continue
            ax.errorbar(s.index, s['mean'], s['sem'] * 1.96, label=v, color=COL.get(v), marker='o', ms=3, lw=1, capsize=2)
        if col in ('frac', 'factor', 'mfrac', 'm'): ax.set_xscale('log')
        ax.set_xlabel(col); ax.set_ylabel(m); ax.grid(alpha=.3)
    axs[0][0].legend(fontsize=6); fig.tight_layout(); fig.savefig(os.path.join(OUT, f'{name}.svg')); plt.close(fig)
    return df, g, P

if __name__ == '__main__':
    pd.set_option('display.width', 250); pd.set_option('display.max_columns', 40); pd.set_option('display.max_rows', 500)
    df, g, P = run(sys.argv[1], sys.argv[2], sys.argv[3], tuple(sys.argv[4].split(',')) if len(sys.argv) > 4 else ('MAP', 'acc'))
    print(g.round(4).to_string())
    if len(P): print(P[[ 'a', 'b', 'metric', sys.argv[2], 'n', 'mean_a', 'mean_b', 'diff', 'rel', 'rel_lo', 'rel_hi', 'p']].round(4).to_string())
