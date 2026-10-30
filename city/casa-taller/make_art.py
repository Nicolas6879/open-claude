#!/usr/bin/env python3
"""Pintora (casa-taller): obras generativas en SVG hechas con datos de las casas vecinas.

Entradas (solo lectura):
    casa-mosca/out/activity.json   circuito olfativo sintetico de la mosca
    casa-agora/out/results.json    mercado sintetico (AMM x*y=k)

Salidas:
    gallery/*.svg                  cinco obras autonomas

Uso:
    PYTHONDONTWRITEBYTECODE=1 python3 make_art.py

Determinista: no usa azar. Dos ejecuciones producen los mismos bytes.
"""
from __future__ import annotations

import bisect
import json
import math
from collections import defaultdict
from pathlib import Path
from xml.sax.saxutils import escape

HERE = Path(__file__).resolve().parent
CITY = Path(__file__).resolve().parents[1]
ACTIVITY = CITY / "casa-mosca" / "out" / "activity.json"
RESULTS = CITY / "casa-agora" / "out" / "results.json"
GALLERY = HERE / "gallery"

SERIF = "Georgia, 'Times New Roman', serif"
SANS = "system-ui, -apple-system, 'Segoe UI', Helvetica, Arial, sans-serif"

ODOUR_COL = {"A": "#f08a3e", "B": "#2ec4b6", "C": "#8d99ae"}
GOLD = "#ffd166"


# ---------------------------------------------------------------- utilidades
def num(v: float) -> str:
    s = f"{v:.2f}"
    if "." in s:
        s = s.rstrip("0").rstrip(".")
    return "0" if s in ("-0", "") else s


def ramp(stops, t: float) -> str:
    """Interpolacion lineal entre paradas [(pos, '#rrggbb'), ...] con pos en [0, 1]."""
    t = min(1.0, max(0.0, t))
    for (p0, c0), (p1, c1) in zip(stops, stops[1:]):
        if t <= p1:
            u = 0.0 if p1 == p0 else (t - p0) / (p1 - p0)
            a = [int(c0[k:k + 2], 16) for k in (1, 3, 5)]
            b = [int(c1[k:k + 2], 16) for k in (1, 3, 5)]
            return "#" + "".join(f"{round(a[j] + (b[j] - a[j]) * u):02x}" for j in range(3))
    return stops[-1][1]


def text(x, y, s, size=14, fill="#000", anchor="start", weight="normal", family=SANS, extra=""):
    return (f'<text x="{num(x)}" y="{num(y)}" font-size="{size}" fill="{fill}" '
            f'text-anchor="{anchor}" font-family="{family}" font-weight="{weight}"{extra}>'
            f"{escape(s)}</text>")


def svg_doc(w, h, title, desc, body, bg):
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" '
        f'width="{w}" height="{h}" role="img" aria-labelledby="ttl dsc">\n'
        f'<title id="ttl">{escape(title)}</title>\n'
        f'<desc id="dsc">{escape(desc)}</desc>\n'
        f'<rect width="{w}" height="{h}" fill="{bg}"/>\n'
        + "\n".join(body)
        + "\n</svg>\n"
    )


def ticks_between(lo, hi, step):
    v = math.ceil(lo / step) * step
    out = []
    while v <= hi + 1e-9:
        out.append(round(v, 6))
        v += step
    return out


# ---------------------------------------------------------------- carga
def validate_activity(a):
    for key in ("meta", "neurons", "spikes", "stimuli"):
        if key not in a:
            raise ValueError(f"activity.json sin clave '{key}'")
    ids = sorted(n["id"] for n in a["neurons"])
    if ids != list(range(len(ids))):
        raise ValueError("activity.json: ids de neurona no contiguos desde 0")
    if float(a["meta"]["duration_ms"]) <= 0:
        raise ValueError("activity.json: duration_ms no valido")


def validate_results(r):
    for key in ("meta", "price_path", "pool_path"):
        if key not in r:
            raise ValueError(f"results.json sin clave '{key}'")
    n = len(r["price_path"])
    if len(r["pool_path"]["reserve_x"]) != n or len(r["pool_path"]["reserve_y"]) != n:
        raise ValueError("results.json: longitudes de precio y reservas no coinciden")
    if any(x <= 0 or y <= 0 for x, y in zip(r["pool_path"]["reserve_x"], r["pool_path"]["reserve_y"])):
        raise ValueError("results.json: reservas no positivas")


class Fly:
    def __init__(self, a):
        self.meta = a["meta"]
        self.duration = float(a["meta"]["duration_ms"])
        self.neurons = sorted(a["neurons"], key=lambda n: n["id"])
        self.type_of = {n["id"]: n["type"] for n in self.neurons}
        self.kc = [n for n in self.neurons if n["type"] == "KC"]
        self.mbon_ids = [n["id"] for n in self.neurons if n["type"] == "MBON"]
        self.stimuli = list(a["stimuli"])
        self.stim = {s["name"]: s for s in self.stimuli}
        self.spikes = [(float(t), int(i)) for t, i in a["spikes"]]

    def window_counts(self, name):
        s = self.stim[name]
        c = defaultdict(int)
        for t, i in self.spikes:
            if s["t_start"] <= t < s["t_end"]:
                c[i] += 1
        return c

    def mbon_total(self, name):
        c = self.window_counts(name)
        return sum(c[i] for i in self.mbon_ids)


