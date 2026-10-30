"""Carga de datos del conectoma MaleCNS v1.0 (archivos Feather planos).

Todo se lee de CONECTOMA_DATA (por defecto ~/.cache/conectoma-male-cns), fuera del repo.
Si pyarrow no esta instalado, se busca en CONECTOMA_LIBS (directorio creado con pip --target).
Los datos son no confiables: solo se leen columnas; nunca se ejecuta nada de ellos.
"""
import os
import sys

import numpy as np

DATA_DIR = os.environ.get("CONECTOMA_DATA", os.path.join(os.path.expanduser("~"), ".cache", "conectoma-male-cns"))
ANN = "body-annotations-male-cns-v1.0-minconf-0.5.feather"
NT = "body-neurotransmitters-male-cns-v1.0.feather"
WEIGHTS = "connectome-weights-male-cns-v1.0-minconf-0.5-significant-only.feather"

# Clases que forman el subcircuito olfativo/MB que estudiamos.
MB_CLASSES = ("Kenyon_Cell", "ALPN", "MBON", "DAN", "ALLN")


def _arrow():
    libs = os.environ.get("CONECTOMA_LIBS")
    if libs and libs not in sys.path:
        sys.path.insert(0, libs)
    import pyarrow.compute as pc
    import pyarrow.feather as feather
    return feather, pc


def path(name):
    p = os.path.join(DATA_DIR, name)
    if not os.path.exists(p):
        raise FileNotFoundError(f"falta {p}: ejecuta fetch_data.sh (o define CONECTOMA_DATA)")
    return p


def load_annotations():
    """Devuelve dict bodyId -> dict(type, cls, side, soma=(x,y,z) o None)."""
    feather, _ = _arrow()
    t = feather.read_table(path(ANN), columns=["bodyId", "type", "class", "somaSide", "somaLocation"], memory_map=True)
    out = {}
    for b, ty, c, s, loc in zip(t["bodyId"].to_pylist(), t["type"].to_pylist(), t["class"].to_pylist(),
                                t["somaSide"].to_pylist(), t["somaLocation"].to_pylist()):
        soma = tuple(loc) if loc else None
        out[int(b)] = {"type": ty, "cls": c, "side": s, "soma": soma}
    return out


def load_neurotransmitters():
    """dict bodyId -> nt predicho (acetylcholine, gaba, glutamate, dopamine, ...)."""
    feather, _ = _arrow()
    t = feather.read_table(path(NT), columns=["body", "predicted_nt"], memory_map=True)
    return {int(b): n for b, n in zip(t["body"].to_pylist(), t["predicted_nt"].to_pylist())}


def is_mb_neuron(info):
    return info["cls"] in MB_CLASSES or info["type"] == "APL"


def load_subcircuit(ann, cache=True):
    """Aristas (pre, post, peso en sinapsis) entre neuronas del subcircuito MB.

    Lee la matriz de pesos completa (25.6 M filas) solo en columnas numericas y filtra con is_in.
    Cachea el resultado en DATA_DIR/mb_subset_v1.npz (no es un dato del repo).
    """
    cache_path = os.path.join(DATA_DIR, "mb_subset_v1.npz")
    if cache and os.path.exists(cache_path):
        z = np.load(cache_path)
        return z["pre"], z["post"], z["w"]
    feather, pc = _arrow()
    import pyarrow as pa
    S = sorted(b for b, info in ann.items() if is_mb_neuron(info))
    sarr = pa.array(S, type=pa.int64())
    w = feather.read_table(path(WEIGHTS), columns=["body_pre", "body_post", "weight"], memory_map=True)
    m = pc.and_(pc.is_in(w["body_pre"], value_set=sarr), pc.is_in(w["body_post"], value_set=sarr))
    sub = w.filter(m)
    pre = sub["body_pre"].to_numpy()
    post = sub["body_post"].to_numpy()
    wt = sub["weight"].to_numpy()
    if cache:
        np.savez(cache_path, pre=pre, post=post, w=wt)
    return pre, post, wt


def glomerulus(type_name):
    """Token de glomerulo a partir del tipo (p. ej. 'DA1_lPN' -> 'DA1'); 'M' agrupa PN multiglomerulares."""
    if not type_name:
        return None
    return type_name.split("_")[0]
