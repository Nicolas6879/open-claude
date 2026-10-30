#!/usr/bin/env python3
"""Crónica de la ciudad: lee el historial de git, city.json y errores.json y
escribe cronica.html (un solo archivo, sin dependencias). Determinista para un
mismo historial. Uso: python3 chronicle.py"""
import html
import json
import math
import re
import subprocess
from collections import Counter
from pathlib import Path

AQUI = Path(__file__).resolve().parent
RAIZ = AQUI.parents[1]


def git_log():
    out = subprocess.run(
        ["git", "-C", str(RAIZ), "log", "--reverse", "--format=%h|%ct|%s"],
        capture_output=True, text=True, check=True).stdout.strip().splitlines()
    commits = []
    for linea in out:
        h, t, s = linea.split("|", 2)
        commits.append({"hash": h, "t": int(t), "msg": s})
    return commits


def fila(msg):
    m = re.match(r"(casa-[a-z]+):", msg)
    if m:
        return m.group(1)
    if msg.startswith("index.html"):
        return "mapa"
    return "alcaldia"


def hora(t):
    import time
    return time.strftime("%H:%M", time.gmtime(t))


def svg_linea(commits, casas):
    filas = ["alcaldia"] + [c["id"] for c in casas] + ["mapa"]
    ids = {f: i for i, f in enumerate(filas)}
    w, h0, dy, mx = 920, 36, 34, 150
    alto = h0 + dy * len(filas) + 30
    n = max(len(commits) - 1, 1)
    p = [f'<svg viewBox="0 0 {w} {alto}" role="img" aria-label="Línea de tiempo de commits por casa">']
    for f, i in ids.items():
        y = h0 + dy * i
        p.append(f'<line x1="{mx}" y1="{y}" x2="{w-20}" y2="{y}" class="grid"/>')
        p.append(f'<text x="{mx-10}" y="{y+4}" text-anchor="end" class="lbl">{html.escape(f)}</text>')
    for k, c in enumerate(commits):
        x = mx + (w - mx - 30) * k / n
        f = fila(c["msg"])
        y = h0 + dy * ids.get(f, 0)
        cls = "dot a" if f == "alcaldia" else "dot"
        p.append(f'<circle cx="{x:.1f}" cy="{y}" r="6.5" class="{cls}"><title>{html.escape(hora(c["t"]))} · {html.escape(c["hash"])} · {html.escape(c["msg"])}</title></circle>')
        if k % 3 == 0 or k == len(commits) - 1:
            p.append(f'<text x="{x:.1f}" y="{alto-10}" text-anchor="middle" class="tick">{hora(c["t"])}</text>')
    p.append("</svg>")
    return "\n".join(p)


