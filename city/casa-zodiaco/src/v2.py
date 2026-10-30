"""Modelo v2 (regimen B): 'propension de arista' aprendida con rasgos gestalticos universales.

Idea: en vez de dos pesos fijos (brillo, proximidad), se aprende P(arista e aparece en una cultura al azar)
a partir de rasgos geometricos/perceptivos de la arista calculados SOLO con el cielo (nunca con la cultura):
  ln d, mag de la mas debil/brillante, escalado local (R=30, 60), rango del vecino 'mas brillante o igual'
  (cada estrella se une a su vecino brillante mas cercano), bloqueadores en la lente RNG (hay otra estrella
  entre ambas?), densidad local de estrellas brillantes, grado en el grafo candidato.
Etiqueta: aparece/no aparece en la cultura de entrenamiento (con peso 1/|familia| / n_familias).
Modelo: HistGradientBoosting pequeno (profundidad 3) y regresion logistica (interpretable).
Se aplica a cualquier cielo (posiciones + magnitudes aparentes), p. ej. el visto desde otra estrella.
"""
import numpy as np
from scipy.spatial import cKDTree
import modelo as M

NOMBRES = ["ln_d", "m_debil", "m_brillante", "dm", "P30", "B30", "P60", "B60", "rango_debil", "rango_brillante",
           "bloq_igual", "bloq_45", "dens10", "dens25", "grado_i", "grado_j", "d_rel_nn"]
KNN = 40


def chord(a, b):
    return np.linalg.norm(a - b, axis=-1)


def rasgos(v, mag, umbrales=(3.5, 4.0, 4.5, 5.5)):
    """Aristas candidatas y matriz de rasgos para un cielo (v unitarios (n,3), mag aparentes)."""
    cand = M.Candidatas(v, mag, umbrales=umbrales)
    e = cand.e
    n = len(v)
    if len(e) == 0:
        return cand, np.zeros((0, len(NOMBRES)))
    # orientar: i = mas brillante, j = mas debil
    sw = mag[e[:, 0]] > mag[e[:, 1]]
    i = np.where(sw, e[:, 1], e[:, 0])
    j = np.where(sw, e[:, 0], e[:, 1])
    mi, mj = mag[i], mag[j]
    dch = chord(v[i], v[j])
    kd = cKDTree(v)
    k = min(KNN + 1, n)
    dist, nn = kd.query(v, k=k)  # (n,k) incluye a la propia estrella en la columna 0
    # rango de i entre los vecinos de j que son al menos tan brillantes como j  (cada estrella debil busca un brillante)
    nnj = nn[j]
    dj = dist[j]
    ok_b = (mag[nnj] <= mj[:, None]) & (nnj != j[:, None])
    mas_cerca = ok_b & (dj < dch[:, None] - 1e-12)
    rango_debil = 1 + mas_cerca.sum(1)
    # rango de j entre los vecinos de i que son al menos tan brillantes como i
    nni = nn[i]
    di = dist[i]
    ok_i = (mag[nni] <= mi[:, None]) & (nni != i[:, None])
    rango_brillante = 1 + (ok_i & (di < dch[:, None] - 1e-12)).sum(1)
    # bloqueadores de la lente RNG: k con d(i,k)<d y d(j,k)<d
    def bloq(umbral_mag):
        cnt = np.zeros(len(e), dtype=int)
        for c in range(1, k):
            kk = nni[:, c]
            m = (di[:, c] < dch - 1e-12) & (kk != j) & (mag[kk] <= umbral_mag)
            m &= chord(v[kk], v[j]) < dch - 1e-12
            cnt += m
        return cnt
    bloq_igual = bloq(mj + 0.0)
    bloq_45 = bloq(4.5)
    mid = v[i] + v[j]
    mid /= np.linalg.norm(mid, axis=1, keepdims=True)
    br = np.where(mag <= 4.5)[0]
    kb = cKDTree(v[br])
    dens10 = np.array([len(x) for x in kb.query_ball_point(mid, 2 * np.sin(np.radians(10) / 2))])
    dens25 = np.array([len(x) for x in kb.query_ball_point(mid, 2 * np.sin(np.radians(25) / 2))])
    grado = np.bincount(e.ravel(), minlength=n)
    # distancia relativa al vecino mas cercano de la estrella debil
    dnn_j = dist[j, 1]
    d_rel = dch / np.maximum(dnn_j, 1e-9)
    P30 = cand._centrar(cand.P, 30, "P"); B30 = cand._centrar(cand.B, 30, "B")
    P60 = cand._centrar(cand.P, 60, "P"); B60 = cand._centrar(cand.B, 60, "B")
    X = np.stack([np.log(cand.d), mj, mi, mj - mi, P30, B30, P60, B60, np.log(rango_debil), np.log(rango_brillante),
                  bloq_igual, bloq_45, dens10, dens25, grado[i], grado[j], np.log(d_rel)], axis=1)
    cand.i, cand.j = i, j
    return cand, X


# ---------------------------------------------------------------- aprendizaje
def ajustar(X, Y, w_cult, tipo="hgb", neg_frac=0.1, seed=0):
    """X (E,d); Y (nc,E) 0/1; w_cult (nc,) pesos. Devuelve funcion prob(X')."""
    from sklearn.ensemble import HistGradientBoostingClassifier
    from sklearn.linear_model import LogisticRegression
    from sklearn.preprocessing import StandardScaler
    from sklearn.pipeline import make_pipeline
    rng = np.random.default_rng(seed)
    nc, E = Y.shape
    xs, ys, ws = [], [], []
    for c in range(nc):
        pos = np.where(Y[c] == 1)[0]
        neg = np.where(Y[c] == 0)[0]
        neg = neg[rng.random(len(neg)) < neg_frac]
        idx = np.concatenate([pos, neg])
        xs.append(X[idx]); ys.append(Y[c][idx])
        ws.append(np.where(Y[c][idx] == 1, 1.0, 1.0 / neg_frac) * w_cult[c])
    Xt, yt, wt = np.concatenate(xs), np.concatenate(ys), np.concatenate(ws)
    wt = wt / wt.mean()
    if tipo == "hgb":
        mdl = HistGradientBoostingClassifier(max_depth=3, max_iter=120, learning_rate=0.08, min_samples_leaf=80,
                                             l2_regularization=1.0, random_state=seed)
    else:
        mdl = make_pipeline(StandardScaler(), LogisticRegression(C=0.5, max_iter=500))
        mdl.fit(Xt, yt, logisticregression__sample_weight=wt)
        return lambda Z: mdl.predict_proba(Z)[:, 1]
    mdl.fit(Xt, yt, sample_weight=wt)
    return lambda Z: mdl.predict_proba(Z)[:, 1]


def consenso(Y, w_cult):
    w = w_cult / w_cult.sum()
    return w @ Y.astype(float)
