"""Cableado PN->KC: carga, nulos y variantes. Todo con numpy/numba; propio de esta casa."""
import os, numpy as np, scipy.sparse as sp
from numba import njit

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, '..', 'data', 'pnkc.npz')


class Wiring:
    """Matriz m x n (KC x PN) dispersa + metadatos. W[k,p] = peso (nº de sinapsis o 1)."""
    def __init__(self, W, kc_side, pn_side, kc_group=None, pn_type=None, name=''):
        self.W = sp.csr_matrix(W, dtype=np.float32)
        self.kc_side = np.asarray(kc_side); self.pn_side = np.asarray(pn_side)
        self.kc_group = np.zeros(self.W.shape[0], np.int8) if kc_group is None else np.asarray(kc_group)
        self.pn_type = pn_type; self.name = name

    @property
    def m(self): return self.W.shape[0]
    @property
    def n(self): return self.W.shape[1]
    def binary(self):
        B = self.W.copy(); B.data[:] = 1; return Wiring(B, self.kc_side, self.pn_side, self.kc_group, self.pn_type, self.name + '_bin')
    def subset(self, idx):
        idx = np.asarray(idx)
        return Wiring(self.W[idx], self.kc_side[idx], self.pn_side, self.kc_group[idx], self.pn_type, self.name)
    def edges(self):
        c = self.W.tocoo(); return c.col.astype(np.int32), c.row.astype(np.int32), c.data.astype(np.float32)  # pn, kc, w


def load_real(path=DATA):
    z = np.load(path, allow_pickle=False)
    n, m = len(z['pn_body']), len(z['kc_body'])
    W = sp.coo_matrix((z['weight'].astype(np.float32), (z['kc_idx'].astype(int), z['pn_idx'].astype(int))), shape=(m, n)).tocsr()
    return Wiring(W, z['kc_side'], z['pn_side'], z['kc_group'], z['pn_type'], 'real')


# ---------------------------------------------------------------- nulo: intercambio de aristas por bloques
@njit(cache=False)
def _swap(pn, kc, block, nswap, seed):
    """Intercambio doble de aristas (p1,k1),(p2,k2)->(p1,k2),(p2,k1) solo si ambas son del mismo bloque
    (lado PN, lado KC), y no crea aristas duplicadas. Conserva grado de cada PN y de cada KC."""
    np.random.seed(seed)
    E = len(pn)
    # conjunto de aristas existentes como hash simple (p*65536+k)
    keys = set()
    for i in range(E):
        keys.add(np.int64(pn[i]) * 65536 + kc[i])
    # indices por bloque
    nb = block.max() + 1
    cnt = np.zeros(nb, np.int64)
    for i in range(E): cnt[block[i]] += 1
    start = np.zeros(nb + 1, np.int64)
    for b in range(nb): start[b + 1] = start[b] + cnt[b]
    order = np.empty(E, np.int64); fill = start[:-1].copy()
    for i in range(E):
        order[fill[block[i]]] = i; fill[block[i]] += 1
    done = 0; tries = 0
    while done < nswap and tries < nswap * 50:
        tries += 1
        i = np.random.randint(0, E); b = block[i]
        if cnt[b] < 2: continue
        j = order[start[b] + np.random.randint(0, cnt[b])]
        if i == j: continue
        p1, k1, p2, k2 = pn[i], kc[i], pn[j], kc[j]
        if p1 == p2 or k1 == k2: continue
        a = np.int64(p1) * 65536 + k2; c = np.int64(p2) * 65536 + k1
        if a in keys or c in keys: continue
        keys.remove(np.int64(p1) * 65536 + k1); keys.remove(np.int64(p2) * 65536 + k2)
        keys.add(a); keys.add(c)
        kc[i] = k2; kc[j] = k1
        done += 1
    return done


