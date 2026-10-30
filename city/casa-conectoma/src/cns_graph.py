"""Grafo completo del SNC de MaleCNS v1.0 como matriz dispersa (CSR), con signo por neurotransmisor.

Salida (cache fuera del repo, DATA_DIR/cns_graph_v1.npz):
  ids      (N,) int64  bodyId de cada nodo (orden creciente)
  indptr   (N+1,) int64, indices (E,) int32, syn (E,) float32 (n de sinapsis, pre -> post)
  sign     (N,) int8   +1 ACh/dopamina/octopamina/serotonina, -1 GABA/glutamato, 0 unclear.
           Neurotransmisor = consensus_nt (predicted_nt estaba mal para las KC).
  types, classes, superclasses, sides (N,) str ; soma (N,3) float32 con NaN si no hay
Uso: PYTHONDONTWRITEBYTECODE=1 python3 src/cns_graph.py
"""
import collections
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import conectoma_io as cio  # noqa: E402

# Convencion de Shiu et al. 2024 (PMC11446845): GABA y glutamato inhibitorios; dopamina, octopamina y serotonina
# se tratan como excitatorias. "unclear" queda sin signo (0).
SIGN = {"acetylcholine": 1, "gaba": -1, "glutamate": -1, "dopamine": 1, "octopamine": 1, "serotonin": 1}
CACHE = "cns_graph_v3.npz"  # v3: consensus_nt + monoaminas excitatorias (Shiu 2024). v1 predicted_nt (invalido), v2 sin monoaminas


def load_graph(build_if_missing=True):
    p = os.path.join(cio.DATA_DIR, CACHE)
    if not os.path.exists(p):
        if not build_if_missing:
            raise FileNotFoundError(p)
        build()
    z = np.load(p, allow_pickle=False)
    return {k: z[k] for k in z.files}


def build():
    feather, pc = cio._arrow()
    ann = feather.read_table(cio.path(cio.ANN), columns=["bodyId", "type", "class", "superclass", "somaSide", "somaLocation"]).to_pydict()
    ids_ann = np.asarray(ann["bodyId"], dtype=np.int64)
    w = feather.read_table(cio.path(cio.WEIGHTS), columns=["body_pre", "body_post", "weight"], memory_map=True)
    pre_raw = w["body_pre"].to_numpy()
    post_raw = w["body_post"].to_numpy()
    wt = w["weight"].to_numpy()
    ids = np.unique(np.concatenate([ids_ann, pre_raw, post_raw]))
    N = len(ids)
    pi = np.searchsorted(ids, pre_raw)
    qi = np.searchsorted(ids, post_raw)
    del pre_raw, post_raw
    # CSR por neurona presinaptica
    order = np.argsort(pi, kind="stable")
    pi, qi, wt = pi[order], qi[order], wt[order]
    indptr = np.zeros(N + 1, dtype=np.int64)
    np.add.at(indptr, pi + 1, 1)
    indptr = np.cumsum(indptr)
    # signo por neurotransmisor (moda por cuerpo)
    nt = feather.read_table(cio.path(cio.NT), columns=["body", "consensus_nt"]).to_pydict()
    cnt = collections.defaultdict(collections.Counter)
    for b, n in zip(nt["body"], nt["consensus_nt"]):
        cnt[int(b)][n] += 1
    sign = np.zeros(N, dtype=np.int8)
    ntname = np.array([""] * N, dtype=object)
    for i, b in enumerate(ids.tolist()):
        if b in cnt:
            n = cnt[b].most_common(1)[0][0]
            ntname[i] = n or ""
            sign[i] = SIGN.get(n, 0)
    # anotaciones por nodo
    types = np.array([""] * N, dtype=object)
    classes = np.array([""] * N, dtype=object)
    supers = np.array([""] * N, dtype=object)
    sides = np.array([""] * N, dtype=object)
    soma = np.full((N, 3), np.nan, dtype=np.float32)
    pos = np.searchsorted(ids, ids_ann)
    for k, j in enumerate(pos.tolist()):
        types[j] = ann["type"][k] or ""
        classes[j] = ann["class"][k] or ""
        supers[j] = ann["superclass"][k] or ""
        sides[j] = ann["somaSide"][k] or ""
        if ann["somaLocation"][k]:
            soma[j] = np.asarray(ann["somaLocation"][k], dtype=np.float32)[:3]
    out = os.path.join(cio.DATA_DIR, CACHE)
    np.savez(out, ids=ids, indptr=indptr, indices=qi.astype(np.int32), syn=wt.astype(np.float32), sign=sign,
             types=types.astype(str), classes=classes.astype(str), superclasses=supers.astype(str),
             sides=sides.astype(str), soma=soma, nt=ntname.astype(str))
    print("grafo:", N, "nodos", len(qi), "aristas", "->", out)


if __name__ == "__main__":
    build()
