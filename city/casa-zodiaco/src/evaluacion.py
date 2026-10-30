"""Evaluacion leave-one-culture/family-out del modelo gestaltico, nulos y bootstrap.

Regimen A ("estrellas conocidas"): el modelo recibe las estrellas que la cultura usa (sin saber cuales
  se unen) y propone aristas. Aisla la pregunta "dadas estas estrellas, cuales se conectan".
Regimen B ("cielo ciego"): el modelo recibe TODO el cielo hasta m_lim y debe decidir estrellas y aristas.
  Es el que exige la extension a otros cielos.
Un solo conjunto de hiperparametros global por regimen, elegido en las culturas de entrenamiento.
"""
import itertools
import numpy as np
import modelo as M

ELEGIBLE_MIN_ARISTAS = 15
NSEM_NULO = 100


# ---------------------------------------------------------------- estructuras
class Cultura:
    def __init__(self, nombre, familia, aristas_hip, hip2vec, hip2mag):
        """aristas_hip: lista (a, b, grupo) con IDs de Hipparcos."""
        self.nombre = nombre
        self.familia = familia
        a = np.array([x[0] for x in aristas_hip], dtype=np.int64)
        b = np.array([x[1] for x in aristas_hip], dtype=np.int64)
        self.grupo = np.array([x[2] for x in aristas_hip], dtype=np.int64)
        self.a, self.b = a, b
        self.keys = M.clave(a, b)
        self.n_aristas = len(a)
        self.hips = np.unique(np.concatenate([a, b])) if len(a) else np.zeros(0, dtype=np.int64)
        self.hip2vec, self.hip2mag = hip2vec, hip2mag
        self.eligible = self.n_aristas >= ELEGIBLE_MIN_ARISTAS

    def estrellas(self, hips):
        v = np.stack([self.hip2vec[h] for h in hips]) if len(hips) else np.zeros((0, 3))
        m = np.array([self.hip2mag[h] for h in hips])
        return v, m

    def subconjunto(self, grupos):
        """Cultura restringida a (con repeticion de) ciertos grupos -> claves unicas y estrellas."""
        sel = np.isin(self.grupo, grupos)
        return np.unique(self.keys[sel]), np.unique(np.concatenate([self.a[sel], self.b[sel]]))


def grados_de(keys, hips):
    a = keys // M.K_ENC
    b = keys % M.K_ENC
    idx = {h: i for i, h in enumerate(hips)}
    g = np.zeros(len(hips), dtype=int)
    for x in np.concatenate([a, b]):
        g[idx[x]] += 1
    return g


# ---------------------------------------------------------------- regimen A
def f1_grid_A(cult, keys=None, hips=None):
    """F1 para todo el rejilla (lam, R, r) en una cultura. Devuelve array [n_lam, n_R, n_r]."""
    keys = cult.keys if keys is None else keys
    hips = cult.hips if hips is None else hips
    v, m = cult.estrellas(hips)
    cand = M.Candidatas(v, m)
    out = np.zeros((len(M.LAMS), len(M.RADIOS), len(M.RATIOS)))
    for i, lam in enumerate(M.LAMS):
        for j, R in enumerate(M.RADIOS):
            for k, r in enumerate(M.RATIOS):
                e = cand.top_k(lam, R, round(r * len(hips)))
                out[i, j, k] = M.f1_claves(M.claves_de(e, hips), keys)
    return out


def elegir_params(Mtr, pesos):
    """Mtr: [n_cult, ...rejilla]; pesos: [n_cult]. Devuelve indice (tupla) del maximo de la media ponderada."""
    w = pesos / pesos.sum()
    media = np.tensordot(w, Mtr, axes=(0, 0))
    return np.unravel_index(np.argmax(media), media.shape), media


def pesos_por_familia(nombres, familias, entrenar):
    """Cada familia pesa igual en el entrenamiento (la media de medias); peso culturas = 1/|familia|."""
    fam = np.array([familias[n] for n in nombres])
    w = np.zeros(len(nombres))
    for f in set(fam[entrenar]):
        mask = entrenar & (fam == f)
        w[mask] = 1.0 / mask.sum()
    return w


def lofo_indices(Mgrid, nombres, familias, eligibles, modo="familia", sub=None):
    """Para cada cultura elige hiperparametros con el resto (excluida su familia o solo ella).
    sub: funcion opcional que recorta la rejilla (p. ej. solo lam=0,R=0). Devuelve lista de tuplas."""
    n = len(nombres)
    fam = np.array([familias[x] for x in nombres])
    elegidos = []
    for c in range(n):
        if modo == "familia":
            ent = eligibles & (fam != fam[c])
        else:
            ent = eligibles.copy()
            ent[c] = False
        w = pesos_por_familia(nombres, familias, ent)
        idx, _ = elegir_params(Mgrid[ent], w[ent])
        elegidos.append(idx)
    return elegidos


def predecir_A(cult_hips, v, m, params, ratio_idx=None):
    lam, R, r = params
    cand = M.Candidatas(v, m)
    e = cand.top_k(lam, R, round(r * len(cult_hips)))
    return M.claves_de(e, cult_hips), cand


