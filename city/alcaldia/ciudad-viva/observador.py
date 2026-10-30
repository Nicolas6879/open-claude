#!/usr/bin/env python3
"""Observador de la ciudad: vigila el repo y escribe, una por línea y en JSON, lo que pasa de verdad:
  - mensajes nuevos del bus (city/alcaldia/bus/ciudad.jsonl)
  - commits nuevos (git log)
  - actividad por casa (archivos cambiados en city/<casa>/), agregada cada 30 s en una sola línea
Solo lee el repo. Lo usa Monitor para despertar al Alcalde, que empuja cada evento a la página «Ciudad viva».
Uso: python3 observador.py [segundos_de_ejecución]"""
import json
import subprocess
import sys
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[3]
BUS = RAIZ / "city" / "alcaldia" / "bus" / "ciudad.jsonl"
CASAS = RAIZ / "city"


def git(*args):
    return subprocess.run(["git", "-C", str(RAIZ), *args], capture_output=True, text=True).stdout.strip()


def snapshot():
    out = {}
    for casa in CASAS.iterdir():
        if not casa.is_dir() or not casa.name.startswith("casa-"):
            continue
        for p in casa.rglob("*"):
            if p.is_file() and "__pycache__" not in p.parts and p.suffix != ".pyc":
                try:
                    out[str(p)] = (casa.name, p.stat().st_mtime_ns)
                except OSError:
                    pass
    return out


def emite(ev, k=[0]):
    k[0] += 1
    t = int(time.time() * 1000)
    ev.update({"id": f"{t}-{k[0]}", "t": t})
    print(json.dumps(ev, ensure_ascii=False), flush=True)


def main(duracion):
    fin = time.time() + duracion
    bus_vistos = sum(1 for _ in open(BUS, encoding="utf-8")) if BUS.exists() else 0
    cabeza = git("rev-parse", "HEAD")
    prev = snapshot()
    acum, ultimo_trabajo = {}, time.time()
    while time.time() < fin:
        time.sleep(4)
        if BUS.exists():
            lineas = [l for l in open(BUS, encoding="utf-8").read().splitlines() if l.strip()]
            for l in lineas[bus_vistos:]:
                try:
                    m = json.loads(l)
                    emite({"tipo": "bus", "de": m["de"], "a": m["a"], "texto": m["cuerpo"][:220], "etiqueta": m.get("etiqueta") or ""})
                except Exception:
                    pass
            bus_vistos = len(lineas)
        nueva = git("rev-parse", "HEAD")
        if nueva and nueva != cabeza:
            for sub in reversed(git("log", "--format=%s", f"{cabeza}..{nueva}").splitlines()):
                emite({"tipo": "commit", "texto": sub[:140]})
            cabeza = nueva
        cur = snapshot()
        for ruta, (casa, mt) in cur.items():
            if prev.get(ruta, (None, None))[1] != mt:
                acum[casa] = acum.get(casa, 0) + 1
        prev = cur
        if acum and time.time() - ultimo_trabajo >= 30:
            emite({"tipo": "trabajo", "casas": sorted(acum), "n": sum(acum.values())})
            acum, ultimo_trabajo = {}, time.time()


if __name__ == "__main__":
    main(float(sys.argv[1]) if len(sys.argv) > 1 else 1500)