class Market:
    def __init__(self, r):
        self.meta = r["meta"]
        self.price = [float(v) for v in r["price_path"]]
        self.rx = [float(v) for v in r["pool_path"]["reserve_x"]]
        self.ry = [float(v) for v in r["pool_path"]["reserve_y"]]
        self.k = [x * y for x, y in zip(self.rx, self.ry)]
        self.marg = [y / x for x, y in zip(self.rx, self.ry)]


def odour_of(name):
    for letter in "ABC":
        if f"_{letter}" in name:
            return letter
    return None


# ---------------------------------------------------------------- obra 1: cielo de espigas
def fig_cielo(fly: Fly):
    W, H = 1200, 780
    BG = "#0b0d14"
    X0, X1 = 150.0, 1160.0
    T = fly.duration

    def xt(t):
        return X0 + t / T * (X1 - X0)

    bands = [("ORN", 80.0), ("PN", 80.0), ("APL", 8.0), ("KC", 280.0), ("MBON", 24.0), ("DAN", 24.0)]
    gap = 6.0
    ycoord, box = {}, {}
    y = 140.0
    for typ, h in bands:
        ids = sorted(i for i, t in fly.type_of.items() if t == typ)
        box[typ] = (y, h, len(ids))
        for j, i in enumerate(ids):
            ycoord[i] = y + (j + 0.5) * h / len(ids)
        y += h + gap
    plot_bottom = y - gap

    style = {
        "ORN": ("#7fb3d5", 0.75, 1.1),
        "PN": ("#f5b041", 0.75, 1.1),
        "APL": ("#c39bd3", 1.0, 1.4),
        "KC": ("#5fd3c0", 0.38, 1.0),
        "MBON": ("#ff4d4d", 1.0, 1.8),
        "DAN": ("#ffe066", 0.9, 1.8),
    }

    paths = defaultdict(list)
    for t, i in fly.spikes:
        paths[fly.type_of[i]].append(f"M{xt(t):.1f} {ycoord[i]:.1f}h1.2")

    body = []
    # fondo de fases (antes/despues): franjas tenues
    for name in ("pre_A", "post_A"):
        s = fly.stim[name]
        body.append(f'<rect x="{num(xt(s["t_start"]))}" y="140" width="{num(xt(s["t_end"]) - xt(s["t_start"]))}" '
                    f'height="{num(plot_bottom - 140)}" fill="#ffffff" fill-opacity="0.07"/>')
    # separadores de fase
    for t_sep in (6250.0, 18250.0):
        body.append(f'<line x1="{num(xt(t_sep))}" y1="140" x2="{num(xt(t_sep))}" y2="{num(plot_bottom)}" '
                    f'stroke="#ffffff" stroke-opacity="0.18" stroke-dasharray="3 4"/>')
    # etiquetas de bandas
    for typ, _ in bands:
        yb, h, n = box[typ]
        body.append(text(X0 - 12, yb + h / 2 + 4, f"{typ} · {n}", size=12, fill="#c9d1e0", anchor="end"))
    # espigas por tipo
    for typ, _ in bands:
        col, op, sw = style[typ]
        body.append(f'<path d="{"".join(paths[typ])}" stroke="{col}" stroke-opacity="{op}" '
                    f'stroke-width="{sw}" fill="none"/>')
    # franja de protocolo
    strip_y = 104.0
    body.append(text(X0 - 12, strip_y + 9, "protocolo", size=11, fill="#8a93a6", anchor="end"))
    for s in fly.stimuli:
        letter = odour_of(s["name"])
        if letter is None:
            continue
        x_a, x_b = xt(s["t_start"]), xt(s["t_end"])
        body.append(f'<rect x="{num(x_a)}" y="{strip_y}" width="{num(x_b - x_a - 0.6)}" height="12" '
                    f'fill="{ODOUR_COL[letter]}" fill-opacity="0.9"/>')
        if x_b - x_a >= 20:
            body.append(text((x_a + x_b) / 2, strip_y + 9.5, letter, size=10, fill="#111",
                             anchor="middle", weight="bold"))
    for s in fly.stimuli:
        if s["name"].startswith("reward"):
            x_a, x_b = xt(s["t_start"]), xt(s["t_end"])
            body.append(f'<rect x="{num(x_a)}" y="{strip_y + 14}" width="{num(x_b - x_a - 0.6)}" height="4" '
                        f'fill="{GOLD}"/>')
    body.append(text(X0 - 12, strip_y + 18, "recompensa", size=11, fill="#8a93a6", anchor="end"))
    # eje x
    body.append(f'<line x1="{num(X0)}" y1="{num(plot_bottom + 10)}" x2="{num(X1)}" y2="{num(plot_bottom + 10)}" '
                f'stroke="#5b6478"/>')
    for sec in range(0, int(T / 1000) + 1, 5):
        xx = xt(sec * 1000.0)
        body.append(f'<line x1="{num(xx)}" y1="{num(plot_bottom + 10)}" x2="{num(xx)}" y2="{num(plot_bottom + 15)}" '
                    f'stroke="#5b6478"/>')
        body.append(text(xx, plot_bottom + 31, f"{sec} s", size=12, fill="#8a93a6", anchor="middle"))
    # fases
    fy = plot_bottom + 56
    body.append(text((xt(500) + xt(6000)) / 2, fy, "pre-prueba (A, B, C)", size=13, fill="#c9d1e0", anchor="middle"))
    body.append(text((xt(6500) + xt(18000)) / 2, fy, "entrenamiento: A + recompensa, B sin recompensa",
                     size=13, fill="#c9d1e0", anchor="middle"))
    body.append(text((xt(18500) + xt(22500)) / 2, fy, "post-prueba", size=13, fill="#c9d1e0", anchor="middle"))

    # titulo y anotacion con datos
    pre_a, post_a = fly.mbon_total("pre_A"), fly.mbon_total("post_A")
    pre_b, post_b = fly.mbon_total("pre_B"), fly.mbon_total("post_B")
    body.insert(0, text(X0, 52, "Cielo de espigas", size=34, fill="#f2efe6", family=SERIF, weight="bold"))
    body.insert(1, text(X0, 78, "23 s de una mosca sintética aprendiendo que el olor A trae recompensa. "
                                "Cada raya es una espiga.", size=15, fill="#aab2c5"))
    body.insert(2, text(X1, 52, f"MBON ante A: {pre_a} → {post_a} espigas", size=15,
                        fill="#ff7b7b", anchor="end", weight="bold"))
    body.insert(3, text(X1, 74, f"MBON ante B: {pre_b} → {post_b} (casi no cambia)", size=13,
                        fill="#aab2c5", anchor="end"))
    body.append(text(X0, H - 16,
                     "Eje x: tiempo del protocolo (ms). Eje y: neuronas agrupadas por tipo, cada banda a alto fijo "
                     "(no es escala por número de neuronas). Fuente: activity.json (sintético, semilla 7).",
                     size=11, fill="#7d8699"))

    desc = ("Raster de las 70149 espigas del protocolo de la mosca sintética (activity.json). "
            "Eje x: tiempo en ms (0 a 23 s). Eje y: 2109 neuronas agrupadas por tipo (ORN, PN, APL, KC, MBON, DAN), "
            "cada banda con alto fijo. Color: tipo de neurona. Franja superior: olor presentado (A naranja, B turquesa, "
            "C gris) y recompensa (dorado). Los números de MBON son espigas en las ventanas pre_A y post_A (y pre_B, post_B) "
            "de 1 s cada una. Mapeo: cada espiga es una raya; la altura de la banda es el tipo, no el número de neuronas.")
    return svg_doc(W, H, "Cielo de espigas: raster de la mosca sintética por tipo", desc, body, BG)


