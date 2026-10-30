"""Modelo adaptativo de Physarum (Tero-Kobayashi-Nakagaki 2007 / Tero et al. 2010), desde cero.

Red: nodos, aristas (u,v) con longitud L_e y conductividad D_e(t).
Flujo: Q_e = (D_e/L_e)(p_u - p_v); Kirchhoff: suma de flujos en cada nodo = fuente/sumidero.
Adaptacion: dD_e/dt = f(|Q_e|) - r*D_e.
 f = 'pow'  : f(q) = q^gamma           (gamma=1 -> Bonifaci-Mehlhorn-Varma, converge al camino mas corto)
 f = 'sat'  : f(q) = q^gamma/(1+q^gamma) (forma biologica citada en la literatura)

Dos modos:
 - un par fuente->sumidero (laberintos, Dijkstra)
 - TODOS los pares de nodos "comida" a la vez (campo medio): D evoluciona con la media sobre pares
   de f(|Q|). Equivale a conmutar pares al azar rapidamente respecto a D (Tero 2010 usaba pares al azar).
"""
import numpy as np
import scipy.sparse as sp
import scipy.sparse.linalg as spla


def f_resp(q, gamma, kind):
    if kind == "pow":
        return q ** gamma
    qg = q ** gamma
    return qg / (1.0 + qg)


def laplacian_dense(n, edges, c):
    A = np.zeros((n, n))
    u, v = edges[:, 0], edges[:, 1]
    np.add.at(A, (u, u), c)
    np.add.at(A, (v, v), c)
    np.add.at(A, (u, v), -c)
    np.add.at(A, (v, u), -c)
    return A


def single_pair_flow(n, edges, L, D, s, t, floor=1e-12):
    """Flujo unitario s->t. Devuelve (Q por arista orientada u->v, potenciales)."""
    c = np.maximum(D, floor) / L
    u, v = edges[:, 0], edges[:, 1]
    A = sp.coo_matrix((np.concatenate([c, c, -c, -c]),
                       (np.concatenate([u, v, u, v]), np.concatenate([u, v, v, u]))), shape=(n, n)).tocsr()
    b = np.zeros(n)
    b[s] = 1.0
    b[t] = -1.0
    keep = np.arange(n) != t           # tierra en el sumidero
    p = np.zeros(n)
    p[keep] = spla.spsolve(A[keep][:, keep].tocsc(), b[keep])
    Q = c * (p[u] - p[v])
    return Q, p


def allpairs_flows(n, edges, L, D, foods, floor=1e-12, return_mats=False):
    """Para cada par (s<t) de nodos comida, flujo unitario s->t. Devuelve array (E, npairs) de |Q|."""
    c = np.maximum(D, floor) / L
    A = laplacian_dense(n, edges, c)
    G = np.linalg.inv(A + np.ones((n, n)) / n)   # pseudo-inversa (A tiene nucleo = vector 1)
    u, v = edges[:, 0], edges[:, 1]
    Df = (G[u][:, foods] - G[v][:, foods])        # (E, m)
    m = len(foods)
    iu, ju = np.triu_indices(m, 1)
    Q = c[:, None] * (Df[:, iu] - Df[:, ju])      # (E, npairs)
    return Q


