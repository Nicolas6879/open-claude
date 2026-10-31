"""Valencia y metricas de aprendizaje a partir de las tasas de los MBON."""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mbdata as md


def valence_vector(nodes, scheme="nt"):
    """v_j por MBON (orden del bloque MBON).  'nt': Aso 2014b (glutamato -1; GABA/ACh +1)."""
    mb = np.flatnonzero(nodes["cls"] == md.MBON)
    nt = nodes["nt_consensus"][mb]
    if scheme == "nt":
        return np.array([-1.0 if x == "glutamate" else (1.0 if x in ("gaba", "acetylcholine") else 0.0) for x in nt])
    if scheme == "nt_predicted":
        nt = nodes["nt_predicted"][mb]
        return np.array([-1.0 if x == "glutamate" else (1.0 if x in ("gaba", "acetylcholine") else 0.0) for x in nt])
    raise ValueError(scheme)


def learning_index(mb_pre, mb_post, v):
    """mb_*: [3 olores, n_mbon] (Hz).  Devuelve LI por olor = (V_post - V_pre)/sum|v| r_pre, y V_pre, V_post (Hz)."""
    Vp = mb_pre @ v
    Vq = mb_post @ v
    den = (np.abs(v)[None, :] * mb_pre).sum(1)
    return (Vq - Vp) / np.maximum(den, 1e-9), Vp, Vq