def svg_grafo(casas, rels):
    nodos = [("ayuntamiento", "Alcaldía")] + [(c["id"], c["nombre"]) for c in casas]
    cx, cy, r, w, h = 290, 210, 135, 580, 420
    pos = {}
    for i, (nid, _) in enumerate(nodos[1:]):
        a = -math.pi / 2 + 2 * math.pi * i / max(len(nodos) - 1, 1)
        pos[nid] = (cx + r * math.cos(a), cy + r * math.sin(a))
    pos["ayuntamiento"] = (cx, cy)
    p = [f'<svg viewBox="0 0 {w} {h}" role="img" aria-label="Quién usa los datos de quién">',
         '<defs><marker id="f" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M0 0L10 5L0 10z" class="flecha"/></marker></defs>']
    for rel in rels:
        if rel["de"] in pos and rel["a"] in pos:
            (x1, y1), (x2, y2) = pos[rel["de"]], pos[rel["a"]]
            d = math.hypot(x2 - x1, y2 - y1) or 1
            x2 -= (x2 - x1) / d * 26
            y2 -= (y2 - y1) / d * 26
            p.append(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" class="arista" marker-end="url(#f)"><title>{html.escape(rel["de"])} → {html.escape(rel["a"])}: {html.escape(rel["que"])}</title></line>')
    for nid, nombre in nodos:
        x, y = pos[nid]
        p.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="22" class="nodo{" alc" if nid=="ayuntamiento" else ""}"/>')
        ox, oy = (x - cx, y - cy)
        d = math.hypot(ox, oy) or 1
        lx, ly = (x + ox / d * 40, y + oy / d * 36 + 4) if nid != "ayuntamiento" else (x, y + 40)
        anc = "middle" if abs(ox) < 30 else ("start" if ox > 0 else "end")
        p.append(f'<text x="{lx:.1f}" y="{ly:.1f}" text-anchor="{anc}" class="lbl">{html.escape(nombre)}</text>')
    p.append("</svg>")
    return "\n".join(p)


def tabla_errores(errores):
    filas = []
    for e in errores:
        filas.append("<tr><td><span class='quien q-{}'>{}</span></td><td>{}</td><td>{}</td><td>{}</td></tr>".format(
            html.escape(e["quien"].lower()), html.escape(e["quien"]), html.escape(e["que"]),
            html.escape(e["como_se_detecto"]), html.escape(e["costo"])))
    return "\n".join(filas)


def main():
    commits = git_log()
    ciudad = json.loads((RAIZ / "city.json").read_text(encoding="utf-8"))
    errores = json.loads((AQUI / "errores.json").read_text(encoding="utf-8"))
    casas, rels = ciudad["casas"], ciudad.get("relaciones", [])
    cuenta = Counter(e["quien"] for e in errores)
    del_alcalde = cuenta.get("Alcalde", 0)
    listas = sum(1 for c in casas if c.get("estado") == "lista")
    barras = "".join(
        f"<li><span class='quien q-{html.escape(q.lower())}'>{html.escape(q)}</span><b style='width:{n*28}px'></b> {n}</li>"
        for q, n in cuenta.most_common())
    doc = f"""<!doctype html>
<html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Crónica de Open Claude</title>
<style>
:root{{--bg:#f4efe4;--fg:#1d2433;--mut:#5d6578;--card:#fffdf7;--line:#d9d0bd;--ac:#9a3b2e;--ok:#2a7f62;--alc:#9a3b2e}}
@media (prefers-color-scheme:dark){{:root{{--bg:#12141c;--fg:#e8e6df;--mut:#9aa0b3;--card:#1a1d28;--line:#343a4d;--ac:#e0705f;--ok:#4fc29b;--alc:#e0705f}}}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--fg);font:16px/1.55 system-ui,sans-serif}}
main{{max-width:980px;margin:0 auto;padding:28px 16px 60px}}
h1{{font:700 2.1rem Georgia,serif;margin:0 0 4px}}h2{{font:700 1.3rem Georgia,serif;margin:34px 0 8px}}
.sub{{color:var(--mut);margin:0 0 20px}}.card{{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:16px;overflow-x:auto}}
.kpis{{display:flex;flex-wrap:wrap;gap:10px;margin:12px 0}}.kpi{{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:8px 14px}}
.kpi b{{font-size:1.5rem;display:block}}svg{{width:100%;height:auto;min-width:560px}}.grafo svg{{max-width:600px;display:block;margin:0 auto}}
.grid{{stroke:var(--line);stroke-width:1}}.lbl{{fill:var(--fg);font-size:12px}}.tick{{fill:var(--mut);font-size:10px}}
.dot{{fill:var(--ok);stroke:var(--card);stroke-width:2}}.dot.a{{fill:var(--alc)}}
.arista{{stroke:var(--mut);stroke-width:1.6}}.flecha{{fill:var(--mut)}}.nodo{{fill:var(--ok);opacity:.85}}.nodo.alc{{fill:var(--alc)}}
table{{width:100%;border-collapse:collapse;font-size:.92rem;min-width:640px}}th,td{{text-align:left;vertical-align:top;padding:8px 8px;border-bottom:1px solid var(--line)}}
th{{color:var(--mut);font-weight:600}}.quien{{display:inline-block;padding:1px 9px;border-radius:99px;border:1px solid var(--line);font-size:.8rem;white-space:nowrap}}
.q-alcalde{{border-color:var(--alc);color:var(--alc)}}ul.bar{{list-style:none;padding:0;margin:0}}ul.bar li{{display:flex;align-items:center;gap:8px;margin:5px 0}}
ul.bar b{{display:inline-block;height:12px;background:var(--ac);border-radius:6px}}.nota{{color:var(--mut);font-size:.9rem}}
</style></head><body><main>
<h1>Crónica de Open Claude</h1>
<p class="sub">Escrita por el Alcalde a partir del historial real de git y de un registro de errores que él mismo mantiene. Se regenera con <code>python3 city/alcaldia/chronicle.py</code>.</p>
<div class="kpis"><div class="kpi"><b>{len(commits)}</b>commits</div><div class="kpi"><b>{len(casas)}</b>casas ({listas} listas)</div><div class="kpi"><b>{len(errores)}</b>errores registrados</div><div class="kpi"><b>{del_alcalde}</b>de ellos, del Alcalde</div></div>
<h2>Línea de tiempo</h2><div class="card">{svg_linea(commits, casas)}</div>
<p class="nota">Un punto por commit, una fila por casa; en rojo, los commits del Alcalde. El eje es el orden de los commits (las horas son de reloj y hay pausas largas entre rondas).</p>
<h2>Quién usa los datos de quién</h2><div class="card grafo">{svg_grafo(casas, rels)}</div>
<p class="nota">Flecha de A a B: A usa o audita lo que produce B. Pasa el cursor sobre una flecha para ver qué.</p>
<h2>Registro de errores</h2>
<div class="card"><ul class="bar">{barras}</ul></div>
<p class="nota">Que el Alcalde tenga más entradas no significa que se equivoque más: significa que es quien más cosas hace y que se las anota. Los habitantes aparecen aquí solo por errores que ellos mismos reportaron en su LOG o que yo detecté al revisar.</p>
<div class="card"><table><thead><tr><th>Quién</th><th>Qué pasó</th><th>Cómo se detectó</th><th>Qué costó / cómo se resolvió</th></tr></thead><tbody>
{tabla_errores(errores)}
</tbody></table></div>
</main></body></html>
"""
    (AQUI / "cronica.html").write_text(doc, encoding="utf-8")
    print(f"cronica.html: {len(commits)} commits, {len(errores)} errores, {len(casas)} casas")


if __name__ == "__main__":
    main()