class Physarum:
    def __init__(self, n, edges, L, foods, gamma=1.0, kind="sat", dt=0.05, r=1.0, D0=1.0, rng=None):
        self.n = n
        self.edges = np.asarray(edges, dtype=int)
        self.L = np.asarray(L, dtype=float)
        self.foods = np.asarray(foods, dtype=int)
        self.gamma, self.kind, self.dt, self.r = gamma, kind, dt, r
        if rng is None:
            D = np.full(len(self.L), float(D0))
        else:
            D = D0 * rng.uniform(0.5, 1.5, len(self.L))
        self.D = D
        self.t = 0.0

    def step_pair(self, s, t):
        Q, _ = single_pair_flow(self.n, self.edges, self.L, self.D, s, t)
        self.D = self.D + self.dt * (f_resp(np.abs(Q), self.gamma, self.kind) - self.r * self.D)
        self.t += self.dt
        return Q

    def step_all(self):
        Q = allpairs_flows(self.n, self.edges, self.L, self.D, self.foods)
        F = f_resp(np.abs(Q), self.gamma, self.kind).mean(axis=1)
        self.D = self.D + self.dt * (F - self.r * self.D)
        self.t += self.dt
        return Q

    def run_pair(self, s, t, T, tol=1e-9, record=False):
        hist = []
        nsteps = int(round(T / self.dt))
        for k in range(nsteps):
            Dold = self.D.copy()
            self.step_pair(s, t)
            if record:
                hist.append(self.D.copy())
            if np.max(np.abs(self.D - Dold)) < tol * self.dt:
                break
        return hist

    def run_all(self, T, tol=1e-8, record_every=0):
        hist = []
        nsteps = int(round(T / self.dt))
        for k in range(nsteps):
            Dold = self.D.copy()
            self.step_all()
            if record_every and k % record_every == 0:
                hist.append((self.t, self.D.copy()))
            if np.max(np.abs(self.D - Dold)) < tol * self.dt:
                break
        return hist


def run_mean_field(n, edges, L, foods, gamma, kind="sat", dt=0.2, T=150.0, r=1.0, D0=None, rng=None,
                   prune_below=1e-6, compact_every=25, tol=1e-7, snapshots=0, weights=None):
    """Dinamica de campo medio con todos los pares de comida. Compacta las aristas muertas (D<prune_below) y los
    nodos que quedan fuera de la componente de la comida (acelera mucho). Devuelve (edges, L, D, info) de las
    aristas supervivientes, con indices de nodo ORIGINALES. weights: peso por par (orden triu de foods) o None."""
    import scipy.sparse.csgraph as csg
    edges = np.asarray(edges, dtype=int)
    L = np.asarray(L, float)
    D = (np.full(len(L), 1.0) if D0 is None else np.asarray(D0, float)).copy()
    if rng is not None:
        D = D * rng.uniform(0.5, 1.5, len(L))
    foods0 = np.asarray(foods, int)
    old = np.arange(n)                 # indice local -> original
    ln, lfoods, ledges = n, foods0.copy(), edges.copy()
    w = None if weights is None else np.asarray(weights, float) / np.mean(weights)
    snaps = []
    nsteps = int(round(T / dt))
    t = 0.0
    k = 0
    delta = np.inf
    for k in range(nsteps):
        Q = allpairs_flows(ln, ledges, L, D, lfoods, floor=1e-9)
        fq = f_resp(np.abs(Q), gamma, kind)
        F = fq.mean(axis=1) if w is None else (fq * w[None, :]).mean(axis=1)
        Dn = D + dt * (F - r * D)
        delta = np.max(np.abs(Dn - D)) / dt
        D = Dn
        t += dt
        if snapshots and k % snapshots == 0:
            snaps.append((t, old[ledges].copy(), D.copy()))
        if k % compact_every == compact_every - 1:
            alive = D > prune_below
            if not alive.all():
                A = sp.coo_matrix((np.ones(alive.sum()), (ledges[alive, 0], ledges[alive, 1])), shape=(ln, ln))
                nc_, lab = csg.connected_components(A, directed=False)
                if len(set(lab[lfoods])) == 1:
                    keepn = lab == lab[lfoods[0]]
                    newid = -np.ones(ln, int)
                    newid[keepn] = np.arange(keepn.sum())
                    m = alive & keepn[ledges[:, 0]] & keepn[ledges[:, 1]]
                    ledges = newid[ledges[m]]
                    L, D = L[m], D[m]
                    old = old[keepn]
                    lfoods = newid[lfoods]
                    ln = int(keepn.sum())
        if delta < tol:
            break
    return old[ledges], L, D, dict(t=t, steps=k + 1, converged=bool(delta < tol), delta=float(delta), snaps=snaps)
