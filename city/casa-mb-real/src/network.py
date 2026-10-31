"""Construye la red (PN, KC, APL, MBON, DAN) a partir del conectoma real o de un control, y corre protocolos.

Escalas sinapticas (mV por sinapsis) = parametros libres calibrados en calibrate.py (supuesto).
Signos: segun consensus_nt de la neurona presinaptica (ACh +, GABA -, glutamato -; otros 0).
"""
import os
import sys
from dataclasses import dataclass, field

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import engine as eng
import mbdata as md

SIGN = {"acetylcholine": 1.0, "gaba": -1.0, "glutamate": -1.0}


@dataclass
class Params:
    # escalas (mV por sinapsis, salvo S_mbon)
    s_pn: float = 0.5          # PN -> KC
    s_kcapl: float = 0.1       # KC -> APL
    s_aplkc: float = 1.0       # APL -> KC
    S_mbon: float = 7000.0     # ganancia KC -> MBON (con norm='N1': mV por (sinapsis / suma de sinapsis del MBON))
    s_mbon0: float = 0.5       # idem con norm='N0' (mV por sinapsis, sin normalizar)
    norm: str = "N1"           # N1: normalizada por MBON; N0: cruda
    wmin_pnkc: int = 1
    wmin_kcmbon: int = 1
    pn_base_hz: float = 3.0
    pn_odor_hz: float = 80.0   # amplitud maxima por canal
    n_channels_active: int = 12
    dan_us_hz: float = 50.0
    ramp_ms: float = 100.0     # subida lineal de la tasa de PN/DAN al inicio del estimulo
    gthr: float = 0.05         # umbral del perfil de compartimento DAN->MBON
    g_mode: str = "real"       # real | shuf_type | shuf_mbon | flat | none
    dan_ref_hz: float = 50.0
    tau_e_ms: float = 500.0
    eta: float = 2.3           # 1/s; calibrada con Hige 2015 (MBON-g1pedc CS+ -80% tras 1 emparejamiento), ver calibrate.py
    theta: float = 0.3         # umbral de traza para 'KC activa'
    n_pairs: int = 1
    ntest: int = 4
    tau_da_ms: float = 150.0
    kc_mbon_uniform: bool = False   # control: pesos KC->MBON uniformes (misma topologia)
    pn_kc_uniform: bool = False
    s_mbonmbon: float = 0.5    # escala de MBON->MBON (solo con 'MBON_MBON' en extra)
    s_aplmbon: float = 1.0     # escala de APL->MBON (solo con 'APL_MBON' en extra)
    nt_source: str = "consensus"   # 'consensus' (principal) | 'predicted' (control: reproduce el problema de datos de las KC)
    extra: tuple = ()          # proyecciones reales adicionales: 'PN_APL','APL_MBON','MBON_MBON','KC_KC5'


def _edges(nodes, edges, c0, c1, wmin=1):
    m = (nodes["cls"][edges["pre"]] == c0) & (nodes["cls"][edges["post"]] == c1) & (edges["w"] >= wmin)
    return edges["pre"][m].copy(), edges["post"][m].copy(), edges["w"][m].astype(np.float32).copy()


def group_codes(*arrs):
    """Codigo entero por combinacion unica de las etiquetas (determinista, sin hash())."""
    keys = np.array(["|".join(map(str, t)) for t in zip(*arrs)])
    return np.unique(keys, return_inverse=True)[1]


def swap_edges(pre, post, w, groups, rng, nswap_per_edge=10, slot="post"):
    """Intercambio de aristas que conserva los grados (Maslov-Sneppen) dentro de `groups` (etiqueta por arista).

    slot='post': se intercambian los PRESINAPTICOS entre dos aristas; el peso y el postsinaptico se quedan en su sitio
    (conserva grado de entrada y suma de pesos de entrada de cada postsinaptico, y grado de salida de cada presinaptico).
    Se rechazan los intercambios que duplicarian una arista.  Devuelve el nuevo `pre`.
    """
    pre = pre.copy()
    E = len(pre)
    present = set(zip(pre.tolist(), post.tolist()))
    # indices por grupo
    order = np.argsort(groups, kind="stable")
    g_sorted = groups[order]
    bounds = np.flatnonzero(np.r_[True, g_sorted[1:] != g_sorted[:-1], True])
    done = 0
    for a, b in zip(bounds[:-1], bounds[1:]):
        idx = order[a:b]
        m = len(idx)
        if m < 2:
            continue
        for _ in range(nswap_per_edge * m):
            i, j = idx[rng.integers(m)], idx[rng.integers(m)]
            if i == j:
                continue
            p1, p2 = pre[i], pre[j]
            if p1 == p2:
                continue
            q1, q2 = post[i], post[j]
            if (p2, q1) in present or (p1, q2) in present:
                continue
            present.discard((p1, q1)); present.discard((p2, q2))
            present.add((p2, q1)); present.add((p1, q2))
            pre[i], pre[j] = p2, p1
            done += 1
    return pre


