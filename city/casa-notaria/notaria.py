"""Núcleo de Casa Notaría.

Sella con SHA-256 el contenido de cada casa de city/ (árbol de Merkle por casa),
encadena las raíces en bloques con una prueba de trabajo trivial y permite
comprobar después si algún archivo sellado cambió.

Solo biblioteca estándar. Sin red, sin claves, sin consenso: es un registro local.
"""
from __future__ import annotations

import hashlib
import json
import os
import unicodedata
from pathlib import Path

DIFICULTAD = 4                      # ceros hexadecimales que exige el hash de cada bloque
PREFIJO_PRUEBA = "0" * DIFICULTAD
NOMBRE_CASA = "casa-notaria"        # esta casa no se sella: sellarse a sí misma sería circular
DIR_NOTARIA = Path(__file__).resolve().parent
DIR_CIUDAD = DIR_NOTARIA.parent
RUTA_CADENA = DIR_NOTARIA / "ledger" / "chain.json"

# Raíz de un árbol sin hojas (casa sin archivos, o lista de casas vacía).
RAIZ_VACIA = hashlib.sha256(b"\x02vacio").hexdigest()


class ErrorEscaneo(Exception):
    """Algo de una casa no se puede sellar (por ejemplo, un enlace simbólico)."""


# ---------------------------------------------------------------- hashes y Merkle

def sha256_archivo(ruta: Path) -> str:
    h = hashlib.sha256()
    with open(ruta, "rb") as f:
        for trozo in iter(lambda: f.read(1 << 20), b""):
            h.update(trozo)
    return h.hexdigest()


def hoja(nombre: str, valor_hex: str) -> bytes:
    """Hoja del árbol: SHA-256(0x00 || nombre UTF-8 || valor de 32 bytes).

    El nombre va dentro de la hoja: renombrar un archivo cambia la raíz aunque
    su contenido no cambie. El prefijo 0x00 separa dominios de los nodos internos.
    """
    valor = bytes.fromhex(valor_hex)
    if len(valor) != 32:
        raise ValueError("el valor de una hoja debe ocupar 32 bytes")
    return hashlib.sha256(b"\x00" + nombre.encode("utf-8") + valor).digest()


def nodo(izq: bytes, der: bytes) -> bytes:
    """Nodo interno: SHA-256(0x01 || izquierda || derecha)."""
    return hashlib.sha256(b"\x01" + izq + der).digest()


def _niveles(hojas: list[bytes]) -> list[list[bytes]]:
    """Todos los niveles del árbol, de las hojas (índice 0) a la raíz.

    Hojas impares: la última hoja de un nivel se PROMOCIONA tal cual al nivel
    siguiente. No se duplica (duplicarla permite que [a, b, c] y [a, b, c, c]
    tengan la misma raíz, el fallo de Bitcoin CVE-2012-2459).
    """
    niveles = [list(hojas)]
    while len(niveles[-1]) > 1:
        actual = niveles[-1]
        siguiente = [nodo(actual[i], actual[i + 1]) for i in range(0, len(actual) - 1, 2)]
        if len(actual) % 2 == 1:
            siguiente.append(actual[-1])
        niveles.append(siguiente)
    return niveles


def raiz_merkle(hojas: list[bytes]) -> bytes:
    if not hojas:
        return bytes.fromhex(RAIZ_VACIA)
    return _niveles(hojas)[-1][0]


def generar_prueba(hojas: list[bytes], indice: int) -> list[dict]:
    """Pasos de la prueba de inclusión de hojas[indice]: [{lado, hash}, ...].

    'lado' indica dónde va el hermano: "izq" o "der". Un nivel en el que la hoja
    se promociona no genera paso.
    """
    if not 0 <= indice < len(hojas):
        raise IndexError("índice de hoja fuera de rango")
    pasos = []
    pos = indice
    for nivel in _niveles(hojas)[:-1]:
        if pos % 2 == 1:
            pasos.append({"lado": "izq", "hash": nivel[pos - 1].hex()})
        elif pos + 1 < len(nivel):
            pasos.append({"lado": "der", "hash": nivel[pos + 1].hex()})
        pos //= 2
    return pasos


