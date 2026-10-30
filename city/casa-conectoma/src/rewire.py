"""Controles de cableado: aleatorizacion conservando grados y barajado de neurotransmisores.

swap_targets: intercambia destinos entre dos aristas (a->b, c->d) => (a->d, c->b). Conserva el grado de salida
de cada neurona (a y c) y el grado de entrada de cada destino (multiconjunto). Las sinapsis (peso) viajan con la
posicion de la arista, asi que la distribucion de pesos se conserva globalmente, no por neurona destino.
Se permiten multi-aristas duplicadas (no se comprueban); el numero de duplicados se reporta.
shuffle_signs: permuta el signo (ACh/GABA/glutamato/otros) entre neuronas, conservando cuantas hay de cada signo.
"""
import numba as nb
import numpy as np


@nb.njit(cache=False)
def _swap(indices, src, n_swaps, seed):
    np.random.seed(seed)
    E = indices.shape[0]
    done = 0
    for _ in range(n_swaps):
        e1 = np.random.randint(E)
        e2 = np.random.randint(E)
        if src[e1] == src[e2] or indices[e1] == indices[e2]:
            continue
        if src[e1] == indices[e2] or src[e2] == indices[e1]:
            continue
        t = indices[e1]
        indices[e1] = indices[e2]
        indices[e2] = t
        done += 1
    return done


def swap_targets(G, factor=10, seed=0):
    indptr = G["indptr"]
    N = indptr.shape[0] - 1
    src = np.repeat(np.arange(N, dtype=np.int32), np.diff(indptr))
    indices = G["indices"].astype(np.int32).copy()
    E = indices.shape[0]
    done = _swap(indices, src, int(factor * E), int(seed))
    return indices, done


def duplicate_fraction(indptr, indices):
    """Fraccion de aristas que son duplicados (mismo pre y post) dentro de cada neurona."""
    dup = 0
    N = indptr.shape[0] - 1
    for i in range(N):
        seg = indices[indptr[i]:indptr[i + 1]]
        if seg.size > 1:
            dup += seg.size - np.unique(seg).size
    return dup / max(1, indices.shape[0])


def shuffle_signs(sign, seed=0):
    rng = np.random.default_rng(seed)
    return rng.permutation(sign)