@dataclass
class Net:
    n: int
    p: Params
    nodes: dict
    ranges: dict
    kind_lif: np.ndarray
    ptr: np.ndarray
    post: np.ndarray
    w: np.ndarray
    kptr: np.ndarray
    kpost: np.ndarray
    kw0: np.ndarray
    kf0: np.ndarray
    gen_pn: np.ndarray
    dptr: np.ndarray
    dpost: np.ndarray
    dg: np.ndarray
    channels: np.ndarray         # canal por PN generador
    info: dict = field(default_factory=dict)


def _csr(n, pre, post, w):
    o = np.argsort(pre, kind="stable")
    cnt = np.bincount(pre, minlength=n)
    ptr = np.zeros(n + 1, np.int64)
    ptr[1:] = np.cumsum(cnt)
    return ptr, post[o].astype(np.int64), w[o].astype(np.float32)


def dan_compartment_matrix(nodes, edges, p, rng=None):
    """Perfil dopaminergico (neurona DAN i -> MBON j) normalizado por tipo.  Devuelve (rows, cols, vals) en indices locales."""
    dan = np.flatnonzero(nodes["cls"] == md.DAN)
    mb = np.flatnonzero(nodes["cls"] == md.MBON)
    ld = {g: i for i, g in enumerate(dan)}
    lm = {g: i for i, g in enumerate(mb)}
    pre, post, w = _edges(nodes, edges, md.DAN, md.MBON, 1)
    C = np.zeros((len(dan), len(mb)), np.float32)
    for a, b, x in zip(pre, post, w):
        C[ld[a], lm[b]] += x
    types = nodes["type"][dan]
    G = np.zeros_like(C)
    ut = sorted(set(types))
    rowprof = {}
    for t in ut:
        ii = np.flatnonzero(types == t)
        prof = C[ii].sum(0)
        mx = prof.max()
        rowprof[t] = (prof / mx) if mx > 0 else prof
    mode = p.g_mode
    if mode == "shuf_type":     # cada tipo de DAN recibe el perfil de OTRO tipo (derangement)
        r = rng if rng is not None else np.random.default_rng(0)
        valid = [t for t in ut if rowprof[t].max() > 0]
        perm = list(valid)
        while True:
            perm = list(r.permutation(valid))
            if all(a != b for a, b in zip(valid, perm)):
                break
        mapping = dict(zip(valid, perm))
        rowprof = {t: (rowprof[mapping[t]] if t in mapping else rowprof[t]) for t in ut}
    elif mode == "shuf_mbon":   # el perfil de cada tipo se coloca sobre MBON al azar (misma forma, otros blancos)
        r = rng if rng is not None else np.random.default_rng(0)
        rowprof = {t: rowprof[t][r.permutation(len(mb))] for t in ut}
    elif mode == "flat":
        rowprof = {t: np.ones(len(mb), np.float32) for t in ut}
    elif mode == "none":
        rowprof = {t: np.zeros(len(mb), np.float32) for t in ut}
    for t in ut:
        ii = np.flatnonzero(types == t)
        prof = rowprof[t].copy()
        prof[prof < p.gthr] = 0.0
        G[ii] = prof[None, :] / len(ii)
    r_, c_ = np.nonzero(G)
    return r_, c_, G[r_, c_]


