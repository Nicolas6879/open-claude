"""Estadistica pareada: diferencias por replica, IC95 bootstrap (percentil), p por permutacion de signos,
correccion de Holm / BH (statsmodels). Potencia: MDE aproximado y potencia empirica por remuestreo."""
import glob, json, numpy as np, pandas as pd
from statsmodels.stats.multitest import multipletests

def load(pattern):
    rows = []
    for f in sorted(glob.glob(pattern)):
        for l in open(f):
            if l.strip(): rows.append(json.loads(l))
    return pd.DataFrame(rows)

def paired(df, a, b, metric, by=('dataset', 'mapper', 'cond', 'level', 'frac', 'norm', 'mfrac', 'tag'), rel=True, nboot=4000, seed=0):
    """Una fila por grupo: media de (a-b) por replica, dif relativa a b, IC95 bootstrap, p (permutacion de signos)."""
    rng = np.random.default_rng(seed); out = []
    by = [c for c in by if c in df.columns]
    for key, g in df.groupby(by, dropna=False):
        pa = g[g.variant == a].set_index('rep')[metric]; pb = g[g.variant == b].set_index('rep')[metric]
        idx = pa.index.intersection(pb.index)
        if len(idx) < 3: continue
        d = (pa.loc[idx] - pb.loc[idx]).values; base = pb.loc[idx].values.mean()
        bs = rng.choice(d, (nboot, len(d)), replace=True).mean(1)
        signs = rng.choice([-1, 1], (nboot, len(d))); perm = np.abs((signs * d).mean(1))
        p = (np.sum(perm >= abs(d.mean()) - 1e-15) + 1) / (nboot + 1)
        r = dict(zip(by, key if isinstance(key, tuple) else (key,)))
        r.update(a=a, b=b, metric=metric, n=len(d), mean_a=pa.loc[idx].mean(), mean_b=pb.loc[idx].mean(), diff=d.mean(),
                 lo=np.percentile(bs, 2.5), hi=np.percentile(bs, 97.5), sd=d.std(ddof=1), p=p,
                 rel=d.mean() / base, rel_lo=np.percentile(bs, 2.5) / base, rel_hi=np.percentile(bs, 97.5) / base)
        out.append(r)
    return pd.DataFrame(out)

def adjust(df, method='holm', col='p'):
    if len(df) == 0: return df
    df = df.copy(); df['p_adj'] = multipletests(df[col].values, method=method)[1]; return df

def mde(sd, n, power_z=0.84, alpha_z=1.96):
    """Efecto minimo detectable (potencia 80 %, alfa 5 % bilateral) para una media de n diferencias con sd dada."""
    return (power_z + alpha_z) * sd / np.sqrt(n)

def empirical_power(d, shift, n, nsim=2000, seed=0):
    """Potencia empirica: remuestrea n diferencias de d (centradas en 0) sumando `shift` y cuenta cuantas veces el IC95
    (t) excluye 0. Mide cuanto veria el procedimiento una ventaja conocida `shift` (en unidades de la metrica)."""
    from scipy import stats
    rng = np.random.default_rng(seed); d0 = np.asarray(d) - np.mean(d); hits = 0
    for _ in range(nsim):
        x = rng.choice(d0, n, replace=True) + shift
        t = x.mean() / (x.std(ddof=1) / np.sqrt(n) + 1e-12); hits += abs(t) > stats.t.ppf(0.975, n - 1)
    return hits / nsim