# ---------------------------------------------------------------- obra 2: nube KC antes y despues
def fig_kc(fly: Fly):
    W, H = 1200, 640
    BG = "#0b0d14"
    S = 330.0
    PX = [70.0, 435.0, 800.0]
    PY = 150.0
    XD = (0.38, 0.78)

    pre = fly.window_counts("pre_A")
    post = fly.window_counts("post_A")
    kc_ids = [n["id"] for n in fly.kc]
    pos = {n["id"]: (n["x"], n["y"]) for n in fly.kc}

    def place(i, ox):
        x, y = pos[i]
        return ox + (x - XD[0]) / (XD[1] - XD[0]) * S, PY + (1 - y) * S

    count_stops = [(0.0, "#1b1f33"), (0.35, "#5b2a86"), (0.65, "#e4572e"), (1.0, "#fff3b0")]
    diff_stops = [(0.0, "#4cc9f0"), (0.5, "#1b1f33"), (1.0, "#ff7b54")]

    body = []
    titles = ["Antes · pre_A", "Después · post_A", "Cambio · después − antes"]
    for p, ox in enumerate(PX):
        body.append(text(ox, PY - 14, titles[p], size=16, fill="#e7e3d8", weight="bold"))
        body.append(f'<rect x="{num(ox)}" y="{num(PY)}" width="{num(S)}" height="{num(S)}" fill="none" '
                    f'stroke="#2a3044"/>')
        if p < 2:
            counts = pre if p == 0 else post
            order = sorted(kc_ids, key=lambda i: counts[i])
            for i in order:
                x, y = place(i, ox)
                v = min(counts[i], 8) / 8.0
                body.append(f'<circle cx="{num(x)}" cy="{num(y)}" r="3.6" fill="{ramp(count_stops, v)}"/>')
        else:
            order = sorted(kc_ids, key=lambda i: abs(post[i] - pre[i]))
            for i in order:
                x, y = place(i, ox)
                d = max(-5, min(5, post[i] - pre[i]))
                body.append(f'<circle cx="{num(x)}" cy="{num(y)}" r="3.6" '
                            f'fill="{ramp(diff_stops, (d / 5.0 + 1) / 2)}"/>')

    tot_pre = sum(pre[i] for i in kc_ids)
    tot_post = sum(post[i] for i in kc_ids)
    chg = (tot_post / tot_pre - 1) * 100
    act_pre = sum(1 for i in kc_ids if pre[i] > 0)
    act_post = sum(1 for i in kc_ids if post[i] > 0)
    m_pre, m_post = fly.mbon_total("pre_A"), fly.mbon_total("post_A")

    body.insert(0, text(70, 60, "Nube de Kenyon iluminada por el olor A", size=32, fill="#f2efe6",
                        family=SERIF, weight="bold"))
    body.insert(1, text(70, 88, "Cada punto es una célula de Kenyon (KC) en su posición del archivo. "
                                "Color: espigas durante 1 s de olor A.", size=15, fill="#aab2c5"))

    # leyenda de color para conteos
    ly = 530.0
    grad = ('<defs><linearGradient id="gc" x1="0" x2="1" y1="0" y2="0">'
            + "".join(f'<stop offset="{num(p)}" stop-color="{c}"/>' for p, c in count_stops)
            + '</linearGradient><linearGradient id="gd" x1="0" x2="1" y1="0" y2="0">'
            + "".join(f'<stop offset="{num(p)}" stop-color="{c}"/>' for p, c in diff_stops)
            + "</linearGradient></defs>")
    body.append(grad)
    body.append(text(70, ly - 6, "espigas en 1 s", size=12, fill="#aab2c5"))
    body.append(f'<rect x="70" y="{num(ly)}" width="{num(S)}" height="12" fill="url(#gc)"/>')
    body.append(text(70, ly + 28, "0", size=12, fill="#aab2c5"))
    body.append(text(70 + S, ly + 28, "8 o más", size=12, fill="#aab2c5", anchor="end"))
    body.append(text(800, ly - 6, "cambio en espigas (−5 a +5)", size=12, fill="#aab2c5"))
    body.append(f'<rect x="800" y="{num(ly)}" width="{num(S)}" height="12" fill="url(#gd)"/>')
    body.append(text(800, ly + 28, "−5 (menos)", size=12, fill="#aab2c5"))
    body.append(text(800 + S, ly + 28, "+5 (más)", size=12, fill="#aab2c5", anchor="end"))

    body.append(text(70, 596,
                     f"Espigas de las 2000 KC: {tot_pre} antes, {tot_post} después ({chg:+.0f} %). "
                     f"KC activas: {act_pre} → {act_post}.",
                     size=15, fill="#e7e3d8"))
    body.append(text(70, 618,
                     f"La nube casi no cambia, pero la salida sí: MBON ante A pasa de {m_pre} a {m_post} espigas. "
                     "El aprendizaje está en la salida, no en la entrada.",
                     size=15, fill="#ff9b9b"))

    desc = ("Tres paneles de la nube de 2000 células de Kenyon de la mosca sintética (activity.json). "
            "Posicion: coordenadas x,y de cada KC. Panel izquierdo: espigas de cada KC en la ventana pre_A (1 s, "
            "olor A antes del entrenamiento), color de oscuro (0) a amarillo (8 o más, recortado). Panel central: "
            "lo mismo en post_A (1 s, olor A despues del entrenamiento). Panel derecho: diferencia post_A menos pre_A "
            "por KC, azul si baja, naranja si sube, recortado a ±5. Las cifras de la parte inferior son totales de esas "
            "ventanas, incluido el conteo de MBON.")
    return svg_doc(W, H, "Nube de células de Kenyon antes y despues del olor A", desc, body, BG)


