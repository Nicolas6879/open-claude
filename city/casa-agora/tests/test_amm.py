"""Pruebas del laboratorio AMM. Ejecutar con:  python3 tests/test_amm.py"""
import math
import os
import random
import sys
import unittest

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)

from amm import Pool  # noqa: E402
from agentes import arbitrar, TraderRuido  # noqa: E402
from mercado import generar_precios, ESCENARIOS  # noqa: E402
import simulacion as S  # noqa: E402
from estrategias import GuardiaVolatilidad  # noqa: E402


def pool_con(x, y, fee):
    p = Pool(fee)
    p.add_liquidity("init", x, y)
    return p


def clonar(p):
    q = Pool(p.fee)
    q.x, q.y, q.total_shares = p.x, p.y, p.total_shares
    q.shares = dict(p.shares)
    return q


class TestAMM(unittest.TestCase):

    def test_k_no_disminuye_con_comision(self):
        rng = random.Random(1)
        p = pool_con(1000.0, 100000.0, 0.003)
        for _ in range(200):
            k0 = p.k()
            if rng.random() < 0.5:
                p.swap_x_in(rng.uniform(0.01, 50.0))
            else:
                p.swap_y_in(rng.uniform(0.1, 5000.0))
            self.assertGreaterEqual(p.k(), k0 * (1 - 1e-12))

    def test_conservacion_sin_comision(self):
        p = pool_con(1000.0, 100000.0, 0.0)
        x0, y0, k0 = p.x, p.y, p.k()
        trader_x, trader_y = 0.0, 0.0
        dx = 25.0
        dy_out, fee = p.swap_x_in(dx)
        trader_x -= dx
        trader_y += dy_out
        self.assertEqual(fee, 0.0)
        # Los tokens se conservan: pool + trader igual al inicial.
        self.assertAlmostEqual(p.x + trader_x, x0, places=9)
        self.assertAlmostEqual(p.y + trader_y, y0, places=9)
        # Sin comision, el producto constante se mantiene exacto.
        self.assertAlmostEqual(p.k() / k0, 1.0, places=9)

    def test_swap_inverso_sin_beneficio(self):
        # Sin comision, ida y vuelta devuelve lo mismo.
        p = pool_con(1000.0, 100000.0, 0.0)
        dx = 10.0
        dy, _ = p.swap_x_in(dx)
        dx_back, _ = p.swap_y_in(dy)
        self.assertAlmostEqual(dx_back, dx, places=9)
        # Con comision, ida y vuelta siempre pierde (no hay beneficio).
        q = pool_con(1000.0, 100000.0, 0.003)
        dy, _ = q.swap_x_in(dx)
        dx_back, _ = q.swap_y_in(dy)
        self.assertLess(dx_back, dx)

    def test_arbitraje_alinea_precio(self):
        f = 0.003
        for p_ext in (110.0, 90.0):
            p = pool_con(1000.0, 100000.0, f)  # precio 100
            beneficio, _ = arbitrar(p, p_ext)
            self.assertGreaterEqual(beneficio, -1e-9)
            ratio = p.price() / p_ext
            # Tras arbitrar, el precio queda dentro de la banda sin arbitraje.
            self.assertGreaterEqual(ratio, 1 - f - 1e-9)
            self.assertLessEqual(ratio, 1 / (1 - f) + 1e-9)
            # Y ya no queda margen de arbitraje neto de comision.
            b2, ev2 = arbitrar(p, p_ext)
            self.assertEqual(ev2, [])
            self.assertEqual(b2, 0.0)

    def test_arbitraje_optimo_y_sin_operacion_dentro_de_banda(self):
        f = 0.003
        p = pool_con(1000.0, 100000.0, f)
        p_ext = 110.0

        def beneficio_con_entrada(scale):
            q = clonar(p)
            # Entrada perturbada: se compra x con y cantidad (scale * optimo).
            ybar = math.sqrt((1 - f) * q.x * q.y * p_ext)
            y_in = (ybar - q.y) / (1 - f) * scale
            x_out, _ = q.swap_y_in(y_in)
            return x_out * p_ext - y_in

        opt = beneficio_con_entrada(1.0)
        self.assertGreater(opt, 0)
        self.assertGreaterEqual(opt, beneficio_con_entrada(0.9))
        self.assertGreaterEqual(opt, beneficio_con_entrada(1.1))
        # Dentro de la banda no hay operacion.
        q = pool_con(1000.0, 100000.0, f)
        self.assertEqual(arbitrar(q, 100.1), (0.0, []))

    def test_reproducibilidad_con_semilla(self):
        e = ESCENARIOS["saltos"]
        a = generar_precios(100.0, e["sigma"], 300, 7, e["lam_anual"], e["sigma_salto"])
        b = generar_precios(100.0, e["sigma"], 300, 7, e["lam_anual"], e["sigma_salto"])
        c = generar_precios(100.0, e["sigma"], 300, 8, e["lam_anual"], e["sigma_salto"])
        self.assertEqual(a, b)
        self.assertNotEqual(a, c)
        r1 = S.correr(a, 0.003, 99)
        r2 = S.correr(b, 0.003, 99)
        self.assertEqual(r1["valor_final"], r2["valor_final"])
        self.assertEqual(r1["fees"], r2["fees"])
        # El trader de ruido tambien es reproducible.
        t1 = TraderRuido(random.Random(5))
        t2 = TraderRuido(random.Random(5))
        p1, p2 = pool_con(500.0, 50000.0, 0.003), pool_con(500.0, 50000.0, 0.003)
        for _ in range(50):
            self.assertEqual(t1.paso(p1), t2.paso(p2))
        self.assertEqual(p1.x, p2.x)

    def test_anadir_y_retirar_devuelve_lo_aportado(self):
        p = pool_con(1000.0, 100000.0, 0.003)
        dx = 37.0
        dy = dx * p.y / p.x  # aporte en proporcion al pool
        s, ux, uy = p.add_liquidity("lp", dx, dy)
        self.assertAlmostEqual(ux, dx, places=9)
        self.assertAlmostEqual(uy, dy, places=9)
        ox, oy = p.remove_liquidity("lp", s)
        self.assertAlmostEqual(ox, dx, places=9)
        self.assertAlmostEqual(oy, dy, places=9)
        self.assertAlmostEqual(p.shares.get("lp", 0.0), 0.0, places=9)
        # Un aporte no proporcional solo usa la parte que cabe.
        s2, ux2, uy2 = p.add_liquidity("lp", 10.0, 10000.0)
        self.assertLessEqual(ux2, 10.0 + 1e-12)
        self.assertAlmostEqual(uy2 / ux2, p.y / p.x, places=9)

    def test_identidad_contable_coincide_con_formula_il(self):
        # LP - HODL - comisiones debe coincidir con la formula de perdida impermanente
        # 2*sqrt(r)/(1+r) - 1 (x HODL), con error medio pequeno frente al capital.
        e = ESCENARIOS["gbm"]
        errores = []
        for s in range(60):
            pr = generar_precios(100.0, e["sigma"], S.PASOS, s)
            res = S.correr(pr, 0.003, s + 10_000_000)
            h = S.CAP_X * pr[-1] + S.CAP_Y
            r = pr[-1] / 100.0
            il = h * (2 * math.sqrt(r) / (1 + r) - 1)
            errores.append((res["valor_final"] - h - res["fees"]) - il)
        capital = 2 * S.CAP_Y
        # Error por trayectoria (medido: max ~75 sobre 200 000): tope 0.1% del capital.
        self.assertLess(max(abs(e) for e in errores), 0.001 * capital)

    def test_guardia_sale_en_volatilidad_alta_y_no_en_calma(self):
        g = GuardiaVolatilidad(salida=0.8)
        acciones = [g.decidir(0.05, True) for _ in range(60)]  # retornos enormes
        self.assertIn("retirar", acciones)
        g2 = GuardiaVolatilidad(salida=0.8)
        acciones2 = [g2.decidir(0.0005, True) for _ in range(300)]  # calma
        self.assertNotIn("retirar", acciones2)


if __name__ == "__main__":
    unittest.main(verbosity=2)
