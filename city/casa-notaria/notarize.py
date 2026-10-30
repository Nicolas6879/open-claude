"""Añade un bloque a ledger/chain.json con el estado actual de city/.

Uso: python3 notarize.py [--ciudad DIR] [--cadena FICHERO]

Si la cadena ya está alterada no añade nada. Si ninguna casa cambió desde el
último bloque, tampoco añade bloque (no hay nada nuevo que sellar).
Códigos de salida: 0 bloque añadido o sin cambios, 1 cadena alterada, 2 error de E/S o de escaneo.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.dont_write_bytecode = True

import notaria  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Sella el estado actual de la ciudad en la cadena.")
    ap.add_argument("--ciudad", type=Path, default=notaria.DIR_CIUDAD)
    ap.add_argument("--cadena", type=Path, default=notaria.RUTA_CADENA)
    args = ap.parse_args(argv)
    ciudad = args.ciudad.resolve()
    ruta_cadena = args.cadena.resolve()

    nueva = not ruta_cadena.exists()
    try:
        cadena = notaria.cadena_inicial() if nueva else notaria.cargar_cadena(ruta_cadena)
    except (OSError, ValueError) as e:
        print(f"No se puede leer {ruta_cadena}: {e}")
        return 2

    problemas = notaria.validar_cadena(cadena)
    if problemas:
        print("La cadena está alterada. No se añade ningún bloque hasta revisarla:")
        for p in problemas:
            print(f"  - {p}")
        return 1

    try:
        escaneo = notaria.escanear_ciudad(ciudad)
    except (notaria.ErrorEscaneo, OSError) as e:
        print(f"No se puede sellar la ciudad: {e}")
        return 2

    ultimo = cadena[-1]
    sellado = {c["casa"]: c["raiz"] for c in ultimo["casas"]}
    actual = {n: notaria.raiz_casa(arch) for n, arch in escaneo.items()}
    if not nueva and actual == sellado:
        print(f"Sin cambios desde el bloque {ultimo['indice']}: no se añade bloque.")
        return 0

    for ausente in sorted(set(sellado) - set(actual)):
        print(f"AVISO: {ausente} estaba sellada y ya no existe; verify la marcará como DESAPARECIDA.")

    bloque = notaria.construir_bloque(ultimo["indice"] + 1, ultimo["hash"], escaneo)
    cadena.append(bloque)
    notaria.guardar_cadena(ruta_cadena, cadena)

    print(f"Bloque {bloque['indice']} sellado. hash {bloque['hash']}")
    print(f"  nonce {bloque['nonce']} (dificultad {notaria.DIFICULTAD} ceros hex)")
    for c in bloque["casas"]:
        print(f"  {c['casa']}: {c['n_archivos']} archivos, raíz {c['raiz']}")
    print(f"  raíz de casas: {bloque['raiz_casas']}")
    print(f"Cadena: {len(cadena)} bloques en {ruta_cadena}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