def swap_null(wr, seed, sweeps=10, weights='kc', blocks='side'):
    """Nulo con grados PN y KC conservados, respetando bloques de hemisferio.
    weights: 'kc' -> el peso viaja con el extremo KC (conserva el multiconjunto de pesos de cada KC);
             'shuffle' -> pesos de toda la red barajados entre aristas; 'none' -> binario."""
    pn, kc, w = wr.edges()
    kc = kc.copy()
    if blocks == 'side': block = (wr.pn_side[pn] > 0).astype(np.int64) * 2 + (wr.kc_side[kc] > 0).astype(np.int64)
    elif blocks == 'none': block = np.zeros(len(pn), np.int64)
    elif blocks == 'jdd':   # conserva la matriz de grados conjuntos (cuantiles de grado de salida PN x grado de entrada KC) y el lado
        od = np.bincount(pn, minlength=wr.n); idg = np.diff(wr.W.indptr)
        def qbin(x, nb):
            u = np.unique(x); q = np.unique(np.quantile(x, np.linspace(0, 1, nb + 1)[1:-1])); return np.searchsorted(q, x, side='right')
        pb = qbin(od, 6)[pn]; kb = qbin(idg[idg > 0], 6)
        kbin = np.zeros(wr.m, np.int64); kbin[idg > 0] = kb; kb_e = kbin[kc]
        block = (((wr.pn_side[pn] > 0).astype(np.int64) * 2 + (wr.kc_side[kc] > 0).astype(np.int64)) * 8 + pb) * 8 + kb_e
    elif blocks == 'group':  # lado PN x lado KC x subtipo KC (nulo mas estricto)
        block = ((wr.pn_side[pn] > 0).astype(np.int64) * 2 + (wr.kc_side[kc] > 0).astype(np.int64)) * 4 + wr.kc_group[kc]
    else: raise ValueError
    kc_orig = kc.copy()
    pn64 = pn.astype(np.int64); kc64 = kc.astype(np.int64)
    done = _swap(pn64, kc64, block, sweeps * len(pn), seed)
    kc = kc64
    # reconstruir: las aristas conservan su peso w (viaja con el extremo PN) por defecto
    rng = np.random.default_rng(seed + 12345)
    if weights == 'none': ww = np.ones_like(w)
    elif weights == 'shuffle': ww = rng.permutation(w)
    elif weights == 'kc':
        # el peso viaja con el extremo KC: la arista (p, k_old) con peso w pasa a (p, k_new) con el peso
        # de la arista que tenia a k_new. Se implementa reasignando por KC el multiconjunto de pesos.
        ww = np.empty_like(w)
        order_old = np.argsort(kc_orig, kind='stable'); order_new = np.argsort(kc, kind='stable')
        # misma cuenta de aristas por KC (grado conservado) -> alinear por bloque de KC
        wo = w[order_old]; ww_sorted = np.empty_like(w)
        # dentro de cada KC, barajar los pesos entre sus aristas nuevas
        kn = kc[order_new]
        bounds = np.flatnonzero(np.diff(kn)) + 1
        starts = np.r_[0, bounds]; ends = np.r_[bounds, len(kn)]
        for s, e in zip(starts, ends):
            ww_sorted[s:e] = rng.permutation(wo[s:e])
        ww[order_new] = ww_sorted
    else: raise ValueError
    W = sp.coo_matrix((ww, (kc, pn)), shape=(wr.m, wr.n)).tocsr()
    return Wiring(W, wr.kc_side, wr.pn_side, wr.kc_group, wr.pn_type, f'swap_{weights}'), done


def fixed_indegree(m, n, deg, rng, kc_side=None, pn_side=None, ipsi=0.979):
    """FlyHash clasico: cada KC muestrea `deg` PN distintos al azar (uniforme). Si se dan lados, respeta
    el hemisferio: con prob. `ipsi` cada sinapsis viene de un PN ipsilateral."""
    rows = np.repeat(np.arange(m), deg); cols = np.empty(m * deg, np.int64)
    if kc_side is None:
        for k in range(m): cols[k*deg:(k+1)*deg] = rng.choice(n, deg, replace=False)
    else:
        P = {s: np.flatnonzero(pn_side == s) for s in (0, 1)}
        for k in range(m):
            s = kc_side[k]; sel = []
            while len(sel) < deg:
                side = s if rng.random() < ipsi else 1 - s
                p = rng.choice(P[side])
                if p not in sel: sel.append(p)
            cols[k*deg:(k+1)*deg] = sel
    W = sp.coo_matrix((np.ones(m * deg, np.float32), (rows, cols)), shape=(m, n)).tocsr()
    return Wiring(W, kc_side if kc_side is not None else np.zeros(m, int), pn_side if pn_side is not None else np.zeros(n, int),
                  None, None, f'fixed{deg}')


