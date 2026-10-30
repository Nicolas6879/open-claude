import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import telegrafo as t  # noqa: E402


def bus_valido():
    m = []
    m.append(t.construir(m, "casa-a", "*", "afirmo", "x vale 3", "medido", "experimento 1"))
    m.append(t.construir(m, "casa-b", "casa-a", "corrijo", "x vale 4", "medido", "experimento 2", 1))
    m.append(t.construir(m, "casa-a", "casa-b", "pido", "¿repites el experimento?"))
    return m


class T(unittest.TestCase):
    def test_bus_valido(self):
        self.assertEqual(t.verificar(bus_valido()), [])

    def test_afirmar_sin_etiqueta_o_medido_sin_fuente_es_rechazado(self):
        with self.assertRaises(ValueError):
            t.construir([], "a", "*", "afirmo", "algo")
        with self.assertRaises(ValueError):
            t.construir([], "a", "*", "afirmo", "algo", "medido")

    def test_correccion_exige_objetivo_afirmacion(self):
        m = bus_valido()
        with self.assertRaises(ValueError):
            t.construir(m, "a", "*", "corrijo", "no", "supuesto", None, None)
        with self.assertRaises(ValueError):                  # el mensaje 3 es un 'pido'
            t.construir(m, "a", "*", "corrijo", "no", "supuesto", None, 3)
        with self.assertRaises(ValueError):                  # apunta a un mensaje futuro
            t.construir(m, "a", "*", "corrijo", "no", "supuesto", None, 9)

    def test_etiqueta_solo_en_afirmaciones(self):
        with self.assertRaises(ValueError):
            t.construir([], "a", "*", "pido", "algo", "medido", "f")

    def test_alterar_contenido_se_detecta(self):
        m = bus_valido()
        m[0]["cuerpo"] = "x vale 99"
        self.assertTrue(any("alterado" in e for e in t.verificar(m)))

    def test_cadena_rota_al_borrar_un_mensaje(self):
        m = bus_valido()
        del m[1]
        self.assertTrue(t.verificar(m))

    def test_enviar_y_leer_en_disco_y_cli(self):
        with tempfile.TemporaryDirectory() as d:
            ruta = str(Path(d) / "bus.jsonl")
            self.assertEqual(t.main(["enviar", ruta, "--de", "a", "--tipo", "afirmo", "--cuerpo", "hola",
                                     "--etiqueta", "supuesto"]), 0)
            self.assertEqual(t.main(["enviar", ruta, "--de", "a", "--tipo", "corrijo", "--cuerpo", "no"]), 1)
            self.assertEqual(t.main(["verificar", ruta]), 0)
            self.assertEqual(len(t.leer(ruta)), 1)

    def test_resumen_detecta_no_verificadas_sin_corregir(self):
        m = []
        m.append(t.construir(m, "a", "*", "afirmo", "uno", "no_verificado"))
        m.append(t.construir(m, "a", "*", "afirmo", "dos", "no_verificado"))
        m.append(t.construir(m, "b", "a", "corrijo", "uno estaba mal", "supuesto", None, 1))
        self.assertEqual(t.resumen(m)["no_verificadas_que_nadie_corrigio"], [2])

    def test_escritores_concurrentes_no_rompen_la_cadena(self):
        import subprocess
        with tempfile.TemporaryDirectory() as d:
            ruta = str(Path(d) / "bus.jsonl")
            script = str(Path(__file__).resolve().parents[1] / "telegrafo.py")
            ps = [subprocess.Popen([sys.executable, script, "enviar", ruta, "--de", f"a{i}", "--tipo", "pido",
                                    "--cuerpo", f"mensaje {i}"], stdout=subprocess.DEVNULL) for i in range(12)]
            for p in ps:
                self.assertEqual(p.wait(), 0)
            msgs = t.leer(ruta)
            self.assertEqual(len(msgs), 12)
            self.assertEqual(t.verificar(msgs), [])

    def test_el_bus_real_de_la_sesion_es_valido(self):
        ruta = Path(__file__).resolve().parents[1] / "bus_sesion.jsonl"
        if ruta.exists():
            self.assertEqual(t.verificar(t.leer(str(ruta))), [])


if __name__ == "__main__":
    unittest.main()
