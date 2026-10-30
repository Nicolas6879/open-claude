"""Politicas del LP. Solo deciden; simulacion.py ejecuta las acciones en el pool.

- LPPasivo: deposita al inicio y no toca nada.
- GuardiaVolatilidad (estrategia propia de Tendera): estima la volatilidad con un
  EWMA de retornos logaritmicos horarios. Si la vol. anualizada supera `salida`,
  retira toda la liquidez (queda en tokens, sin comisiones). Vuelve a entrar cuando
  baja de `salida * factor_entrada` (histeresis, para no oscilar).
  Hipotesis: la comision que cobra un LP es ~proporcional al volumen de
  arbitraje, que crece con la volatilidad, pero la perdida impermanente crece con
  la volatilidad al cuadrado. En regimenes muy volatiles conviene salir.
"""
import math


class LPPasivo:
    nombre = "LP pasivo"

    def decidir(self, ret_log, en_pool):
        return None


class GuardiaVolatilidad:
    nombre = "Tendera: guardia de volatilidad"

    def __init__(self, salida=0.8, factor_entrada=0.75, ventana_pasos=168,
                 calentamiento=24, pasos_anio=8760):
        self.salida = salida
        self.entrada = salida * factor_entrada
        self.lam = 1.0 - 2.0 / (ventana_pasos + 1.0)  # EWMA de span ventana_pasos
        self.calentamiento = calentamiento
        self.pasos_anio = pasos_anio
        self.var = None
        self.n = 0

    def sigma_hat(self):
        if self.var is None:
            return 0.0
        return math.sqrt(self.var * self.pasos_anio)

    def decidir(self, ret_log, en_pool):
        r2 = ret_log * ret_log
        self.var = r2 if self.var is None else self.lam * self.var + (1.0 - self.lam) * r2
        self.n += 1
        if self.n < self.calentamiento:
            return None
        s = self.sigma_hat()
        if en_pool and s > self.salida:
            return "retirar"
        if (not en_pool) and s < self.entrada:
            return "entrar"
        return None