def kc_degree_null(wr, rng, ipsi=None):
    """Grado de entrada de cada KC igual al real, PN elegidos uniformemente (con hemisferio), pesos barajados."""
    deg = np.diff(wr.W.indptr); pn, kc, w = wr.edges()
    P = {s: np.flatnonzero(wr.pn_side == s) for s in (0, 1)}
    ips = np.mean(wr.pn_side[pn] == wr.kc_side[kc]) if ipsi is None else ipsi
    rows, cols, vals = [], [], []
    wk = [w[kc == k] for k in range(wr.m)]  # lento pero una sola vez
    for k in range(wr.m):
        s = wr.kc_side[k]; sel = []
        while len(sel) < deg[k]:
            side = s if rng.random() < ips else 1 - s
            p = rng.choice(P[side])
            if p not in sel: sel.append(p)
        rows += [k] * deg[k]; cols += sel; vals += list(rng.permutation(wk[k]))
    W = sp.coo_matrix((np.array(vals, np.float32), (rows, cols)), shape=(wr.m, wr.n)).tocsr()
    return Wiring(W, wr.kc_side, wr.pn_side, wr.kc_group, wr.pn_type, 'kcdeg')


def dense_gauss(m, n, rng):
    return rng.standard_normal((m, n)).astype(np.float32)


def sparse_gauss_same_edges(wr, rng):
    """Control: misma topologia real pero pesos gaussianos (con signo) -> separa 'topologia' de 'peso'."""
    W = wr.W.copy(); W.data = rng.standard_normal(W.nnz).astype(np.float32)
    return Wiring(W, wr.kc_side, wr.pn_side, wr.kc_group, wr.pn_type, 'real_gaussw')


def scaled_null(wr, factor, rng):
    """Red `factor` veces mas grande con el mismo patron de grados: cada KC real se replica `factor` veces
    (grado, pesos y lado conservados), con PN elegidos al azar proporcionalmente al grado de salida real
    (hemisferio respetado). Es la version 'configuracion' escalada del nulo de intercambio."""
    pn, kc, w = wr.edges(); deg = np.diff(wr.W.indptr)
    pdeg = np.bincount(pn, minlength=wr.n).astype(float)
    ips = np.mean(wr.pn_side[pn] == wr.kc_side[kc])
    P = {s: np.flatnonzero(wr.pn_side == s) for s in (0, 1)}
    Pp = {s: pdeg[P[s]] / pdeg[P[s]].sum() for s in (0, 1)}
    wk = [w[kc == k] for k in range(wr.m)]
    rows, cols, vals, ksd, kgr = [], [], [], [], []
    r = 0
    for rep in range(factor):
        for k in range(wr.m):
            s = wr.kc_side[k]; sel = []
            while len(sel) < deg[k]:
                side = s if rng.random() < ips else 1 - s
                p = rng.choice(P[side], p=Pp[side])
                if p not in sel: sel.append(p)
            rows += [r] * deg[k]; cols += sel; vals += list(rng.permutation(wk[k])); ksd.append(s); kgr.append(wr.kc_group[k]); r += 1
    W = sp.coo_matrix((np.array(vals, np.float32), (rows, cols)), shape=(r, wr.n)).tocsr()
    return Wiring(W, np.array(ksd), wr.pn_side, np.array(kgr), wr.pn_type, f'scaled{factor}')


def random_wiring(deg, kc_side, pn_side, pn_w=None, ipsi=0.979, weights=None, rng=None, group=None):
    """Generador vectorizado de cableado aleatorio con grado de entrada `deg[k]` por KC. Cada sinapsis es ipsilateral con
    prob. `ipsi`; el PN se elige con prob. ∝ pn_w dentro del lado (None -> uniforme); sin aristas repetidas.
    weights: vector de pesos por arista (orden por KC) o None -> 1."""
    rng = rng or np.random.default_rng(0)
    deg = np.asarray(deg); m = len(deg); n = len(pn_side); E = int(deg.sum())
    kc = np.repeat(np.arange(m), deg)
    ip = rng.random(E) < ipsi
    side = np.where(ip, kc_side[kc], 1 - kc_side[kc])
    P = {s: np.flatnonzero(pn_side == s) for s in (0, 1)}
    pw = np.ones(n) if pn_w is None else np.asarray(pn_w, float)
    Pp = {s: pw[P[s]] / pw[P[s]].sum() for s in (0, 1)}
    pn = np.empty(E, np.int64)
    for s in (0, 1):
        sel = np.flatnonzero(side == s); pn[sel] = rng.choice(P[s], len(sel), p=Pp[s])
    for _ in range(50):                       # eliminar repetidos redibujando
        key = kc.astype(np.int64) * n + pn
        order = np.argsort(key, kind='stable'); ks = key[order]
        dup = order[1:][ks[1:] == ks[:-1]]
        if len(dup) == 0: break
        for s in (0, 1):
            sel = dup[side[dup] == s]
            if len(sel): pn[sel] = rng.choice(P[s], len(sel), p=Pp[s])
    w = np.ones(E, np.float32) if weights is None else np.asarray(weights, np.float32)
    W = sp.coo_matrix((w, (kc, pn)), shape=(m, n)).tocsr()
    return Wiring(W, kc_side, pn_side, group, None, 'rand')