# ---------------------------------------------------------------- obra 3: caminata sobre la hipérbola
def fig_caminata(mk: Market):
    W, H = 1200, 790
    BG = "#f4efe4"
    INK = "#1f2235"
    L, R, T, B = 130.0, 1080.0, 150.0, 650.0
    xmin = math.floor(min(mk.rx) - 120)
    xmax = math.ceil(max(mk.rx) + 120)
    kend, k0 = mk.k[-1], mk.k[0]
    ylo = math.floor((min(min(mk.ry), kend / xmax) - 8000) / 5000) * 5000
    yhi = math.ceil((max(max(mk.ry), kend / xmin) + 8000) / 5000) * 5000

    def px(x):
        return L + (x - xmin) / (xmax - xmin) * (R - L)

    def py(y):
        return B - (y - ylo) / (yhi - ylo) * (B - T)

    sx = (R - L) / (xmax - xmin)
    sy = (B - T) / (yhi - ylo)
    ramp_stops = [(0.0, "#1d3557"), (0.5, "#e76f51"), (1.0, "#e9c46a")]

    body = []
    # marco y ejes
    body.append(f'<rect x="{num(L)}" y="{num(T)}" width="{num(R - L)}" height="{num(B - T)}" fill="none" '
                f'stroke="#c9bfa8"/>')
    for xv in ticks_between(xmin, xmax, 200):
        body.append(f'<line x1="{num(px(xv))}" y1="{num(B)}" x2="{num(px(xv))}" y2="{num(B + 5)}" stroke="#8a8270"/>')
        body.append(text(px(xv), B + 20, f"{xv:,.0f}".replace(",", " "), size=12, fill="#6b6456", anchor="middle"))
    for yv in ticks_between(ylo, yhi, 20000):
        body.append(f'<line x1="{num(L - 5)}" y1="{num(py(yv))}" x2="{num(L)}" y2="{num(py(yv))}" stroke="#8a8270"/>')
        body.append(text(L - 10, py(yv) + 4, f"{yv:,.0f}".replace(",", " "), size=12, fill="#6b6456", anchor="end"))
    body.append(text((L + R) / 2, B + 44, "reserva del token X (x)", size=14, fill="#4a4538", anchor="middle"))
    body.append(text(L - 84, (T + B) / 2, "reserva del token Y (y)", size=14, fill="#4a4538", anchor="middle",
                     extra=f' transform="rotate(-90 {num(L - 84)} {num((T + B) / 2)})"'))

    # franja entre k inicial y k final
    xs = [xmin + (xmax - xmin) * i / 300 for i in range(301)]
    upper = [f"{num(px(x))} {num(py(kend / x))}" for x in xs]
    lower = [f"{num(px(x))} {num(py(k0 / x))}" for x in reversed(xs)]
    body.append(f'<path d="M{" L".join(upper)} L{" L".join(lower)} Z" fill="#e9c46a" fill-opacity="0.35"/>')
    body.append(f'<path d="M{" L".join(f"{num(px(x))} {num(py(k0 / x))}" for x in xs)}" fill="none" '
                f'stroke="{INK}" stroke-opacity="0.6" stroke-dasharray="6 5" stroke-width="1.4"/>')
    body.append(f'<path d="M{" L".join(f"{num(px(x))} {num(py(kend / x))}" for x in xs)}" fill="none" '
                f'stroke="{INK}" stroke-width="1.6"/>')

    # camino: 720 segmentos coloreados por tiempo
    n = len(mk.rx) - 1
    for k in range(n):
        col = ramp(ramp_stops, k / (n - 1))
        body.append(f'<line x1="{num(px(mk.rx[k]))}" y1="{num(py(mk.ry[k]))}" '
                    f'x2="{num(px(mk.rx[k + 1]))}" y2="{num(py(mk.ry[k + 1]))}" stroke="{col}" '
                    f'stroke-width="2.4" stroke-linecap="round"/>')

    # marcas por dia
    for day in range(0, 31, 5):
        k = min(day * 24, n)
        body.append(f'<circle cx="{num(px(mk.rx[k]))}" cy="{num(py(mk.ry[k]))}" r="3.6" fill="{INK}"/>')
        if day not in (0, 30):
            body.append(text(px(mk.rx[k]) + 8, py(mk.ry[k]) - 8, f"día {day}", size=12, fill=INK))

    # tangentes: pendiente = -(y/x), el precio marginal del pool
    for k, lab in ((0, "inicio"), (n, "final")):
        m = -mk.marg[k]
        dxp, dyp = sx, -m * sy
        norm = math.hypot(dxp, dyp)
        hx, hy = 52 * dxp / norm, 52 * dyp / norm
        cx_, cy_ = px(mk.rx[k]), py(mk.ry[k])
        body.append(f'<line x1="{num(cx_ - hx)}" y1="{num(cy_ - hy)}" x2="{num(cx_ + hx)}" y2="{num(cy_ + hy)}" '
                    f'stroke="{INK}" stroke-width="2"/>')
    body.append(f'<circle cx="{num(px(mk.rx[0]))}" cy="{num(py(mk.ry[0]))}" r="7" fill="#1d3557" stroke="{INK}"/>')
    body.append(f'<circle cx="{num(px(mk.rx[n]))}" cy="{num(py(mk.ry[n]))}" r="7" fill="#e9c46a" stroke="{INK}"/>')

    gain = (kend / k0 - 1) * 100
    body.insert(0, text(L, 62, "Caminata sobre la hipérbola", size=34, fill=INK, family=SERIF, weight="bold"))
    body.insert(1, text(L, 90, "El pool x·y = k recorre 720 horas (30 días) de un mercado sintético. "
                               "Cada segmento es una hora.", size=15, fill="#4a4538"))
    body.insert(2, text(R, 62, f"k: {k0 / 1e9:.4f} → {kend / 1e9:.4f} · 10⁹", size=17, fill=INK,
                        anchor="end", weight="bold"))
    body.insert(3, text(R, 90, f"+{gain:.2f} % en 30 días", size=15, fill="#4a4538", anchor="end"))

    body.append(text(L, 728,
                     f"Línea discontinua: k inicial. Línea sólida: k final. Franja: crecimiento de k, que el dato "
                     f"muestra monótono (nunca baja).",
                     size=13, fill="#4a4538"))
    body.append(text(L, 748,
                     f"Tangentes: pendiente = −precio marginal (y/x). Vale {mk.marg[0]:.1f} al inicio y "
                     f"{mk.marg[n]:.1f} al final. Color del camino: azul al día 0, amarillo al día 30.",
                     size=13, fill="#4a4538"))
    body.append(text(L, 768,
                     "Fuente: casa-agora/out/results.json (sintético, semilla 0). Mapeo: x e y = reservas; "
                     "color = tiempo; franja = k final menos k inicial.",
                     size=13, fill="#6b6456"))

    desc = ("Trayectoria del pool de un AMM x·y=k (results.json, pool_path) con 721 estados horarios. Eje x: reserva "
            "del token X. Eje y: reserva del token Y. Curva discontinua: x·y = k inicial (2.5e9). Curva sólida: x·y = k "
            "final, mayor en 30 días; en un AMM así ese crecimiento viene de las comisiones que quedan en el pool. La franja entre ambas es el crecimiento de k. "
            "Color del camino: tiempo, de azul (día 0) a amarillo (día 30). Tangentes: pendiente igual a menos el precio "
            "marginal y/x, al inicio y al final.")
    return svg_doc(W, H, "Caminata del pool sobre la hipérbola x*y=k", desc, body, BG)


