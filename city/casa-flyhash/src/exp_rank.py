"""E11: posicion del cableado real dentro de la distribucion de nulos, con el mapeo FIJO (descompone varianza: instancia de nulo vs mapeo).
Por mapeo: MAP del real y de K nulos de intercambio independientes (y K2 F6). Salida: out/raw/E11_*.jsonl
Uso: python -I src/exp_rank.py --mappings 0:12 --K 30 --K2 10 --out out/raw/E11.jsonl"""
import argparse, json, os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from wiring import *
from engine import *
from data import split

ap = argparse.ArgumentParser(); ap.add_argument('--dataset', default='digits'); ap.add_argument('--mapper', default='proj')
ap.add_argument('--mappings', default='0:12'); ap.add_argument('--K', type=int, default=30); ap.add_argument('--K2', type=int, default=10)
ap.add_argument('--frac', type=float, default=0.05); ap.add_argument('--sizes', default=None); ap.add_argument('--out', required=True)
a = ap.parse_args(); sizes = tuple(int(x) for x in a.sizes.split(',')) if a.sizes else None
wr = load_real(); alive = np.flatnonzero(np.diff(wr.W.indptr) > 0); wa = wr.subset(alive)
pn_order = np.argsort(-np.diff(wr.W.tocsc().indptr), kind='stable')
r0, r1 = (int(x) for x in a.mappings.split(':'))
for s in range(r0, r1):
    seed = 8000 + s; rng = np.random.default_rng(seed); D = split(a.dataset, rng, sizes)
    mp = Mapper(a.mapper, seed * 17 + 3, pn_type=wr.pn_type, pn_order=pn_order).fit(D['Xfit'])
    Pfit, Pdb, Pq = mp(D['Xfit']), mp(D['Xdb']), mp(D['Xq']); truth = true_neighbors(D['Xq'], D['Xdb'])
    def ev(W, tag):
        cd = KCCoder(W, a.frac).fit(Pfit); r = retrieval_metrics(cd.sim(cd.encode(Pq), cd.encode(Pdb)), truth, D['yq'], D['ydb'], np.random.default_rng(seed))
        return dict(mapping=s, kind=tag, MAP=r['MAP'], P10=r['P10'])
    rows = [ev(wa.binary().W, 'real')]
    rows += [ev(swap_null(wa, 100000 + 977 * s + j, weights='none')[0].W, 'null') for j in range(a.K)]
    rrng = np.random.default_rng(seed + 1)
    rows += [ev(fixed_indegree(wa.m, wa.n, 6, rrng, wa.kc_side, wa.pn_side).W, 'f6') for j in range(a.K2)]
    with open(a.out, 'a') as f:
        for r in rows: f.write(json.dumps(r) + '\n')
    print('mapping', s, 'real', round(rows[0]['MAP'], 4), 'null mean', round(np.mean([r['MAP'] for r in rows[1:a.K + 1]]), 4), flush=True)
