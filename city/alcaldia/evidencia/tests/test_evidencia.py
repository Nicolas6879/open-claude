import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from evidencia import ErrorEvidencia, Programa  # noqa: E402

AQUI = Path(__file__).resolve().parents[1]


def corre(t):
    return Programa().correr(t)


class T(unittest.TestCase):
    def test_garantizada_y_refutada(self):
        r = corre("medido a = 3\nmedido b = 5\nafirmar a < b\nafirmar a > b")
        self.assertEqual([x["veredicto"] for x in r], ["GARANTIZADA", "REFUTADA"])

    def test_condicional_con_contraejemplo(self):
        r = corre("supuesto x en [-1, 1]\nafirmar x > 0")[0]
        self.assertEqual(r["veredicto"], "CONDICIONAL")
        self.assertLess(r["contraejemplo"]["x"], 0.0 + 1e-12)
        self.assertTrue(0.4 < r["fraccion_que_cumple"] < 0.6)

    def test_eslabon_mas_debil(self):
        r = corre("medido a = 2\nsupuesto s = 1 en [1, 2]\nno_verificado n = 1\ndef c = a * s + n\nafirmar c > 0")[0]
        self.assertEqual(r["etiqueta"], "no_verificado")
        r = corre("medido a = 2\nsupuesto s = 1 en [1, 2]\ndef c = a * s\nafirmar c > 0")[0]
        self.assertEqual(r["etiqueta"], "supuesto")
        r = corre("medido a = 2\nafirmar a > 0")[0]
        self.assertEqual(r["etiqueta"], "medido")

    def test_error_estandar_y_signo(self):
        r = corre("medido g = -29 ± 23\nafirmar g < 0")[0]
        self.assertEqual(r["veredicto"], "GARANTIZADA")
        r = corre("medido g = -29 ± 46\nafirmar g < 0")[0]
        self.assertEqual(r["veredicto"], "CONDICIONAL")

    def test_dependencia_repetida_no_da_falsa_garantia_ni_falsa_refutacion(self):
        # x - x == 0 siempre: la comparación se evalúa sobre (a-b), pero x aparece dos veces en el intervalo.
        r = corre("supuesto x = 1 en [1, 2]\nafirmar x - x == 0")[0]
        self.assertIn(r["veredicto"], ("CONDICIONAL", "NO_REFUTADA", "GARANTIZADA"))
        self.assertNotEqual(r["veredicto"], "REFUTADA")

    def test_determinismo(self):
        t = "supuesto x = 0 en [0, 10]\nsupuesto y = 0 en [0, 10]\nafirmar x * y > 20"
        self.assertEqual(corre(t), corre(t))

    def test_errores_de_sintaxis_y_semantica(self):
        for t in ("supuesto x\n", "medido a = \n", "afirmar b > 1\n", "medido a = 1 @\n",
                  "medido a = 1\ndef c = a / (a - 1)\n", "foo a = 1\n"):
            with self.assertRaises(ErrorEvidencia, msg=t):
                corre(t)

    def test_ejemplos_del_repo(self):
        r = corre((AQUI / "ejemplos" / "errata.ev").read_text(encoding="utf-8"))
        self.assertEqual([x["veredicto"] for x in r], ["REFUTADA", "GARANTIZADA"])
        r = corre((AQUI / "ejemplos" / "mosca.ev").read_text(encoding="utf-8"))
        v = [x["veredicto"] for x in r]
        self.assertEqual(v[0], "REFUTADA")
        self.assertEqual(v[1:], ["GARANTIZADA"] * 3)
        self.assertEqual(r[-1]["etiqueta"], "no_verificado")
        r = corre((AQUI / "ejemplos" / "agora.ev").read_text(encoding="utf-8"))
        self.assertEqual(r[0]["veredicto"], "CONDICIONAL")
        self.assertEqual(r[2]["veredicto"], "CONDICIONAL")


if __name__ == "__main__":
    unittest.main(verbosity=1)