def build(nodes, edges, p: Params, rng=None, rewire=None):
    """rewire: None | dict(kind='kcmbon_global'|'kcmbon_lobe'|'pnkc_global'..., seed=int)."""
    rng = rng if rng is not None else np.random.default_rng(0)
    N = len(nodes["id"])
    cls = nodes["cls"]
    ranges = {c: (int(np.flatnonzero(cls == k)[0]), int(np.flatnonzero(cls == k)[-1]) + 1)
              for c, k in zip(md.CLASS_NAMES, range(5))}
    ntcol = nodes["nt_consensus"] if p.nt_source == "consensus" else nodes["nt_predicted"]
    sign = np.array([SIGN.get(x, 0.0) for x in ntcol], np.float32)
    # --- PN -> KC
    ppre, ppost, pw = _edges(nodes, edges, md.PN, md.KC, p.wmin_pnkc)
    if rewire and rewire.get("pnkc"):
        side_pre, side_post = nodes["side"][ppre], nodes["side"][ppost]
        gr = group_codes(side_pre, side_post)
        ppre = swap_edges(ppre, ppost, pw, gr, rng)
    if p.pn_kc_uniform:
        pw = np.full_like(pw, pw.mean())
    pre_l, post_l, w_l = [ppre], [ppost], [p.s_pn * sign[ppre] * pw]
    # --- KC -> APL, APL -> KC
    a, b, x = _edges(nodes, edges, md.KC, md.APL, 1)
    pre_l.append(a); post_l.append(b); w_l.append(p.s_kcapl * sign[a] * x)
    a, b, x = _edges(nodes, edges, md.APL, md.KC, 1)
    pre_l.append(a); post_l.append(b); w_l.append(p.s_aplkc * sign[a] * x)
    for name in p.extra:
        if name == "PN_APL":
            a, b, x = _edges(nodes, edges, md.PN, md.APL, 1); s = p.s_kcapl   # escala de las entradas al APL (con s_pn el APL saturaba a 177 Hz y callaba todas las KC)
        elif name == "APL_MBON":
            a, b, x = _edges(nodes, edges, md.APL, md.MBON, 1); s = p.s_aplmbon
        elif name == "MBON_MBON":
            a, b, x = _edges(nodes, edges, md.MBON, md.MBON, 3); s = p.s_mbonmbon
            if rewire and rewire.get("mbonmbon"):      # control: MBON->MBON con grados conservados (dentro de lado presinaptico/postsinaptico)
                a = swap_edges(a, b, x, group_codes(nodes["side"][a], nodes["side"][b]), rng)
        elif name == "KC_KC5":
            a, b, x = _edges(nodes, edges, md.KC, md.KC, 5); s = p.s_pn
        else:
            continue
        pre_l.append(a); post_l.append(b); w_l.append(s * sign[a] * x)
    pre = np.concatenate(pre_l); post = np.concatenate(post_l); w = np.concatenate(w_l).astype(np.float32)
    ptr, spost, sw = _csr(N, pre, post, w)
    # --- KC -> MBON (plastica)
    kpre, kpost_g, kw = _edges(nodes, edges, md.KC, md.MBON, p.wmin_kcmbon)
    if rewire and rewire.get("kcmbon"):
        kind = rewire["kcmbon"]
        sidep, sidepo = nodes["side"][kpre], nodes["side"][kpost_g]
        if kind == "global":
            gr = group_codes(sidep, sidepo)
        else:   # 'lobe': conserva subtipo de KC y lobulo (clase dominante) del MBON
            kc_cls = np.array([0 if t.startswith("KCg") else (1 if t.startswith("KCa'b'") else 2) for t in nodes["type"][kpre]])
            lob = rewire["mbon_lobe"][kpost_g]
            gr = group_codes(sidep, sidepo, kc_cls, lob)
        kpre = swap_edges(kpre, kpost_g, kw, gr, rng)
    if p.kc_mbon_uniform:
        kw = np.full_like(kw, kw.mean())
    wsum = np.bincount(kpost_g, weights=kw, minlength=N)
    if p.norm == "N1":
        kmv = p.S_mbon * kw / np.maximum(wsum[kpost_g], 1e-9)
    else:
        kmv = p.s_mbon0 * kw
    kc_lo, kc_hi = ranges["KC"]
    nkc = kc_hi - kc_lo
    kptr, kpost2, kw0 = _csr(nkc, kpre - kc_lo, kpost_g, kmv.astype(np.float32))
    # --- compartimentos DAN -> MBON (dg en indices locales)
    r_, c_, v_ = dan_compartment_matrix(nodes, edges, p, rng)
    ndan = ranges["DAN"][1] - ranges["DAN"][0]
    dptr, dpost, dgv = _csr(ndan, r_.astype(np.int64), c_.astype(np.int64), v_.astype(np.float32))
    # --- generadores PN (solo los que tienen salida) y canales por tipo
    pn_lo, pn_hi = ranges["PN"]
    has_out = np.bincount(pre, minlength=N)[pn_lo:pn_hi] > 0
    gen_pn = np.flatnonzero(has_out) + pn_lo
    types = nodes["type"][gen_pn]
    ut = sorted(set(types))
    ch = np.array([ut.index(t) for t in types])
    kind = np.zeros(N, np.bool_)
    for c in ("KC", "APL", "MBON"):
        kind[ranges[c][0]:ranges[c][1]] = True
    net = Net(n=N, p=p, nodes=nodes, ranges=ranges, kind_lif=kind, ptr=ptr, post=spost, w=sw, kptr=kptr, kpost=kpost2,
              kw0=kw0, kf0=np.ones_like(kw0), gen_pn=gen_pn, dptr=dptr, dpost=dpost, dg=dgv, channels=ch,
              info=dict(n_channels=len(ut), n_edges_static=int(len(sw)), n_edges_kcmbon=int(len(kw0))))
    return net
