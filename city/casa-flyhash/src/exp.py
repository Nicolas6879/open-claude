"""Corredor de experimentos: una replica = (particion de datos, mapeo entrada->PN, instancias de nulos).
Escribe filas JSON (una por variante x condicion) en out/<archivo>.jsonl.
Uso: python -I src/exp.py --dataset digits --mapper proj --reps 0:20 --frac 0.05 --out out/x.jsonl [...]"""
import argparse, json, math, os, sys, time
import numpy as np, scipy.sparse as sp
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from wiring import *
from engine import *
from data import split

ALL = ['real_b', 'real_w', 'null_b', 'null_w', 'f6', 'kcdeg_b', 'gauss', 'sgauss', 'sim_k', 'sim_st', 'sim_m', 'noexp', 'raw']

def log2binom(m, k): return (math.lgamma(m + 1) - math.lgamma(k + 1) - math.lgamma(m - k + 1)) / math.log(2)

def build(name, wr_alive, rep_seed, m, frac, norm, lesion, sub, pn_deg):
    """Construye un codificador. wr_alive: cableado real sin KC de grado 0. sub: indices de KC (submuestreo).
    Sufijo '_pn': compensacion presinaptica de PN: cada columna (PN) se escala por 1/sqrt(suma de w^2 de su salida), de modo que todos los PN aportan la misma
    varianza total de excitacion (con pesos binarios: 1/sqrt(grado de salida))."""
    if name.endswith('_pn'):
        cd = build(name[:-3], wr_alive, rep_seed, m, frac, norm, lesion, sub, pn_deg)
        W = cd.W.tocsc(); ss = np.asarray(W.multiply(W).sum(0)).ravel(); g = 1.0 / np.sqrt(np.maximum(ss, 1e-9))
        cd.W = (W @ sp.diags(g.astype(np.float32))).tocsr(); cd.name = name; return cd
    rng = np.random.default_rng(rep_seed * 7919 + 13)
    les = None if lesion is None else lesion
    if name in ('real_b', 'real_w'):
        w = wr_alive if name == 'real_w' else wr_alive.binary()
        return KCCoder(w.subset(sub).W, frac, norm, les, name)
    if name in ('null_b', 'null_w'):
        nl, _ = swap_null(wr_alive, rep_seed * 101 + 1, weights='kc' if name == 'null_w' else 'none')
        return KCCoder(nl.subset(sub).W, frac, norm, les, name)
    if name == 'nullsh_w':      # pesos barajados entre aristas del nulo
        nl, _ = swap_null(wr_alive, rep_seed * 101 + 2, weights='shuffle'); return KCCoder(nl.subset(sub).W, frac, norm, les, name)
    if name == 'realtop_shw':   # topologia real, pesos barajados globalmente
        w = wr_alive.subset(sub); W = w.W.copy(); W.data = np.random.default_rng(rep_seed).permutation(W.data)
        return KCCoder(W, frac, norm, les, name)
    if name == 'realdd_b':      # real SIN entradas repetidas del mismo tipo de PN en una KC (866 repetidos eliminados por intercambios que conservan grados)
        d, _, _ = dedup_type_swaps(wr_alive, rep_seed * 101 + 6); return KCCoder(d.binary().subset(sub).W, frac, norm, les, name)
    if name == 'nulljdd_b':     # nulo que ademas conserva la matriz de grados conjuntos (disasortatividad)
        nl, _ = swap_null(wr_alive, rep_seed * 101 + 5, weights='none', blocks='jdd'); return KCCoder(nl.subset(sub).W, frac, norm, les, name)
    if name == 'nullbl_b':      # nulo mas estricto: bloques lado x lado x subtipo KC
        nl, _ = swap_null(wr_alive, rep_seed * 101 + 3, weights='none', blocks='group'); return KCCoder(nl.subset(sub).W, frac, norm, les, name)
    if name == 'null_nb_b':     # nulo SIN respetar hemisferio (el artefacto que se quiere evitar)
        nl, _ = swap_null(wr_alive, rep_seed * 101 + 4, weights='none', blocks='none'); return KCCoder(nl.subset(sub).W, frac, norm, les, name)
    if name.startswith('plus'):   # copia del real con +e % de KC extra (ventaja CONOCIDA inyectada para medir potencia): plusE_b / plusE_w
        e = int(name[4:].split('_')[0]) / 100.0; wsub = wr_alive.subset(sub); n_ex = int(round(e * wsub.m))
        pn, kc, w = wsub.edges(); deg = np.diff(wsub.W.indptr); pick = rng.integers(0, wsub.m, n_ex)
        pdeg = np.bincount(pn, minlength=wsub.n).astype(float)
        ex = random_wiring(deg[pick], wsub.kc_side[pick], wsub.pn_side, pdeg, 0.979, None, rng)
        base = wsub.W if name.endswith('_w') else wsub.binary().W
        if name.endswith('_w'):  # pesos de las extra: muestreados de los pesos reales
            ex.W.data = rng.choice(w, ex.W.nnz).astype(np.float32)
        return KCCoder(sp.vstack([base, ex.W]).tocsr(), frac, norm, les, name)
    if name == 'f6':
        w = fixed_indegree(m, wr_alive.n, 6, rng, wr_alive.kc_side[sub], wr_alive.pn_side); return KCCoder(w.W, frac, norm, les, name)
    if name == 'kcdeg_b':
        nl = kc_degree_null(wr_alive.binary().subset(sub), rng); return KCCoder(nl.W, frac, norm, les, name)
    if name == 'gauss':
        return KCCoder(dense_gauss(m, wr_alive.n, rng), frac, norm, les, name)
    if name == 'sgauss':
        return KCCoder(sparse_gauss_same_edges(wr_alive.subset(sub), rng).W, frac, norm, les, name)
    if name == 'sgauss_f6':
        w = fixed_indegree(m, wr_alive.n, 6, rng, wr_alive.kc_side[sub], wr_alive.pn_side); w.W.data = rng.standard_normal(w.W.nnz).astype(np.float32)
        return KCCoder(w.W, frac, norm, les, name)
    k = max(1, int(round(frac * m)))
    if name == 'sim_k': return SimHash(k, rep_seed * 31 + 5, name)
    if name == 'sim_st': return SimHash(int(round(log2binom(m, k))), rep_seed * 31 + 6, name)
    if name == 'sim_m': return SimHash(m, rep_seed * 31 + 7, name)
    if name == 'noexp': return TopKPN(frac)
    if name == 'raw': return RawPN()
    raise ValueError(name)

