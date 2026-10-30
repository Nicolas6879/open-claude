"""Dos plasmodios (A, B) en el mismo medio, cada uno con sus propias conductividades D^s y sus propios nodos comida.
Parametros de interaccion:
  lam  (permeabilidad): la especie s puede usar los tubos de la otra con eficacia lam (conductancia efectiva (D^s + lam D^s')/L).
  mu   (reciprocidad): fraccion del refuerzo que recibe el tubo ANFITRION por el flujo del invitado (0 = parasitismo puro,
       1 = el flujo del invitado engorda el tubo del anfitrion igual que el suyo).
El flujo de s por una arista se reparte entre su tubo (fraccion phi = D^s/(D^s+lam D^s')) y el tubo de la otra especie.
  dD^s/dt = mean_pares f(|Q^s| phi^s) + mu * mean_pares f(|Q^s'| (1-phi^s')) - D^s
(modelo de juguete mio: las reglas de interaccion son SUPUESTO; lo medido es lo que implican.)
"""
import numpy as np
from .physarum import allpairs_flows, f_resp


def compete(n, edges, L, foodsA, foodsB, gamma, lam, mu, T=150.0, dt=0.25, DA0=1.0, DB0=1.0, kind="sat", tol=1e-6):
    edges = np.asarray(edges, int)
    DA = np.full(len(L), float(DA0))
    DB = np.full(len(L), float(DB0))
    t = 0.0
    for k in range(int(T / dt)):
        QA = np.abs(allpairs_flows(n, edges, L, DA + lam * DB, foodsA, floor=1e-9))
        QB = np.abs(allpairs_flows(n, edges, L, DB + lam * DA, foodsB, floor=1e-9)) if lam > 0 or True else None
        phiA = DA / (DA + lam * DB + 1e-12)
        phiB = DB / (DB + lam * DA + 1e-12)
        own_A = f_resp(QA * phiA[:, None], gamma, kind).mean(1)
        own_B = f_resp(QB * phiB[:, None], gamma, kind).mean(1)
        gst_A = f_resp(QA * (1 - phiA)[:, None], gamma, kind).mean(1)    # flujo de A que va por tubos de B
        gst_B = f_resp(QB * (1 - phiB)[:, None], gamma, kind).mean(1)    # flujo de B que va por tubos de A
        dA = own_A + mu * gst_B - DA
        dB = own_B + mu * gst_A - DB
        DA, DB = DA + dt * dA, DB + dt * dB
        t += dt
        if max(np.abs(dA).max(), np.abs(dB).max()) < tol:
            break
    return DA, DB, dict(t=t, converged=bool(max(np.abs(dA).max(), np.abs(dB).max()) < tol))