def nulos_A(keys, hips, v, m, params_modelo, r_prox, rng, nsem=NSEM_NULO, cand=None):
    """F1 del modelo y de los nulos en una cultura (regimen A). Devuelve dict."""
    lam, R, r = params_modelo
    cand = M.Candidatas(v, m) if cand is None else cand
    k = round(r * len(hips))
    pred = M.claves_de(cand.top_k(lam, R, k), hips)
    out = {"modelo": M.f1_claves(pred, keys), "n_pred": len(pred)}
    # (b) vecino mas cercano entre las estrellas de la cultura
    out["nn"] = M.f1_claves(M.claves_de(M.nn_aristas(v), hips), keys)
    # (b2) solo proximidad (lam=0, sin escalado local), presupuesto propio r_prox
    out["prox"] = M.f1_claves(M.claves_de(cand.top_k(0.0, 0, round(r_prox * len(hips))), hips), keys)
    # (a) grafo aleatorio, mismas estrellas y mismos grados que la cultura
    g = grados_de(keys, hips)
    f_a, f_c = [], []
    for _ in range(nsem):
        e = M.grado_aleatorio(g, np.arange(len(hips)), rng)
        f_a.append(M.f1_claves(M.claves_de(e, hips), keys))
        # (c) subconjunto aleatorio de las aristas candidatas, mismo presupuesto que el modelo
        f_c.append(M.f1_claves(M.claves_de(M.subconjunto_aleatorio(cand.e, k, rng), hips), keys))
    out["aleatorio_grado"] = float(np.mean(f_a))
    out["aleatorio_grado_sd"] = float(np.std(f_a))
    out["sub_aleatorio"] = float(np.mean(f_c))
    # (a') variante: grafo aleatorio con el MISMO presupuesto que el modelo
    return out


def bootstrap_A(cult, params_modelo, r_prox, rng, B=200, nsem=10):
    """Bootstrap por cluster (constelacion/asterismo) de la cultura: recalcula estrellas, prediccion y nulos."""
    grupos = np.unique(cult.grupo)
    res = []
    for _ in range(B):
        g = rng.choice(grupos, size=len(grupos), replace=True)
        # una arista duplicada por remuestreo cuenta una vez (es un conjunto)
        keys, hips = cult.subconjunto(np.unique(g))
        if len(hips) < 4 or len(keys) < 3:
            continue
        v, m = cult.estrellas(hips)
        res.append(nulos_A(keys, hips, v, m, params_modelo, r_prox, rng, nsem=nsem))
    return res


# ---------------------------------------------------------------- regimen B
class Universo:
    """Todo el cielo (estrellas con ID Hipparcos y mag <= mag_max) para el regimen ciego."""

    def __init__(self, hips, v, mag, mag_max=6.5):
        s = mag <= mag_max
        o = np.argsort(hips[s])
        self.hips, self.v, self.mag = hips[s][o], v[s][o], mag[s][o]
        self.sub = {}
        self.cand = {}

    def candidatas(self, m_lim):
        if m_lim not in self.cand:
            idx = np.where(self.mag <= m_lim)[0]
            self.sub[m_lim] = idx
            um = tuple(t for t in M.UMBRALES if t <= m_lim) + (99.0,)
            self.cand[m_lim] = M.Candidatas(self.v[idx], self.mag[idx], umbrales=um)
        return self.sub[m_lim], self.cand[m_lim]

    def pred(self, m_lim, lam, R, r):
        idx, cand = self.candidatas(m_lim)
        e = cand.top_k(lam, R, round(r * len(idx)))
        return M.claves_de(e, self.hips[idx])

    def nn(self, m_lim):
        idx, _ = self.candidatas(m_lim)
        e = M.nn_aristas(self.v[idx])
        return M.claves_de(e, self.hips[idx])

    def aleatorio_grado(self, m_lim, pred_keys, rng):
        """Nulo (a): mismos nodos y secuencia de grados que el grafo predicho, emparejamiento aleatorio."""
        idx, _ = self.candidatas(m_lim)
        hips = self.hips[idx]
        g = grados_de(pred_keys, hips)
        e = M.grado_aleatorio(g, np.arange(len(hips)), rng)
        return M.claves_de(e, hips)

    def sub_aleatorio(self, m_lim, k, rng):
        idx, cand = self.candidatas(m_lim)
        return M.claves_de(M.subconjunto_aleatorio(cand.e, k, rng), self.hips[idx])


def rejilla_B(univ, cult_keys_list):
    """F1 para todo (m_lim, lam, R, r) y todas las culturas: array [n_cult, n_m, n_lam, n_R, n_r]."""
    out = np.zeros((len(cult_keys_list), len(M.MLIMS), len(M.LAMS), len(M.RADIOS), len(M.RATIOS)))
    for a, ml in enumerate(M.MLIMS):
        for i, lam in enumerate(M.LAMS):
            for j, R in enumerate(M.RADIOS):
                for k, r in enumerate(M.RATIOS):
                    p = univ.pred(ml, lam, R, r)
                    for c, tk in enumerate(cult_keys_list):
                        out[c, a, i, j, k] = M.f1_claves(p, tk)
    return out


def f1_vs_truth_boot(pred_keys, truth_keys):
    return M.f1_claves(pred_keys, truth_keys)


def bootstrap_B(cult, preds, rng, B=300):
    """preds: dict nombre -> lista de arrays de claves (los nulos con varias semillas son lista).
    Remuestrea grupos de la cultura; F1 de cada prediccion fija contra la verdad remuestreada."""
    grupos = np.unique(cult.grupo)
    out = {k: [] for k in preds}
    for _ in range(B):
        g = np.unique(rng.choice(grupos, size=len(grupos), replace=True))
        keys, _ = cult.subconjunto(g)
        if len(keys) < 3:
            continue
        for nombre, lst in preds.items():
            out[nombre].append(float(np.mean([M.f1_claves(p, keys) for p in lst])))
    return {k: np.array(v) for k, v in out.items()}
