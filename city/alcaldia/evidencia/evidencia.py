#!/usr/bin/env python3
"""Evidencia: un lenguaje diminuto donde cada número sabe de dónde viene.

Cada valor lleva (a) un intervalo, (b) una etiqueta epistémica y (c) las hojas de
las que depende. Las etiquetas, de más a menos fuertes: medido > supuesto >
no_verificado. Un valor derivado hereda la etiqueta de su eslabón más débil.
Una `afirmar` no responde sí/no a secas: dice si se cumple GARANTIZADAMENTE en todo
el rango de los supuestos, si es REFUTADA, si es CONDICIONAL (se cumple en unas
partes y no en otras, con contraejemplo) o si NO_REFUTADA (nadie encontró un
contraejemplo, pero tampoco hay garantía).

Sintaxis (una sentencia por línea; # comenta):
  medido NOMBRE = EXPR [± ERR] [fuente "texto"]
  supuesto NOMBRE [= EXPR] en [LO, HI] [porque "texto"]
  no_verificado NOMBRE = EXPR [fuente "texto"]
  def NOMBRE = EXPR
  afirmar EXPR (<|<=|>|>=|==) EXPR [llamado "texto"]
Expresiones: + - * / ^, paréntesis, sqrt abs exp log min max.

Límites honestos: la aritmética de intervalos sobreestima cuando una variable
aparece varias veces (problema de dependencia), así que GARANTIZADA es fiable pero
CONDICIONAL/NO_REFUTADA salen de un muestreo uniforme con semilla fija, que es una
heurística: la «fracción» que se informa depende de esa distribución uniforme.
"""
import json
import math
import random
import re
import sys
from dataclasses import dataclass, field

FUERZA = {"medido": 3, "supuesto": 2, "no_verificado": 1}
NOMBRE_FUERZA = {v: k for k, v in FUERZA.items()}


class ErrorEvidencia(Exception):
    pass


# ---------------------------------------------------------------- léxico y parser
TOKEN = re.compile(r'\s*(?:(\d+\.?\d*(?:[eE][-+]?\d+)?)|([A-Za-zÁÉÍÓÚáéíóúñÑ_][\wÁÉÍÓÚáéíóúñÑ]*)|("[^"]*")|(<=|>=|==|±|\+-|[-+*/^()\[\],=<>]))')


def tokenizar(linea, n):
    out, pos = [], 0
    linea = linea.split("#", 1)[0].rstrip()
    while pos < len(linea):
        m = TOKEN.match(linea, pos)
        if not m or m.end() == pos:
            raise ErrorEvidencia(f"línea {n}: carácter inesperado cerca de «{linea[pos:pos+10]}»")
        pos = m.end()
        num, nom, cad, op = m.groups()
        if num is not None:
            out.append(("num", float(num)))
        elif nom is not None:
            out.append(("nom", nom))
        elif cad is not None:
            out.append(("str", cad[1:-1]))
        else:
            out.append(("op", "±" if op == "+-" else op))
    return out


class Parser:
    def __init__(self, toks, n):
        self.t, self.i, self.n = toks, 0, n

    def peek(self):
        return self.t[self.i] if self.i < len(self.t) else ("fin", None)

    def toma(self, tipo=None, val=None):
        tk = self.peek()
        if tk[0] == "fin" or (tipo and tk[0] != tipo) or (val is not None and tk[1] != val):
            raise ErrorEvidencia(f"línea {self.n}: se esperaba {val or tipo}, hay {tk[1]!r}")
        self.i += 1
        return tk

    def es(self, tipo, val=None):
        tk = self.peek()
        return tk[0] == tipo and (val is None or tk[1] == val)

    def expr(self):
        a = self.term()
        while self.es("op", "+") or self.es("op", "-"):
            o = self.toma()[1]
            a = ("bin", o, a, self.term())
        return a

    def term(self):
        a = self.pot()
        while self.es("op", "*") or self.es("op", "/"):
            o = self.toma()[1]
            a = ("bin", o, a, self.pot())
        return a

    def pot(self):
        a = self.unario()
        if self.es("op", "^"):
            self.toma()
            return ("bin", "^", a, self.pot())
        return a

    def unario(self):
        if self.es("op", "-"):
            self.toma()
            return ("neg", self.unario())
        return self.atomo()

    def atomo(self):
        if self.es("num"):
            return ("num", self.toma()[1])
        if self.es("op", "("):
            self.toma()
            e = self.expr()
            self.toma("op", ")")
            return e
        if self.es("nom"):
            nom = self.toma()[1]
            if self.es("op", "(") and nom in ("sqrt", "abs", "exp", "log", "min", "max"):
                self.toma()
                args = [self.expr()]
                while self.es("op", ","):
                    self.toma()
                    args.append(self.expr())
                self.toma("op", ")")
                return ("fn", nom, args)
            return ("var", nom)
        raise ErrorEvidencia(f"línea {self.n}: expresión inválida cerca de {self.peek()[1]!r}")


