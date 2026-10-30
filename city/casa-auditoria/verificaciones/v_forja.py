"""Auditor: comprobaciones de los datos y de las cifras del LOG de casa-forja (estado en curso). Uso: python v_forja.py <casa-forja>"""
import sys, os, gzip, numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from veredicto import check, resumen
d = os.path.join(sys.argv[1], "datos")
a = pd.read_csv(os.path.join(d, "sp500_1990_2022.csv.gz")); print("sp500_1990_2022 columnas", list(a.columns), len(a), a.iloc[0].tolist(), a.iloc[-1].tolist())
b = pd.read_csv(os.path.join(d, "sp500_ohlc_1999_2018.csv.gz")); print("ohlc columnas", list(b.columns), len(b))
da, db = a.columns[0], b.columns[0]
a[da] = pd.to_datetime(a[da]); b[db] = pd.to_datetime(b[db])
ca = a.set_index(da).iloc[:, 0]; cb = b.set_index(db)[[c for c in b.columns if c.lower() == "close"][0]]
j = pd.concat([ca, cb], axis=1, join="inner").dropna(); rel = (j.iloc[:, 0] / j.iloc[:, 1] - 1).abs()
print("solape", len(j), "diferencia relativa max", rel.max(), "(declarado 6e-8)")
sel = ca[:"2013-12-31"]; fin = ca["2014-01-01":]
print("seleccion dias", len(sel), sel.index[0].date(), sel.index[-1].date(), "| final dias", len(fin), fin.index[0].date(), fin.index[-1].date(), "(declarado 6049 / 2264)")
r = np.log(sel).diff().dropna().values; rr = r - r.mean()
ac = lambda x: np.corrcoef(x[:-1], x[1:])[0, 1]
print("autocorr lag1 retorno (seleccion) %.3f  (declarado -0,059)" % ac(rr))
print("autocorr lag1 |r| %.3f (declarado 0,23 real)" % ac(np.abs(rr)))
# bootstrap por bloques de 20 (bloque fijo) e iid: autocorrelacion esperada
rng = np.random.default_rng(1)
def blk(x, L=20):
    n = len(x); out = []
    while len(out) < n: s = rng.integers(0, n - L); out.extend(x[s:s + L])
    return np.array(out[:n])
print("autocorr bloques-20 (media 200 remuestreos) %.3f (declarado -0,048) | iid %.3f (declarado +0,011)" % (
    np.mean([ac(blk(rr)) for _ in range(200)]), np.mean([ac(rng.choice(rr, len(rr))) for _ in range(200)])))
# exceso del bloque con signo aleatorio
sg = lambda: blk(np.abs(rr)) * rng.choice([-1, 1], len(rr))
print("signo aleatorio: autocorr r %.3f ; autocorr |r| %.3f (declarado 0,22)" % (np.mean([ac(sg()) for _ in range(200)]), np.mean([ac(np.abs(sg())) for _ in range(200)])))

check("solape skfolio vs arch: dif relativa max (declarado 6e-8)", rel.max(), 6e-8, 1e-8); check("dias seleccion", len(sel), 6049); check("dias final", len(fin), 2264)
check("autocorr lag1 retorno", ac(rr), -0.059, 0.002); check("autocorr lag1 |r|", ac(np.abs(rr)), 0.23, 0.005)
# intervalos exactos de Clopper-Pearson para los recuentos que reporta casa-forja (calibracion.json / bus n=34)
from scipy.stats import beta
def cp(k, n): return (beta.ppf(0.025, k, n - k + 1) if k > 0 else 0.0, beta.ppf(0.975, k + 1, n - k) if k < n else 1.0)
for k, n, txt in ((0, 300, "nulo signo: campeones"), (0, 200, "nulo iid: campeones"), (3, 150, "potencia SR 0,3 (2,0 %)"), (22, 150, "potencia SR 0,6 (14,7 %)")):
    lo, hi = cp(k, n); print(f"IC95 exacto {txt}: {k}/{n} -> [{100*lo:.2f} %, {100*hi:.2f} %]")
cal = os.path.join(sys.argv[1], "out", "calibracion.json")
if os.path.exists(cal):
    import json; r = json.load(open(cal))["resumen"]
    for k, v in r.items(): print("calibracion.json", k, "tasa_campeon", v["tasa_campeon"], "campeon_ic95", [round(x, 6) for x in v["campeon_ic95"]], "n", v["n_mundos"])
sys.exit(1 if resumen() else 0)
