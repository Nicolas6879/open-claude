"""Agentes del mercado simulado.

(a) ArbitrajistaOptimo: en cada paso lleva el precio del pool hasta la banda sin
    arbitraje, descontando la comision. Usa la solucion cerrada del swap optimo.
(b) TraderRuido: flujo no informado, aleatorio, con semilla propia.
(c) El proveedor de liquidez pasivo del resto del mercado vive en simulacion.py
    (aporte inicial y sin acciones posteriores); el LP que estudiamos es Tendera.

Todos los eventos de comision se devuelven como (token_de_entrada, importe).
"""
import math


def arbitrar(pool, p_ext):
    """Arbitraje de una sola operacion optimo. Devuelve (beneficio_en_y, eventos).

    Banda sin arbitraje: p_ext*(1-f) <= p_pool <= p_ext/(1-f).
    - Si p_pool < p_ext*(1-f): se compra x con y. Maximizar
      p_ext*x_out(y_in) - y_in da Ybar^2 = (1-f)*x*y*p_ext, con
      y_in = (Ybar - y)/(1-f).
    - Si p_pool > p_ext/(1-f): se vende x. Simetrico: Xbar^2 = (1-f)*x*y/p_ext,
      x_in = (Xbar - x)/(1-f).
    """
    f = pool.fee
    x, y = pool.x, pool.y
    p_pool = y / x
    if p_pool < p_ext * (1.0 - f):
        ybar = math.sqrt((1.0 - f) * x * y * p_ext)
        y_in = (ybar - y) / (1.0 - f)
        x_out, fee = pool.swap_y_in(y_in)
        return x_out * p_ext - y_in, [("y", fee)]
    if p_pool > p_ext / (1.0 - f):
        xbar = math.sqrt((1.0 - f) * x * y / p_ext)
        x_in = (xbar - x) / (1.0 - f)
        y_out, fee = pool.swap_x_in(x_in)
        return y_out - x_in * p_ext, [("x", fee)]
    return 0.0, []


class TraderRuido:
    """Con probabilidad `prob` por paso compra o vende x (50/50) por un importe
    exponencial de media `tam_medio` veces la reserva de entrada. Siempre consume
    tres aleatorios por paso (aunque no opere) para mantener alineados los flujos
    entre estrategias que comparten semilla."""

    def __init__(self, rng, prob=0.5, tam_medio=0.002):
        self.rng = rng
        self.prob = prob
        self.tam_medio = tam_medio

    def paso(self, pool):
        u = self.rng.random()
        lado = self.rng.random()
        e = self.rng.expovariate(1.0)
        if u >= self.prob:
            return []
        if lado < 0.5:
            _, fee = pool.swap_y_in(pool.y * self.tam_medio * e)
            return [("y", fee)]
        _, fee = pool.swap_x_in(pool.x * self.tam_medio * e)
        return [("x", fee)]