def verificar_prueba(hoja_b: bytes, indice: int, n: int, pasos: list[dict], raiz_hex: str) -> bool:
    """Comprueba una prueba de inclusión. Exige que los 'lado' coincidan con la
    estructura que implican (índice y número de hojas), así que una prueba no
    puede tener pasos de más, de menos ni en el lado equivocado."""
    if not (isinstance(n, int) and n > 0 and isinstance(indice, int) and 0 <= indice < n):
        return False
    h = hoja_b
    pos, m, k = indice, n, 0
    while m > 1:
        if pos % 2 == 1:
            esperado = "izq"
        elif pos + 1 < m:
            esperado = "der"
        else:
            esperado = None  # hoja promocionada: no hay hermano en este nivel
        if esperado is not None:
            if k >= len(pasos) or not isinstance(pasos[k], dict) or pasos[k].get("lado") != esperado:
                return False
            try:
                hermano = bytes.fromhex(pasos[k]["hash"])
            except (KeyError, TypeError, ValueError):
                return False
            if len(hermano) != 32:
                return False
            h = nodo(hermano, h) if esperado == "izq" else nodo(h, hermano)
            k += 1
        pos //= 2
        m = (m + 1) // 2
    return k == len(pasos) and h.hex() == raiz_hex


def raiz_casa(archivos: list[tuple[str, str]]) -> str:
    """Raíz de una casa a partir de [(ruta, sha256), ...] ya ordenados."""
    return raiz_merkle([hoja(ruta, sha) for ruta, sha in archivos]).hex()


def raiz_de_casas(casas: list[dict]) -> str:
    """Raíz del árbol de casas: hojas (nombre de casa, raíz de la casa), ordenadas."""
    return raiz_merkle([hoja(c["casa"], c["raiz"]) for c in casas]).hex()


# ---------------------------------------------------------------- recorrido de casas

def _ignorada(nombre: str) -> bool:
    return nombre.startswith(".") or nombre == "__pycache__" or nombre.endswith(".pyc")


def escanear_casa(carpeta: Path) -> list[tuple[str, str]]:
    """[(ruta, sha256)] de todos los archivos de la casa, ordenados por ruta.

    Rutas relativas, con '/', normalizadas a NFC. Se ignoran __pycache__, *.pyc
    y cualquier ruta con un componente oculto (que empiece por punto).
    Un enlace simbólico es un error: no se puede sellar lo que apunta fuera.
    """
    base = Path(carpeta)
    encontrados: dict[str, str] = {}
    for dirpath, dirnames, filenames in os.walk(base):
        dir_actual = Path(dirpath)
        for d in dirnames:
            if not _ignorada(d) and (dir_actual / d).is_symlink():
                raise ErrorEscaneo(f"enlace simbólico no sellable: {(dir_actual / d).relative_to(base).as_posix()}")
        dirnames[:] = sorted(d for d in dirnames if not _ignorada(d))
        for nombre in sorted(filenames):
            if _ignorada(nombre):
                continue
            ruta_abs = dir_actual / nombre
            ruta = unicodedata.normalize("NFC", ruta_abs.relative_to(base).as_posix())
            if ruta_abs.is_symlink():
                raise ErrorEscaneo(f"enlace simbólico no sellable: {ruta}")
            if ruta in encontrados:
                raise ErrorEscaneo(f"ruta duplicada tras normalizar a NFC: {ruta}")
            encontrados[ruta] = sha256_archivo(ruta_abs)
    return sorted(encontrados.items())


def descubrir_casas(ciudad: Path) -> list[str]:
    """Carpetas de primer nivel de city/, salvo casa-notaria y las ocultas."""
    return sorted(
        p.name
        for p in Path(ciudad).iterdir()
        if p.is_dir() and not p.name.startswith(".") and p.name != NOMBRE_CASA
    )


def escanear_ciudad(ciudad: Path) -> dict[str, list[tuple[str, str]]]:
    return {n: escanear_casa(Path(ciudad) / n) for n in descubrir_casas(ciudad)}


# ---------------------------------------------------------------- bloques

def canonico(obj) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _hasher_base(bloque: dict):
    """SHA-256 ya alimentado con el JSON canónico del bloque sin 'hash' ni 'nonce'.

    Serializar una vez y variar solo el nonce hace el minado rápido sin
    cambiar la prueba: el hash es SHA-256(JSON canónico || '|' || nonce).
    No hay marcas de tiempo: el identificador lógico es 'indice'.
    """
    sin = {k: v for k, v in bloque.items() if k not in ("hash", "nonce")}
    return hashlib.sha256(canonico(sin).encode("utf-8") + b"|")


def hash_bloque(bloque: dict) -> str:
    h = _hasher_base(bloque)
    h.update(str(bloque["nonce"]).encode("ascii"))
    return h.hexdigest()


def minar(bloque: dict) -> dict:
    """Busca un nonce que deje el hash del bloque con DIFICULTAD ceros hex."""
    bloque["dificultad"] = DIFICULTAD
    base = _hasher_base(bloque)
    nonce = 0
    while True:
        h = base.copy()
        h.update(str(nonce).encode("ascii"))
        digest = h.hexdigest()
        if digest.startswith(PREFIJO_PRUEBA):
            bloque["nonce"] = nonce
            bloque["hash"] = digest
            return bloque
        nonce += 1


