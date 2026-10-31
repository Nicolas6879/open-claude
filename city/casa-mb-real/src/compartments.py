"""Compartimentos del cuerpo fungiforme: lectura de las anotaciones del conectoma y tabla "de memoria".

* parse_instance(): extrae los compartimentos de la cadena `instance` de las anotaciones (p. ej.
  'MBON05(y4>y1y2)_R' -> dendrita en y4, axon en y1,y2).  Etiqueta: medido (es una anotacion de Janelia, no una
  medicion de conectividad; ver `anatomy.py` para la validacion con conectividad real).
* MEMORIA_*: tablas escritas DE MEMORIA (Aso et al. 2014 eLife, Owald 2015, Hige 2015, hemibrain Li 2020).
  Etiqueta: no_verificado.  Se contrastan con los datos en anatomy.py.
"""
import re

LOBE_GREEK = {"y": "g", "a'": "a'", "a": "a", "B'": "b'", "B": "b", "b'": "b'", "b": "b"}   # g=gamma, a=alfa, b=beta (ASCII)
_TOK = re.compile(r"(y|a'|a|B'|B|b'|b)(\d)")   # las anotaciones mezclan B y b (p. ej. 'MBON26(b'2d)')


def _tokens(s):
    return [LOBE_GREEK[m.group(1)] + m.group(2) for m in _TOK.finditer(s)]


def parse_instance(inst):
    """-> (primarios, secundarios).  Primarios = antes de '>' o '<' (dendrita en MBON, arbol principal en DAN)."""
    m = re.search(r"\(([^)]*)\)", inst)
    if not m:
        return (), ()
    body = m.group(1)
    if body == "calyx":
        return ("calyx",), ()
    # casos ambiguos conocidos
    if body == "a2p3p":
        return ("a2", "a3"), ()
    parts = re.split(r"[<>]", body)
    prim = tuple(_tokens(parts[0].split("/")[0]))
    sec = tuple(_tokens("".join(parts[1:]))) if len(parts) > 1 else ()
    return prim, sec


# --- Tabla DE MEMORIA (no_verificado) ------------------------------------------------------------------
# Compartimentos canonicos (15) y lobulo/subtipo de KC dominante.
COMPARTIMENTOS = ["g1", "g2", "g3", "g4", "g5", "b'1", "b'2", "b1", "b2", "a'1", "a'2", "a'3", "a1", "a2", "a3"]
LOBULO_KC = {"g": "KCg", "b'": "KCa'b'", "a'": "KCa'b'", "b": "KCab", "a": "KCab"}

# DAN: valencia que se les atribuye en la literatura (PAM recompensa; PPL1 castigo).  +1 recompensa, -1 castigo.
# Excepciones que recuerdo (no verificadas): algunos PAM codifican castigo (p. ej. subtipos de PAM-g4/g5, Yamagata 2015),
# PPL1-a'2a2/PPL1-a3 participan en memoria olfativa de ambos signos.  Aqui se usa solo la regla de clase.
def dan_valence_class(dtype):
    if dtype.startswith("PAM"):
        return +1
    if dtype.startswith("PPL1"):
        return -1
    return 0   # PPL2, PAL, etc.: sin valencia asignada


# MBON: valencia conductual de memoria (+1 promueve acercamiento, -1 promueve evitacion), 0 = desconocido.
# Regla de oponencia (Aso 2014b, Owald 2015, de memoria): MBON de compartimentos con PAM -> evitacion (-1); con PPL1 -> acercamiento (+1).
# La tabla explicita siguiente solo recoge los que recuerdo con mas seguridad; el resto queda a 0 (neutro).
MEMORIA_MBON_VALENCIA = {
    "MBON01": -1,   # g5b'2a  (glutamato): evitacion
    "MBON03": -1,   # b'2mp   (glutamato): evitacion
    "MBON04": -1,   # b'2mp_bilateral: evitacion
    "MBON05": -1,   # g4>g1g2: evitacion
    "MBON02": -1,   # b2b'2a: evitacion
    "MBON09": -1,   # g3b'1: evitacion
    "MBON11": +1,   # g1pedc>a/b: acercamiento (castigo PPL1-g1pedc lo deprime)
    "MBON12": +1,   # g2a'1: acercamiento
    "MBON14": +1,   # a3: acercamiento
    "MBON15": +1,   # a'1
    "MBON16": +1,   # a'3ap
    "MBON17": +1,   # a'3m
    "MBON07": -1,   # a1 (PAM-a1 recompensa LTM)
    "MBON06": -1,   # b1>a
}
