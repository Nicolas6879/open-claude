"""Mercado externo sintetico: trayectorias de precio con semilla fija.

Unidad de tiempo: 1 paso = 1 hora (8760 pasos por ano). Dos regimenes:
- GBM: movimiento browniano geometrico con volatilidad anual sigma.
- Saltos: difusion + saltos de Poisson (aprox. Bernoulli por paso, lam*dt << 1),
  con tamano de salto log-normal N(0, sigma_salto).
"""
import math
import random

PASOS_ANIO = 8760


def generar_precios(p0, sigma, pasos, semilla, lam_anual=0.0, sigma_salto=0.0, mu=0.0):
    """Devuelve una lista de pasos+1 precios. Siempre consume el mismo numero de
    aleatorios por paso, para que las trayectorias con igual semilla sean comparables."""
    rng = random.Random(semilla)
    dt = 1.0 / PASOS_ANIO
    p_salto = lam_anual * dt
    precios = [p0]
    p = p0
    for _ in range(pasos):
        z = rng.gauss(0.0, 1.0)
        u = rng.random()
        j = rng.gauss(0.0, 1.0)
        r = (mu - 0.5 * sigma * sigma) * dt + sigma * math.sqrt(dt) * z
        if u < p_salto:
            r += sigma_salto * j
        p *= math.exp(r)
        precios.append(p)
    return precios


ESCENARIOS = {
    "gbm": {
        "sigma": 0.6, "lam_anual": 0.0, "sigma_salto": 0.0,
        "nombre": "GBM, volatilidad 60% anual",
    },
    "saltos": {
        "sigma": 0.4, "lam_anual": 60.0, "sigma_salto": 0.05,
        "nombre": "Difusion 40% + saltos (60/ano, sigma 5%), vol total ~56%",
    },
}
