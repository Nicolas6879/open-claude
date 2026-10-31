"""Carga del subcircuito del cuerpo fungiforme (MB) de MaleCNS v1.0 para casa-mb-real.

Nodos: ALPN (neuronas de proyeccion), KC, APL, MBON, DAN.  No se incluyen ALLN (neuronas locales) ni nada mas.
Todo se lee de CONECTOMA_DATA (fuera del repo).  El subcircuito se cachea en NEURO2_CACHE (fuera del repo).
Los signos usan consensus_nt (NO predicted_nt: ver LOG, mensajes 10-11 del bus).
Etiquetas: medido = sale de los feather; el resto se declara en el sitio donde se usa.
"""
import os
import sys

import numpy as np

HOME = os.path.expanduser("~")
DATA_DIR = os.environ.get("CONECTOMA_DATA", os.path.join(HOME, ".cache", "conectoma-male-cns"))
CACHE_DIR = os.environ.get("NEURO2_CACHE", os.path.join(HOME, ".cache", "neuro2-mbreal"))
ANN = "body-annotations-male-cns-v1.0-minconf-0.5.feather"
NT = "body-neurotransmitters-male-cns-v1.0.feather"
WEIGHTS = "connectome-weights-male-cns-v1.0-minconf-0.5-significant-only.feather"

# codigos de clase de nodo
PN, KC, APL, MBON, DAN = 0, 1, 2, 3, 4
CLASS_NAMES = ["PN", "KC", "APL", "MBON", "DAN"]


def _arrow():
    libs = os.environ.get("CONECTOMA_LIBS")
    if libs and libs not in sys.path:
        sys.path.insert(0, libs)
    import pyarrow as pa
    import pyarrow.compute as pc
    import pyarrow.feather as feather
    return pa, pc, feather


def _path(name):
    p = os.path.join(DATA_DIR, name)
    if not os.path.exists(p):
        raise FileNotFoundError(f"falta {p}: ejecuta fetch_data.sh (o define CONECTOMA_DATA)")
    return p


def build_subset():
    """Lee los feather y devuelve (nodos, aristas). ~30 s la primera vez."""
    pa, pc, feather = _arrow()
    a = feather.read_table(_path(ANN), columns=["bodyId", "type", "class", "somaSide", "instance"], memory_map=True)
    bid = a["bodyId"].to_numpy()
    typ = np.array([t if t is not None else "" for t in a["type"].to_pylist()], dtype=object)
    cls = np.array([t if t is not None else "" for t in a["class"].to_pylist()], dtype=object)
    side = np.array([t if t is not None else "" for t in a["somaSide"].to_pylist()], dtype=object)
    inst = np.array([t if t is not None else "" for t in a["instance"].to_pylist()], dtype=object)
    code = np.full(len(bid), -1, dtype=np.int8)
    code[cls == "ALPN"] = PN
    code[cls == "Kenyon_Cell"] = KC
    code[typ == "APL"] = APL
    code[cls == "MBON"] = MBON
    code[cls == "DAN"] = DAN
    keep = np.where(code >= 0)[0]
    ids = bid[keep]
    order = np.lexsort((ids, code[keep]))        # ordenado por clase y bodyId -> indices estables
    keep = keep[order]
    ids = bid[keep]
    nodes = dict(id=ids.astype(np.int64), cls=code[keep], type=typ[keep].astype(str), side=side[keep].astype(str),
                 instance=inst[keep].astype(str))
    # neurotransmisor de consenso y predicho (se guardan los dos para comparar)
    n = feather.read_table(_path(NT), columns=["body", "consensus_nt", "predicted_nt"], memory_map=True)
    nb = n["body"].to_numpy()
    cons = n["consensus_nt"].to_pylist()
    pred = n["predicted_nt"].to_pylist()
    pos = {int(b): i for i, b in enumerate(nb)}
    nodes["nt_consensus"] = np.array([cons[pos[int(b)]] or "" for b in ids], dtype=str)
    nodes["nt_predicted"] = np.array([pred[pos[int(b)]] or "" for b in ids], dtype=str)
    # aristas entre nodos del subcircuito
    w = feather.read_table(_path(WEIGHTS), columns=["body_pre", "body_post", "weight"], memory_map=True)
    sarr = pa.array(ids, type=pa.int64())
    m = pc.and_(pc.is_in(w["body_pre"], value_set=sarr), pc.is_in(w["body_post"], value_set=sarr))
    sub = w.filter(m)
    pre, post, wt = sub["body_pre"].to_numpy(), sub["body_post"].to_numpy(), sub["weight"].to_numpy()
    idx = {int(b): i for i, b in enumerate(ids)}
    lut = np.vectorize(idx.get, otypes=[np.int64])
    edges = dict(pre=lut(pre), post=lut(post), w=wt.astype(np.float32))
    return nodes, edges


def load(cache=True):
    """(nodes, edges) con cache en NEURO2_CACHE/mbsubset_v1.npz."""
    cp = os.path.join(CACHE_DIR, "mbsubset_v1.npz")
    if cache and os.path.exists(cp):
        z = np.load(cp, allow_pickle=False)
        nodes = {k[2:]: z[k] for k in z.files if k.startswith("n_")}
        edges = {k[2:]: z[k] for k in z.files if k.startswith("e_")}
        return nodes, edges
    nodes, edges = build_subset()
    if cache:
        os.makedirs(CACHE_DIR, exist_ok=True)
        np.savez(cp, **{"n_" + k: v for k, v in nodes.items()}, **{"e_" + k: v for k, v in edges.items()})
    return nodes, edges
