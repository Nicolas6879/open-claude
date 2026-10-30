"""Familia primaria pre-registrada: {digits E1, MNIST E2} x {MAP, acc} x {H1 real_b-nulo_b, H2 real_w-nulo_w, H3 real_b-F6}; Holm sobre las 12 pruebas.
Escribe out/PRIMARY.csv y out/PRIMARY.md"""
import os, sys, pandas as pd, numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from stats import load, paired, adjust
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'out'); RAW = os.path.join(OUT, 'raw')
rows = []
for ds, pat in (('digits', 'E1_*.jsonl'), ('MNIST', 'E2_*.jsonl')):
    df = load(os.path.join(RAW, pat))
    for h, a, b in (('H1', 'real_b', 'null_b'), ('H2', 'real_w', 'null_w'), ('H3', 'real_b', 'f6')):
        for m in ('MAP', 'acc'):
            r = paired(df, a, b, m, nboot=20000)
            if len(r): r = r.iloc[0]; rows.append(dict(set=ds, hip=h, a=a, b=b, metric=m, n=int(r.n), mean_a=r.mean_a, mean_b=r.mean_b, diff=r['diff'], rel=r.rel, rel_lo=r.rel_lo, rel_hi=r.rel_hi, lo=r.lo, hi=r.hi, p=r.p))
P = adjust(pd.DataFrame(rows), 'holm'); P.to_csv(os.path.join(OUT, 'PRIMARY.csv'), index=False)
with open(os.path.join(OUT, 'PRIMARY.md'), 'w') as f:
    f.write('| conjunto | hip. | metrica | n | a | b | dif. (IC95) | dif. relativa (IC95) | p | p Holm(12) |\n|---|---|---|---|---|---|---|---|---|---|\n')
    for _, r in P.iterrows():
        u = 'pp' if r.metric == 'acc' else ''
        f.write(f"| {r.set} | {r.hip} | {r.metric} | {r.n} | {r.mean_a:.4f} | {r.mean_b:.4f} | {r['diff']:+.4f} [{r.lo:+.4f}, {r.hi:+.4f}] | {100*r.rel:+.2f} % [{100*r.rel_lo:+.2f}, {100*r.rel_hi:+.2f}] | {r.p:.4f} | {r.p_adj:.4f} |\n")
print(open(os.path.join(OUT, 'PRIMARY.md')).read())
