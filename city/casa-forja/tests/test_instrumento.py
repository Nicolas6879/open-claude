"""Pruebas del instrumento. Ejecutar: python3 tests/test_instrumento.py  (con el python del venv).

Cubren: causalidad de las senales, contabilidad de costes, bootstrap, Sharpe deflactado,
BH y tamano de la SPA con ruido puro (la prueba que importa: no debe encontrar nada).
"""
import math
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from cazador import motor as M  # noqa: E402
from cazador import senales as S  # noqa: E402


class TestCausalidad(unittest.TestCase):
    """Cambiar precios posteriores a t0 no debe cambiar los pesos hasta t0-1 (ni en t0 - 1 y t0 - 2)."""

    @classmethod
    def setUpClass(cls):
        rng = np.random.default_rng(3)
        T = 900
        r = rng.normal(0.0003, 0.01, T)
        cls.precio = 100 * np.cumprod(1 + r)
        cls.fechas = pd.bdate_range("2001-01-01", periods=T)
        cls.t0 = 600
        p2 = cls.precio.copy()
        p2[cls.t0:] = p2[cls.t0:] * np.exp(rng.normal(0, 0.2, T - cls.t0))  # futuro distinto
        cls.precio2 = p2

    def _pesos(self, precio):
        f = S.familias_diarias(precio, self.fechas[: len(precio)])
        return {(a, b): w for a, b, w in f}

    def test_familias_precio_sin_mirar_futuro(self):
        full = self._pesos(self.precio)
        otra = self._pesos(self.precio2)
        malas = []
        for clave, w in full.items():
            if clave[0] == "estacional":
                continue  # calendario conocido de antemano: se comprueba en test_calendario
            w2 = otra[clave]
            if not np.allclose(w[: self.t0 - 1], w2[: self.t0 - 1], equal_nan=True, atol=1e-9):
                malas.append(clave)
        self.assertEqual(malas, [], f"Estas senales usan informacion futura: {malas}")

    def test_calendario_solo_depende_del_calendario(self):
        full = self._pesos(self.precio)
        otra = self._pesos(self.precio2)
        for clave, w in full.items():
            if clave[0] != "estacional":
                continue
            self.assertTrue(np.allclose(w, otra[clave]), clave)

    def test_motor_aplica_pesos_al_periodo_siguiente(self):
        # Peso 1 solo en t=5. Debe ganar el retorno de t=6, no el de t=5.
        T = 10
        W = np.zeros((1, 1, T))
        W[0, 0, 5] = 1.0
        R = np.zeros((1, T))
        R[0, 5] = 0.10   # retorno que NO debe capturarse
        R[0, 6] = 0.02   # retorno que SI
        rf = np.zeros(T)
        net, Wh = M.retornos_netos(W, R, rf, 252, 0.0, 0.0)
        self.assertAlmostEqual(net[0, 6], 0.02)
        self.assertAlmostEqual(net[0, 5], 0.0)


class TestCostes(unittest.TestCase):
    def test_coste_proporcional_a_rotacion(self):
        T = 6
        W = np.zeros((1, 1, T))
        W[0, 0, 1:] = 1.0            # compra en t=0 -> posicion 1 desde t=1
        W[0, 0, 4:] = 0.0            # venta en t=3 -> posicion 0 desde t=4
        R = np.full((1, T), 0.0)
        rf = np.zeros(T)
        net, Wh = M.retornos_netos(W, R, rf, 252, 10.0, 0.0)  # 10 bps por lado
        # La orden decidida en t=0 entra en el periodo 2 (W[1]=1 -> Wh[2]=1) y la de t=3 en el 5.
        # Ida y vuelta = 2 unidades de rotacion = 20 bps en total.
        self.assertAlmostEqual(net[0, 2], -0.0010)
        self.assertAlmostEqual(net[0, 5], -0.0010)
        self.assertAlmostEqual(net.sum(), -0.0020)

    def test_financiacion_con_apalancamiento(self):
        T = 4
        W = np.full((1, 1, T), 2.0)
        R = np.zeros((1, T))
        rf = np.zeros(T)
        net, _ = M.retornos_netos(W, R, rf, 252, 0.0, 0.01)  # 1% anual sobre el exceso de 1
        self.assertAlmostEqual(net[0, 2], -0.01 / 252)

    def test_fijo_por_periodo(self):
        T = 5
        W = np.ones((1, 2, T))
        R = np.zeros((2, T))
        rf = np.zeros(T)
        net, _ = M.retornos_netos(W, R, rf, 252, 0.0, 0.0, coste_fijo_bps=10.0)
        self.assertAlmostEqual(net[0, 3], -0.0010)


