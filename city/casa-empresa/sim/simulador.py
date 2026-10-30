"""Simulador de Monte Carlo del modelo de negocio de Mosquita.

Modelo semanal por cohortes, vectorizado sobre N trayectorias. Todo es SIMULACION:
los parametros vienen de supuestos.json (etiquetados como supuestos) y no hay
ninguna medicion de mercado detras. Solo depende de numpy.

Uso:  PYTHONDONTWRITEBYTECODE=1 python3 simulador.py [--n 4000] [--out out/resultados.json]
"""
import argparse
import json
import math
import os

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))


def cargar_supuestos(ruta=None):
    ruta = ruta or os.path.join(HERE, "supuestos.json")
    with open(ruta, encoding="utf-8") as f:
        return json.load(f)


def muestrea(R, spec, n):
    """Muestra n valores de una distribucion declarada en supuestos.json."""
    if spec["dist"] == "tri":
        if spec["max"] <= spec["min"]:
            return np.full(n, float(spec["min"]))   # valor fijo declarado
        return R.triangular(spec["min"], spec["moda"], spec["max"], size=n)
    if spec["dist"] == "lognorm":
        return spec["mediana"] * np.exp(spec["sigma"] * R.standard_normal(n))
    raise ValueError("dist desconocida: %s" % spec["dist"])


def muestra_parametros(sup, n, R):
    """Matriz de parametros por trayectoria: dict nombre -> array (n,)."""
    return {k: muestrea(R, v, n) for k, v in sup["parametros"].items()}


def simula(par, presupuesto_semana, aula, T=156, seed=0):
    """Corre T semanas para todas las trayectorias. Devuelve dict de series (n, T)."""
    n = len(next(iter(par.values())))
    R = np.random.default_rng(seed + 1)
    t_idx = np.arange(T)
    # Pw[i, k] = (1+k)^(-b_i): kernel de retencion por trayectoria
    logk = np.log1p(t_idx)
    Pw = np.exp(-par["retencion_b"][:, None] * logk[None, :])
    cc = par["retencion_c"]

    inst = np.zeros((n, T))           # instalaciones por semana
    act = np.zeros((n, T))            # usuarios activos por semana
    pagos_lab = np.zeros((n, T))      # suscriptores Laboratorio (stock)
    escuelas = np.zeros((n, T))       # aulas activas (stock)
    ing = {k: np.zeros((n, T)) for k in ("lab", "cosm", "aula")}
    cost = {k: np.zeros((n, T)) for k in ("fee", "soporte", "alojamiento", "equipo", "marketing")}
    paid_inst = np.zeros((n, T))
    activ = par["activacion"]
    mes_sem = 1.0 / 4.33

    lab_stock = np.zeros(n)
    esc_stock = np.zeros(n)
    adquiridos = np.zeros(n)          # suscriptores del Laboratorio que entran (acumulado, antes de abandonar)
    for t in range(T):
        k_viral = par["regalo_prob"] * par["regalo_aceptacion"] * par["abandono_final"]
        viral = k_viral * act[:, t - 1] if t > 0 else 0.0
        org = muestrea_org(par, R, n)
        pag = presupuesto_semana / par["cpi_usd"]
        paid_inst[:, t] = pag
        inst[:, t] = org + viral + pag
        # activos de esta semana: cada cohorte c aporta activacion * c * (1+k)^-b, k=t-c
        if t == 0:
            act[:, t] = inst[:, 0] * activ * cc * Pw[:, 0]
        else:
            ks = t - t_idx[: t + 1]                      # k para c=0..t
            contrib = inst[:, : t + 1] * Pw[:, ks]       # (n, t+1)
            act[:, t] = (contrib.sum(axis=1)) * activ * cc
        act[:, t] = np.maximum(act[:, t], 0.0)

        # suscriptores del Laboratorio
        nuevos = par["lab_conversion_semana"] * act[:, t]
        adquiridos += nuevos
        lab_stock = lab_stock * (1 - par["lab_abandono_semana"]) + nuevos
        pagos_lab[:, t] = lab_stock
        precio_lab_sem = par["lab_precio_mes_efectivo"] * mes_sem
        ing["lab"][:, t] = lab_stock * precio_lab_sem

        # cosmeticos (compra unica)
        ing["cosm"][:, t] = act[:, t] * par["cosmeticos_compra_semana"] * par["cosmeticos_precio"]

        # aulas (si el escenario las incluye)
        if aula:
            nuevas = R.poisson(par["aula_ventas_semana"] * 1.0)
            esc_stock = esc_stock * (1 - par["aula_abandono_anio"] / 52.0) + nuevas
            escuelas[:, t] = esc_stock
            ing["aula"][:, t] = esc_stock * par["aula_precio_anio"] / 52.0

        ingreso = ing["lab"][:, t] + ing["cosm"][:, t] + ing["aula"][:, t]
        cost["fee"][:, t] = ingreso * par["comision_pago"]
        cost["soporte"][:, t] = lab_stock * par["soporte_por_pago_semana"]
        cost["alojamiento"][:, t] = par["alojamiento_mes_usd"] * mes_sem
        cost["equipo"][:, t] = par["equipo_mes_usd"] * mes_sem
        cost["marketing"][:, t] = presupuesto_semana * np.ones(n)

    ingreso_total = sum(ing[k] for k in ing)
    coste_total = sum(cost[k] for k in cost)
    margen = ingreso_total - coste_total
    return {
        "activos": act, "instalaciones": inst, "paid_instalaciones": paid_inst,
        "lab_suscriptores": pagos_lab, "aulas": escuelas,
        "ingreso": ingreso_total, "coste": coste_total, "margen_semanal": margen, "suscriptores_adquiridos": adquiridos,
        "margen_acumulado": np.cumsum(margen, axis=1),
        "ingreso_por_fuente": ing, "coste_por_fuente": cost,
    }


