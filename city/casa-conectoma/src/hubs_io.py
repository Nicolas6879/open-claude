"""Indices de hubs (desde out/hubs.json) y control aleatorio emparejado por grado de salida."""
import json
import os

import numpy as np

import cns_graph

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load_hub_indices(n=20):
    """Indices (posicion en el grafo) de los n hubs con mayor uso de caminos ORN->DN."""
    G = cns_graph.load_graph(build_if_missing=False)
    d = json.load(open(os.path.join(HERE, "out", "hubs.json"), encoding="utf-8"))
    pos = {int(b): i for i, b in enumerate(G["ids"])}
    return np.array([pos[h["id"]] for h in d["top"][:n]], dtype=np.int64)


def matched_random(hub_idx, seed=5):
    """Para cada hub, una neurona al azar (no sensorial ni DN) con grado de salida parecido (mismo cuartil)."""
    G = cns_graph.load_graph(build_if_missing=False)
    outdeg = np.diff(G["indptr"])
    types = G["types"].astype(str)
    supers = G["superclasses"].astype(str)
    pool = np.nonzero((~np.char.startswith(types, "ORN_")) & (supers != "descending_neuron") & (outdeg > 0))[0]
    rng = np.random.default_rng(seed)
    chosen = []
    used = set(hub_idx.tolist())
    for h in hub_idx:
        d = outdeg[h]
        cand = pool[np.abs(np.log1p(outdeg[pool]) - np.log1p(d)) < 0.25]
        cand = [c for c in cand.tolist() if c not in used]
        pick = int(rng.choice(cand))
        used.add(pick)
        chosen.append(pick)
    return np.array(chosen, dtype=np.int64)
