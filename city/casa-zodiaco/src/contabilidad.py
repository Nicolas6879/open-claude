"""Genera out/contabilidad_culturas.csv (perdidas de datos + licencia + familia). Uso: python contabilidad.py"""
import os, sys
sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pandas as pd
import datos

df = datos.cargar_hyg()
hs = set(df.hip.dropna().astype(int))
filas = []
for c in datos.lista_culturas():
    ar, ct = datos.parsear_cultura(c, hs)
    ct["familia"] = datos.familia_de(c)
    ct["licencia"] = datos.licencia(c)
    ct["elegible_>=15_aristas"] = ct["aristas_finales"] >= 15
    filas.append(ct)
t = pd.DataFrame(filas).rename(columns={"culturas": "cultura"})
out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "out", "contabilidad_culturas.csv")
t.to_csv(out, index=False)
print(t[["aristas_brutas", "aristas_no_hip", "aristas_hip_fuera_hyg", "aristas_duplicadas", "aristas_finales"]].sum())
print("elegibles:", int(t["elegible_>=15_aristas"].sum()), "de", len(t))
