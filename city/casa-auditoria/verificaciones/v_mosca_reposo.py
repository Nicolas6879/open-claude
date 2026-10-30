"""Auditor: reposo largo de casa-mosca (10 s sin olor) con SU simulador en la copia; el README dice MBON ~3.5 Hz en reposo. Uso: python v_mosca_reposo.py <casa-mosca>"""
import sys; sys.path.insert(0, sys.argv[1])
from fly_mb import MushroomBody
for sd in (7, 8, 9):
    r = MushroomBody(sd).run([{"name": "rest", "t0": 0, "t1": 10000}])
    print(sd, "MBON reposo 1-10 s (Hz):", round(r.window_counts("MBON", 1000, 10000).mean() / 9, 2), "| KC>=5Hz %:", round(100 * (r.window_counts("KC", 1000, 10000) >= 45).mean(), 3), "| KC>=1 espiga %:", round(100 * (r.window_counts("KC", 1000, 10000) >= 1).mean(), 1))
