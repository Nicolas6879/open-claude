#!/usr/bin/env python3
"""«Una mosca aprende a querer el olor A»: convierte la actividad neuronal de
casa-mosca/out/activity.json en música (mosca.wav) y en una página que la muestra
(mosca.html). Determinista. Requiere numpy. Uso: python3 sonificar.py

Qué suena qué (cada elemento musical viene de un dato):
  ORN  llovizna de clics casi inaudibles          (entra el olor)
  PN   sinusoides suaves, registro medio          (lo que llega al cerebro)
  KC   plucks pentatónicos: cada célula, su nota  (el código disperso: pocas a la vez)
  APL  pulso grave de 55 Hz                       (la inhibición que mantiene la dispersión)
  DAN  acorde cálido de Do mayor                  (la dopamina: la recompensa)
  MBON campanas de Mi menor 7                     (la decisión: cuanto más suenan, más responde)
El tiempo se estira x3 (23 s -> 69 s).
"""
import hashlib
import json
import wave
from pathlib import Path

import numpy as np

AQUI = Path(__file__).resolve().parent
SR = 22050
ESTIRA = 3.0
ENTRADA = AQUI.parents[1] / "casa-mosca" / "out" / "activity.json"


def midi(n):
    return 440.0 * 2 ** ((n - 69) / 12)


PENTA = [0, 2, 4, 7, 9]


def tono(f, dur, dec, parciales=((1, 1.0),), ataque=0.004):
    t = np.arange(int(dur * SR)) / SR
    y = sum(a * np.sin(2 * np.pi * f * k * t) for k, a in parciales)
    env = np.minimum(1.0, t / ataque) * np.exp(-t / dec)
    return (y * env).astype(np.float32)


def cargar(ruta=ENTRADA):
    d = json.loads(Path(ruta).read_text(encoding="utf-8"))
    tipo = {n["id"]: n["type"] for n in d["neurons"]}
    pos = {n["id"]: i for i, n in enumerate(sorted((n for n in d["neurons"] if n["type"] == "KC"), key=lambda n: n["id"]))}
    return d, tipo, pos


