"""Mapa tipo-a-tipo del cuerpo fungiforme: KC -> MBON y DAN -> MBON (solo aristas con >= 5 sinapsis).

Escribe out/map_kc_mbon.csv, out/map_dan_mbon.csv y out/map_kc_mbon.svg (mapa de calor, sin dependencias).
Umbral de 5 sinapsis: la mediana de KC->KC es 1 sinapsis, asi que se filtra el ruido de baja confianza.
"""
import collections
import csv
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import conectoma_io as cio  # noqa: E402

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MIN_SYN = 5


def heat_color(v, vmax):
    """Escala de color secuencial simple (blanco -> azul oscuro), v en [0, vmax]."""
    if vmax <= 0 or v <= 0:
        return "#f4f4f4"
    t = min(1.0, (v ** 0.5) / (vmax ** 0.5))
    r = int(244 + (16 - 244) * t)
    g = int(244 + (60 - 244) * t)
    b = int(244 + (140 - 244) * t)
    return f"#{r:02x}{g:02x}{b:02x}"


def write_svg(path, rows, cols, M, title):
    cell, left, top = 18, 90, 150
    W = left + cell * len(cols) + 20
    H = top + cell * len(rows) + 40
    vmax = max((max(r) for r in M), default=1)
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" font-family="sans-serif" font-size="10">',
           f'<rect width="{W}" height="{H}" fill="#ffffff"/>',
           f'<text x="10" y="18" font-size="13" font-weight="bold">{title}</text>',
           f'<text x="10" y="34" fill="#444">sinapsis sumadas por tipo, solo aristas con &gt;= {MIN_SYN} sinapsis (MaleCNS v1.0)</text>']
    for j, c in enumerate(cols):
        x = left + j * cell + cell / 2
        out.append(f'<text transform="translate({x:.1f},{top - 6}) rotate(-70)" text-anchor="start">{c}</text>')
    for i, r in enumerate(rows):
        y = top + i * cell
        out.append(f'<text x="{left - 6}" y="{y + cell * 0.7:.1f}" text-anchor="end">{r}</text>')
        for j, c in enumerate(cols):
            v = M[i][j]
            out.append(f'<rect x="{left + j * cell}" y="{y}" width="{cell - 1}" height="{cell - 1}" fill="{heat_color(v, vmax)}">'
                       f'<title>{r} -> {c}: {v}</title></rect>')
    out.append("</svg>")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(out) + "\n")


def build(pre, post, w, cls_of, typ_of, src_cls, dst_cls, src_type_filter=None):
    cnt = collections.Counter()
    for p, q, x in zip(pre.tolist(), post.tolist(), w.tolist()):
        if x < MIN_SYN:
            continue
        if cls_of.get(p) != src_cls or cls_of.get(q) != dst_cls:
            continue
        if src_type_filter and not src_type_filter(typ_of.get(p)):
            continue
        cnt[(typ_of.get(p), typ_of.get(q))] += x
    return cnt


def main():
    ann = cio.load_annotations()
    pre, post, w = cio.load_subcircuit(ann)
    cls_of = {b: v["cls"] for b, v in ann.items()}
    typ_of = {b: v["type"] for b, v in ann.items()}
    # KC: tipo ausente en 2 cuerpos y 1 cuerpo 'KCg' -> se mantienen como estan
    kc = build(pre, post, w, cls_of, typ_of, "Kenyon_Cell", "MBON")
    kc_rows = sorted({a for a, _ in kc}, key=lambda s: (s is None, s))
    mb_cols = sorted({b for _, b in kc}, key=lambda s: (s is None, s))
    M = [[kc.get((r, c), 0) for c in mb_cols] for r in kc_rows]
    with open(os.path.join(HERE, "out", "map_kc_mbon.csv"), "w", newline="", encoding="utf-8") as fh:
        wr = csv.writer(fh)
        wr.writerow(["KC_tipo\\MBON_tipo"] + mb_cols)
        for r, row in zip(kc_rows, M):
            wr.writerow([r] + row)
    write_svg(os.path.join(HERE, "out", "map_kc_mbon.svg"), kc_rows, mb_cols, M, "KC -> MBON por tipo (MaleCNS v1.0)")

    dan = build(pre, post, w, cls_of, typ_of, "DAN", "MBON")
    d_rows = sorted({a for a, _ in dan}, key=lambda s: (s is None, s))
    d_cols = sorted({b for _, b in dan}, key=lambda s: (s is None, s))
    DM = [[dan.get((r, c), 0) for c in d_cols] for r in d_rows]
    with open(os.path.join(HERE, "out", "map_dan_mbon.csv"), "w", newline="", encoding="utf-8") as fh:
        wr = csv.writer(fh)
        wr.writerow(["DAN_tipo\\MBON_tipo"] + d_cols)
        for r, row in zip(d_rows, DM):
            wr.writerow([r] + row)

    # Resumen en consola
    tot_kc = sum(kc.values())
    print(f"KC->MBON (>= {MIN_SYN} sinapsis): {tot_kc} sinapsis en {len(kc_rows)} tipos KC x {len(mb_cols)} tipos MBON")
    print(f"DAN->MBON (>= {MIN_SYN} sinapsis): {sum(dan.values())} sinapsis")
    top = sorted(kc.items(), key=lambda kv: -kv[1])[:8]
    print("top KC->MBON tipos:", [(a, b, v) for (a, b), v in top])
    dtop = sorted(dan.items(), key=lambda kv: -kv[1])[:8]
    print("top DAN->MBON tipos:", [(a, b, v) for (a, b), v in dtop])


if __name__ == "__main__":
    main()