def muestrea_org(par, R, n):
    """Instalaciones organicas semanales (constantes por trayectoria, ruido de Poisson)."""
    lam = par["instalaciones_organicas_semana"]
    return R.poisson(lam).astype(float)


def resume(res, par):
    fin = res["margen_acumulado"][:, -1]
    acum = res["margen_acumulado"]
    positivo = acum > 0
    primera_pos = np.where(positivo.any(axis=1), positivo.argmax(axis=1), -1)
    gasto = res["coste_por_fuente"]["marketing"].sum(axis=1)
    lab_total = res["lab_suscriptores"][:, -1]
    adq = res["suscriptores_adquiridos"]
    # Margen por suscriptor del Laboratorio y semana, y vida media (1/abandono semanas)
    margen_sus = (par["lab_precio_mes_efectivo"] / 4.33) * (1 - par["comision_pago"]) - par["soporte_por_pago_semana"]
    ltv = margen_sus / par["lab_abandono_semana"]
    # Dos denominadores, con definicion explicita:
    #  - por suscriptor ADQUIRIDO: gasto total / suscriptores que entran en toda la simulacion (incluye organicos y virales)
    #  - por suscriptor en STOCK FINAL: gasto total / suscriptores vivos al final (sobrestima el coste: quedan fuera los que abandonaron)
    cac_adq = np.where(adq > 0, gasto / np.maximum(adq, 1e-9), np.nan)
    cac_stock = np.where(lab_total > 0, gasto / np.maximum(lab_total, 1), np.nan)
    return {
        "margen_final_mediana": float(np.median(fin)),
        "margen_final_p10": float(np.percentile(fin, 10)),
        "margen_final_p90": float(np.percentile(fin, 90)),
        "prob_margen_final_negativo": float(np.mean(fin < 0)),
        "prob_margen_positivo_en_algun_momento": float(np.mean(positivo.any(axis=1))),
        "semana_recuperacion_mediana": float(np.median(primera_pos[primera_pos >= 0])) if (primera_pos >= 0).any() else None,
        "suscriptores_lab_final_mediana": float(np.median(lab_total)),
        "aulas_final_mediana": float(np.median(res["aulas"][:, -1])),
        "ltv_suscriptor_lab_mediana": float(np.median(ltv)),
        "gasto_marketing_mediana": float(np.median(gasto)),
        "suscriptores_adquiridos_mediana": float(np.median(adq)),
        "coste_por_suscriptor_adquirido_mediana": float(np.nanmedian(cac_adq)) if np.isfinite(cac_adq).any() else None,
        "coste_por_suscriptor_stock_final_mediana": float(np.nanmedian(cac_stock)) if np.isfinite(cac_stock).any() else None,
        "nota_denominadores": "gasto/adquiridos: denominador = todos los suscriptores que entran (incluye organicos y virales; es una cota inferior del coste pagado por suscriptor). gasto/stock final: denominador = suscriptores vivos al final (sobrestima).",
    }