def sintetizar(d, tipo, kc_idx, semilla=1, solo=None):
    rng = np.random.default_rng(semilla)
    dur = d["meta"]["duration_ms"] / 1000.0 * ESTIRA + 3.0
    y = np.zeros(int(dur * SR) + SR, dtype=np.float32)
    cache = {}

    def nota(clave, fabrica):
        if clave not in cache:
            cache[clave] = fabrica()
        return cache[clave]

    mbon_ids = sorted(n["id"] for n in d["neurons"] if n["type"] == "MBON")
    mbon_notas = [64, 67, 71, 74]                       # Mi menor 7
    mbon_idx = {i: k % 4 for k, i in enumerate(mbon_ids)}
    for t_ms, nid in d["spikes"]:
        t = t_ms / 1000.0 * ESTIRA
        i0 = int(t * SR)
        ty = tipo[nid]
        if solo is not None and ty not in solo:
            continue
        if ty == "KC":
            k = kc_idx[nid]
            m = 48 + PENTA[k % 5] + 12 * ((k // 5) % 4)
            s = nota(("KC", m), lambda m=m: 0.05 * tono(midi(m), 0.5, 0.11))
        elif ty == "PN":
            m = 57 + PENTA[nid % 5] + 12 * ((nid // 5) % 2)
            s = nota(("PN", m), lambda m=m: 0.035 * tono(midi(m), 0.6, 0.18, ataque=0.05))
        elif ty == "ORN":
            s = nota(("ORN", int(rng.integers(0, 8))), lambda: (0.006 * rng.standard_normal(int(0.012 * SR)) * np.hanning(int(0.012 * SR))).astype(np.float32))
        elif ty == "APL":
            s = nota(("APL",), lambda: 0.13 * tono(55.0, 0.35, 0.12, ataque=0.01))
        elif ty == "DAN":
            s = nota(("DAN",), lambda: 0.05 * sum(tono(midi(m), 1.2, 0.35, ataque=0.08) for m in (60, 64, 67, 72)))
        elif ty == "MBON":
            m = mbon_notas[mbon_idx.get(nid, 0)]
            s = nota(("MBON", m), lambda m=m: 0.22 * tono(midi(m + 12), 1.6, 0.55, parciales=((1, 1.0), (2.76, 0.45), (5.4, 0.2)), ataque=0.002))
        else:
            continue
        j = min(len(y), i0 + len(s))
        y[i0:j] += s[: j - i0]
    # un poco de espacio: dos ecos suaves
    for retraso, g in ((int(0.19 * SR), 0.30), (int(0.37 * SR), 0.18)):
        y[retraso:] += g * y[:-retraso]
    if solo is None:
        y /= max(1e-9, float(np.abs(y).max())) / 0.9
    return y[: int(dur * SR)]


def guardar_wav(y, ruta):
    pcm = (np.clip(y, -1, 1) * 32767).astype("<i2")
    with wave.open(str(ruta), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())


def espigas_en(d, tipo, ty, estimulo):
    est = next(s for s in d["stimuli"] if s["name"] == estimulo)
    return sum(1 for t, i in d["spikes"] if tipo[i] == ty and est["t_start"] <= t < est["t_end"])


def energia_campanas(y, d, tipo, estimulo, banda=(300, 1600)):
    """Energía de la banda de las campanas durante un estímulo (para comprobar que el sonido lleva el dato)."""
    est = next(s for s in d["stimuli"] if s["name"] == estimulo)
    a, b = int(est["t_start"] / 1000 * ESTIRA * SR), int((est["t_end"] / 1000 * ESTIRA + 1.2) * SR)
    seg = y[a:b]
    esp = np.abs(np.fft.rfft(seg)) ** 2
    f = np.fft.rfftfreq(len(seg), 1 / SR)
    return float(esp[(f >= banda[0]) & (f <= banda[1])].sum())


def datos_visuales(d, tipo):
    filas = {"ORN": 0, "PN": 1, "KC": 2, "APL": 3, "MBON": 4, "DAN": 5}
    ng = {t: sum(1 for n in d["neurons"] if n["type"] == t) for t in filas}
    kc = sorted(n["id"] for n in d["neurons"] if n["type"] == "KC")
    kc_pos = {i: k for k, i in enumerate(kc)}
    out = []
    rng = np.random.default_rng(3)
    for t_ms, nid in d["spikes"]:
        ty = tipo[nid]
        if ty not in filas:
            continue
        if ty == "ORN" and rng.random() > 0.05:
            continue
        if ty == "KC" and rng.random() > 0.3:
            continue
        idx = kc_pos[nid] if ty == "KC" else nid % max(1, ng[ty])
        out.append([round(t_ms), filas[ty], round(idx / max(1, ng[ty]), 3)])
    return out


def main():
    d, tipo, kc_idx = cargar()
    y = sintetizar(d, tipo, kc_idx)
    guardar_wav(y, AQUI / "mosca.wav")
    plantilla = (AQUI / "mosca.template.html").read_text(encoding="utf-8")
    est = [{"n": s["name"], "a": s["t_start"], "b": s["t_end"]} for s in d["stimuli"]]
    html = (plantilla.replace("/*SPIKES*/[]", json.dumps(datos_visuales(d, tipo), separators=(",", ":")))
            .replace("/*ESTIMULOS*/[]", json.dumps(est, ensure_ascii=False))
            .replace("/*ESTIRA*/3", str(ESTIRA)).replace("/*DUR*/0", str(d["meta"]["duration_ms"])))
    (AQUI / "mosca.html").write_text(html, encoding="utf-8")
    pre = energia_campanas(y, d, tipo, "pre_A")
    post = energia_campanas(y, d, tipo, "post_A")
    preB, postB = energia_campanas(y, d, tipo, "pre_B"), energia_campanas(y, d, tipo, "post_B")
    print(f"mosca.wav: {len(y)/SR:.1f} s, pico {np.abs(y).max():.2f}, sha1 {hashlib.sha1(y.tobytes()).hexdigest()[:12]}")
    print(f"energía de las campanas (300-1600 Hz): A después/antes = {post/pre:.2f} · B después/antes = {postB/preB:.2f}")


if __name__ == "__main__":
    main()
