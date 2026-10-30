"""Computacion de reservorio: red espacial tipo Physarum (conductividades adaptativas) vs Echo State Network.

Reservorio Physarum: grafo Delaunay en el cuadrado unidad. Estado lento: D_e (conductividad de cada tubo).
En cada paso se inyecta una corriente b(t) = (bias + gain*u(t)) * w (w de suma cero, aleatorio), se resuelve
Kirchhoff A(D) p = b y se actualiza  D <- D + dt*( |Q|^gamma_eff - r*D ),  Q_e = D_e (p_u-p_v)/L_e.
Caracteristicas de lectura: potenciales de nodo (y opcionalmente D).  Sin ninguna tanh: la no linealidad
viene solo de que D depende del flujo (bilineal: p ~ I * g(D)).
"""
import numpy as np
from .graphs import delaunay_edges, edge_lengths


class PhysarumReservoir:
    def __init__(self, n=40, gamma=2.0, r_dt=0.05, gain=1.0, bias=0.5, nin=3, seed=0, D0=0.5, Dmax=None,
                 dt=1.0, noise=0.0, spread=0.0):
        rng = np.random.default_rng(seed)
        self.n = n
        pts = rng.random((n, 2))
        self.edges = delaunay_edges(pts)
        self.L = edge_lengths(pts, self.edges)
        self.E = len(self.L)
        self.gamma, self.r_dt, self.gain, self.bias, self.D0 = gamma, r_dt, gain, bias, D0
        self.dt = dt
        self.r_vec = np.minimum(r_dt * 10 ** (spread * (rng.random(self.E) - 0.5)), 0.9) if spread > 0 else np.full(self.E, r_dt)
        # direcciones de inyeccion: nin pares fuente-sumidero aleatorios -> w (suma cero)
        self.W = np.zeros((nin, n))
        for k in range(nin):
            a, b = rng.choice(n, 2, replace=False)
            self.W[k, a], self.W[k, b] = 1.0, -1.0
        self.w_in = rng.uniform(-1, 1, nin)       # mezcla de entrada
        self.b0 = np.zeros(n)                      # corriente de fondo
        a, b = rng.choice(n, 2, replace=False)
        self.b0[a], self.b0[b] = 1.0, -1.0
        self.ground = int(rng.integers(n))
        self.u_, self.v_ = self.edges[:, 0], self.edges[:, 1]
        self.B = np.zeros((self.E, n))              # matriz de incidencia
        self.B[np.arange(self.E), self.u_] = 1.0
        self.B[np.arange(self.E), self.v_] = -1.0

    def run(self, u, return_D=True, washout=0):
        u = np.asarray(u, float)
        T = len(u)
        n, E = self.n, self.E
        D = np.full(E, self.D0)
        keep = np.arange(n) != self.ground
        P = np.zeros((T, n))
        DD = np.zeros((T, E)) if return_D else None
        wsum = self.w_in @ self.W
        for t in range(T):
            b = self.bias * self.b0 + self.gain * u[t] * wsum
            c = D / self.L
            A = self.B.T @ (c[:, None] * self.B)
            p = np.zeros(n)
            p[keep] = np.linalg.solve(A[np.ix_(keep, keep)] + 1e-12 * np.eye(n - 1), b[keep])
            Q = c * (p[self.u_] - p[self.v_])
            D = D + self.r_vec * (np.abs(Q) ** self.gamma - D)
            D = np.clip(D, 1e-6, 1e3)
            P[t] = p
            if return_D:
                DD[t] = D
        return P, DD


class ESN:
    def __init__(self, N=100, rho=0.9, in_scale=0.5, leak=1.0, density=0.1, seed=0, bias_scale=0.1):
        rng = np.random.default_rng(seed)
        W = rng.normal(size=(N, N)) * (rng.random((N, N)) < density)
        ev = np.max(np.abs(np.linalg.eigvals(W)))
        self.W = W * (rho / ev) if ev > 0 else W
        self.Win = rng.uniform(-1, 1, N) * in_scale
        self.b = rng.uniform(-1, 1, N) * bias_scale
        self.leak, self.N = leak, N

    def run(self, u):
        T = len(u)
        x = np.zeros(self.N)
        X = np.zeros((T, self.N))
        for t in range(T):
            x = (1 - self.leak) * x + self.leak * np.tanh(self.W @ x + self.Win * u[t] + self.b)
            X[t] = x
        return X


def ridge_fit(X, y, lam):
    X1 = np.c_[X, np.ones(len(X))]
    A = X1.T @ X1 + lam * np.eye(X1.shape[1])
    return np.linalg.solve(A, X1.T @ y)


def ridge_pred(X, w):
    return np.c_[X, np.ones(len(X))] @ w


# ---------------------------------------------------------------- tareas
def narma10(T, rng):
    u = rng.uniform(0, 0.5, T)
    y = np.zeros(T)
    for t in range(10, T):
        y[t] = 0.3 * y[t - 1] + 0.05 * y[t - 1] * np.sum(y[t - 10:t]) + 1.5 * u[t - 10] * u[t - 1] + 0.1
    return u, y


def mackey_glass(T, tau=17, h=1.0, sub=3, rng=None, x0=None):
    """Euler con paso h=1 (suficiente para esta comparacion) y submuestreo sub. Devuelve serie normalizada a [0,1]-ish."""
    n = T * sub + 1000
    x = np.zeros(n + tau + 1)
    x[: tau + 1] = 1.2 + (0.0 if rng is None else 0.05 * rng.random(tau + 1))
    for t in range(tau, n + tau):
        xt = x[t]
        xd = x[t - tau]
        x[t + 1] = xt + h * (0.2 * xd / (1 + xd ** 10) - 0.1 * xt)
    s = x[tau + 1000:][::sub][:T]
    return (s - s.mean()) / s.std()


def nrmse(y, yh):
    return float(np.sqrt(np.mean((y - yh) ** 2) / np.var(y)))
