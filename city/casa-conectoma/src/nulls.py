"""Modelos nulos que conservan grados: intercambios de aristas bipartitas (Maslov-Sneppen).

Un intercambio toma dos aristas (a,b) y (c,d) y las cambia por (a,d) y (c,b), sin duplicados ni
autoaristas. Asi cada KC conserva su numero de PN y cada PN conserva su numero de KC.
"""
import numpy as np


def _swap_core(edges, n_swaps, rng):
    es = [list(e) for e in edges]
    E = len(es)
    eset = set(map(tuple, es))
    done, tries = 0, 0
    while done < n_swaps and tries < n_swaps * 20:
        tries += 1
        i, j = rng.integers(E, size=2)
        a, b = es[i]
        c, d = es[j]
        if a == c or b == d or (a, d) in eset or (c, b) in eset:
            continue
        eset.discard((a, b))
        eset.discard((c, d))
        es[i] = [a, d]
        es[j] = [c, b]
        eset.add((a, d))
        eset.add((c, b))
        done += 1
    return es, done


def swap_null(pairs, n_swaps, rng):
    """pairs: (kc, pn) -> (dict kc -> set(pn), numero de intercambios hechos)."""
    es, done = _swap_core(pairs, n_swaps, rng)
    out = {}
    for a, b in es:
        out.setdefault(a, set()).add(b)
    return out, done


def swap_null_weighted(pre, post, w, n_swaps, rng):
    """Como swap_null, pero el peso de cada arista viaja con ella. Devuelve (pre, post, w, hechos)."""
    es, done = _swap_core(list(zip(pre.tolist(), post.tolist())), n_swaps, rng)
    new_pre = np.array([a for a, _ in es], dtype=np.int64)
    new_post = np.array([b for _, b in es], dtype=np.int64)
    return new_pre, new_post, np.asarray(w), done


def shared_matrix(sets, universe):
    """sets: dict kc -> set(pn); universe: lista ordenada de pn. Devuelve (kcs, M binaria kc x pn)."""
    kcs = sorted(sets)
    idx = {p: i for i, p in enumerate(universe)}
    M = np.zeros((len(kcs), len(universe)), dtype=np.float32)
    for r, k in enumerate(kcs):
        for p in sets[k]:
            M[r, idx[p]] = 1.0
    return kcs, M


def pair_overlap(M):
    """Para una matriz binaria kc x pn: solapamiento medio por par y fraccion de pares con >=1 PN compartida."""
    S = M @ M.T
    n = M.shape[0]
    iu = np.triu_indices(n, k=1)
    vals = S[iu]
    return float(vals.mean()), float((vals > 0).mean())
