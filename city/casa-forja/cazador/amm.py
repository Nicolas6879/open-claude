"""Proveedor de liquidez tipo Uniswap v2 (x*y=k) sobre precios REALES. Solo contabilidad.

No es una prueba estadistica de direccion: es una identidad. Para cada serie calcula:
- Perdida impermanente (IL) sin comisiones: V_LP / V_HODL - 1.
- Umbral de comisiones: la rotacion diaria (volumen / TVL) tau* que hace que LP = HODL al final.
  Si tau* es alto respecto a lo que aguanta un pool real, ser LP no compensa.

Supuestos (de memoria, declarados): comision 0,30 % sobre el volumen (nivel de Uniswap v2);
volumen en proporcion constante al TVL (tau); sin apalancamiento ni rebalanceo.
"""
import math

import numpy as np

FEE = 0.003


def trayectoria_lp_hodl(precio, V0=1.0):
    """Devuelve (V_lp, V_hodl) en unidades de cotizacion sin comisiones."""
    p = np.asarray(precio, float)
    p0 = p[0]
    k = (V0 / 2 / p0) * (V0 / 2)           # x0 * y0
    V_lp = 2.0 * np.sqrt(k * p)            # valor del pool sin comisiones (en cotizacion)
    V_h = (V0 / 2) * (p / p0) + V0 / 2     # 50 % base + 50 % cotizacion, sin rebalanceo
    return V_lp, V_h


def umbral_rotacion(precio, fee=FEE, periodos_anuales=252.0):
    """tau* por periodo: rotacion (volumen/TVL) necesaria para igualar HODL al final."""
    V_lp, V_h = trayectoria_lp_hodl(precio)
    n = len(V_lp) - 1
    ingreso_base = np.sum(V_lp[:-1])        # TVL acumulado sobre el que se cobra la comision
    deficit = V_h[-1] - V_lp[-1]
    tau = deficit / (fee * ingreso_base) if deficit > 0 else 0.0
    anios = n / periodos_anuales
    return dict(
        IL_sin_comisiones=float(V_lp[-1] / V_h[-1] - 1.0),
        tau_por_periodo=float(tau),
        rotacion_anual_necesaria=float(tau * periodos_anuales),          # volumen/TVL al año
        apr_comisiones_necesario=float(tau * fee * periodos_anuales),    # fraccion de TVL al año
        periodos=int(n),
        anios=float(anios),
        vol_anual_precio=float(np.std(np.diff(np.log(p_safe(precio))), ddof=1)
                               * math.sqrt(periodos_anuales)),
    )


def p_safe(precio):
    return np.asarray(precio, float)


def curva_comisiones(precio, fees=(0.0005, 0.001, 0.003, 0.01), periodos_anuales=252.0):
    """Para varias comisiones, rotacion diaria necesaria para no perder frente a HODL."""
    return {str(f): umbral_rotacion(precio, f, periodos_anuales)["tau_por_periodo"] for f in fees}
