"""Motor de simulacion: un pool, un LP (Tendera) y un mercado externo por trayectoria.

Por paso: (1) el trader de ruido opera, (2) el arbitrajista alinea el pool con el
precio externo, (3) la politica del LP decide, (4) se marca a mercado.
Todo se valora en la moneda de cuenta "y" (precio inicial P0 = 100 y por x).
HODL de referencia: mismo capital inicial (CAP_X de x y CAP_Y de y), sin tocarlo.
"""
import math
import random

from amm import Pool
from agentes import arbitrar, TraderRuido

PASOS = 720          # 30 dias de pasos horarios
P0 = 100.0           # precio inicial (y por x)
CAP_X = 1000.0       # capital de Tendera en x
CAP_Y = CAP_X * P0   # capital de Tendera en y (valor inicial 200 000)
MERCADO = 4.0        # el resto del mercado aporta 4x el capital de Tendera (cuota 20%)
DUENO_MERCADO = "mercado"
DUENO_TENDERA = "tendera"


def _mdd(valores):
    pico = valores[0]
    peor = 0.0
    for v in valores:
        if v > pico:
            pico = v
        if pico > 0:
            peor = max(peor, (pico - v) / pico)
    return peor


def hodl(precios):
    """Mantener el capital inicial sin tocarlo. Devuelve valor final y drawdown."""
    valores = [CAP_X * p + CAP_Y for p in precios]
    return {"valor_final": valores[-1], "mdd": _mdd(valores)}


TAM_RUIDO = 0.002    # importe medio del trader de ruido (fraccion de la reserva)


def correr(precios, fee, semilla_ruido, guardia=None, serie=False, tam_ruido=TAM_RUIDO):
    """Simula el pool con el LP de Tendera durante toda la trayectoria.

    guardia: None para LP pasivo, o un objeto con .decidir(ret_log, en_pool).
    serie: si True, devuelve las reservas y valores por paso.
    tam_ruido: intensidad del flujo no informado (afecta al volumen y a las comisiones).
    """
    pool = Pool(fee)
    pool.add_liquidity(DUENO_MERCADO, CAP_X * MERCADO, CAP_Y * MERCADO)
    ruido = TraderRuido(random.Random(semilla_ruido), tam_medio=tam_ruido)
    _, ux, uy = pool.add_liquidity(DUENO_TENDERA, CAP_X, CAP_Y)
    cartera = {"x": CAP_X - ux, "y": CAP_Y - uy}  # tokens no aportados (en cartera)
    en_pool = True

    p_prev = precios[0]
    valores = [CAP_X * p_prev + CAP_Y]
    rx, ry = [pool.x], [pool.y]
    fees = 0.0
    salidas = 0
    v_final = valores[0]

    for p in precios[1:]:
        frac = pool.share_of(DUENO_TENDERA)
        eventos = ruido.paso(pool) + arbitrar(pool, p)[1]
        for token, fe in eventos:
            fees += frac * (fe if token == "y" else fe * p)

        if guardia is not None:
            accion = guardia.decidir(math.log(p / p_prev), en_pool)
            if accion == "retirar":
                s = pool.shares.get(DUENO_TENDERA, 0.0)
                dx, dy = pool.remove_liquidity(DUENO_TENDERA, s)
                cartera["x"] += dx
                cartera["y"] += dy
                en_pool = False
                salidas += 1
            elif accion == "entrar" and cartera["x"] > 0 and cartera["y"] > 0:
                _, ux, uy = pool.add_liquidity(DUENO_TENDERA, cartera["x"], cartera["y"])
                cartera["x"] -= ux
                cartera["y"] -= uy
                en_pool = True
        p_prev = p

        v_final = (pool.share_of(DUENO_TENDERA) * (pool.x * p + pool.y)
                   + cartera["x"] * p + cartera["y"])
        valores.append(v_final)
        if serie:
            rx.append(pool.x)
            ry.append(pool.y)

    h_final = CAP_X * p_prev + CAP_Y
    out = {
        "valor_final": v_final,
        "hodl_final": h_final,
        "fees": fees,
        "mdd": _mdd(valores),
        "salidas": salidas,
    }
    if serie:
        out.update({"valores": valores, "reserve_x": rx, "reserve_y": ry})
    return out
