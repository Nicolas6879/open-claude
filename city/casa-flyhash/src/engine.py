"""Motor: mapeo entrada->PN, codigos de KC (top-k tipo APL), codificadores comparadores, metricas.
Propio de esta casa; solo numpy/scipy/sklearn."""
import numpy as np, scipy.sparse as sp, scipy.linalg as sla
from wiring import Wiring, swap_null, fixed_indegree, kc_degree_null, dense_gauss, sparse_gauss_same_edges

N_PN = 314

# ------------------------------------------------------------------ mapeo entrada -> 314 PN
class Mapper:
    """kinds: proj | select | pca | glom | pca_deg | pca_rdeg.  Todo se ajusta SOLO con Xfit."""
    def __init__(self, kind, seed, pn_type=None, pn_order=None, n_pn=N_PN):
        self.kind, self.rng, self.pn_type, self.pn_order, self.n_pn = kind, np.random.default_rng(seed), pn_type, pn_order, n_pn

    def fit(self, X):
        d = X.shape[1]; self.mu = X.mean(0).astype(np.float32); Xc = X - self.mu; k = self.kind
        if k == 'proj':
            self.M = self.rng.standard_normal((d, self.n_pn)).astype(np.float32)
        elif k == 'select':
            ok = np.flatnonzero(X.std(0) > 1e-6)
            idx = self.rng.choice(ok, self.n_pn, replace=len(ok) < self.n_pn)
            self.M = np.zeros((d, self.n_pn), np.float32); self.M[idx, np.arange(self.n_pn)] = 1
        elif k in ('pca', 'pca_deg', 'pca_rdeg'):
            if d < self.n_pn: raise ValueError('pca necesita d >= 314')
            sub = Xc if len(Xc) <= 8000 else Xc[self.rng.choice(len(Xc), 8000, replace=False)]
            _, _, Vt = np.linalg.svd(sub, full_matrices=False)
            V = Vt[:self.n_pn].T.astype(np.float32)           # d x 314, columnas = PC1..PC314
            if k == 'pca': perm = self.rng.permutation(self.n_pn)   # PC j -> PN perm[j]
            else:
                order = np.asarray(self.pn_order)                   # PN de mayor a menor grado de salida
                perm = order if k == 'pca_deg' else order[::-1]     # PC1 -> PN de mayor (o menor) grado
            M = np.zeros_like(V); M[:, perm] = V; self.M = M
        elif k == 'glom':
            types = np.unique(self.pn_type, return_inverse=True)[1]; G = types.max() + 1
            R = self.rng.standard_normal((d, G)).astype(np.float32)
            self.M = R[:, types]                                    # cada PN copia el canal de su glomerulo
        else: raise ValueError(k)
        P = Xc @ self.M; self.mp = P.mean(0); self.sc = float(np.sqrt(P.var(0).mean()) + 1e-9)
        return self

    def __call__(self, X):
        return ((((X - self.mu) @ self.M) - self.mp) / self.sc).astype(np.float32)


# ------------------------------------------------------------------ codigos KC
def kc_drive(P, W):
    if sp.issparse(W): return np.ascontiguousarray((W @ P.T).T, dtype=np.float32)
    return (P @ W.T).astype(np.float32)

def topk_idx(D, k, dead=None):
    if dead is not None and dead.any():
        D = D.copy(); D[:, dead] = -np.inf
    return np.argpartition(D, D.shape[1] - k, axis=1)[:, -k:]

def idx_to_dense(idx, m):
    C = np.zeros((idx.shape[0], m), np.float32); np.put_along_axis(C, idx, 1.0, axis=1); return C


def idx_to_csr(idx, m):
    n, k = idx.shape
    return sp.csr_matrix((np.ones(n * k, np.float32), idx.ravel().astype(np.int64), np.arange(0, n * k + 1, k)), shape=(n, m))