def corrupt(X, cond, rng, fstd):
    kind, val = cond
    if kind == 'gnoise': return (X + rng.standard_normal(X.shape).astype(np.float32) * val * fstd).astype(np.float32)
    if kind == 'mask': return (X * (rng.random(X.shape) > val)).astype(np.float32)
    return X

def run_rep(a, rep):
    t0 = time.time(); seed = a.seed0 + rep
    rng = np.random.default_rng(seed)
    D = split(a.dataset, rng, a.sizes)
    wr = load_real()
    alive = np.flatnonzero(np.diff(wr.W.indptr) > 0)
    wa = wr.subset(alive) if not a.keep_dead else wr
    wa.name = 'real'
    m_all = wa.m
    pn_order = np.argsort(-np.diff(wr.W.tocsc().indptr), kind='stable')
    mp = Mapper(a.mapper, seed * 17 + 3, pn_type=wr.pn_type, pn_order=pn_order).fit(D['Xfit'])
    if a.subtype is not None:            # solo KC de un subtipo (con igual n que el menor), ver exp_subtype
        sub = np.flatnonzero(wa.kc_group == a.subtype)
        if a.m_cap: sub = np.random.default_rng(seed).choice(sub, a.m_cap, replace=False)
    elif a.mfrac < 1:
        sub = np.sort(np.random.default_rng(seed).choice(m_all, int(round(a.mfrac * m_all)), replace=False))
    else: sub = np.arange(m_all)
    m = len(sub)
    Pfit, Pdb = mp(D['Xfit']), mp(D['Xdb'])
    truth = true_neighbors(D['Xq'], D['Xdb'])
    fstd = float(D['Xfit'].std(0).mean())
    rows = []
    for cond in a.conds:
        crng = np.random.default_rng(seed * 3 + 1)
        lesion = None
        if cond[0] == 'lesion': lesion = np.random.default_rng(seed * 5 + 2).random(m) < cond[1]
        Xq = corrupt(D['Xq'], cond, crng, fstd); Xte = corrupt(D['Xte'], cond, crng, fstd)
        Pq, Pte = mp(Xq), mp(Xte)
        for v in a.variants:
            cd = build(v, wa, seed, m, a.frac, a.norm, lesion, sub, None).fit(Pfit)
            row = dict(dataset=a.dataset, mapper=a.mapper, rep=rep, variant=v, frac=a.frac, norm=a.norm, mfrac=a.mfrac, m=int(m),
                       cond=cond[0], level=cond[1], k=int(cd.n_active()), nnz=int(cd.nnz), tag=a.tag)
            if 'ret' in a.tasks:
                Iq, Idb = cd.encode(Pq), cd.encode(Pdb)
                row.update(retrieval_metrics(cd.sim(Iq, Idb).astype(np.float32), truth, D['yq'], D['ydb'], np.random.default_rng(seed), integer_sim=getattr(cd, 'integer_sim', True)))
            if 'clf' in a.tasks:
                acc, lam = ridge_classify(cd.feats(Pfit), D['yfit'], cd.feats(Pte), D['yte'], seed=seed)
                row.update(acc=acc, lam=lam)
            rows.append(row)
    print(f'[{a.tag}] {a.dataset}/{a.mapper} rep {rep} {len(rows)} filas {time.time()-t0:.1f}s', flush=True)
    return rows

def parse_conds(s):
    out = []
    for t in s.split(','):
        if t == 'clean': out.append(('clean', 0.0))
        else: k, v = t.split(':'); out.append((k, float(v)))
    return out

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dataset', default='digits'); ap.add_argument('--mapper', default='proj')
    ap.add_argument('--reps', default='0:5'); ap.add_argument('--seed0', type=int, default=1000)
    ap.add_argument('--frac', type=float, default=0.05); ap.add_argument('--norm', type=int, default=0)
    ap.add_argument('--mfrac', type=float, default=1.0); ap.add_argument('--keep_dead', type=int, default=0)
    ap.add_argument('--variants', default=','.join(ALL)); ap.add_argument('--tasks', default='ret,clf')
    ap.add_argument('--conds', default='clean'); ap.add_argument('--subtype', type=int, default=None); ap.add_argument('--m_cap', type=int, default=0)
    ap.add_argument('--sizes', default=None); ap.add_argument('--tag', default='run'); ap.add_argument('--out', required=True)
    a = ap.parse_args()
    a.variants = a.variants.split(','); a.tasks = a.tasks.split(','); a.conds = parse_conds(a.conds)
    a.sizes = tuple(int(x) for x in a.sizes.split(',')) if a.sizes else None
    r0, r1 = (int(x) for x in a.reps.split(':'))
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    with open(a.out, 'a') as f:
        for rep in range(r0, r1):
            for row in run_rep(a, rep): f.write(json.dumps(row) + '\n')
            f.flush()

if __name__ == '__main__': main()