# --------------------------------------------------------------------- aritmética
@dataclass
class Val:
    lo: float
    hi: float
    fuerza: int = 3
    deps: frozenset = field(default_factory=frozenset)


def une(a, b, lo, hi):
    return Val(lo, hi, min(a.fuerza, b.fuerza), a.deps | b.deps)


def op_int(o, a, b):
    if o == "+":
        return une(a, b, a.lo + b.lo, a.hi + b.hi)
    if o == "-":
        return une(a, b, a.lo - b.hi, a.hi - b.lo)
    if o == "*":
        c = [a.lo * b.lo, a.lo * b.hi, a.hi * b.lo, a.hi * b.hi]
        return une(a, b, min(c), max(c))
    if o == "/":
        if b.lo <= 0 <= b.hi:
            raise ErrorEvidencia("división por un intervalo que contiene 0")
        c = [a.lo / b.lo, a.lo / b.hi, a.hi / b.lo, a.hi / b.hi]
        return une(a, b, min(c), max(c))
    if o == "^":
        if b.lo != b.hi:
            raise ErrorEvidencia("el exponente debe ser un valor exacto")
        e = b.lo
        if e == int(e) and int(e) % 2 == 0:
            m = [abs(a.lo) ** e, abs(a.hi) ** e]
            lo = 0.0 if a.lo <= 0 <= a.hi else min(m)
            return une(a, b, lo, max(m))
        if a.lo < 0:
            raise ErrorEvidencia("potencia de base negativa con exponente no par")
        return une(a, b, a.lo ** e, a.hi ** e) if e >= 0 else une(a, b, a.hi ** e, a.lo ** e)
    raise ErrorEvidencia(f"operador {o}")


def fn_int(nom, args):
    f = args[0]
    d = frozenset().union(*[x.deps for x in args])
    fu = min(x.fuerza for x in args)
    if nom == "sqrt":
        if f.lo < 0:
            raise ErrorEvidencia("sqrt de un intervalo con negativos")
        return Val(math.sqrt(f.lo), math.sqrt(f.hi), fu, d)
    if nom == "abs":
        lo = 0.0 if f.lo <= 0 <= f.hi else min(abs(f.lo), abs(f.hi))
        return Val(lo, max(abs(f.lo), abs(f.hi)), fu, d)
    if nom == "exp":
        return Val(math.exp(f.lo), math.exp(f.hi), fu, d)
    if nom == "log":
        if f.lo <= 0:
            raise ErrorEvidencia("log de un intervalo no positivo")
        return Val(math.log(f.lo), math.log(f.hi), fu, d)
    if nom == "min":
        return Val(min(x.lo for x in args), min(x.hi for x in args), fu, d)
    return Val(max(x.lo for x in args), max(x.hi for x in args), fu, d)


def op_pt(o, a, b):
    if o == "+":
        return a + b
    if o == "-":
        return a - b
    if o == "*":
        return a * b
    if o == "/":
        return a / b
    return a ** b


FN_PT = {"sqrt": math.sqrt, "abs": abs, "exp": math.exp, "log": math.log, "min": min, "max": max}