# ---------------------------------------------------------------- obra 4: precio contra precio marginal
def fig_precio(mk: Market):
    W, H = 1200, 780
    BG = "#f4efe4"
    INK = "#1f2235"
    ramp_stops = [(0.0, "#1d3557"), (0.5, "#e76f51"), (1.0, "#e9c46a")]

    gaps = [m - p for m, p in zip(mk.marg, mk.price)]
    rel = [abs(g) / p for g, p in zip(gaps, mk.price)]
    mean_abs = sum(abs(g) for g in gaps) / len(gaps)
    max_abs = max(abs(g) for g in gaps)
    max_rel = max(rel) * 100

    # panel izquierdo: dispersion precio vs precio marginal
    L, T, S = 130.0, 175.0, 480.0
    lo = math.floor(min(min(mk.price), min(mk.marg)) - 1)
    hi = math.ceil(max(max(mk.price), max(mk.marg)) + 1)

    def sx_(v):
        return L + (v - lo) / (hi - lo) * S

    def sy_(v):
        return T + S - (v - lo) / (hi - lo) * S

    body = []
    body.append(f'<rect x="{num(L)}" y="{num(T)}" width="{num(S)}" height="{num(S)}" fill="none" stroke="#c9bfa8"/>')
    body.append(f'<line x1="{num(sx_(lo))}" y1="{num(sy_(lo))}" x2="{num(sx_(hi))}" y2="{num(sy_(hi))}" '
                f'stroke="{INK}" stroke-opacity="0.5" stroke-dasharray="6 5"/>')
    n = len(mk.price)
    for i in range(n):
        col = ramp(ramp_stops, i / (n - 1))
        body.append(f'<circle cx="{num(sx_(mk.price[i]))}" cy="{num(sy_(mk.marg[i]))}" r="2.8" fill="{col}" '
                    f'fill-opacity="0.85"/>')
    for v in ticks_between(lo, hi, 5):
        body.append(text(sx_(v), T + S + 20, f"{v:.0f}", size=12, fill="#6b6456", anchor="middle"))
        body.append(text(L - 10, sy_(v) + 4, f"{v:.0f}", size=12, fill="#6b6456", anchor="end"))
    body.append(text(L + S / 2, T + S + 44, "precio de mercado (price_path)", size=14, fill="#4a4538",
                     anchor="middle"))
    body.append(text(L - 62, T + S / 2, "precio marginal del pool (y/x)", size=14, fill="#4a4538", anchor="middle",
                     extra=f' transform="rotate(-90 {num(L - 62)} {num(T + S / 2)})"'))
    body.append(text(sx_(hi) - 6, sy_(hi) + 18, "y = x", size=12, fill=INK, anchor="end"))

    # panel derecho: brecha en el tiempo
    L2, R2 = 700.0, 1110.0
    G = math.ceil(max_abs * 1.15 * 20) / 20.0
    mid = T + S / 2

    def dx(day):
        return L2 + day / 30.0 * (R2 - L2)

    def dy(g):
        return mid - g / G * (S / 2)

    body.append(f'<rect x="{num(L2)}" y="{num(T)}" width="{num(R2 - L2)}" height="{num(S)}" fill="none" '
                f'stroke="#c9bfa8"/>')
    body.append(f'<line x1="{num(L2)}" y1="{num(mid)}" x2="{num(R2)}" y2="{num(mid)}" stroke="{INK}" '
                f'stroke-opacity="0.5"/>')
    for gv in (-G, -G / 2, 0.0, G / 2, G):
        body.append(text(L2 - 10, dy(gv) + 4, f"{gv:+.2f}" if gv else "0", size=12, fill="#6b6456", anchor="end"))
    for day in range(0, 31, 5):
        body.append(text(dx(day), T + S + 20, f"día {day}", size=12, fill="#6b6456", anchor="middle"))
    for i in range(n):
        g = gaps[i]
        col = "#1b7f79" if g >= 0 else "#b5442e"
        body.append(f'<circle cx="{num(dx(i / 24))}" cy="{num(dy(g))}" r="1.9" fill="{col}" fill-opacity="0.8"/>')
    body.append(text((L2 + R2) / 2, T + S + 44, "tiempo (días de 24 h)", size=14, fill="#4a4538", anchor="middle"))
    body.append(text(L2 - 62, mid, "brecha = marginal − mercado", size=14, fill="#4a4538", anchor="middle",
                     extra=f' transform="rotate(-90 {num(L2 - 62)} {num(mid)})"'))

    body.insert(0, text(L, 62, "La sombra del pool", size=34, fill=INK, family=SERIF, weight="bold"))
    body.insert(1, text(L, 90, "Precio de mercado frente al precio marginal del AMM. "
                               "Si el pool sigue al mercado, los puntos caen sobre la diagonal.",
                        size=15, fill="#4a4538"))
    body.insert(2, text(L2, 128, "Brecha en el tiempo", size=20, fill=INK, weight="bold"))
    body.insert(3, text(L2, 150, "turquesa: el pool cotiza por encima; rojo: por debajo", size=13, fill="#4a4538"))

    body.append(text(L, 738,
                     f"Brecha media |marginal − mercado| = {mean_abs:.2f}; máxima = {max_abs:.2f} "
                     f"({max_rel:.2f} % del precio). La comisión del pool es 0.30 %.",
                     size=15, fill=INK))
    body.append(text(L, 760,
                     "Fuente: casa-agora/out/results.json (sintético, semilla 0). Color de los puntos: tiempo, "
                     "de azul (día 0) a amarillo (día 30).",
                     size=13, fill="#6b6456"))

    desc = ("Dos paneles con los datos de results.json. Izquierda: cada punto es una hora (721 estados); eje x = precio "
            "de mercado (price_path), eje y = precio marginal del pool (y/x de las reservas), color = tiempo. Si el pool "
            "siguiera exactamente al mercado, todos los puntos estarían sobre la diagonal. Derecha: la brecha "
            "(precio marginal menos precio de mercado) a lo largo de 30 días, turquesa si el pool cotiza por encima y rojo "
            "si por debajo. Ningún elemento es decorativo: cada punto y cada segmento sale de una hora del dato.")
    return svg_doc(W, H, "Precio de mercado frente al precio marginal del pool", desc, body, BG)