def scaled_real_like(wr, factor, rng, weighted=False):
    """Red `factor` veces mayor con el patron de grados real: grados de entrada de KC (replicados), grado de salida de PN
    proporcional al real, hemisferio, y (opcional) pesos reales barajados dentro de cada KC replicada."""
    pn, kc, w = wr.edges(); deg = np.diff(wr.W.indptr)
    pdeg = np.bincount(pn, minlength=wr.n).astype(float)
    ips = float(np.mean(wr.pn_side[pn] == wr.kc_side[kc]))
    order = np.argsort(kc, kind='stable'); wk = w[order]
    degs = np.tile(deg, factor); sides = np.tile(wr.kc_side, factor); grp = np.tile(wr.kc_group, factor)
    ww = None
    if weighted:
        ww = np.empty(int(degs.sum()), np.float32); pos = 0
        bounds = np.r_[0, np.cumsum(deg)]
        for f in range(factor):
            for k in range(wr.m):
                d = deg[k]; ww[pos:pos + d] = rng.permutation(wk[bounds[k]:bounds[k + 1]]); pos += d
    out = random_wiring(degs, sides, wr.pn_side, pdeg, ips, ww, rng, grp)
    out.name = f'scaled{factor}'; return out


def dedup_type_swaps(wr, seed, max_tries=400000):
    """Control de mecanismo: elimina del cableado real las entradas REPETIDAS del mismo tipo de PN (mismo glomerulo) en una misma KC,
    mediante intercambios de aristas que conservan exactamente el grado de cada PN y de cada KC, el hemisferio por bloques
    (lado PN x lado KC) y el nº de aristas. Devuelve (Wiring, nº de repetidos antes, nº de repetidos despues)."""
    rng = np.random.default_rng(seed)
    t = np.unique(wr.pn_type, return_inverse=True)[1]
    pn, kc, w = wr.edges(); E = len(pn); pn = pn.copy(); kc = kc.copy()
    ps = (wr.pn_side > 0).astype(int); ks = (wr.kc_side > 0).astype(int)
    inputs = [dict() for _ in range(wr.m)]            # por KC: tipo -> nº de entradas
    pset = [set() for _ in range(wr.m)]
    for e in range(E):
        inputs[kc[e]][t[pn[e]]] = inputs[kc[e]].get(t[pn[e]], 0) + 1; pset[kc[e]].add(pn[e])
    def ndup(): return sum(c - 1 for d in inputs for c in d.values() if c > 1)
    before = ndup()
    byk = {}
    for e in range(E): byk.setdefault(kc[e], []).append(e)
    tries = 0
    while tries < max_tries:
        dup_k = [k for k in range(wr.m) if any(c > 1 for c in inputs[k].values())]
        if not dup_k: break
        for k in dup_k:
            # una arista cuyo tipo esta repetido en k
            es = [e for e in byk[k] if inputs[k][t[pn[e]]] > 1]
            if not es: continue
            e = es[rng.integers(len(es))]; p2 = pn[e]
            for _ in range(200):
                tries += 1
                e2 = rng.integers(E); k2 = kc[e2]; p1 = pn[e2]
                if k2 == k or ps[p1] != ps[p2] or ks[k2] != ks[k]: continue
                if t[p1] in inputs[k] or p1 in pset[k] or p2 in pset[k2]: continue
                if inputs[k2].get(t[p2], 0) > 0 and t[p2] != t[p1]: continue   # no crear repetido nuevo en k2
                # aplicar: (p2,k),(p1,k2) -> (p1,k),(p2,k2)
                for kk, pold, pnew in ((k, p2, p1), (k2, p1, p2)):
                    inputs[kk][t[pold]] -= 1
                    if inputs[kk][t[pold]] == 0: del inputs[kk][t[pold]]
                    inputs[kk][t[pnew]] = inputs[kk].get(t[pnew], 0) + 1
                    pset[kk].discard(pold); pset[kk].add(pnew)
                pn[e], pn[e2] = p1, p2
                break
        if tries >= max_tries: break
    W = sp.coo_matrix((w, (kc, pn)), shape=(wr.m, wr.n)).tocsr()
    return Wiring(W, wr.kc_side, wr.pn_side, wr.kc_group, wr.pn_type, 'dedup'), before, ndup()