# ------------------------------------------------------------------ intérprete
class Programa:
    def __init__(self):
        self.hojas = {}     # nombre -> dict(lo, hi, fuerza, fuente, tipo)
        self.defs = {}      # nombre -> AST
        self.informe = []

    def eval_int(self, n):
        k = n[0]
        if k == "num":
            return Val(n[1], n[1], 3)
        if k == "var":
            nom = n[1]
            if nom in self.defs:
                return self.eval_int(self.defs[nom])
            if nom in self.hojas:
                h = self.hojas[nom]
                return Val(h["lo"], h["hi"], h["fuerza"], frozenset([nom]))
            raise ErrorEvidencia(f"nombre sin definir: {nom}")
        if k == "neg":
            v = self.eval_int(n[1])
            return Val(-v.hi, -v.lo, v.fuerza, v.deps)
        if k == "bin":
            return op_int(n[1], self.eval_int(n[2]), self.eval_int(n[3]))
        return fn_int(n[1], [self.eval_int(a) for a in n[2]])

    def eval_pt(self, n, pt):
        k = n[0]
        if k == "num":
            return n[1]
        if k == "var":
            nom = n[1]
            if nom in self.defs:
                return self.eval_pt(self.defs[nom], pt)
            return pt[nom]
        if k == "neg":
            return -self.eval_pt(n[1], pt)
        if k == "bin":
            return op_pt(n[1], self.eval_pt(n[2], pt), self.eval_pt(n[3], pt))
        return FN_PT[n[1]](*[self.eval_pt(a, pt) for a in n[2]])

    def sentencia(self, linea, n):
        toks = tokenizar(linea, n)
        if not toks:
            return
        p = Parser(toks, n)
        kw = p.toma("nom")[1]
        if kw in FUERZA:
            nom = p.toma("nom")[1]
            if kw == "supuesto" and p.es("nom", "en"):
                v = Val(0.0, 0.0)            # el valor típico es opcional: manda el rango
            else:
                p.toma("op", "=")
                v = self.eval_int(p.expr())
            lo, hi, fuente = v.lo, v.hi, ""
            if kw == "supuesto":
                if not (p.es("nom") and p.peek()[1] == "en"):
                    raise ErrorEvidencia(f"línea {n}: un supuesto necesita «en [lo, hi]»")
                p.toma("nom")
                p.toma("op", "[")
                a = self.eval_int(p.expr())
                p.toma("op", ",")
                b = self.eval_int(p.expr())
                p.toma("op", "]")
                lo, hi = a.lo, b.hi
                if lo > hi:
                    raise ErrorEvidencia(f"línea {n}: rango invertido")
            elif p.es("op", "±"):
                p.toma()
                err = abs(self.eval_int(p.expr()).lo)
                lo, hi = v.lo - err, v.hi + err
            while p.es("nom", "fuente") or p.es("nom", "porque"):
                p.toma()
                fuente = p.toma("str")[1]
            if p.peek()[0] != "fin":
                raise ErrorEvidencia(f"línea {n}: sobra «{p.peek()[1]}»")
            self.hojas[nom] = dict(lo=lo, hi=hi, fuerza=FUERZA[kw], fuente=fuente, tipo=kw)
        elif kw == "def":
            nom = p.toma("nom")[1]
            p.toma("op", "=")
            self.defs[nom] = p.expr()
            self.eval_int(self.defs[nom])
        elif kw == "afirmar":
            izq = p.expr()
            op = p.toma("op")[1]
            if op not in ("<", "<=", ">", ">=", "=="):
                raise ErrorEvidencia(f"línea {n}: comparador inválido {op}")
            der = p.expr()
            nombre = ""
            if p.es("nom", "llamado"):
                p.toma()
                nombre = p.toma("str")[1]
            self.informe.append(self.juzga(izq, op, der, nombre or linea.strip(), n))
        else:
            raise ErrorEvidencia(f"línea {n}: sentencia desconocida «{kw}»")

    def juzga(self, izq, op, der, nombre, n, muestras=20000):
        d = self.eval_int(("bin", "-", izq, der))
        cumple = {"<": lambda x: x < 0, "<=": lambda x: x <= 0, ">": lambda x: x > 0,
                  ">=": lambda x: x >= 0, "==": lambda x: abs(x) < 1e-12}[op]
        gar = {"<": d.hi < 0, "<=": d.hi <= 0, ">": d.lo > 0, ">=": d.lo >= 0, "==": d.lo == d.hi == 0}[op]
        nunca = {"<": d.lo >= 0, "<=": d.lo > 0, ">": d.hi <= 0, ">=": d.hi < 0, "==": d.lo > 0 or d.hi < 0}[op]
        hojas = sorted(d.deps)
        base = {h: (self.hojas[h]["lo"] + self.hojas[h]["hi"]) / 2 for h in self.hojas}
        r = {"afirmacion": nombre, "linea": n, "etiqueta": NOMBRE_FUERZA[d.fuerza], "depende_de": [
            {"nombre": h, "tipo": self.hojas[h]["tipo"], "rango": [self.hojas[h]["lo"], self.hojas[h]["hi"]],
             "fuente": self.hojas[h]["fuente"]} for h in hojas]}
        if gar:
            r["veredicto"] = "GARANTIZADA"
        elif nunca:
            r["veredicto"] = "REFUTADA"
        else:
            rng = random.Random(0)
            ok, contra = 0, None
            libres = [h for h in hojas if self.hojas[h]["lo"] != self.hojas[h]["hi"]]
            for _ in range(muestras):
                pt = dict(base)
                for h in libres:
                    pt[h] = rng.uniform(self.hojas[h]["lo"], self.hojas[h]["hi"])
                try:
                    c = cumple(self.eval_pt(izq, pt) - self.eval_pt(der, pt))
                except (ValueError, ZeroDivisionError, OverflowError):
                    continue
                if c:
                    ok += 1
                elif contra is None:
                    contra = {h: round(pt[h], 6) for h in libres}
            frac = ok / muestras
            r["fraccion_que_cumple"] = round(frac, 4)
            if contra is None:
                r["veredicto"] = "NO_REFUTADA"
            elif ok == 0:
                r["veredicto"] = "REFUTADA"
            else:
                r["veredicto"] = "CONDICIONAL"
            if contra is not None:
                r["contraejemplo"] = contra
        return r

    def correr(self, texto):
        for n, linea in enumerate(texto.splitlines(), 1):
            if linea.split("#", 1)[0].strip():
                self.sentencia(linea, n)
        return self.informe