# ---------------------------------------------------------------- obra 5: cruce, la mosca lee la cinta
def fig_cinta(fly: Fly, mk: Market):
    W, H = 1000, 1085
    BG = "#07070d"
    cx, cy = 500.0, 560.0
    T = fly.duration
    N = 720
    SIGMA = 100.0  # ms, nucleo gaussiano para suavizar las espigas de MBON
    dens_stops = [(0.0, "#2b2f5a"), (0.35, "#6a1b9a"), (0.7, "#ff4d6d"), (1.0, "#ffe66d")]

    ts = sorted(t for t, i in fly.spikes if fly.type_of[i] == "MBON")

    def density(t):
        lo = bisect.bisect_left(ts, t - 4 * SIGMA)
        hi = bisect.bisect_right(ts, t + 4 * SIGMA)
        return sum(math.exp(-0.5 * ((t - u) / SIGMA) ** 2) for u in ts[lo:hi])

    t_hour = [(k + 0.5) / N * T for k in range(N)]
    dens = [density(t) for t in t_hour]
    dmax = max(dens)

    prices = mk.price[:N]  # 720 horas (el punto final 721 se omite)
    pmin, pmax = min(prices), max(prices)
    r_base, r_lo, r_hi = 190.0, 190.0, 335.0

    def ang(t):
        return math.radians(-90.0 + 360.0 * t / T)

    def pt(r, t):
        a = ang(t)
        return cx + r * math.cos(a), cy + r * math.sin(a)

    body = []
    # anillo de protocolo: arcos por olor y recompensa
    R_OD, R_RW = 398.0, 380.0
    for s in fly.stimuli:
        letter = odour_of(s["name"])
        if letter is not None:
            x1, y1 = pt(R_OD, s["t_start"])
            x2, y2 = pt(R_OD, s["t_end"])
            body.append(f'<path d="M{num(x1)} {num(y1)} A{num(R_OD)} {num(R_OD)} 0 0 1 {num(x2)} {num(y2)}" '
                        f'fill="none" stroke="{ODOUR_COL[letter]}" stroke-width="16"/>')
    for s in fly.stimuli:
        if s["name"].startswith("reward"):
            x1, y1 = pt(R_RW, s["t_start"])
            x2, y2 = pt(R_RW, s["t_end"])
            body.append(f'<path d="M{num(x1)} {num(y1)} A{num(R_RW)} {num(R_RW)} 0 0 1 {num(x2)} {num(y2)}" '
                        f'fill="none" stroke="{GOLD}" stroke-width="5"/>')
    # marcas de tiempo de la mosca
    for sec in (5, 10, 15, 20):
        x_, y_ = pt(R_OD + 30, sec * 1000.0)
        body.append(text(x_, y_ + 4, f"{sec} s", size=13, fill="#9aa3b8", anchor="middle"))
    body.append(text(cx, cy - R_OD - 34, "0 s = 23 s", size=13, fill="#9aa3b8", anchor="middle"))

    # barras del mercado: radio = precio, color = MBON en el mismo angulo
    for k in range(N):
        t = t_hour[k]
        r_out = r_lo + (prices[k] - pmin) / (pmax - pmin) * (r_hi - r_lo)
        x1, y1 = pt(r_base, t)
        x2, y2 = pt(r_out, t)
        col = ramp(dens_stops, dens[k] / dmax)
        body.append(f'<line x1="{num(x1)}" y1="{num(y1)}" x2="{num(x2)}" y2="{num(y2)}" stroke="{col}" '
                    f'stroke-width="2.2"/>')

    # centro
    body.append(f'<circle cx="{num(cx)}" cy="{num(cy)}" r="172" fill="#0e0e1c"/>')
    body.append(text(cx, cy - 14, "720 h de mercado", size=17, fill="#f2efe6", anchor="middle", weight="bold"))
    body.append(text(cx, cy + 8, "enrollado sobre", size=14, fill="#aab2c5", anchor="middle"))
    body.append(text(cx, cy + 28, "23 s de la mosca", size=17, fill="#f2efe6", anchor="middle", weight="bold"))
    body.append(text(cx, cy + 56, "radio = precio", size=13, fill="#aab2c5", anchor="middle"))
    body.append(text(cx, cy + 74, "color = MBON", size=13, fill="#aab2c5", anchor="middle"))

    body.insert(0, text(50, 56, "La mosca lee la cinta", size=34, fill="#f2efe6", family=SERIF, weight="bold"))
    body.insert(1, text(50, 82, "Un mes de precio de mercado, enrollado sobre el protocolo de 23 s de la mosca.",
                        size=15, fill="#aab2c5"))

    legend = [
        "Radio de cada barra = precio de mercado (mín. a máx.).",
        "Color = espigas MBON suavizadas (gaussiana 100 ms) en el instante de la mosca con el mismo ángulo.",
        "Anillo exterior: A naranja, B turquesa, C gris; dorado = recompensa. La hora k cae en el ángulo (k+½)/720 de los 23 s.",
        "Lectura visual, no predicción ni señal de trading: el tiempo de la mosca se estira sobre el tiempo del mercado.",
    ]
    for i, line in enumerate(legend):
        body.append(text(50, 1010 + i * 20, line, size=13, fill="#8a93a6"))

    desc = ("Cruce de ambos mundos. Cada una de las 720 horas del precio de mercado (price_path de results.json) es una "
            "barra radial. Radio: precio (min a max del dato). Ángulo: la hora k se coloca en el mismo ángulo que el "
            "instante (k+0.5)/720 de los 23 s del protocolo de la mosca (activity.json). Color: densidad de espigas "
            "de las neuronas MBON, suavizada con gaussiana de 100 ms, normalizada por su máximo. Anillo exterior: "
            "estímulos del protocolo (A naranja, B turquesa, C gris) y recompensa (dorado). El punto 721 de la trayectoria "
            "de precio se omite. Es una alineación visual, no una predicción.")
    return svg_doc(W, H, "La mosca lee la cinta: precio de mercado y actividad MBON", desc, body, BG)


# ---------------------------------------------------------------- principal
def main():
    a = json.loads(ACTIVITY.read_text(encoding="utf-8"))
    r = json.loads(RESULTS.read_text(encoding="utf-8"))
    validate_activity(a)
    validate_results(r)
    fly = Fly(a)
    mk = Market(r)

    works = [
        ("01-cielo-de-espigas.svg", fig_cielo(fly)),
        ("02-nube-kc-antes-despues.svg", fig_kc(fly)),
        ("03-caminata-hiperbola.svg", fig_caminata(mk)),
        ("04-sombra-del-pool.svg", fig_precio(mk)),
        ("05-la-mosca-lee-la-cinta.svg", fig_cinta(fly, mk)),
    ]
    GALLERY.mkdir(parents=True, exist_ok=True)
    for name, svg in works:
        with open(GALLERY / name, "w", encoding="utf-8", newline="\n") as f:
            f.write(svg)
        print(f"{name}: {len(svg.encode('utf-8')) / 1024:.0f} KiB")


if __name__ == "__main__":
    main()
