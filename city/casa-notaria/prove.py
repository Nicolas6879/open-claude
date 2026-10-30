"""Prueba de inclusión de un archivo sellado.

Uso: python3 prove.py casa/ruta/del/archivo [--bloque N] [--json] [--ciudad DIR] [--cadena FICHERO]

Ejemplo: python3 prove.py casa-agora/out/results.json

Construye la cadena de pasos (archivo -> raíz de su casa -> raíz de casas del bloque),
la comprueba contra la cadena y contra el archivo tal como está en disco.
Códigos de salida: 0 prueba válida y archivo igual a lo sellado,
1 prueba inválida o archivo alterado/desaparecido, 2 no hay nada que probar (no sellado, sin cadena, argumentos mal).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True

import notaria  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Prueba de inclusión de un archivo sellado.")
    ap.add_argument("archivo", help="ruta como casa/ruta/archivo, relativa a city/")
    ap.add_argument("--bloque", type=int, default=None, help="bloque concreto (por defecto, el último que lo contiene)")
    ap.add_argument("--json", action="store_true", help="imprime la prueba completa en JSON")
    ap.add_argument("--ciudad", type=Path, default=notaria.DIR_CIUDAD)
    ap.add_argument("--cadena", type=Path, default=notaria.RUTA_CADENA)
    args = ap.parse_args(argv)

    partes = Path(args.archivo).parts
    if len(partes) < 2:
        print("Indica casa y ruta, por ejemplo: casa-agora/out/results.json")
        return 2
    casa, ruta = partes[0], "/".join(partes[1:])

    if not args.cadena.exists():
        print(f"No hay cadena en {args.cadena}.")
        return 2
    cadena = notaria.cargar_cadena(args.cadena.resolve())
    problemas = notaria.validar_cadena(cadena)
    if problemas:
        print("RESULTADO: MANIPULACIÓN DETECTADA: la cadena no es íntegra.")
        for p in problemas:
            print(f"  - {p}")
        return 1

    try:
        prueba = notaria.generar_prueba_archivo(cadena, casa, ruta, args.bloque)
    except LookupError as e:
        print(str(e))
        return 2

    valida = notaria.verificar_prueba_archivo(prueba, cadena)
    disco = args.ciudad.resolve() / casa / ruta
    if not disco.is_file():
        estado_disco = "DESAPARECIDO del disco"
        coincide = False
    else:
        coincide = notaria.sha256_archivo(disco) == prueba["sha256"]
        estado_disco = "coincide con lo sellado" if coincide else "NO coincide con lo sellado (alterado)"

    if args.json:
        print(json.dumps(prueba, indent=2, sort_keys=True, ensure_ascii=False))
    else:
        print(f"ARCHIVO: {casa}/{ruta}")
        print(f"  sha256 sellado: {prueba['sha256']}")
        print(f"  bloque: {prueba['bloque']}")
        print(f"  pasos hasta la raíz de la casa: {len(prueba['archivo']['pasos'])} (hoja {prueba['archivo']['indice']} de {prueba['archivo']['n']})")
        print(f"  pasos hasta la raíz de casas: {len(prueba['casa_en_bloque']['pasos'])}")
        print(f"  raíz de casas del bloque: {prueba['raiz_casas']}")
        print(f"  prueba de inclusión: {'VÁLIDA' if valida else 'NO VÁLIDA'}")
        print(f"  archivo en disco: {estado_disco}")

    ok = valida and coincide
    print("RESULTADO: " + ("OK" if ok else "MANIPULACIÓN DETECTADA"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
