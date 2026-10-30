"""Comprobacion de que la conclusion de clasificacion no depende de la lectura ridge: regresion logistica (sklearn, lbfgs, L2) sobre el codigo binario.
C elegido en una validacion interna (80/20) del TRAIN; test aparte. Uso: python -I src/exp_logreg.py --dataset digits --reps 0:12 --out out/raw/E15_logreg.jsonl"""
import argparse, json, os, sys, time
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sklearn.linear_model import LogisticRegression
from wiring import *
from engine import *
from data import split
import exp as E
from argparse import Namespace

ap = argparse.ArgumentParser(); ap.add_argument('--dataset', default='digits'); ap.add_argument('--mapper', default='proj'); ap.add_argument('--reps', default='0:12')
ap.add_argument('--variants', default='real_b,null_b,f6,sim_m'); ap.add_argument('--sizes', default=None); ap.add_argument('--out', required=True)
a = ap.parse_args(); sizes = tuple(int(x) for x in a.sizes.split(',')) if a.sizes else None
wr = load_real(); alive = np.flatnonzero(np.diff(wr.W.indptr) > 0); wa = wr.subset(alive); pn_order = np.argsort(-np.diff(wr.W.tocsc().indptr), kind='stable')
r0, r1 = (int(x) for x in a.reps.split(':'))
for rep in range(r0, r1):
    seed = 1000 + rep; rng = np.random.default_rng(seed); D = split(a.dataset, rng, sizes)
    mp = Mapper(a.mapper, seed * 17 + 3, pn_type=wr.pn_type, pn_order=pn_order).fit(D['Xfit']); Pfit, Pte = mp(D['Xfit']), mp(D['Xte'])
    sub = np.arange(wa.m)
    for v in a.variants.split(','):
        t0 = time.time(); cd = E.build(v, wa, seed, wa.m, 0.05, 0, None, sub, None).fit(Pfit)
        Z = cd.feats(Pfit).astype(np.float32); Zt = cd.feats(Pte).astype(np.float32); mu = Z.mean(0); Z -= mu; Zt -= mu
        n = len(Z); p = np.random.default_rng(seed).permutation(n); va, tr = p[:n // 5], p[n // 5:]
        best, bc = -1, None
        for C in (0.001, 0.01, 0.1):
            clf = LogisticRegression(C=C, max_iter=300).fit(Z[tr], D['yfit'][tr]); acc = (clf.predict(Z[va]) == D['yfit'][va]).mean()
            if acc > best: best, bc = acc, C
        clf = LogisticRegression(C=bc, max_iter=300).fit(Z, D['yfit']); acc = float((clf.predict(Zt) == D['yte']).mean())
        row = dict(dataset=a.dataset, mapper=a.mapper, rep=rep, variant=v, C=bc, acc=acc, cond='clean', level=0.0, frac=0.05, norm=0, mfrac=1.0, tag='E15')
        with open(a.out, 'a') as f: f.write(json.dumps(row) + '\n')
        print(rep, v, round(acc, 4), bc, round(time.time() - t0, 1), flush=True)