def con_overrides(sup, overrides):
    """Copia de supuestos con sobreescrituras declaradas (solo para escenarios de rediseno)."""
    nuevo = json.loads(json.dumps(sup))
    for k, v in (overrides or {}).items():
        nuevo["parametros"][k] = v
    return nuevo


def sensibilidad(sup, n, seed, presupuesto, aula, T):
    """Correlacion de rango (Spearman) entre cada supuesto y el margen final."""
    R = np.random.default_rng(seed)
    par = muestra_parametros(sup, n, R)
    res = simula(par, presupuesto, aula, T=T, seed=seed)
    y = res["margen_acumulado"][:, -1]
    ry = np.argsort(np.argsort(y))
    out = {}
    for k, v in par.items():
        rx = np.argsort(np.argsort(v))
        out[k] = float(np.corrcoef(rx, ry)[0, 1])
    return dict(sorted(out.items(), key=lambda kv: -abs(kv[1])))


def mapa_aula(sup, n, seed, T):
    """Decision: probabilidad de perdida y margen mediano segun ventas de aulas por semana
    (filas) y coste mensual de equipo (columnas). Resto de supuestos muestreados."""
    ventas = [0.05, 0.10, 0.20, 0.30, 0.50, 0.80]
    equipo = [0, 500, 1000, 1500, 2500]
    P_loss = np.zeros((len(ventas), len(equipo)))
    M_med = np.zeros_like(P_loss)
    R = np.random.default_rng(seed)
    for i, v in enumerate(ventas):
        for j, e in enumerate(equipo):
            par = muestra_parametros(sup, n, R)
            par["aula_ventas_semana"] = np.full(n, v)
            par["equipo_mes_usd"] = np.full(n, float(e))
            par["aula_ventas_semana"] = np.full(n, v)
            res = simula(par, 0, True, T=T, seed=seed + 11 * i + j)
            fin = res["margen_acumulado"][:, -1]
            P_loss[i, j] = np.mean(fin < 0)
            M_med[i, j] = np.median(fin)
    return {"aulas_por_semana": ventas, "equipo_mes_usd": equipo,
            "prob_perdida": P_loss.round(3).tolist(), "margen_final_mediana": M_med.round(0).tolist()}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=None)
    ap.add_argument("--out", default=os.path.join(HERE, "out", "resultados.json"))
    ap.add_argument("--rapido", action="store_true", help="menos trayectorias (para pruebas)")
    args = ap.parse_args()
    sup = cargar_supuestos()
    n = args.n or (300 if args.rapido else sup["trayectorias"])
    T = sup["horizonte_semanas"]
    seed = sup["semilla"]
    resultados = {"n_trayectorias": n, "horizonte_semanas": T, "semilla": seed,
                  "nota": "Resultados de SIMULACION. Los parametros son supuestos (sim/supuestos.json).",
                  "escenarios": {}}
    for nombre, esc in sup["escenarios"].items():
        sup_e = con_overrides(sup, esc.get("overrides"))
        R = np.random.default_rng(seed)
        par = muestra_parametros(sup_e, n, R)
        res = simula(par, esc["presupuesto_paid_semana"], esc["aula"], T=T, seed=seed)
        resultados["escenarios"][nombre] = {
            "descripcion": esc["descripcion"],
            "overrides": esc.get("overrides", {}),
            "resumen": resume(res, par),
            "margen_acumulado_percentiles": {
                str(p): np.percentile(res["margen_acumulado"], p, axis=0)[::13].round(0).tolist()
                for p in (10, 50, 90)},
        }
    # sensibilidad sobre el escenario D (el que contiene todos los canales)
    esc_e = sup["escenarios"]["C_aula_regalo"]
    sup_e = con_overrides(sup, esc_e.get("overrides"))
    resultados["sensibilidad_escenario_C"] = sensibilidad(sup_e, min(n, 2000), seed, 0, True, T)
    # criterio de muerte: mapa de decision de aulas (ventas frente a equipo)
    resultados["mapa_decision_aulas"] = mapa_aula(sup, min(n, 300), seed, T)
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(resultados, f, ensure_ascii=False, indent=1)
    print("escrito", args.out)


if __name__ == "__main__":
    main()
