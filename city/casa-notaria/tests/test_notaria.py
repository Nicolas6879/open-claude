"""Pruebas de Casa Notaría. Ejecutar con: python3 tests/test_notaria.py

Todas las pruebas que manipulan algo trabajan sobre COPIAS en directorios
temporales del sistema. Nunca tocan city/ real ni ledger/chain.json real.
"""
from __future__ import annotations

import copy
import hashlib
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.dont_write_bytecode = True

NOTARIA = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(NOTARIA))

import notaria  # noqa: E402

CIUDAD_REAL = notaria.DIR_CIUDAD
CASAS_REALES = ["casa-mosca", "casa-agora", "casa-taller"]
ENV = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")


def h(data: bytes) -> bytes:
    return hashlib.sha256(data).digest()


def cli(script: str, ciudad: Path, cadena: Path, *extra: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(NOTARIA / script), "--ciudad", str(ciudad), "--cadena", str(cadena), *extra],
        capture_output=True, text=True, env=ENV,
    )


def ciudad_sintetica(raiz: Path) -> Path:
    """Ciudad pequeña inventada: dos casas con varios archivos, uno oculto y una caché."""
    ciudad = raiz / "city"
    archivos = {
        "casa-alfa/README.md": "alfa\n",
        "casa-alfa/LOG.md": "diario alfa\n",
        "casa-alfa/out/datos.json": '{"x": 1}\n',
        "casa-alfa/out/tabla.csv": "a,b\n1,2\n",
        "casa-beta/README.md": "beta\n",
        "casa-beta/src/main.py": "print('hola')\n",
    }
    for rel, texto in archivos.items():
        p = ciudad / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(texto, encoding="utf-8")
    return ciudad


def copia_casas_reales(raiz: Path) -> Path:
    """Copia (nunca original) de las casas reales en un directorio temporal."""
    ciudad = raiz / "city"
    ciudad.mkdir()
    for nombre in CASAS_REALES:
        origen = CIUDAD_REAL / nombre
        if origen.is_dir():
            shutil.copytree(origen, ciudad / nombre,
                            ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".*"))
    return ciudad


class MerkleTests(unittest.TestCase):
    def test_raiz_con_1_2_3_y_4_hojas(self):
        a, b, c, d = (h(x) for x in (b"a", b"b", b"c", b"d"))
        self.assertEqual(notaria.raiz_merkle([]).hex(), notaria.RAIZ_VACIA)
        self.assertEqual(notaria.raiz_merkle([a]), a)
        self.assertEqual(notaria.raiz_merkle([a, b]), notaria.nodo(a, b))
        # 3 hojas: la tercera se promociona sin duplicarse
        self.assertEqual(notaria.raiz_merkle([a, b, c]), notaria.nodo(notaria.nodo(a, b), c))
        self.assertEqual(notaria.raiz_merkle([a, b, c, d]),
                         notaria.nodo(notaria.nodo(a, b), notaria.nodo(c, d)))

    def test_hoja_impar_no_se_duplica(self):
        a, b, c = (h(x) for x in (b"a", b"b", b"c"))
        self.assertNotEqual(notaria.raiz_merkle([a, b, c]), notaria.raiz_merkle([a, b, c, c]))

    def test_pruebas_validas_para_todas_las_hojas(self):
        for n in range(1, 10):
            hojas = [h(bytes([i])) for i in range(n)]
            raiz = notaria.raiz_merkle(hojas).hex()
            for i in range(n):
                pasos = notaria.generar_prueba(hojas, i)
                self.assertTrue(notaria.verificar_prueba(hojas[i], i, n, pasos, raiz),
                                f"prueba válida rechazada: n={n}, i={i}")

    def test_pruebas_manipuladas_rechazadas(self):
        for n in (3, 4):
            hojas = [h(bytes([i])) for i in range(n)]
            raiz = notaria.raiz_merkle(hojas).hex()
            pasos = notaria.generar_prueba(hojas, 1)
            otra_hoja = h(b"falsa")
            self.assertFalse(notaria.verificar_prueba(otra_hoja, 1, n, pasos, raiz), "hoja cambiada aceptada")
            self.assertFalse(notaria.verificar_prueba(hojas[1], 0, n, pasos, raiz), "índice cambiado aceptado")
            self.assertFalse(notaria.verificar_prueba(hojas[1], 1, n, pasos[:-1], raiz), "paso quitado aceptado")
            self.assertFalse(notaria.verificar_prueba(hojas[1], 1, n, pasos + [pasos[0]], raiz), "paso añadido aceptado")
            cambiado = copy.deepcopy(pasos)
            cambiado[0]["hash"] = h(b"hermano falso").hex()
            self.assertFalse(notaria.verificar_prueba(hojas[1], 1, n, cambiado, raiz), "hermano cambiado aceptado")
            lado = copy.deepcopy(pasos)
            lado[0]["lado"] = "der" if lado[0]["lado"] == "izq" else "izq"
            self.assertFalse(notaria.verificar_prueba(hojas[1], 1, n, lado, raiz), "lado invertido aceptado")


