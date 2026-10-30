import hashlib
import sys
import unittest
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import sonificar as S  # noqa: E402


class T(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.d, cls.tipo, cls.kc = S.cargar()

    def test_determinista_y_sin_saturar(self):
        a = S.sintetizar(self.d, self.tipo, self.kc)
        b = S.sintetizar(self.d, self.tipo, self.kc)
        self.assertEqual(hashlib.sha1(a.tobytes()).hexdigest(), hashlib.sha1(b.tobytes()).hexdigest())
        self.assertLessEqual(float(np.abs(a).max()), 0.9 + 1e-6)
        self.assertAlmostEqual(len(a) / S.SR, self.d["meta"]["duration_ms"] / 1000 * S.ESTIRA + 3.0, delta=0.1)

    def test_el_canal_de_campanas_lleva_el_dato(self):
        """Solo MBON: la energía de las campanas debe seguir el recuento de espigas del dato."""
        y = S.sintetizar(self.d, self.tipo, self.kc, solo={"MBON"})
        eA = S.energia_campanas(y, self.d, self.tipo, "post_A", (150, 3000)) / S.energia_campanas(y, self.d, self.tipo, "pre_A", (150, 3000))
        eB = S.energia_campanas(y, self.d, self.tipo, "post_B", (150, 3000)) / S.energia_campanas(y, self.d, self.tipo, "pre_B", (150, 3000))
        nA = S.espigas_en(self.d, self.tipo, "MBON", "post_A") / S.espigas_en(self.d, self.tipo, "MBON", "pre_A")
        nB = S.espigas_en(self.d, self.tipo, "MBON", "post_B") / S.espigas_en(self.d, self.tipo, "MBON", "pre_B")
        self.assertLess(nA, nB)                       # el dato: A baja más que B
        self.assertLess(eA, eB)                       # el sonido lo conserva
        self.assertLess(eA, 0.6)
        self.assertAlmostEqual(eA, nA, delta=0.15)    # y con una magnitud parecida
        print(f"  espigas MBON A {nA:.2f}  B {nB:.2f} | energía de campanas A {eA:.2f}  B {eB:.2f}")

    def test_un_error_inyectado_se_detecta(self):
        """Si se borran las espigas de MBON de post_A, el comprobador debe verlo como una caída enorme."""
        import copy
        d2 = copy.deepcopy(self.d)
        est = next(s for s in d2["stimuli"] if s["name"] == "post_A")
        d2["spikes"] = [s for s in d2["spikes"] if not (self.tipo[s[1]] == "MBON" and est["t_start"] <= s[0] < est["t_end"])]
        y = S.sintetizar(d2, self.tipo, self.kc, solo={"MBON"})
        e = S.energia_campanas(y, d2, self.tipo, "post_A", (150, 3000)) / S.energia_campanas(y, d2, self.tipo, "pre_A", (150, 3000))
        self.assertLess(e, 0.15)


if __name__ == "__main__":
    unittest.main(verbosity=1)
