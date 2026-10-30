"""E9: potencia con ventaja inyectada (copia del real con +e % de KC). Reutiliza real_b y null_b de E1 (mismas semillas)."""
import os, sys, numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from stats import load, paired
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'out')
e1 = load(os.path.join(OUT, 'raw', 'E1_*.jsonl')); e9 = load(os.path.join(OUT, 'raw', 'E9_power.jsonl'))
df = pd.concat([e1[e1.variant.isin(['real_b', 'null_b'])], e9], ignore_index=True)
rng = np.random.default_rng(0); rows = []
nb = df[df.variant == 'null_b'].set_index('rep').MAP
def detect(d, n, nsim=1000):
    hit = 0
    for _ in range(nsim):
        x = rng.choice(d, n, replace=True); s = rng.choice([-1, 1], (500, n)); perm = np.abs((s * x).mean(1))
        hit += ((perm >= abs(x.mean())).mean() < 0.05) and x.mean() > 0
    return hit / nsim
for v in ['real_b', 'plus10_b', 'plus25_b', 'plus50_b', 'plus100_b']:
    a = df[df.variant == v].set_index('rep').MAP; idx = a.index.intersection(nb.index); d = (a.loc[idx] - nb.loc[idx]).values
    base = nb.loc[idx].mean(); r = dict(variante=v, n=len(d), dif_rel=d.mean() / base, sd=d.std(ddof=1))
    bs = rng.choice(d, (4000, len(d))).mean(1) / base; r['ic_lo'], r['ic_hi'] = np.percentile(bs, [2.5, 97.5])
    for n in (10, 20, 30): r[f'deteccion_n{n}'] = detect(d, n)
    rows.append(r)
T = pd.DataFrame(rows); T.to_csv(os.path.join(OUT, 'E9_power.csv'), index=False)
pd.set_option('display.width', 200); print(T.round(4).to_string())
sd = T[T.variante == 'real_b'].sd.iloc[0]; print('MDE(80 %, n=30) relativo ~', 2.8 * sd / np.sqrt(30) / nb.mean())