class CadenaTests(unittest.TestCase):
    def test_genesis_fijo_con_prueba_de_trabajo(self):
        g = notaria.GENESIS
        self.assertEqual(notaria.hash_bloque(g), g["hash"])
        self.assertTrue(g["hash"].startswith("0" * notaria.DIFICULTAD))
        self.assertEqual(notaria.validar_cadena([g]), [])

    def test_pow_invalido_detectado(self):
        b = copy.deepcopy(notaria.GENESIS)
        b["nonce"] += 1  # el hash guardado ya no corresponde
        self.assertTrue(notaria.validar_cadena([b]))
        falso = copy.deepcopy(notaria.GENESIS)
        falso["hash"] = "1" + falso["hash"][1:]  # sin ceros iniciales
        self.assertTrue(any("prueba de trabajo" in p or "hash" in p for p in notaria.validar_cadena([falso])))

    def test_cadena_rota_si_se_altera_un_bloque(self):
        with tempfile.TemporaryDirectory() as tmp:
            ciudad = ciudad_sintetica(Path(tmp))
            cadena = notaria.cadena_inicial()
            cadena.append(notaria.construir_bloque(1, cadena[-1]["hash"], notaria.escanear_ciudad(ciudad)))
            cadena.append(notaria.construir_bloque(2, cadena[-1]["hash"], notaria.escanear_ciudad(ciudad)))
            self.assertEqual(notaria.validar_cadena(cadena), [])

            alterada = copy.deepcopy(cadena)
            alterada[1]["casas"][0]["archivos"][0]["sha256"] = "00" * 32
            problemas = notaria.validar_cadena(alterada)
            self.assertTrue(any("bloque 1" in p and "alterado" in p for p in problemas), problemas)

            # Reescribir el bloque 1 con hash y PoW válidos rompe el enlace con el 2.
            reescrito = copy.deepcopy(cadena)
            reescrito[1]["casas"][0]["archivos"][0]["sha256"] = "00" * 32
            reescrito[1]["casas"][0]["raiz"] = notaria.raiz_casa(
                [(a["ruta"], a["sha256"]) for a in reescrito[1]["casas"][0]["archivos"]])
            reescrito[1]["raiz_casas"] = notaria.raiz_de_casas(reescrito[1]["casas"])
            notaria.minar(reescrito[1])
            problemas = notaria.validar_cadena(reescrito)
            self.assertTrue(any("bloque 2" in p and "enlace roto" in p for p in problemas), problemas)

    def test_prueba_de_inclusion_de_archivo(self):
        with tempfile.TemporaryDirectory() as tmp:
            ciudad = ciudad_sintetica(Path(tmp))
            cadena = notaria.cadena_inicial()
            cadena.append(notaria.construir_bloque(1, cadena[-1]["hash"], notaria.escanear_ciudad(ciudad)))
            prueba = notaria.generar_prueba_archivo(cadena, "casa-alfa", "out/datos.json")
            self.assertTrue(notaria.verificar_prueba_archivo(prueba, cadena))

            falsa = copy.deepcopy(prueba)
            falsa["sha256"] = h(b"otro contenido").hex()
            self.assertFalse(notaria.verificar_prueba_archivo(falsa, cadena))

            # out/datos.json es la hoja 2 de 4: su prueba tiene al menos un paso.
            self.assertTrue(prueba["archivo"]["pasos"])
            otra = copy.deepcopy(prueba)
            otra["archivo"]["pasos"][0]["hash"] = h(b"hermano falso").hex()
            self.assertFalse(notaria.verificar_prueba_archivo(otra, cadena))


