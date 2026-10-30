"""Auditor: comprueba cifras del negocio de casa-empresa ejecutando SU simulador (en una copia) y calculando yo
las metricas que importan: (1) umbral '3,7x la demanda base ~ 150 instalaciones/semana': factor aplicado a TODA la demanda
(4 parametros a la vez) frente a SOLO instalaciones; (2) 'cada suscriptor cuesta ~370 USD': coste por suscriptor
usando el stock final (lo que hace el codigo) frente a suscriptores adquiridos acumulados; (3) k del bucle viral.
Uso: python v_empresa_sim.py <ruta casa-empresa>"""
import sys, os, numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from veredicto import check, resumen
sys.path.insert(0, os.path.join(sys.argv[1], "sim")); import simulador as S
sup = S.cargar_supuestos(); seed = sup["semilla"]; n = 2000
DEM = ["instalaciones_organicas_semana", "lab_conversion_semana", "cosmeticos_compra_semana", "aula_ventas_semana"]
def mm(claves, m):
    R = np.random.default_rng(seed); par = S.muestra_parametros(sup, n, R)
    for k in claves: par[k] = par[k] * m
    res = S.simula(par, 0, True, T=156, seed=seed); return float(np.median(res["margen_semanal"][:, -52:].sum(axis=1) / 12.0))
print("margen mensual mediano, anio 3 (escenario C, equipo 0), n=%d" % n)
print("%6s %14s %14s" % ("m", "toda demanda", "solo install."))
for m in (1, 2, 3, 3.5, 3.7, 4, 5, 8, 10, 14, 15, 20):
    print("%6s %14.0f %14.0f" % (m, mm(DEM, m), mm(["instalaciones_organicas_semana"], m)))
# cruce de 1000 por bisección
def cruce(claves):
    lo, hi = 1.0, 60.0
    for _ in range(14):
        mid = (lo + hi) / 2
        if mm(claves, mid) < 1000: lo = mid
        else: hi = mid
    return hi
c_all, c_inst = cruce(DEM), cruce(["instalaciones_organicas_semana"])
print("factor que alcanza 1000 USD/mes: toda la demanda %.2f (=%.0f inst/sem) | solo instalaciones %.1f (=%.0f inst/sem)  [declarado: 3,7x = ~150 inst/sem]" % (c_all, 40 * c_all, c_inst, 40 * c_inst))
# CAC
R = np.random.default_rng(seed); par = S.muestra_parametros(sup, n, R)
res = S.simula(par, 750, False, T=156, seed=seed)
gasto = res["coste_por_fuente"]["marketing"].sum(axis=1); stock = res["lab_suscriptores"][:, -1]
adquiridos = (par["lab_conversion_semana"][:, None] * res["activos"]).sum(axis=1)
print("escenario B (paid 3000/mes): coste/suscriptor con stock final (codigo) mediana %.0f | con suscriptores adquiridos acumulados mediana %.0f | adquiridos/stock mediana %.1f" % (np.median(gasto / stock), np.median(gasto / adquiridos), np.median(adquiridos / stock)))
mar = (par["lab_precio_mes_efectivo"] / 4.33) * (1 - par["comision_pago"]) - par["soporte_por_pago_semana"]
print("LTV suscriptor mediana %.1f USD (margen semanal/abandono)" % np.median(mar / par["lab_abandono_semana"]))
# viral
b, c = 0.5, 0.5; L = float(np.sum(c * (1 + np.arange(156)) ** (-b))); k = 0.4 * 0.25 * 0.1 * L
print("L=%.2f k por usuaria activa=%.3f ; por instalacion (x activacion .45)=%.3f ; aceptacion critica k=1: %.2f" % (L, k, k * 0.45, 1 / (0.4 * 0.1 * L)))

# --- cifras del README (escenarios, 4000 trayectorias, semilla de supuestos.json)
decl = {"A_organico_regalo": (345, 0.41), "C_aula_regalo": (1437, 0.14), "B_paid": (-95800, 0.98), "E_aula_equipo_1500": (-52600, 1.0)}
for nombre, (med, pl) in decl.items():
    esc = sup["escenarios"][nombre]; se = S.con_overrides(sup, esc.get("overrides")); R = np.random.default_rng(seed)
    par = S.muestra_parametros(se, sup["trayectorias"], R); res = S.simula(par, esc["presupuesto_paid_semana"], esc["aula"], T=156, seed=seed); r = S.resume(res, par)
    check(nombre + " margen mediano", r["margen_final_mediana"], med, 0.0015 * abs(med) + 1); check(nombre + " P(perdida)", r["prob_margen_final_negativo"], pl, 0.006)
    if nombre == "B_paid": check("B_paid coste por suscriptor (README ~370), definicion del codigo (gasto/stock final)", r["coste_por_suscriptor_mediana"], 370, 1)
check("umbral 'toda la demanda' (README 3,7x)", c_all, 3.7, 0.2); check("README: ~150 inst/sem para 1000 USD/mes -> recomputado con SOLO instalaciones", 40 * c_inst, 150, 10, nota="<- el 3,7x multiplica 4 parametros a la vez")
check("coste por suscriptor con adquiridos acumulados (README 370)", float(np.median(gasto / adquiridos)), 370, 20, nota="<- cada suscriptor adquirido, no el stock final")
check("k por usuaria", k, 0.12, 0.005); check("aceptacion critica k=1", 1 / (0.4 * 0.1 * L), 2.1, 0.05)
sys.exit(1 if resumen() else 0)