def construir_bloque(indice: int, anterior: str, escaneo: dict[str, list[tuple[str, str]]]) -> dict:
    casas = []
    for nombre in sorted(escaneo):
        arch = escaneo[nombre]
        casas.append({
            "archivos": [{"ruta": r, "sha256": s} for r, s in arch],
            "casa": nombre,
            "n_archivos": len(arch),
            "raiz": raiz_casa(arch),
        })
    return minar({
        "anterior": anterior,
        "casas": casas,
        "indice": indice,
        "raiz_casas": raiz_de_casas(casas),
    })


GENESIS_MENSAJE = "Génesis de Casa Notaría: bloque fijo, sin casas selladas."
GENESIS = minar({
    "anterior": "0" * 64,
    "casas": [],
    "indice": 0,
    "mensaje": GENESIS_MENSAJE,
    "raiz_casas": RAIZ_VACIA,
})


def cadena_inicial() -> list[dict]:
    return [json.loads(canonico(GENESIS))]


def validar_cadena(cadena: list[dict]) -> list[str]:
    """Lista de problemas (vacía si la cadena es íntegra)."""
    if not cadena:
        return ["la cadena está vacía"]
    problemas: list[str] = []
    if cadena[0] != GENESIS:
        problemas.append("el bloque génesis no es el fijo del código")
    for i, b in enumerate(cadena):
        pre = f"bloque {i}: "
        try:
            if b["indice"] != i:
                problemas.append(pre + f"índice {b['indice']} fuera de sitio")
            if i > 0 and b["anterior"] != cadena[i - 1]["hash"]:
                problemas.append(pre + "enlace roto con el bloque anterior")
            if hash_bloque(b) != b["hash"]:
                problemas.append(pre + "el hash no corresponde al contenido (bloque alterado)")
            if b["dificultad"] != DIFICULTAD or not b["hash"].startswith(PREFIJO_PRUEBA):
                problemas.append(pre + "prueba de trabajo no cumplida")
            nombres = [c["casa"] for c in b["casas"]]
            if nombres != sorted(set(nombres)):
                problemas.append(pre + "casas repetidas o desordenadas")
            for c in b["casas"]:
                rutas = [a["ruta"] for a in c["archivos"]]
                if rutas != sorted(set(rutas)):
                    problemas.append(pre + f"archivos repetidos o desordenados en {c['casa']}")
                if c["n_archivos"] != len(rutas):
                    problemas.append(pre + f"nº de archivos de {c['casa']} no cuadra")
                if raiz_casa([(a["ruta"], a["sha256"]) for a in c["archivos"]]) != c["raiz"]:
                    problemas.append(pre + f"la raíz de {c['casa']} no corresponde a sus archivos")
            if raiz_de_casas(b["casas"]) != b["raiz_casas"]:
                problemas.append(pre + "la raíz de casas no corresponde a las raíces de cada casa")
        except (KeyError, TypeError, ValueError, AttributeError) as e:
            problemas.append(pre + f"bloque malformado ({type(e).__name__})")
    return problemas


# ---------------------------------------------------------------- persistencia

def cargar_cadena(ruta: Path) -> list[dict]:
    with open(ruta, encoding="utf-8") as f:
        return json.load(f)


