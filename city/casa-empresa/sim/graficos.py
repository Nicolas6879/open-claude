"""Graficos SVG de los resultados de simulacion (lee out/resultados.json).
Uso: PYTHONDONTWRITEBYTECODE=1 /tmp/.../scratchpad/venv/bin/python graficos.py
"""
import json
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out")
r = json.load(open(os.path.join(OUT, "resultados.json"), encoding="utf-8"))
plt.rcParams.update({"font.size": 10, "svg.fonttype": "none"})

# 1. margen acumulado por escenario (mediana y banda p10-p90)
fig, ax = plt.subplots(figsize=(7.2, 4.2))
semanas = np.arange(0, 156, 13)
colores = {"A_organico": "#8a7f6a", "B_paid": "#c4502a", "C_organico_aula": "#6b9e8f",
           "D_todo": "#a3564a", "E_aula_primero": "#2f7a6b", "F_aula_sin_salario": "#e0b030"}
for nombre, esc in r["escenarios"].items():
    p = esc["margen_acumulado_percentiles"]
    med = np.array(p["50"]); lo = np.array(p["10"]); hi = np.array(p["90"])
    c = colores.get(nombre, "#333")
    ax.plot(semanas, med / 1000, color=c, lw=2, label=nombre.replace("_", " "))
    ax.fill_between(semanas, lo / 1000, hi / 1000, color=c, alpha=0.10)
ax.axhline(0, color="#555", lw=0.8)
ax.set_xlabel("semana")
ax.set_ylabel("margen acumulado (miles de USD)")
ax.set_title("Margen acumulado por escenario (mediana y banda p10-p90)")
ax.legend(fontsize=8, loc="lower left", frameon=False)
fig.tight_layout(); fig.savefig(os.path.join(OUT, "margen_por_escenario.svg"), format="svg"); plt.close(fig)

# 2. sensibilidad: correlacion de rango con el margen final (escenario E)
sens = r["sensibilidad_escenario_E"]
items = list(sens.items())[:10]
fig, ax = plt.subplots(figsize=(7.2, 4.0))
nombres = [k for k, _ in items][::-1]; vals = [v for _, v in items][::-1]
ax.barh(nombres, vals, color=["#c4502a" if v < 0 else "#2f7a6b" for v in vals])
ax.axvline(0, color="#555", lw=0.8)
ax.set_xlabel("correlacion de rango (Spearman) con el margen final")
ax.set_title("Que supuesto manda (escenario E, rediseno)")
fig.tight_layout(); fig.savefig(os.path.join(OUT, "sensibilidad_escenario_E.svg"), format="svg"); plt.close(fig)

# 3. mapa de decision: ventas de aulas x equipo -> probabilidad de perdida
m = r["mapa_decision_aulas"]
P = np.array(m["prob_perdida"])
fig, ax = plt.subplots(figsize=(6.6, 4.4))
im = ax.imshow(P, cmap="RdYlGn_r", vmin=0, vmax=1, aspect="auto")
ax.set_xticks(range(len(m["equipo_mes_usd"]))); ax.set_xticklabels([str(x) for x in m["equipo_mes_usd"]])
ax.set_yticks(range(len(m["aulas_por_semana"]))); ax.set_yticklabels([str(x) for x in m["aulas_por_semana"]])
ax.set_xlabel("equipo (USD/mes)"); ax.set_ylabel("aulas vendidas por semana")
for i in range(P.shape[0]):
    for j in range(P.shape[1]):
        ax.text(j, i, "%d %%" % round(P[i, j] * 100), ha="center", va="center", fontsize=8)
ax.set_title("Probabilidad de perdida tras 3 anios (escenario E)")
fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
fig.tight_layout(); fig.savefig(os.path.join(OUT, "mapa_decision_aulas.svg"), format="svg"); plt.close(fig)
print("svg escritos en", OUT)
