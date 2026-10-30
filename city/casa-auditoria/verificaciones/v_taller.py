"""Auditor: recomputo independiente de las cifras impresas en las obras de casa-taller, desde los JSON de mosca y agora.
Uso: python v_taller.py <city_dir>"""
import json, sys, os, re, hashlib
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from veredicto import check, resumen
city = sys.argv[1]
a = json.load(open(f"{city}/casa-mosca/out/activity.json")); r = json.load(open(f"{city}/casa-agora/out/results.json"))
typ = np.array([n["type"] for n in a["neurons"]]); sp = np.array(a["spikes"]); t, ids = sp[:, 0], sp[:, 1].astype(int)
st = {s["name"]: (s["t_start"], s["t_end"]) for s in a["stimuli"]}
kc = np.flatnonzero(typ == "KC"); mb = np.flatnonzero(typ == "MBON")
def c(ix, n): m = (t >= st[n][0]) & (t < st[n][1]); return np.bincount(ids[m], minlength=len(typ))[ix]
for n in ("pre_A", "post_A"):
    k = c(kc, n); print(n, "KC espigas totales", k.sum(), "| KC con >=1 espiga", int((k >= 1).sum()), "| KC >=5 espigas (def. casa-mosca)", int((k >= 5).sum()), "| MBON espigas", c(mb, n).sum())
for n in ("pre_B", "post_B"): print(n, "MBON espigas", c(mb, n).sum())
print("declarado taller: KC espigas 2199->2041 (-7%), KC activas 778->772, MBON A 90->31, B 88->77")
x = np.array(r["pool_path"]["reserve_x"]); y = np.array(r["pool_path"]["reserve_y"]); p = np.array(r["price_path"])
k = x * y; print("k inicio/fin", k[0] / 1e9, k[-1] / 1e9, "crec % ", 100 * (k[-1] / k[0] - 1), "monotono", bool((np.diff(k) >= -1e-6).all()), "n puntos", len(p))
g = y / x - p; print("brecha |media|", np.abs(g).mean(), "max", np.abs(g).max(), "max % precio", 100 * (np.abs(g) / p).max(), "precio ini/fin", p[0], p[-1], "marg fin", (y / x)[-1])
print("rango x", x.min(), x.max())
print("precio marginal dentro de banda [p(1-f),p/(1-f)] (f=.003):", bool(((y / x) >= p * 0.997 - 1e-9).all() and ((y / x) <= p / 0.997 + 1e-9).all()), "(es consecuencia del arbitrajista por construccion)")

k0, k1 = c(kc, "pre_A"), c(kc, "post_A")
check("KC espigas pre_A", k0.sum(), 2199); check("KC espigas post_A", k1.sum(), 2041); check("variacion KC espigas (%)", 100 * (k1.sum() / k0.sum() - 1), -7, 0.5)
check("'KC activas' pre_A (taller; = >=1 espiga)", (k0 >= 1).sum(), 778); check("'KC activas' post_A (taller)", (k1 >= 1).sum(), 772)
check("KC activas pre_A con la definicion de casa-mosca (>=5 espigas) vs 778 de taller", (k0 >= 5).sum(), 778, 0, nota="<- DEFINICION DISTINTA a la de casa-mosca")
check("MBON A pre", c(mb, "pre_A").sum(), 90); check("MBON A post", c(mb, "post_A").sum(), 31); check("MBON B pre", c(mb, "pre_B").sum(), 88); check("MBON B post", c(mb, "post_B").sum(), 77)
check("k inicio (1e9)", k[0] / 1e9, 2.5, 1e-4); check("k final (1e9)", k[-1] / 1e9, 2.5156, 1e-4); check("crecimiento k (%)", 100 * (k[-1] / k[0] - 1), 0.62, 0.005)
check("brecha media", np.abs(g).mean(), 0.22, 0.005); check("brecha maxima", np.abs(g).max(), 0.32, 0.005); check("precio marginal final", (y / x)[-1], 74.0, 0.05)
check("rango x min", x.min(), 4870, 5); check("rango x max", x.max(), 5830, 20)
sys.exit(1 if resumen() else 0)