def formatea(informe):
    out = []
    for r in informe:
        out.append(f"[{r['veredicto']:<11}] {r['afirmacion']}  (etiqueta: {r['etiqueta']})")
        for d in r["depende_de"]:
            rg = f"{d['rango'][0]:g}" if d["rango"][0] == d["rango"][1] else f"{d['rango'][0]:g}..{d['rango'][1]:g}"
            out.append(f"    · {d['nombre']} [{d['tipo']}] {rg}" + (f"  — {d['fuente']}" if d["fuente"] else ""))
        if "fraccion_que_cumple" in r:
            out.append(f"    cumple en ≈{r['fraccion_que_cumple']*100:.0f}% del espacio de supuestos (muestreo uniforme, heurístico)")
        if "contraejemplo" in r:
            out.append("    contraejemplo: " + ", ".join(f"{k}={v}" for k, v in r["contraejemplo"].items()))
    return "\n".join(out)


def main(argv):
    if len(argv) < 2:
        print("uso: python3 evidencia.py programa.ev [--json]")
        return 2
    try:
        informe = Programa().correr(open(argv[1], encoding="utf-8").read())
    except ErrorEvidencia as e:
        print(f"error: {e}")
        return 2
    print(json.dumps(informe, ensure_ascii=False, indent=2) if "--json" in argv else formatea(informe))
    return 0 if all(r["veredicto"] in ("GARANTIZADA", "NO_REFUTADA") for r in informe) else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