def serializar_cadena(cadena: list[dict]) -> str:
    return json.dumps(cadena, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def guardar_cadena(ruta: Path, cadena: list[dict]) -> None:
    ruta = Path(ruta)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    tmp = ruta.with_name(ruta.name + ".tmp")
    tmp.write_text(serializar_cadena(cadena), encoding="utf-8")
    os.replace(tmp, ruta)


# ---------------------------------------------------------------- estado actual

def estado_ciudad(cadena: list[dict], ciudad: Path) -> list[dict]:
    """Compara cada casa con el último bloque que la contiene.

    estado: OK, MODIFICADA (con 'cambios'), DESAPARECIDA, SIN_SELLAR o ANOMALIA.
    """
    ultimo: dict[str, tuple[int, dict]] = {}
    for b in cadena:
        for c in b["casas"]:
            ultimo[c["casa"]] = (b["indice"], c)
    presentes = set(descubrir_casas(ciudad))
    filas = []
    for nombre in sorted(set(ultimo) | presentes):
        fila: dict = {"casa": nombre, "bloque": None, "estado": None, "cambios": [],
                      "archivos": None, "raiz_sellada": None, "raiz_actual": None}
        sellada = ultimo.get(nombre)
        if sellada:
            fila["bloque"] = sellada[0]
            fila["raiz_sellada"] = sellada[1]["raiz"]
        if nombre not in presentes:
            fila["estado"] = "DESAPARECIDA"
            filas.append(fila)
            continue
        try:
            actual = escanear_casa(Path(ciudad) / nombre)
        except ErrorEscaneo as e:
            fila["estado"] = "ANOMALIA"
            fila["cambios"] = [{"tipo": "no sellable", "ruta": str(e)}]
            filas.append(fila)
            continue
        fila["archivos"] = len(actual)
        fila["raiz_actual"] = raiz_casa(actual)
        if not sellada:
            fila["estado"] = "SIN_SELLAR"
            filas.append(fila)
            continue
        cambios = _comparar_archivos(sellada[1]["archivos"], actual)
        fila["cambios"] = cambios
        fila["estado"] = "OK" if not cambios and fila["raiz_actual"] == fila["raiz_sellada"] else "MODIFICADA"
        filas.append(fila)
    return filas


def _comparar_archivos(sellados: list[dict], actuales: list[tuple[str, str]]) -> list[dict]:
    sello = {a["ruta"]: a["sha256"] for a in sellados}
    ahora = dict(actuales)
    cambios = []
    for ruta in sorted(set(sello) | set(ahora)):
        if ruta not in ahora:
            cambios.append({"tipo": "desaparecido", "ruta": ruta})
        elif ruta not in sello:
            cambios.append({"tipo": "añadido", "ruta": ruta})
        elif sello[ruta] != ahora[ruta]:
            cambios.append({"tipo": "modificado", "ruta": ruta})
    return cambios


# ---------------------------------------------------------------- prueba de inclusión

def generar_prueba_archivo(cadena: list[dict], casa: str, ruta: str, bloque: int | None = None) -> dict:
    """Prueba de que el archivo (casa, ruta) está en el bloque indicado (o en el último que lo contiene)."""
    ruta = unicodedata.normalize("NFC", ruta)
    if bloque is None:
        candidatos = [b for b in cadena if _buscar_archivo(b, casa, ruta) is not None]
        if not candidatos:
            raise LookupError(f"{casa}/{ruta} no está sellado en ningún bloque")
        b = candidatos[-1]
    else:
        if not 0 <= bloque < len(cadena):
            raise LookupError(f"no existe el bloque {bloque}")
        b = cadena[bloque]
        if _buscar_archivo(b, casa, ruta) is None:
            raise LookupError(f"{casa}/{ruta} no está en el bloque {bloque}")
    c = next(x for x in b["casas"] if x["casa"] == casa)
    rutas = [a["ruta"] for a in c["archivos"]]
    hojas_arch = [hoja(a["ruta"], a["sha256"]) for a in c["archivos"]]
    idx_arch = rutas.index(ruta)
    nombres = [x["casa"] for x in b["casas"]]
    hojas_casas = [hoja(x["casa"], x["raiz"]) for x in b["casas"]]
    idx_casa = nombres.index(casa)
    return {
        "casa": casa,
        "ruta": ruta,
        "sha256": c["archivos"][idx_arch]["sha256"],
        "bloque": b["indice"],
        "archivo": {"indice": idx_arch, "n": len(hojas_arch), "pasos": generar_prueba(hojas_arch, idx_arch)},
        "raiz_casa": c["raiz"],
        "casa_en_bloque": {"indice": idx_casa, "n": len(hojas_casas), "pasos": generar_prueba(hojas_casas, idx_casa)},
        "raiz_casas": b["raiz_casas"],
    }


def _buscar_archivo(bloque: dict, casa: str, ruta: str) -> dict | None:
    for c in bloque["casas"]:
        if c["casa"] == casa:
            for a in c["archivos"]:
                if a["ruta"] == ruta:
                    return a
    return None


def verificar_prueba_archivo(prueba: dict, cadena: list[dict]) -> bool:
    """La prueba cuadra con sus pasos Y con la raíz real del bloque que cita en la cadena."""
    try:
        bloque = cadena[prueba["bloque"]]
        a, k = prueba["archivo"], prueba["casa_en_bloque"]
        ok_archivo = verificar_prueba(hoja(prueba["ruta"], prueba["sha256"]),
                                      a["indice"], a["n"], a["pasos"], prueba["raiz_casa"])
        ok_casa = verificar_prueba(hoja(prueba["casa"], prueba["raiz_casa"]),
                                   k["indice"], k["n"], k["pasos"], prueba["raiz_casas"])
        ancla = prueba["raiz_casas"] == bloque["raiz_casas"]
    except (KeyError, IndexError, TypeError, ValueError):
        return False
    return ok_archivo and ok_casa and ancla
