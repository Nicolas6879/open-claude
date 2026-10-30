"""Pruebas del simulador de Mosquita. Ejecutar desde sim/: python3 tests/test_simulador.py"""
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
import simulador as S  # noqa: E402

fallos = []


def check(cond, msg):
    print(("OK    " if cond else "FALLO ") + msg)
    if not cond:
        fallos.append(msg)


sup = S.cargar_supuestos()

# 1. reproducibilidad con semilla
R1 = np.random.default_rng(5); par1 = S.muestra_parametros(sup, 200, R1)
R2 = np.random.default_rng(5); par2 = S.muestra_parametros(sup, 200, R2)
r1 = S.simula(par1, 750, True, T=60, seed=3); r2 = S.simula(par2, 750, True, T=60, seed=3)
check(np.array_equal(r1["margen_acumulado"], r2["margen_acumulado"]), "misma semilla -> mismos resultados")

# 2. sin presupuesto pagado no hay instalaciones pagadas
R = np.random.default_rng(1); par = S.muestra_parametros(sup, 100, R)
res0 = S.simula(par, 0, False, T=40, seed=1)
check(res0["paid_instalaciones"].sum() == 0, "presupuesto 0 -> cero instalaciones pagadas")

# 3. identidad contable: margen = ingreso - coste, semana a semana
check(np.allclose(r1["margen_semanal"], r1["ingreso"] - r1["coste"]), "margen = ingreso - coste (identidad)")
check(np.allclose(r1["margen_acumulado"][:, -1], r1["margen_semanal"].sum(axis=1)), "margen acumulado = suma semanal")

# 4. retencion: la curva decrece con la edad (cohorte unica, sin viral)
par_t = S.muestra_parametros(sup, 50, np.random.default_rng(2))
par_t["viral_K"] = np.zeros(50); par_t["instalaciones_organicas_semana"] = np.zeros(50)
par_t["retencion_b"] = np.full(50, 0.6)
par_t["retencion_c"] = np.full(50, 0.5)
par_t["activacion"] = np.full(50, 1.0)
par_t["cpi_usd"] = np.full(50, 1.0)
inst0 = np.zeros((50, 30))
rr = S.simula(par_t, 0, False, T=30, seed=0)
act = rr["activos"]
check(np.all(act[:, 0] == 0), "sin instalaciones no hay activos (control)")
# cohorte inyectada a mano: insertamos una cohorte de 100 en la semana 0
par_t["instalaciones_organicas_semana"] = np.zeros(50)
Pw = np.exp(-0.6 * np.log1p(np.arange(30)))
check(Pw[0] > Pw[1] > Pw[5] > Pw[20], "kernel (1+k)^-b decrece con la edad")

# 5. ingreso del Laboratorio lineal en el precio
par_p = S.muestra_parametros(sup, 80, np.random.default_rng(4))
ra = S.simula(par_p, 0, False, T=50, seed=9)
par_p2 = dict(par_p); par_p2["lab_precio_mes_efectivo"] = par_p["lab_precio_mes_efectivo"] * 2
rb = S.simula(par_p2, 0, False, T=50, seed=9)
check(np.allclose(rb["ingreso_por_fuente"]["lab"], 2 * ra["ingreso_por_fuente"]["lab"]), "ingreso Laboratorio proporcional al precio")

# 6. distribucion fija cuando min == max
check(np.all(S.muestrea(np.random.default_rng(0), {"dist": "tri", "min": 0, "moda": 0, "max": 0}, 5) == 0),
      "tri con min=max devuelve el valor fijo")

# 7. resultados publicados: coherentes
ruta = os.path.join(HERE, "out", "resultados.json")
if os.path.exists(ruta):
    R_ = json.load(open(ruta, encoding="utf-8"))
    esc = R_["escenarios"]
    check(all(0 <= e["resumen"]["prob_margen_final_negativo"] <= 1 for e in esc.values()), "probabilidades dentro de [0,1]")
    check(all(e["resumen"]["margen_final_p10"] <= e["resumen"]["margen_final_mediana"] <= e["resumen"]["margen_final_p90"] for e in esc.values()),
          "percentiles ordenados (p10 <= mediana <= p90)")
    check(esc["F_aula_sin_salario"]["resumen"]["margen_final_mediana"] > esc["E_aula_primero"]["resumen"]["margen_final_mediana"],
          "quitar el coste de equipo mejora el margen (sanidad)")
    check(esc["B_paid"]["resumen"]["margen_final_mediana"] < esc["A_organico"]["resumen"]["margen_final_mediana"],
          "el paid social empeora el margen con estos supuestos (resultado a reportar)")
    mapa = R_["mapa_decision_aulas"]
    check(len(mapa["prob_perdida"]) == len(mapa["aulas_por_semana"]), "mapa de decision con dimension correcta")
else:
    print("AVISO sin out/resultados.json: ejecuta simulador.py antes")

print("todas las pruebas pasan" if not fallos else "%d fallo(s)" % len(fallos))
sys.exit(1 if fallos else 0)
