"""Regenera todas las tablas (out/*.csv, out/PRIMARY.md) y figuras (out/*.svg) desde out/raw/*.jsonl.  Uso: python -I src/analyze_all.py"""
import os, sys, json, glob, subprocess, numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from stats import load, paired, adjust
import analyze, analyze_sweep, analyze_primary, figs
OUT = analyze.OUT; RAW = os.path.join(OUT, 'raw')
R = lambda p: os.path.join(RAW, p)

def sweep_block(pattern, by, name, extra_pairs):
    df = load(R(pattern)); rows = []
    for a, b in extra_pairs:
        for m in [c for c in ('MAP', 'acc') if c in df.columns]:
            r = paired(df, a, b, m, by=by)
            if len(r): r['pair'] = f'{a} - {b}'; rows.append(r)
    P = pd.concat(rows, ignore_index=True); P.to_csv(os.path.join(OUT, f'{name}_paired.csv'), index=False); return df, P

# E1, E2, E2f, E2n (nucleo) + E3/E4 (barridos)
for pat, name in (('E1_*.jsonl', 'E1'), ('E2_*.jsonl', 'E2'), ('E2f_*.jsonl', 'E2f'), ('E2n_*.jsonl', 'E2n')): analyze.core(R(pat), name)
analyze_sweep.run(R('E3_*.jsonl'), 'frac', 'E3'); analyze_sweep.run(R('E4_scale.jsonl'), 'factor', 'E4')
# E5 robustez
df = load(R('E5_digits_noise.jsonl')); df['condicion'] = df.cond + ':' + df.level.astype(str)
rows = []
for a, b in (('real_b', 'null_b'), ('real_b', 'f6'), ('f6', 'sim_k'), ('f6', 'sim_m')):
    for m in ('MAP', 'acc'):
        r = paired(df, a, b, m, by=('condicion',)); r['pair'] = f'{a} - {b}'; rows.append(r)
pd.concat(rows).to_csv(os.path.join(OUT, 'E5_paired.csv'), index=False)
# E6 subtipos
df = load(R('E6_*.jsonl')); rows = []
for st in df.tag.unique():
    g = df[df.tag == st]
    for a, b in (('real_b', 'null_b'), ('real_b', 'f6')):
        r = paired(g, a, b, 'MAP', by=('tag',)); r['pair'] = f'{a} - {b}'; rows.append(r)
pd.concat(rows).to_csv(os.path.join(OUT, 'E6_paired.csv'), index=False)
# E7 mapeos
P7 = []
for pat in ('E7_mnist_*.jsonl', 'E7_digits_*.jsonl', 'E7n_news_*.jsonl'):
    df = load(R(pat))
    for a, b in (('real_b', 'null_b'), ('null_b', 'f6'), ('real_b', 'f6'), ('kcdeg_b', 'f6'), ('real_w', 'real_b'), ('null_nb_b', 'null_b'), ('gauss', 'f6')):
        for m in [c for c in ('MAP', 'acc') if c in df.columns]:
            r = paired(df, a, b, m, by=('dataset', 'mapper')); r['pair'] = f'{a} - {b}'; P7.append(r)
pd.concat(P7).to_csv(os.path.join(OUT, 'E7_paired.csv'), index=False)
# E7b (PCA y glom/proj; norm 0/1), E8, E12, E13, E14
P = []
for pat, by in (('E7b_mnist_*_norm*.jsonl', ('dataset', 'mapper', 'norm')),):
    df = load(R(pat))
    for a, b in (('real_b', 'null_b'), ('real_b', 'nulljdd_b'), ('real_b', 'nullbl_b'), ('nulljdd_b', 'null_b'), ('real_w', 'real_b'), ('real_b', 'f6'), ('null_b', 'f6')):
        r = paired(df, a, b, 'MAP', by=by)
        if len(r): r['pair'] = f'{a} - {b}'; P.append(r)