class TestBootstrap(unittest.TestCase):
    def test_indices_validos_y_longitud_media_de_bloque(self):
        rng = np.random.default_rng(1)
        T, L = 4000, 20
        idx = M.indices_bootstrap(T, 50, L, rng)
        self.assertTrue(idx.min() >= 0 and idx.max() < T)
        # Un bloque termina cuando idx[t+1] != idx[t] + 1 (mod T)
        saltos = (idx[:, 1:] != (idx[:, :-1] + 1) % T).mean()
        self.assertAlmostEqual(saltos, 1.0 / L, delta=0.01)

    def test_medias_bootstrap_coinciden_con_remuestreo_directo(self):
        rng = np.random.default_rng(2)
        D = rng.normal(size=(3, 300))
        idx = M.indices_bootstrap(300, 20, 10, rng)
        via_conteos = M.medias_bootstrap(D, idx)
        directo = np.stack([D[:, idx[b]].mean(axis=1) for b in range(20)], axis=1)
        self.assertTrue(np.allclose(via_conteos, directo))


class TestEstadistica(unittest.TestCase):
    def test_psr_y_dsr_basicos(self):
        self.assertAlmostEqual(float(M.psr(0.0, 1000, 0.0, 3.0, 0.0)), 0.5)
        self.assertAlmostEqual(M.sr_umbral_dsr(0.01, 1), 0.0)
        self.assertGreater(M.sr_umbral_dsr(0.01, 100), M.sr_umbral_dsr(0.01, 10))

    def test_dsr_penaliza_mas_con_mas_pruebas(self):
        rng = np.random.default_rng(5)
        x = rng.normal(0.0003, 0.01, size=(1, 1500))
        ruido = rng.normal(0.0, 0.01, size=(199, 1500))
        todas = np.vstack([x, ruido])
        _, _, dsr_1, _ = M.deflated_sharpe(x)
        _, _, dsr_200, _ = M.deflated_sharpe(todas)
        self.assertGreater(dsr_1[0], dsr_200[0])

    def test_bh_clasico(self):
        p = np.array([0.001, 0.008, 0.039, 0.041, 0.6])
        rech = M.benjamini_hochberg(p, 0.05)
        self.assertEqual(rech.tolist(), [True, True, False, False, False])

    def test_spa_no_encuentra_nada_en_ruido(self):
        """Tamano: con 25 configuraciones de ruido puro, p<0.10 debe pasar ~10% de las veces."""
        rng = np.random.default_rng(11)
        reps, hits_spa, hits_rc = 120, 0, 0
        for _ in range(reps):
            D = rng.normal(0.0, 0.01, size=(25, 1000))
            idx = M.indices_bootstrap(1000, 300, 1, rng)     # iid
            out = M.reality_check_y_spa(D, idx)
            hits_spa += out["p_spa"] < 0.10
            hits_rc += out["p_rc"] < 0.10
        self.assertLess(hits_spa / reps, 0.20, "SPA demasiado liberal con ruido")
        self.assertLess(hits_rc / reps, 0.25, "RC demasiado liberal con ruido")


if __name__ == "__main__":
    unittest.main(verbosity=2)