class FicherosTests(unittest.TestCase):
    """Cambios sobre una copia en /tmp (directorio temporal del sistema)."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.raiz = Path(self._tmp.name)
        self.ciudad = ciudad_sintetica(self.raiz)
        self.cadena = self.raiz / "chain.json"
        r = cli("notarize.py", self.ciudad, self.cadena)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def tearDown(self):
        self._tmp.cleanup()

    def verificar(self):
        return cli("verify.py", self.ciudad, self.cadena)

    def test_sin_cambios_verifica_ok(self):
        r = self.verificar()
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("RESULTADO: OK", r.stdout)

    def test_archivo_modificado_detectado(self):
        (self.ciudad / "casa-alfa" / "out" / "datos.json").write_text('{"x": 2}\n', encoding="utf-8")
        r = self.verificar()
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("casa-alfa: MODIFICADA", r.stdout)
        self.assertIn("modificado: out/datos.json", r.stdout)

    def test_archivo_anadido_detectado(self):
        (self.ciudad / "casa-beta" / "NUEVO.txt").write_text("intruso\n", encoding="utf-8")
        r = self.verificar()
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("casa-beta: MODIFICADA", r.stdout)
        self.assertIn("añadido: NUEVO.txt", r.stdout)

    def test_archivo_desaparecido_detectado(self):
        (self.ciudad / "casa-alfa" / "LOG.md").unlink()
        r = self.verificar()
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("casa-alfa: MODIFICADA", r.stdout)
        self.assertIn("desaparecido: LOG.md", r.stdout)

    def test_casa_desaparecida_detectada(self):
        shutil.rmtree(self.ciudad / "casa-beta")
        r = self.verificar()
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("casa-beta: DESAPARECIDA", r.stdout)

    def test_pycache_pyc_y_ocultos_no_cuentan(self):
        (self.ciudad / "casa-alfa" / "__pycache__").mkdir()
        (self.ciudad / "casa-alfa" / "__pycache__" / "x.cpython-313.pyc").write_bytes(b"\x00")
        (self.ciudad / "casa-alfa" / "suelto.pyc").write_bytes(b"\x00")
        (self.ciudad / "casa-alfa" / ".oculto").write_text("secreto\n", encoding="utf-8")
        (self.ciudad / "casa-alfa" / ".git").mkdir()
        (self.ciudad / "casa-alfa" / ".git" / "config").write_text("x\n", encoding="utf-8")
        r = self.verificar()
        self.assertEqual(r.returncode, 0, r.stdout)

    def test_chain_json_alterado_a_mano_detectado(self):
        texto = self.cadena.read_text(encoding="utf-8")
        self.cadena.write_text(texto.replace('"nonce": ', '"nonce": 1', 1), encoding="utf-8")
        r = self.verificar()
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("MANIPULACIÓN DETECTADA", r.stdout)

    def test_notarize_sin_cambios_no_anade_bloque(self):
        antes = self.cadena.read_text(encoding="utf-8")
        r = cli("notarize.py", self.ciudad, self.cadena)
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertEqual(self.cadena.read_text(encoding="utf-8"), antes)

    def test_prove_detecta_archivo_alterado(self):
        ok = cli_prove(self.ciudad, self.cadena, "casa-alfa/out/datos.json")
        self.assertEqual(ok.returncode, 0, ok.stdout)
        (self.ciudad / "casa-alfa" / "out" / "datos.json").write_text("{}\n", encoding="utf-8")
        mal = cli_prove(self.ciudad, self.cadena, "casa-alfa/out/datos.json")
        self.assertEqual(mal.returncode, 1, mal.stdout)
        self.assertIn("NO coincide", mal.stdout)

    def test_prove_archivo_no_sellado_devuelve_2(self):
        r = cli_prove(self.ciudad, self.cadena, "casa-alfa/no_existe.txt")
        self.assertEqual(r.returncode, 2, r.stdout)


def cli_prove(ciudad: Path, cadena: Path, archivo: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(NOTARIA / "prove.py"), archivo, "--ciudad", str(ciudad), "--cadena", str(cadena)],
        capture_output=True, text=True, env=ENV,
    )


class CasasRealesCopiaTests(unittest.TestCase):
    """Copia de las casas reales (nunca los originales) sellada y verificada."""

    def test_copia_real_sellada_y_manipulada(self):
        if not all((CIUDAD_REAL / n).is_dir() for n in CASAS_REALES):
            self.skipTest("faltan casas reales")
        with tempfile.TemporaryDirectory() as tmp:
            raiz = Path(tmp)
            ciudad = copia_casas_reales(raiz)
            cadena = raiz / "chain.json"
            self.assertEqual(cli("notarize.py", ciudad, cadena).returncode, 0)
            self.assertEqual(cli("verify.py", ciudad, cadena).returncode, 0)
            destino = ciudad / "casa-agora" / "out" / "results.json"
            destino.write_bytes(destino.read_bytes() + b" ")
            r = cli("verify.py", ciudad, cadena)
            self.assertEqual(r.returncode, 1, r.stdout)
            self.assertIn("casa-agora: MODIFICADA", r.stdout)
            self.assertIn("modificado: out/results.json", r.stdout)


class DeterminismoTests(unittest.TestCase):
    def test_dos_verificaciones_dan_la_misma_salida(self):
        with tempfile.TemporaryDirectory() as tmp:
            raiz = Path(tmp)
            ciudad = ciudad_sintetica(raiz)
            cadena = raiz / "chain.json"
            self.assertEqual(cli("notarize.py", ciudad, cadena).returncode, 0)
            (ciudad / "casa-beta" / "README.md").write_text("cambiado\n", encoding="utf-8")
            a = cli("verify.py", ciudad, cadena)
            b = cli("verify.py", ciudad, cadena)
            self.assertEqual(a.stdout, b.stdout)
            self.assertEqual(a.returncode, b.returncode)

    def test_mismo_contenido_mismo_ledger_byte_a_byte(self):
        with tempfile.TemporaryDirectory() as tmp:
            raiz = Path(tmp)
            ciudad1 = ciudad_sintetica(raiz / "uno")
            ciudad2 = ciudad_sintetica(raiz / "dos")
            c1, c2 = raiz / "uno.json", raiz / "dos.json"
            self.assertEqual(cli("notarize.py", ciudad1, c1).returncode, 0)
            self.assertEqual(cli("notarize.py", ciudad2, c2).returncode, 0)
            self.assertEqual(c1.read_bytes(), c2.read_bytes())

    def test_escaneo_repetible_y_ordenado(self):
        with tempfile.TemporaryDirectory() as tmp:
            ciudad = ciudad_sintetica(Path(tmp))
            a = notaria.escanear_ciudad(ciudad)
            b = notaria.escanear_ciudad(ciudad)
            self.assertEqual(a, b)
            for archivos in a.values():
                rutas = [r for r, _ in archivos]
                self.assertEqual(rutas, sorted(rutas))


if __name__ == "__main__":
    unittest.main(verbosity=2)
