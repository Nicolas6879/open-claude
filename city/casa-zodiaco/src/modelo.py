"""Modelo gestaltico de constelaciones (version 1) + nulos + metricas.

Inspirado en el Graph Clustering (GC) de Kemp et al. (2022), pero a nivel de ARISTAS:
  1. grafo candidato = union de triangulaciones de Delaunay esfericas sobre las estrellas mas
     brillantes que 3.5, 4.0, 4.5, 5.5 y todas (multiescala, como Kemp);
  2. cada arista recibe una puntuacion log-lineal: -(lam * 0.921 * mag_de_la_mas_debil + ln d),
     con 'lam' = peso del brillo frente a la proximidad (Kemp: rho);
  3. escalado local: se resta la mediana local (radio R) de cada cantidad (equivale a su cociente
     bL/bG en escala log); la vecindad se aproxima con ~400 anclas Fibonacci (resolucion ~10 grados);
  4. se conservan las k = r * n_estrellas aristas mas fuertes.
Hiperparametros globales (nunca por cultura): lam, R, r (y m_lim en el regimen ciego).
"""
import numpy as np
from scipy.spatial import ConvexHull, cKDTree

LN_FLUX = 0.4 * np.log(10.0)  # 0.921: ln(flujo) por magnitud
UMBRALES = (3.5, 4.0, 4.5, 5.5, 99.0)
LAMS = (0.0, 0.25, 0.5, 1.0, 2.0, 4.0, 1000.0)
RADIOS = (0, 30, 60, 90)  # 0 = sin escalado local
RATIOS = (0.3, 0.45, 0.6, 0.8, 1.0, 1.25)
import os as _os
if _os.environ.get('ZODIACO_RATIOS'):  # v1b: rejilla ampliada (correccion post hoc del borde de rejilla)
    RATIOS = tuple(float(x) for x in _os.environ['ZODIACO_RATIOS'].split(','))
MLIMS = (3.5, 4.0, 4.5, 5.0, 5.5)
K_ENC = 1 << 20  # clave de arista = a*K_ENC + b (a<b), IDs de Hipparcos < 2^20


def clave(a, b):
    a = np.asarray(a, dtype=np.int64)
    b = np.asarray(b, dtype=np.int64)
    return np.minimum(a, b) * K_ENC + np.maximum(a, b)


def fibonacci_anclas(n=400):
    i = np.arange(n) + 0.5
    z = 1 - 2 * i / n
    phi = np.pi * (1 + 5 ** 0.5) * i
    r = np.sqrt(1 - z * z)
    return np.stack([r * np.cos(phi), r * np.sin(phi), z], axis=1)


ANCLAS = fibonacci_anclas()


def delaunay_aristas(v):
    """Aristas (i<j) de la triangulacion de Delaunay esferica de puntos unitarios v (n,3)."""
    n = len(v)
    if n < 2:
        return np.zeros((0, 2), dtype=np.int64)
    if n < 4:
        ii, jj = np.triu_indices(n, 1)
        return np.stack([ii, jj], 1).astype(np.int64)
    try:
        h = ConvexHull(v)
        s = h.simplices
        e = np.concatenate([s[:, [0, 1]], s[:, [1, 2]], s[:, [0, 2]]])
        e = np.sort(e, axis=1)
        return np.unique(e, axis=0).astype(np.int64)
    except Exception:  # degenerado (coplanar): vecinos mas cercanos k=3
        kd = cKDTree(v)
        _, idx = kd.query(v, k=min(4, n))
        e = np.sort(np.stack([np.repeat(np.arange(n), idx.shape[1] - 1), idx[:, 1:].ravel()], 1), axis=1)
        return np.unique(e, axis=0).astype(np.int64)


def candidatas(v, mag, umbrales=UMBRALES):
    """Union multiescala de Delaunay. Devuelve (i, j) indices (i<j) sobre las estrellas v."""
    partes = []
    for t in umbrales:
        idx = np.where(mag <= t)[0]
        if len(idx) >= 3:
            e = delaunay_aristas(v[idx])
            partes.append(idx[e])
    if not partes:
        return np.zeros((0, 2), dtype=np.int64)
    e = np.unique(np.sort(np.concatenate(partes), axis=1), axis=0)
    return e


def sep_ang(v, e):
    c = np.clip(np.einsum("ij,ij->i", v[e[:, 0]], v[e[:, 1]]), -1, 1)
    return np.degrees(np.arccos(c))


