"""Auditor: recomputo independiente de casa-mosca desde out/activity.json (picos crudos), sin usar su run_experiment.analyse.
Uso: python v_mosca.py <ruta_casa-mosca>   (lee <casa>/out/activity.json)"""
import json, sys, os
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from veredicto import check, resumen
casa = sys.argv[1]
d = json.load(open(os.path.join(casa, "out", "activity.json")))
neu = d["neurons"]; typ = np.array([n["type"] for n in neu])
sp = np.array(d["spikes"]); t = sp[:, 0]; ids = sp[:, 1].astype(int)
stim = {s["name"]: (s["t_start"], s["t_end"]) for s in d["stimuli"]}
idx = lambda ty: np.flatnonzero(typ == ty)
print("meta", d["meta"]["seed"], d["meta"]["duration_ms"], "| neuronas", len(neu))
check("neuronas totales", len(neu), 2109)
tot = {k: int(np.isin(ids, idx(k)).sum()) for k in dict.fromkeys(typ)}
check("espigas totales", len(ids), 70149)
for k, v in dict(ORN=21236, PN=6602, KC=38877, APL=1807, MBON=1308, DAN=319).items(): check("espigas " + k, tot[k], v)
def counts(ty, t0, t1): m = (t >= t0) & (t < t1); return np.bincount(ids[m], minlength=len(neu))[idx(ty)]
mbon_rate = lambda n: counts("MBON", *stim[n]).mean() / ((stim[n][1] - stim[n][0]) / 1000)
kc_act = lambda n: counts("KC", *stim[n]) >= 5
jac = lambda a, b: (a & b).sum() / (a | b).sum()
pre = {"A": ["pre_A", "pre_A_rep"], "B": ["pre_B"], "C": ["pre_C"]}; post = {"A": "post_A", "B": "post_B", "C": "post_C"}
decl = {"A": (23.1, 7.8, -66.5, 6.6), "B": (22.0, 19.2, -12.5, 4.3), "C": (23.8, 17.0, -28.4, 6.0)}
ch = {}
for o in "ABC":
    p = np.mean([mbon_rate(n) for n in pre[o]]); q = mbon_rate(post[o]); ch[o] = 100 * (q - p) / p
    kca = 100 * np.mean([kc_act(n).mean() for n in pre[o]])
    check(f"MBON pre {o} (Hz)", p, decl[o][0], 0.05); check(f"MBON post {o} (Hz)", q, decl[o][1], 0.05)
    check(f"cambio {o} (%)", ch[o], decl[o][2], 0.05); check(f"KC activas {o} (%)", kca, decl[o][3], 0.05)
check("discriminacion A-B (pp)", ch["A"] - ch["B"], -54.0, 0.05)
for (a, b), v in {("pre_A", "pre_B"): 0.03, ("pre_A", "pre_C"): 0.05, ("pre_B", "pre_C"): 0.08, ("pre_A", "pre_A_rep"): 0.49}.items():
    check(f"Jaccard {a}-{b}", jac(kc_act(a), kc_act(b)), v, 0.006)
check("curva A par1..4", sum(abs(np.array([mbon_rate(f"train_AR_{i}") for i in range(1, 5)]) - [16.2, 14.0, 10.2, 12.5])), 0, 0.2)
# reposo: primeros 500 ms (sin olor previo) y huecos entre ensayos
w = 0.5; mb0 = counts("MBON", 0, 500).mean() / w
check("MBON en reposo, primeros 500 ms (Hz) [README: ~3.5]", mb0, 3.5, 0.5, nota="(4 neuronas x 0,5 s: granularidad 0,5 Hz)")
odor_w = sorted(v for k, v in stim.items() if not k.startswith("reward"))
gaps = [counts("MBON", b0 + 100, a1).mean() / ((a1 - b0 - 100) / 1000) for (a0, b0), (a1, b1) in zip(odor_w[:-1], odor_w[1:])]
check("MBON en reposo, media de 14 huecos (Hz) [README: ~3.5]", np.mean(gaps), 3.5, 1.0)
check("KC >=5 Hz en reposo, primeros 500 ms (%) [README: casi nada / 0,2]", 100 * (counts("KC", 0, 500) >= 2.5).mean(), 0.2, 0.2)
sys.exit(1 if resumen() else 0)