pd.concat(P).to_csv(os.path.join(OUT, 'E7b_paired.csv'), index=False)
if os.path.exists(R('E12_digits_proj.jsonl')):
    P = []
    for pat in ('E12_digits_proj.jsonl', 'E12_mnist_*.jsonl'):
        for f in sorted(glob.glob(R(pat))):
            df = load(f)
            for a, b in (('real_b_pn', 'f6'), ('null_b_pn', 'f6'), ('nulljdd_b_pn', 'f6'), ('real_b_pn', 'null_b_pn'), ('real_w_pn', 'real_b_pn'), ('real_w_pn', 'null_w_pn'), ('real_b_pn', 'real_b'), ('null_b_pn', 'null_b'), ('real_b', 'f6'), ('null_b', 'f6'), ('real_b', 'null_b')):
                for m in [c for c in ('MAP', 'acc') if c in df.columns]:
                    r = paired(df, a, b, m, by=('dataset', 'mapper')); r['pair'] = f'{a} - {b}'; P.append(r)
    pd.concat(P).to_csv(os.path.join(OUT, 'E12_paired.csv'), index=False)
df = load(R('E8_digits_norm.jsonl')); e1 = load(R('E1_*.jsonl')); e1 = e1[(e1.rep < 12) & e1.variant.isin(df.variant.unique())]
dd = pd.concat([e1.assign(norm=0), df.assign(norm=1)]); P = []
for a, b in (('real_b', 'null_b'), ('real_w', 'null_w'), ('real_w', 'real_b'), ('real_b', 'f6'), ('kcdeg_b', 'f6')):
    for m in ('MAP', 'acc'):
        r = paired(dd, a, b, m, by=('norm',)); r['pair'] = f'{a} - {b}'; P.append(r)
pd.concat(P).to_csv(os.path.join(OUT, 'E8_paired.csv'), index=False)
df = load(R('E13_digits_keepdead.jsonl')); P = []
for a, b in (('real_b', 'null_b'), ('real_b', 'f6'), ('f6', 'sim_k'), ('f6', 'sim_m'), ('gauss', 'f6')):
    for m in ('MAP', 'acc'):
        r = paired(df, a, b, m); r['pair'] = f'{a} - {b}'; P.append(r)
pd.concat(P).to_csv(os.path.join(OUT, 'E13_paired.csv'), index=False)
df = load(R('E14_*.jsonl')); P = []
for a, b in (('realdd_b', 'null_b'), ('realdd_b', 'real_b'), ('real_b', 'null_b'), ('realdd_b', 'f6')):
    r = paired(df, a, b, 'MAP', by=('dataset', 'mapper')); r['pair'] = f'{a} - {b}'; P.append(r)
pd.concat(P).to_csv(os.path.join(OUT, 'E14_paired.csv'), index=False)
# E11 rango
df = load(R('E11_rank.jsonl')); rows = []
for s, g in df.groupby('mapping'):
    r = g[g.kind == 'real'].MAP.iloc[0]; n = g[g.kind == 'null'].MAP.values; f = g[g.kind == 'f6'].MAP.values
    rows.append(dict(mapping=s, real=r, null_mean=n.mean(), null_sd=n.std(ddof=1), z=(r - n.mean()) / n.std(ddof=1), frac_null_ge_real=(np.sum(n >= r) + 1) / (len(n) + 1), f6_mean=f.mean()))
pd.DataFrame(rows).to_csv(os.path.join(OUT, 'E11_rank.csv'), index=False)
# E15 logistica
df = load(R('E15_logreg_digits.jsonl')); rows = []
for a, b in (('real_b', 'null_b'), ('real_b', 'f6'), ('f6', 'sim_m'), ('null_b', 'f6')):
    r = paired(df, a, b, 'acc', nboot=20000).iloc[0]; rows.append(dict(a=a, b=b, n=r.n, diff_pp=100 * r['diff'], lo_pp=100 * r.lo, hi_pp=100 * r.hi, p=r.p))
pd.DataFrame(rows).to_csv(os.path.join(OUT, 'E15_logreg_paired.csv'), index=False)
# E7n replica
df = pd.concat([load(R('E7nrep_news_*.jsonl')), load(R('E7n_news_*.jsonl'))]); df = df[df.variant.isin(['real_b', 'null_b', 'f6', 'kcdeg_b'])]; rows = []
for a, b in (('real_b', 'null_b'), ('real_b', 'f6')):
    r = paired(df, a, b, 'MAP', by=('mapper',), nboot=20000); r['pair'] = f'{a} - {b}'; rows.append(r)
pd.concat(rows).to_csv(os.path.join(OUT, 'E7n_comb_paired.csv'), index=False)
import analyze_net   # tabla y figura de E10
analyze_primary.__name__; figs.forest(); figs.power()
print('ok')
