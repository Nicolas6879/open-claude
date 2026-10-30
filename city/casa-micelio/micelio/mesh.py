"""Malla de candidatos para Physarum: ciudades + puntos de Steiner (red triangular con ruido) + Delaunay."""
import numpy as np
from .graphs import delaunay_edges, edge_lengths


def make_mesh(city_xy, spacing, rng, jitter=0.35, margin=0.08, keep_away=0.5):
    lo = city_xy.min(0)
    hi = city_xy.max(0)
    pad = margin * (hi - lo)
    lo, hi = lo - pad, hi + pad
    dy = spacing * np.sqrt(3) / 2
    pts = []
    row = 0
    y = lo[1]
    while y <= hi[1]:
        x = lo[0] + (spacing / 2 if row % 2 else 0)
        while x <= hi[0]:
            pts.append((x, y))
            x += spacing
        y += dy
        row += 1
    pts = np.array(pts)
    pts = pts + rng.uniform(-jitter, jitter, pts.shape) * spacing
    d = np.linalg.norm(pts[:, None] - city_xy[None], axis=2).min(axis=1)
    pts = pts[d > keep_away * spacing]
    allp = np.vstack([city_xy, pts])
    edges = delaunay_edges(allp)
    return allp, edges, edge_lengths(allp, edges)
