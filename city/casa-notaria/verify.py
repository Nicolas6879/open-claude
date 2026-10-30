"""Verifica la cadena y el estado actual de city/ frente a los bloques.

Comprueba: génesis, enlaces, hashes, prueba de trabajo, raíces de Merkle del
bloque y que cada casa sigue igual que en el último bloque que la contiene.
Si algo falla, dice qué archivo cambió, apareció o desapareció, y en qué casa.

Uso: python3 verify.py [--ciudad DIR] [--cadena FICHERO]
Códigos de salida: 0 todo bien, 1 manipulación detectada, 2 no se puede verificar (falta la cadena).
La salida no depende del reloj ni del orden de ejecución: dos ejecuciones dan el mismo texto.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True

import notaria  # noqa: E402

ESTADOS_MANIPULADOS = {"MODIFICADA", "DESAPARECIDA", "ANOMALIA"}


def informe(cadena: list[dict], ciudad: Path) -> tuple[list[str], bool]:
    lineas = []
    problemas = notaria.validar_cadena(cadena)
    n = len(cadena)
    lineas.append(f"CADENA: {n} bloque{'s' if n != 1 else ''} (génesis + {n - 1})")
    if problemas:
        lineas.append("  integridad: FALLA")
        lineas.extend(f"    - {p}" for p in problemas)
    else:
        lineas.append(f"  integridad: OK (enlaces, hashes, génesis y prueba de trabajo de {notaria.DIFICULTAD} ceros)")

    filas = []
    if not problemas:
        filas = notaria.estado_ciudad(cadena, ciudad)
    lineas.append("CASAS:")
    if problemas:
        lineas.append("  (no se compara la ciudad: la cadena no es íntegra)")
    for f in filas:
        estado = f["estado"]
        cabecera = f"  {f['casa']}: {estado}"
        if f["bloque"] is not None:
            cabecera += f" (sellada en bloque {f['bloque']})"
        if estado == "OK":
            cabecera += f" · {f['archivos']} archivos · raíz {f['raiz_sellada'][:16]}…"
        lineas.append(cabecera)
        if estado == "DESAPARECIDA":
            lineas.append("    la carpeta ya no existe en city/")
        if estado == "SIN_SELLAR":
            lineas.append("    no está en ningún bloque (aviso, no cuenta como manipulación)")
        for c in f["cambios"]:
            lineas.append(f"    {c['tipo']}: {c['ruta']}")

    manipulacion = bool(problemas) or any(f["estado"] in ESTADOS_MANIPULADOS for f in filas)
    lineas.append("RESULTADO: " + ("MANIPULACIÓN DETECTADA" if manipulacion else "OK"))
    return lineas, manipulacion


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Verifica la cadena y la ciudad.")
    ap.add_argument("--ciudad", type=Path, default=notaria.DIR_CIUDAD)
    ap.add_argument("--cadena", type=Path, default=notaria.RUTA_CADENA)
    args = ap.parse_args(argv)
    ruta_cadena = args.cadena.resolve()

    if not ruta_cadena.exists():
        print(f"No hay cadena en {ruta_cadena}. Ejecuta notarize.py primero.")
        return 2
    try:
        cadena = notaria.cargar_cadena(ruta_cadena)
    except (OSError, ValueError, json.JSONDecodeError) as e:
        print("RESULTADO: MANIPULACIÓN DETECTADA")
        print(f"  chain.json no se puede leer como JSON: {e}")
        return 1
    if not isinstance(cadena, list):
        print("RESULTADO: MANIPULACIÓN DETECTADA")
        print("  chain.json no contiene una lista de bloques")
        return 1

    lineas, manipulacion = informe(cadena, args.ciudad.resolve())
    print("\n".join(lineas))
    return 1 if manipulacion else 0


if __name__ == "__main__":
    sys.exit(main())
