"""Genera zodiaco.html (autonomo: sin red, datos embebidos) a partir de out/*.json|csv. Uso: python hacer_html.py"""
import os, sys, json
sys.dont_write_bytecode = True
import numpy as np, pandas as pd

AQUI = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(AQUI, "..", "out")
DISENO = ['potawatomi', 'romanian', 'nordica', 'belarusian', 'navajo', 'tukano', 'seri', 'balinese', 'tupi', 'polinesia',
          'mongolian', 'arabe_popular', 'tibetan', 'sardinian', 'lokono']


def tabla(sufijo):
    v = pd.read_csv(os.path.join(OUT, f"resultados_v2_sellado_hgb{sufijo}.csv"))
    v = v[~v.familia.isin(DISENO)]
    g = v.groupby("familia").agg(n=("cultura", "size"), modelo=("f1_modelo", "mean"), nn=("f1_nn", "mean"),
                                 consenso=("f1_consenso", "mean"), gana=("f1_modelo", lambda s: 0)).reset_index()
    g["gana"] = [float((v[v.familia == f].f1_modelo > v[v.familia == f].f1_nn).mean()) for f in g.familia]
    return [dict(f=r.familia, n=int(r.n), m=round(r.modelo, 3), nn=round(r.nn, 3), c=round(r.consenso, 3), g=round(r.gana, 2)) for r in g.itertuples()]


datos = dict(
    prereg=tabla(""), kmatch=tabla("_kmatch"),
    resumen={k: json.load(open(os.path.join(OUT, f))) for k, f in
             (("A", "resumen_A.json"), ("B", "resumen_B.json"), ("v2", "resumen_v2.json"), ("v2k", "resumen_v2_kmatch.json"))},
    potencia=pd.read_csv(os.path.join(OUT, "potencia.csv")).round(3).to_dict("records"),
    ext=json.load(open(os.path.join(OUT, "extension.json"))),
    est=pd.read_csv(os.path.join(OUT, "estabilidad.csv")).round(3).fillna(-1).to_dict("records"),
)
# solo lo necesario de los resumenes
r = datos["resumen"]
datos["resumen"] = dict(
    A=dict(g1=r["A"]["g1"]["por_cultura"], g2=r["A"]["g2"]["por_cultura"], g2f=r["A"]["g2"]["por_familia"], f1=r["A"]["mediana_f1_modelo"], nn=r["A"]["mediana_f1_nn"]),
    B=dict(g1=r["B"]["g1"]["por_cultura"], g2=r["B"]["g2"]["por_cultura"], g2f=r["B"]["g2"]["por_familia"], f1=r["B"]["mediana_f1_modelo"], nn=r["B"]["mediana_f1_nn"]),
    v2=dict(g2=r["v2"]["sellado"]["g2"]["por_cultura"], g2f=r["v2"]["sellado"]["g2"]["por_familia"], f1=r["v2"]["sellado"]["mediana_f1_modelo"], nn=r["v2"]["sellado"]["mediana_f1_nn"], n=r["v2"]["sellado"]["n_culturas"], nf=r["v2"]["sellado"]["n_familias"]),
    v2k=dict(g2=r["v2k"]["sellado"]["g2"]["por_cultura"], g2f=r["v2k"]["sellado"]["g2"]["por_familia"], f1=r["v2k"]["sellado"]["mediana_f1_modelo"], nn=r["v2k"]["sellado"]["mediana_f1_nn"]),
)
plantilla = open(os.path.join(AQUI, "plantilla.html"), encoding="utf-8").read()
html = plantilla.replace("/*DATOS*/null", json.dumps(datos, separators=(",", ":"), ensure_ascii=False))
dest = os.path.join(AQUI, "..", "zodiaco.html")
open(dest, "w", encoding="utf-8").write(html)
print("zodiaco.html", os.path.getsize(dest) // 1024, "KB")
