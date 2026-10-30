#!/usr/bin/env python3
"""Paseo: la ciudad habitada. Lee city.json y el LOG.md de cada casa, extrae frases
reales (qué falló, qué sorprendió, qué se aprendió) y escribe paseo.html: un solo
archivo, sin dependencias, donde los habitantes caminan y se las cuentan.
Uso: python3 paseo.py   (determinista para los mismos LOG)"""
import hashlib
import json
import re
from pathlib import Path

AQUI = Path(__file__).resolve().parent
RAIZ = AQUI.parents[1]
CLAVES = re.compile(r"sorprend|fall|error|aprend|honest|no funcion|descart|no gana|bloquead|corregi|raro|equivoc|mentira|b[aá]sic", re.I)
COLORES = ["#e07a5f", "#3d9970", "#6c5ce7", "#d4a017", "#2e86ab", "#c44569", "#16a085", "#8e6c4a"]


def limpiar(t):
    t = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", t)
    t = re.sub(r"[*`_]|^\s*[-\d.]+\s+", "", t)
    return re.sub(r"\s+", " ", t).strip()


def parrafos(texto):
    """Une las líneas con salto duro que pertenecen al mismo punto o párrafo."""
    out, cur = [], ""
    for linea in texto.splitlines():
        crudo = linea.strip()
        nuevo = (not crudo) or re.match(r"^(#|\||```|[-*] |\d+\. )", crudo)
        if nuevo and cur:
            out.append(cur)
            cur = ""
        if crudo and not crudo.startswith(("#", "|", "```")):
            cur = (cur + " " + crudo).strip()
    if cur:
        out.append(cur)
    return out


def frases(path):
    if not path.exists():
        return ["Todavía no tengo nada que contar: sigo trabajando en mi casa."]
    out = []
    for par in parrafos(path.read_text(encoding="utf-8")):
        for s in re.split(r"(?<=[.!?])\s+", limpiar(par)):
            if 45 <= len(s) <= 170 and CLAVES.search(s) and re.match(r"[A-ZÁÉÍÓÚÑ¿¡«\"]", s) \
                    and "http" not in s and "`" not in s and not re.search(r"\.(py|md|json|js)\b", s):
                out.append(s)
    out = sorted(set(out), key=lambda s: hashlib.sha1(s.encode()).hexdigest())
    return out[:9] or ["Todavía no tengo nada que contar: sigo trabajando en mi casa."]


def main():
    ciudad = json.loads((RAIZ / "city.json").read_text(encoding="utf-8"))
    casas = []
    for i, c in enumerate(ciudad["casas"]):
        log = RAIZ / c["log"]
        casas.append({"id": c["id"], "nombre": c["nombre"], "habitante": c["habitante"],
                      "lista": c.get("estado") == "lista", "color": COLORES[i % len(COLORES)],
                      "frases": frases(log), "fuente": c["log"]})
    alcalde = {"id": "alcalde", "nombre": "Ayuntamiento", "habitante": "Alcalde", "lista": True,
               "color": "#9a3b2e", "frases": frases(RAIZ / "LOG.md"), "fuente": "LOG.md"}
    datos = json.dumps({"casas": casas, "alcalde": alcalde}, ensure_ascii=False).replace("</", "<\\/")
    plantilla = (AQUI / "paseo.template.html").read_text(encoding="utf-8")
    (AQUI / "paseo.html").write_text(plantilla.replace("/*DATOS*/null", datos), encoding="utf-8")
    n = sum(len(c["frases"]) for c in casas) + len(alcalde["frases"])
    print(f"paseo.html: {len(casas)} casas, {n} frases reales")


if __name__ == "__main__":
    main()
