#!/usr/bin/env python3
"""Telégrafo: un protocolo mínimo para que los agentes de la ciudad se hablen.

Un bus es un archivo JSONL de solo añadir. Cada línea es un mensaje:
  n           entero consecutivo desde 1
  de, a       emisor y destinatario ("*" = todos)
  tipo        afirmo | corrijo | pido | ofrezco | no_se | entrego
  cuerpo      texto libre (el único campo no estructurado)
  etiqueta    medido | supuesto | no_verificado   (obligatoria en afirmo y corrijo)
  fuente      de dónde sale lo afirmado             (obligatoria si etiqueta=medido)
  responde_a  n de un mensaje anterior o null       (obligatorio en corrijo)
  prev, h     hash encadenado (sha256 truncado a 16 hex) del mensaje anterior y de éste

Por qué estas reglas: casi todos los errores de la ciudad fueron afirmaciones sin
procedencia y correcciones que nadie enlazó con lo que corregían. El protocolo hace
inválidas ambas cosas. No es seguridad: la cadena detecta ediciones accidentales o
descuidadas, no a alguien que reescriba todo el archivo (para eso está la Notaría).
"""
import argparse
import hashlib
import json
import sys
from pathlib import Path

TIPOS = ("afirmo", "corrijo", "pido", "ofrezco", "no_se", "entrego")
ETIQUETAS = ("medido", "supuesto", "no_verificado")
CAMPOS = ("n", "de", "a", "tipo", "cuerpo", "etiqueta", "fuente", "responde_a", "prev", "h")
GENESIS = "0" * 16


def hash_msg(m):
    base = {k: m[k] for k in CAMPOS if k != "h"}
    return hashlib.sha256(json.dumps(base, sort_keys=True, ensure_ascii=False,
                                     separators=(",", ":")).encode()).hexdigest()[:16]


def leer(ruta):
    p = Path(ruta)
    if not p.exists():
        return []
    return [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()]


def problemas_mensaje(m, previos):
    errs = []
    faltan = [k for k in CAMPOS if k not in m]
    if faltan:
        return [f"faltan campos: {faltan}"]
    extra = [k for k in m if k not in CAMPOS]
    if extra:
        errs.append(f"campos desconocidos: {extra}")
    if m["tipo"] not in TIPOS:
        errs.append(f"tipo inválido: {m['tipo']}")
    if not str(m["de"]).strip() or not str(m["a"]).strip() or not str(m["cuerpo"]).strip():
        errs.append("de, a y cuerpo no pueden estar vacíos")
    if m["tipo"] in ("afirmo", "corrijo"):
        if m["etiqueta"] not in ETIQUETAS:
            errs.append("afirmo/corrijo exigen etiqueta medido|supuesto|no_verificado")
        if m["etiqueta"] == "medido" and not str(m["fuente"] or "").strip():
            errs.append("una afirmación «medido» exige fuente")
    elif m["etiqueta"] is not None:
        errs.append(f"la etiqueta solo se usa en afirmo/corrijo, no en {m['tipo']}")
    r = m["responde_a"]
    if m["tipo"] == "corrijo" and r is None:
        errs.append("una corrección debe responder a un mensaje (responde_a)")
    if r is not None:
        if not isinstance(r, int) or not (1 <= r < m["n"]):
            errs.append(f"responde_a inválido: {r!r}")
        elif m["tipo"] == "corrijo" and previos[r - 1]["tipo"] not in ("afirmo", "corrijo"):
            errs.append(f"el mensaje {r} no es una afirmación: no hay nada que corregir")
    return errs


def verificar(msgs):
    """Devuelve la lista de problemas (vacía = bus válido)."""
    out, prev = [], GENESIS
    for i, m in enumerate(msgs, 1):
        if m.get("n") != i:
            out.append(f"mensaje {i}: n={m.get('n')} (debe ser {i})")
            continue
        out += [f"mensaje {i}: {e}" for e in problemas_mensaje(m, msgs[:i - 1])]
        if m.get("prev") != prev:
            out.append(f"mensaje {i}: la cadena está rota (prev no coincide)")
        if "h" in m and all(k in m for k in CAMPOS) and m["h"] != hash_msg(m):
            out.append(f"mensaje {i}: el contenido fue alterado (hash no coincide)")
        prev = m.get("h", prev)
    return out


def construir(msgs, de, a, tipo, cuerpo, etiqueta=None, fuente=None, responde_a=None):
    m = {"n": len(msgs) + 1, "de": de, "a": a, "tipo": tipo, "cuerpo": cuerpo, "etiqueta": etiqueta,
         "fuente": fuente, "responde_a": responde_a, "prev": msgs[-1]["h"] if msgs else GENESIS, "h": ""}
    errs = problemas_mensaje(m, msgs)
    if errs:
        raise ValueError("; ".join(errs))
    m["h"] = hash_msg(m)
    return m


def enviar(ruta, **kw):
    msgs = leer(ruta)
    m = construir(msgs, **kw)
    with open(ruta, "a", encoding="utf-8") as f:
        f.write(json.dumps(m, ensure_ascii=False, separators=(",", ":")) + "\n")
    return m


def resumen(msgs):
    por_tipo = {t: sum(1 for m in msgs if m["tipo"] == t) for t in TIPOS}
    debiles = [m["n"] for m in msgs if m["tipo"] == "afirmo" and m["etiqueta"] == "no_verificado"]
    corregidos = {m["responde_a"] for m in msgs if m["tipo"] == "corrijo"}
    sin_corregir_debiles = [n for n in debiles if n not in corregidos]
    return {"mensajes": len(msgs), "por_tipo": por_tipo,
            "afirmaciones_no_verificadas": debiles,
            "no_verificadas_que_nadie_corrigio": sin_corregir_debiles}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    e = sub.add_parser("enviar")
    e.add_argument("bus")
    e.add_argument("--de", required=True)
    e.add_argument("--a", default="*")
    e.add_argument("--tipo", required=True, choices=TIPOS)
    e.add_argument("--cuerpo", required=True)
    e.add_argument("--etiqueta", choices=ETIQUETAS)
    e.add_argument("--fuente")
    e.add_argument("--responde-a", type=int, dest="responde_a")
    v = sub.add_parser("verificar")
    v.add_argument("bus")
    r = sub.add_parser("resumen")
    r.add_argument("bus")
    a = ap.parse_args(argv)
    if a.cmd == "enviar":
        try:
            m = enviar(a.bus, de=a.de, a=a.a, tipo=a.tipo, cuerpo=a.cuerpo, etiqueta=a.etiqueta,
                       fuente=a.fuente, responde_a=a.responde_a)
        except ValueError as ex:
            print(f"rechazado: {ex}")
            return 1
        print(f"enviado n={m['n']} h={m['h']}")
        return 0
    msgs = leer(a.bus)
    if a.cmd == "verificar":
        errs = verificar(msgs)
        print("\n".join(errs) if errs else f"OK: {len(msgs)} mensajes, cadena íntegra")
        return 1 if errs else 0
    print(json.dumps(resumen(msgs), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
