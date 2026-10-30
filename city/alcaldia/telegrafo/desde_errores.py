#!/usr/bin/env python3
"""Prueba con material real: convierte ../errores.json (los errores de esta sesión) en
un bus Telégrafo. Cada error es un par: la afirmación equivocada (sin verificar) y la
corrección que la enlaza. Escribe bus_sesion.jsonl. Uso: python3 desde_errores.py"""
import json
from pathlib import Path

from telegrafo import construir, verificar, resumen

AQUI = Path(__file__).resolve().parent
errores = json.loads((AQUI.parent / "errores.json").read_text(encoding="utf-8"))
msgs = []
for e in errores:
    emisor = "alcalde" if e["quien"] == "Alcalde" else e["casa"] if e["casa"].startswith("casa-") else e["quien"].lower()
    msgs.append(construir(msgs, de=emisor, a="*", tipo="afirmo", cuerpo=e["que"],
                          etiqueta="no_verificado"))
    msgs.append(construir(msgs, de="alcalde", a=emisor, tipo="corrijo",
                          cuerpo=f"{e['como_se_detecto']} → {e['costo']}", etiqueta="medido",
                          fuente="errores.json (registro del Alcalde)", responde_a=len(msgs)))
assert not verificar(msgs)
(AQUI / "bus_sesion.jsonl").write_text(
    "".join(json.dumps(m, ensure_ascii=False, separators=(",", ":")) + "\n" for m in msgs), encoding="utf-8")
print(json.dumps(resumen(msgs), ensure_ascii=False))