class KCCoder:
    """Expansion tipo mosca: drive = W P, normalizacion opcional por KC (ajustada en FIT), top-k global (APL)."""
    def __init__(self, W, frac, norm=False, lesion=None, name=''):
        self.W, self.frac, self.norm, self.name = W, frac, norm, name
        self.m = W.shape[0]
        indeg = np.diff(W.indptr) if sp.issparse(W) else np.full(self.m, W.shape[1])
        self.dead = (indeg == 0)
        if lesion is not None: self.dead = self.dead | lesion
        self.k = max(1, int(round(frac * (self.m - self.dead.sum()))))   # fraccion de las KC vivas
        self.nnz = W.nnz if sp.issparse(W) else W.size
    def fit(self, Pfit):
        if self.norm:
            D = kc_drive(Pfit, self.W); self.dm = D.mean(0); self.ds = D.std(0) + 1e-6
        return self
    def drive(self, P):
        D = kc_drive(P, self.W)
        if self.norm: D = (D - self.dm) / self.ds
        return D
    def encode(self, P, chunk=None):
        chunk = chunk or max(10, min(2000, int(3e7 // self.m)))
        out = []
        for s in range(0, len(P), chunk):
            out.append(topk_idx(self.drive(P[s:s+chunk]), self.k, self.dead).astype(np.int32))
        return np.vstack(out)                       # (n, k) indices
    def dense(self, idx): return idx_to_dense(idx, self.m)
    def sim(self, Iq, Id):
        if self.m > 30000: return (idx_to_csr(Iq, self.m) @ idx_to_csr(Id, self.m).T).toarray().astype(np.float32)
        Q = self.dense(Iq); D = self.dense(Id); return Q @ D.T          # solapamiento = Hamming para k fijo
    def kernel(self, Ia, Ib): return self.sim(Ia, Ib)
    def feats(self, P): return self.dense(self.encode(P))
    def n_active(self): return self.k


class SimHash:
    """LSH clasico: b hiperplanos gaussianos sobre el vector PN, bits de signo. Distancia de Hamming."""
    def __init__(self, bits, seed, name=''):
        self.bits, self.name = bits, name; self.rng = np.random.default_rng(seed); self.nnz = bits * N_PN
    def fit(self, Pfit):
        self.A = self.rng.standard_normal((self.bits, Pfit.shape[1])).astype(np.float32); return self
    def encode(self, P): return np.sign(P @ self.A.T).astype(np.float32)
    def sim(self, Iq, Id): return Iq @ Id.T        # = bits - 2*Hamming
    def kernel(self, Ia, Ib): return Ia @ Ib.T
    def feats(self, P): return self.encode(P)
    def n_active(self): return self.bits


class RawPN:
    """Sin expansion ni hash: distancia euclidea sobre el vector PN (cota de referencia, continua)."""
    name = 'raw'; nnz = 0; integer_sim = False
    def fit(self, Pfit): return self
    def encode(self, P): return P.astype(np.float32)
    def sim(self, Iq, Id): return 2 * Iq @ Id.T - (Id**2).sum(1)[None, :]
    def kernel(self, Ia, Ib): return Ia @ Ib.T
    def feats(self, P): return P
    def n_active(self): return N_PN


class TopKPN:
    """Sin expansion pero con dispersion: top-k de las propias 314 PN (codigo binario disperso de 314)."""
    def __init__(self, frac): self.frac = frac; self.k = max(1, int(round(frac * N_PN))); self.name = 'noexp_topk'; self.nnz = 0
    def fit(self, Pfit): return self
    def encode(self, P): return topk_idx(P, self.k).astype(np.int32)
    def sim(self, Iq, Id): return idx_to_dense(Iq, N_PN) @ idx_to_dense(Id, N_PN).T
    def kernel(self, Ia, Ib): return self.sim(Ia, Ib)
    def feats(self, P): return idx_to_dense(self.encode(P), N_PN)
    def n_active(self): return self.k


# ------------------------------------------------------------------ metricas
def true_neighbors(Xq, Xd, k=10):
    """Vecinos verdaderos (euclidea en el espacio original) de cada consulta en la base."""
    d2 = (Xq**2).sum(1)[:, None] - 2 * Xq @ Xd.T + (Xd**2).sum(1)[None, :]
    return np.argpartition(d2, k, axis=1)[:, :k]

def retrieval_metrics(S, truth, labels_q=None, labels_d=None, rng=None, k=10, integer_sim=True):
    """S: (nq, nd) similitud (mayor=mejor). Desempate aleatorio. Devuelve MAP (de los k vecinos verdaderos),
    P@k frente al conjunto verdadero, y (si hay etiquetas) precision de etiqueta@k."""
    rng = rng or np.random.default_rng(0)
    S = S + rng.random(S.shape, dtype=np.float32) * (0.5 if integer_sim else 1e-6 * float(np.abs(S).mean()))   # rompe empates
    order = np.argsort(-S, axis=1)
    pos = np.empty_like(order); rows = np.arange(S.shape[0])[:, None]
    pos[rows, order] = np.arange(S.shape[1])[None, :]
    r = np.sort(pos[rows, truth], axis=1)                         # rangos (0-based) de los k verdaderos
    ap = (np.arange(1, truth.shape[1] + 1)[None, :] / (r + 1)).mean(1)
    top = order[:, :k]
    p_at = np.array([len(set(top[i]) & set(truth[i])) for i in range(len(top))]) / truth.shape[1]
    out = {'MAP': float(ap.mean()), 'P10': float(p_at.mean())}
    if labels_q is not None:
        out['LP10'] = float((labels_d[top] == labels_q[:, None]).mean())
    return out

def ridge_classify(Ztr, ytr, Zte, yte, lams=(1e-1, 1, 10, 100, 1000), seed=0, nclass=None):
    """Lectura lineal: regresion ridge a one-hot (primal, estadisticos suficientes), lambda (relativo a la
    traza media) elegido en una validacion interna del TRAIN (80/20) y reajustado con todo el TRAIN.
    Devuelve (exactitud en test, lambda). El test no se usa para nada mas."""
    rng = np.random.default_rng(seed); nclass = nclass or int(ytr.max()) + 1
    Ztr = np.asarray(Ztr, np.float32); n, F = Ztr.shape
    Y = np.eye(nclass, dtype=np.float32)[ytr]
    perm = rng.permutation(n); nv = max(1, n // 5); va, tr = perm[:nv], perm[nv:]
    def stats(idx):
        Z = Ztr[idx]; return Z.T @ Z, Z.sum(0), Z.T @ Y[idx], Y[idx].sum(0), len(idx)
    Sva = stats(va); Sall = stats(np.arange(n))
    Str = tuple(a - b for a, b in zip(Sall, Sva))
    def solve(S, lam):
        A, s, ZY, ys, nn = S; mu = s / nn; ym = ys / nn
        G = A - nn * np.outer(mu, mu); R = ZY - nn * np.outer(mu, ym)
        G[np.diag_indices(F)] += lam * (np.trace(G) / F + 1e-9)
        return mu, sla.solve(G, R, assume_a='pos'), ym
    best, bl = -1, None
    for lam in lams:
        mu, B, ym = solve(Str, lam); acc = ((((Ztr[va] - mu) @ B + ym).argmax(1)) == ytr[va]).mean()
        if acc > best: best, bl = acc, lam
    mu, B, ym = solve(Sall, bl)
    return float(((((np.asarray(Zte, np.float32) - mu) @ B + ym).argmax(1)) == yte).mean()), bl


def ridge_kernel(Ktr, ytr, Kte, yte, lams=(1e-1, 1, 10, 100, 1000), seed=0, nclass=None):
    """Igual que ridge_classify pero en forma dual (para codigos enormes): Ktr (n,n), Kte (nt,n) = k(test, train)."""
    rng = np.random.default_rng(seed); nclass = nclass or int(ytr.max()) + 1
    Ktr = np.asarray(Ktr, np.float64); Kte = np.asarray(Kte, np.float64); n = len(ytr)
    Y = np.eye(nclass)[ytr]
    def fitpred(tr, te_K, lam):                 # te_K: (nt, len(tr)) kernel test-vs-tr
        K = Ktr[np.ix_(tr, tr)]; nt = len(tr)
        Kc = K - K.mean(0)[None, :] - K.mean(1)[:, None] + K.mean()
        Yc = Y[tr] - Y[tr].mean(0)
        A = Kc + lam * (np.trace(Kc) / nt + 1e-9) * np.eye(nt)
        al = sla.solve(A, Yc, assume_a='pos')
        Tc = te_K - te_K.mean(1)[:, None] - K.mean(0)[None, :] + K.mean()
        return (Tc @ al + Y[tr].mean(0)).argmax(1)
    perm = rng.permutation(n); nv = max(1, n // 5); va, tr = perm[:nv], perm[nv:]
    best, bl = -1, None
    for lam in lams:
        acc = (fitpred(tr, Ktr[np.ix_(va, tr)], lam) == ytr[va]).mean()
        if acc > best: best, bl = acc, lam
    return float((fitpred(np.arange(n), Kte, bl) == yte).mean()), bl
