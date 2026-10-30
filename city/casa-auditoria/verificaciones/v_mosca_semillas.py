"""Auditor: robustez de casa-mosca entre semillas Y control sin entrenamiento (0 pares).
Usa SOLO el simulador (fly_mb, build_schedule) de la copia; el analisis es mio.
Uso: python v_mosca_semillas.py <casa-mosca> <pares> <semillas a,b,c>"""
import sys, os, numpy as np
casa, pares, seeds = sys.argv[1], int(sys.argv[2]), [int(s) for s in sys.argv[3].split(",")]
sys.path.insert(0, casa)
from fly_mb import MushroomBody
from run_experiment import build_schedule, BLANK_MS
def rate(res, n):
    s = res.stim(n); return res.window_counts("MBON", s["t0"], s["t1"]).mean() / ((s["t1"] - s["t0"]) / 1000)
print(f"pares={pares}")
rows = []
for sd in seeds:
    mb = MushroomBody(sd); sch = build_schedule(pares); res = mb.run(sch, t_end_ms=max(s["t1"] for s in sch) + BLANK_MS)
    ch = {}
    for o, pre in [("A", ["pre_A", "pre_A_rep"]), ("B", ["pre_B"]), ("C", ["pre_C"])]:
        p = np.mean([rate(res, n) for n in pre]); q = rate(res, "post_" + o); ch[o] = 100 * (q - p) / p
    rows.append([ch["A"], ch["B"], ch["C"]]); print(f"semilla {sd}: A {ch['A']:+.1f} B {ch['B']:+.1f} C {ch['C']:+.1f} A-B {ch['A']-ch['B']:+.1f} A-C {ch['A']-ch['C']:+.1f}", flush=True)
r = np.array(rows)
print("media A,B,C", r.mean(0).round(1), "sd", r.std(0, ddof=1).round(1))
print("A-B media", (r[:,0]-r[:,1]).mean().round(1), "sd", (r[:,0]-r[:,1]).std(ddof=1).round(1), "min/max", (r[:,0]-r[:,1]).min().round(1), (r[:,0]-r[:,1]).max().round(1))
print("A-C media", (r[:,0]-r[:,2]).mean().round(1), "n con A<B", int((r[:,0]<r[:,1]).sum()), "de", len(r), "; n con A<C", int((r[:,0]<r[:,2]).sum()))