class Candidatas:
    """Aristas candidatas y sus rasgos (independientes de los hiperparametros)."""

    def __init__(self, v, mag, umbrales=UMBRALES):
        self.v = v
        self.mag = mag
        self.e = candidatas(v, mag, umbrales)
        if len(self.e) == 0:
            self.d = np.zeros(0)
            self.mf = np.zeros(0)
            self.P = np.zeros(0)
            self.B = np.zeros(0)
            self.ancla = np.zeros(0, dtype=int)
            return
        self.d = np.maximum(sep_ang(v, self.e), 0.01)
        self.mf = np.maximum(mag[self.e[:, 0]], mag[self.e[:, 1]])
        self.P = np.log(self.d)
        self.B = LN_FLUX * self.mf
        mid = v[self.e[:, 0]] + v[self.e[:, 1]]
        mid /= np.maximum(np.linalg.norm(mid, axis=1, keepdims=True), 1e-12)
        self.mid = mid
        self.ancla = np.argmax(mid @ ANCLAS.T, axis=1)  # ancla mas cercana
        self._cache_med = {}

    def _centrar(self, x, R, clave_x):
        if R == 0 or len(x) == 0:
            return x
        k = (clave_x, R)
        if k not in self._cache_med:
            cosR = np.cos(np.radians(R))
            sel = (ANCLAS @ self.mid.T) >= cosR  # (anclas, aristas)
            med = np.zeros(len(ANCLAS))
            g = np.median(x)
            for a in range(len(ANCLAS)):
                s = sel[a]
                med[a] = np.median(x[s]) if s.sum() >= 5 else g
            self._cache_med[k] = med[self.ancla]
        return x - self._cache_med[k]

    def puntuacion(self, lam, R):
        if len(self.e) == 0:
            return np.zeros(0)
        P = self._centrar(self.P, R, "P")
        if lam >= 999:
            return -self._centrar(self.B, R, "B") - 1e-6 * P
        B = self._centrar(self.B, R, "B")
        return -(lam * B + P)

    def top_k(self, lam, R, k):
        s = self.puntuacion(lam, R)
        k = int(min(max(k, 0), len(s)))
        if k == 0:
            return np.zeros((0, 2), dtype=np.int64)
        idx = np.argpartition(-s, k - 1)[:k] if k < len(s) else np.arange(len(s))
        return self.e[idx]


def f1_claves(pred_keys, truth_keys):
    """F1 de aristas = 2*tp/(|pred|+|truth|). Ambos son arrays/sets de claves unicas."""
    if len(pred_keys) + len(truth_keys) == 0:
        return 0.0
    tp = np.intersect1d(pred_keys, truth_keys, assume_unique=True).size
    return 2.0 * tp / (len(pred_keys) + len(truth_keys))


# ---------------- nulos ----------------
def nn_aristas(v, idx=None):
    """Grafo de vecino mas cercano (cada estrella con su vecino angular mas cercano), unico."""
    if idx is None:
        idx = np.arange(len(v))
    if len(idx) < 2:
        return np.zeros((0, 2), dtype=np.int64)
    kd = cKDTree(v[idx])
    _, nn = kd.query(v[idx], k=2)
    e = np.sort(np.stack([idx, idx[nn[:, 1]]], 1), axis=1)
    return np.unique(e, axis=0)


def grado_aleatorio(grados, nodos, rng):
    """Grafo aleatorio con (aprox.) la misma secuencia de grados (modelo de configuracion 'borrado':
    se descartan lazos y aristas repetidas). nodos: array de IDs (misma longitud que grados)."""
    stubs = np.repeat(np.arange(len(grados)), grados)
    rng.shuffle(stubs)
    if len(stubs) % 2:
        stubs = stubs[:-1]
    a = stubs[0::2]
    b = stubs[1::2]
    m = a != b
    a, b = a[m], b[m]
    e = np.unique(np.sort(np.stack([a, b], 1), axis=1), axis=0)
    return nodos[e]


def subconjunto_aleatorio(e_cand, k, rng):
    k = int(min(k, len(e_cand)))
    if k == 0:
        return e_cand[:0]
    return e_cand[rng.choice(len(e_cand), size=k, replace=False)]


def claves_de(e, hips):
    """Convierte aristas en indices locales -> claves de IDs de Hipparcos (unicas, ordenadas)."""
    if len(e) == 0:
        return np.zeros(0, dtype=np.int64)
    return np.unique(clave(hips[e[:, 0]], hips[e[:, 1]]))
