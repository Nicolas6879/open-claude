"""Escalado: ¿se mantienen las ventajas de la expansion dispersa al ampliar la red x f (hasta 100x) con el mismo patron de grados?
Recuperacion (MAP, ranking completo) y clasificacion en forma dual (nucleo) para poder llegar a ~380 000 KC.
Uso: python -I src/exp_scale.py --dataset digits --factors 1,2,4,8,16,32,64,100 --reps 0:3 --variants ... --out out/raw/E4.jsonl"""
import argparse, json, os, sys, time, math
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from wiring import *
from engine import *
from data import split
from exp import log2binom

def build_scaled(name, f, wa, seed, frac, norm):
    rng = np.random.default_rng(seed * 977 + f)
    m = wa.m * f
    if name == 'real_like_b':   # patron de grados real replicado f veces (f=1 -> nulo de configuracion; el real exacto es otra variante)
        return KCCoder(scaled_real_like(wa, f, rng, False).W, frac, norm, None, name)
    if name == 'real_like_w':
        return KCCoder(scaled_real_like(wa, f, rng, True).W, frac, norm, None, name)
    if name == 'f6':
        deg = np.full(m, 6); sides = np.tile(wa.kc_side, f)
        return KCCoder(random_wiring(deg, sides, wa.pn_side, None, 0.979, None, rng).W, frac, norm, None, name)
    if name == 'gauss':
        return KCCoder(dense_gauss(m, wa.n, rng), frac, norm, None, name)
    k = max(1, int(round(frac * m)))
    if name == 'sim_k': return SimHash(k, seed * 31 + 5, name)
    if name == 'sim_st': return SimHash(int(round(log2binom(m, k))), seed * 31 + 6, name)
    if name == 'sim_m': return SimHash(m, seed * 31 + 7, name)
    if name == 'noexp': return TopKPN(frac)
    if name == 'raw': return RawPN()
    raise ValueError(name)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dataset', default='digits'); ap.add_argument('--mapper', default='proj')
    ap.add_argument('--reps', default='0:3'); ap.add_argument('--seed0', type=int, default=3000)
    ap.add_argument('--frac', type=float, default=0.05); ap.add_argument('--norm', type=int, default=0)
    ap.add_argument('--factors', default='0.0625,0.125,0.25,0.5,1,2,4,8,16,32')
    ap.add_argument('--variants', default='real_like_b,real_like_w,f6,gauss,sim_k,sim_st,sim_m,noexp,raw')
    ap.add_argument('--tasks', default='ret,clf'); ap.add_argument('--maxm_dense', type=int, default=70000)
    ap.add_argument('--sizes', default=None); ap.add_argument('--tag', default='E4'); ap.add_argument('--out', required=True)
    a = ap.parse_args()
    variants = a.variants.split(','); tasks = a.tasks.split(',')
    sizes = tuple(int(x) for x in a.sizes.split(',')) if a.sizes else None
    r0, r1 = (int(x) for x in a.reps.split(':'))
    wr = load_real(); alive = np.flatnonzero(np.diff(wr.W.indptr) > 0); wa = wr.subset(alive)
    pn_order = np.argsort(-np.diff(wr.W.tocsc().indptr), kind='stable')
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    for rep in range(r0, r1):
        seed = a.seed0 + rep; rng = np.random.default_rng(seed)
        D = split(a.dataset, rng, sizes)
        mp = Mapper(a.mapper, seed * 17 + 3, pn_type=wr.pn_type, pn_order=pn_order).fit(D['Xfit'])
        Pfit, Pdb, Pq, Pte = mp(D['Xfit']), mp(D['Xdb']), mp(D['Xq']), mp(D['Xte'])
        truth = true_neighbors(D['Xq'], D['Xdb'])
        for fac in [float(x) for x in a.factors.split(',')]:
            for v in variants:
                if v in ('raw', 'noexp') and fac != 1: continue
                t0 = time.time()
                if fac < 1:   # submuestreo del cableado: solo para variantes 'real_like' y nulos: se toma una fraccion aleatoria de KC
                    sub = np.sort(np.random.default_rng(seed).choice(wa.m, int(round(fac * wa.m)), replace=False)); sw = wa.subset(sub)
                    if v in ('real_like_b', 'real_like_w'):
                        cd = KCCoder(sw.W if v.endswith('w') else sw.binary().W, a.frac, a.norm, None, v.replace('real_like', 'real'))
                    else:
                        wm = Wiring(sw.W, sw.kc_side, sw.pn_side, sw.kc_group, sw.pn_type); cd = build_scaled(v, 1, wm, seed, a.frac, a.norm)
                else:
                    f = int(fac)
                    if v in ('gauss', 'sim_m') and wa.m * f > a.maxm_dense: continue
                    cd = build_scaled(v, f, wa, seed, a.frac, a.norm)
                cd.fit(Pfit)
                m = getattr(cd, 'm', None) or getattr(cd, 'bits', N_PN)
                row = dict(dataset=a.dataset, mapper=a.mapper, rep=rep, variant=v, factor=fac, m=int(m), k=int(cd.n_active()),
                           frac=a.frac, norm=a.norm, tag=a.tag, cond='clean', level=0.0, mfrac=fac)
                Iq, Idb = cd.encode(Pq), cd.encode(Pdb)
                if 'ret' in tasks:
                    row.update(retrieval_metrics(cd.sim(Iq, Idb).astype(np.float32), truth, D['yq'], D['ydb'], np.random.default_rng(seed),
                                                 integer_sim=getattr(cd, 'integer_sim', True)))
                if 'clf' in tasks:
                    Itr, Ite = cd.encode(Pfit), cd.encode(Pte)
                    acc, lam = ridge_kernel(cd.kernel(Itr, Itr), D['yfit'], cd.kernel(Ite, Itr), D['yte'], seed=seed)
                    row.update(acc=acc, lam=lam)
                row['t'] = round(time.time() - t0, 1)
                with open(a.out, 'a') as fh: fh.write(json.dumps(row) + '\n')
                print(f'[{a.tag}] rep {rep} f={fac} {v} m={m} MAP={row.get("MAP", 0):.4f} acc={row.get("acc", 0):.4f} {row["t"]}s', flush=True)

if __name__ == '__main__': main()
