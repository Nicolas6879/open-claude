"""Tablas y figuras a partir de out/raw/*.jsonl.  Uso: python -I src/analyze.py core 'out/raw/E1_*.jsonl' E1"""
import os, sys, numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from stats import load, paired, adjust, mde
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'out')
PAIRS = [('real_b', 'null_b', 'H1'), ('real_w', 'null_w', 'H2'), ('real_b', 'f6', 'H3'),
         ('real_w', 'real_b', 'peso vs binario (real)'), ('null_w', 'null_b', 'peso vs binario (nulo)'),
         ('real_w', 'realtop_shw', 'pesos reales vs barajados (topologia real)'), ('real_b', 'nullbl_b', 'real vs nulo con subtipo'),
         ('real_b', 'null_nb_b', 'real vs nulo sin hemisferio'), ('null_nb_b', 'null_b', 'nulo sin hemisferio vs con'),
         ('null_b', 'f6', 'nulo (grados PN reales) vs F6'), ('kcdeg_b', 'f6', 'grado KC real, PN uniforme vs F6'),
         ('gauss', 'f6', 'gaussiana densa vs F6'), ('sgauss', 'real_b', 'topologia real con pesos gaussianos vs binario'),
         ('f6', 'sim_k', 'F6 vs SimHash(k bits=activas)'), ('f6', 'sim_st', 'F6 vs SimHash(almacenamiento igual)'), ('f6', 'sim_m', 'F6 vs SimHash(M bits)'),
         ('f6', 'noexp', 'F6 vs sin expansion (top-k de 314)'), ('real_b', 'noexp', 'real vs sin expansion'), ('f6', 'raw', 'F6 vs euclidea en PN')]

def core(pattern, name):
    df = load(pattern); os.makedirs(OUT, exist_ok=True)
    mets = [m for m in ('MAP', 'P10', 'LP10', 'acc') if m in df.columns]
    g = df.groupby(['dataset', 'mapper', 'cond', 'level', 'frac', 'norm', 'variant'])[mets].agg(['mean', 'sem', 'count'])
    g.columns = ['_'.join(c) for c in g.columns]; g.to_csv(os.path.join(OUT, f'{name}_means.csv'))
    rows = []
    for a, b, lab in PAIRS:
        for m in mets:
            r = paired(df, a, b, m)
            if len(r): r['label'] = lab; rows.append(r)
    P = pd.concat(rows, ignore_index=True)
    P['p_holm_all'] = adjust(P, 'holm')['p_adj'].values; P['p_bh_all'] = adjust(P, 'fdr_bh')['p_adj'].values
    P.to_csv(os.path.join(OUT, f'{name}_paired.csv'), index=False)
    return df, P

if __name__ == '__main__':
    pd.set_option('display.width', 250); pd.set_option('display.max_columns', 40); pd.set_option('display.max_rows', 400)
    df, P = core(sys.argv[2], sys.argv[3])
    mets = [m for m in ('MAP', 'P10', 'LP10', 'acc') if m in df.columns]
    print(df.groupby('variant')[mets].mean().round(4).sort_values(mets[0]))
    cols = ['label', 'metric', 'n', 'mean_a', 'mean_b', 'diff', 'rel', 'rel_lo', 'rel_hi', 'sd', 'p', 'p_holm_all']
    print(P[cols].round(4).to_string())
