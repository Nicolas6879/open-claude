"""[v2: tras la autocritica de v1 (lectura entrenada con Adam subajustada: ridge sobre 3000 muestras daba 0,919 > Adam sobre 20 000 con 0,899) las lecturas lineales
se resuelven en forma cerrada; dense y fly_hid siguen con Adam, 3 lr y 25 epocas.]
Paso 4b: ¿una expansion tipo mosca (fija, dispersa) como primera capa de una red pequena entrenada frente a capas densas, a IGUAL
nº de parametros ENTRENABLES? MNIST. Arquitecturas:
  fly_lin  : x -> PCA 314 (PN) -> expansion fija PN->KC (real | nulo de intercambio | F6) -> top-5% binario -> lectura lineal entrenada (10*m + 10 params)
  fly_hid  : igual pero con capa oculta densa entrenada tras la expansion (m=3812 fija)
  rf_lin   : caracteristicas ReLU aleatorias densas (m unidades) + lectura lineal (mismos params que fly_lin)
  dense    : 784 -> h -> 10 entrenada entera (h elegido para igualar parametros)
Uso: python -I src/exp_net.py --budgets 2500,5000,... --seeds 0:3 --out out/raw/E10.jsonl"""
import argparse, json, os, sys, time
import numpy as np, torch, torch.nn as nn, torch.nn.functional as F
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from wiring import *
from engine import *
from data import load
torch.set_num_threads(1)

class FlyLin(nn.Module):
    def __init__(s, m, k):
        super().__init__(); s.e = nn.EmbeddingBag(m, 10, mode='sum'); nn.init.normal_(s.e.weight, 0, 1.0 / np.sqrt(k)); s.b = nn.Parameter(torch.zeros(10))
    def forward(s, idx): return s.e(idx) + s.b
class FlyHid(nn.Module):
    def __init__(s, m, k, h):
        super().__init__(); s.e = nn.EmbeddingBag(m, h, mode='sum'); nn.init.normal_(s.e.weight, 0, 1.0 / np.sqrt(k)); s.b = nn.Parameter(torch.zeros(h)); s.o = nn.Linear(h, 10)
    def forward(s, idx): return s.o(F.relu(s.e(idx) + s.b))
class Dense(nn.Module):
    def __init__(s, d, h):
        super().__init__(); s.l1 = nn.Linear(d, h); s.l2 = nn.Linear(h, 10)
    def forward(s, x): return s.l2(F.relu(s.l1(x)))
class Lin(nn.Module):
    def __init__(s, d):
        super().__init__(); s.l = nn.Linear(d, 10)
    def forward(s, x): return s.l(x)

def train(model, Xtr, ytr, Xva, yva, Xte, yte, lr, epochs, bs=256, seed=0, wd=0.0, is_idx=False):
    g = torch.Generator().manual_seed(seed); opt = torch.optim.Adam(model.parameters(), lr=lr, weight_decay=wd)
    n = len(ytr); best_va, best_te = -1, 0
    for ep in range(epochs):
        model.train(); perm = torch.randperm(n, generator=g)
        for i in range(0, n, bs):
            b = perm[i:i + bs]; opt.zero_grad(); F.cross_entropy(model(Xtr[b]), ytr[b]).backward(); opt.step()
    model.eval()
    with torch.no_grad():
        va = (model(Xva).argmax(1) == yva).float().mean().item(); te = (model(Xte).argmax(1) == yte).float().mean().item()
    return va, te

def ridge_eig(Ztr, ytr, Zva, yva, Zte, yte, lams=(1e-3, 1e-2, 1e-1, 1, 10, 100)):
    """Lectura lineal ridge a one-hot en forma cerrada. lambda (relativo a la traza media) elegido en la validacion; una sola eigh."""
    Ztr = np.asarray(Ztr, np.float32); mu = Ztr.mean(0); Zc = Ztr - mu; Y = np.eye(10, dtype=np.float32)[ytr]; ym = Y.mean(0)
    G = (Zc.T @ Zc).astype(np.float64); R = (Zc.T @ (Y - ym)).astype(np.float64); sc = np.trace(G) / G.shape[0]
    w, V = np.linalg.eigh(G); VR = V.T @ R
    def pred(Z, lam): return ((np.asarray(Z, np.float32) - mu) @ (V @ (VR / (w + lam * sc + 1e-12)[:, None])).astype(np.float32) + ym).argmax(1)
    best = max(lams, key=lambda l: (pred(Zva, l) == yva).mean())
    return float((pred(Zva, best) == yva).mean()), float((pred(Zte, best) == yte).mean()), best

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--budgets', default='2500,5000,10000,20000,40000,80000'); ap.add_argument('--seeds', default='0:3')
    ap.add_argument('--archs', default='fly_lin_real,fly_lin_null,fly_lin_f6,rf_lin,dense,fly_hid_real,fly_hid_null,fly_hid_f6')
    ap.add_argument('--ntr', type=int, default=10000); ap.add_argument('--epochs', type=int, default=25)
    ap.add_argument('--frac', type=float, default=0.05); ap.add_argument('--mapper', default='proj'); ap.add_argument('--lrs', default='0.003,0.01,0.03'); ap.add_argument('--out', required=True); ap.add_argument('--tag', default='E10v2')
    a = ap.parse_args(); archs = a.archs.split(','); lrs = [float(x) for x in a.lrs.split(',')]
    X, y, Xt, yt = load('mnist'); wr = load_real(); alive = np.flatnonzero(np.diff(wr.W.indptr) > 0); wa = wr.subset(alive)
    s0, s1 = (int(x) for x in a.seeds.split(':'))
    for seed in range(s0, s1):
        rng = np.random.default_rng(5000 + seed); p = rng.permutation(len(X))
        tr, va = p[:a.ntr], p[a.ntr:a.ntr + 5000]
        Xtr, ytr, Xva, yva = X[tr], y[tr], X[va], y[va]; q = rng.permutation(len(Xt))[:5000]; Xte, yte = Xt[q], yt[q]
        mp = Mapper(a.mapper, 5000 + seed, pn_type=wr.pn_type, pn_order=np.argsort(-np.diff(wr.W.tocsc().indptr), kind='stable')).fit(Xtr); P = {k: mp(v) for k, v in dict(tr=Xtr, va=Xva, te=Xte).items()}
        T = lambda z: torch.from_numpy(np.ascontiguousarray(z))
        ytr_t, yva_t, yte_t = T(ytr), T(yva), T(yte)
        for B in [int(b) for b in a.budgets.split(',')]:
            for arch in archs:
                t0 = time.time()
                kind = arch.split('_')[0] + '_' + arch.split('_')[1] if arch.startswith('fly') else arch
                if arch.startswith('fly_lin'):
                    m = max(50, (B - 10) // 10); h = None
                elif arch.startswith('fly_hid'):
                    m = wa.m; h = max(1, int((B - 10) // (m + 1 + 10))); 
                    if h < 2: continue
                elif arch == 'rf_lin': m = max(50, (B - 10) // 10)
                else: m = None
                if arch == 'dense':
                    h = max(1, int((B - 10) // (784 + 1 + 10)))
                    tx = [T(Xtr), T(Xva), T(Xte)]; mk = lambda: Dense(784, h); params = 785 * h + 10 * h + 10; isidx = False
                elif arch == 'rf_lin':
                    G = rng.standard_normal((784, m)).astype(np.float32) / np.sqrt(784); mu = Xtr.mean(0)
                    f = lambda Z: np.maximum((Z - mu) @ G, 0); Z = [f(Xtr), f(Xva), f(Xte)]; sc = Z[0].std() + 1e-6
                    tx = [T((z / sc).astype(np.float32)) for z in Z]; mk = lambda: Lin(m); params = 10 * m + 10; isidx = False
                else:
                    kindw = arch.split('_')[2]
                    if m <= wa.m: sub = np.sort(rng.choice(wa.m, m, replace=False)); sw = wa.subset(sub)
                    else:
                        sw = scaled_real_like(wa, int(np.ceil(m / wa.m)), rng); sw = sw.subset(np.arange(m)); kindw = 'null' if kindw == 'real' else kindw
                    if kindw == 'real': W = sw.binary().W
                    elif kindw == 'null': W = swap_null(sw, seed * 101 + 1, weights='none')[0].W if m <= wa.m else sw.binary().W
                    elif kindw == 'f6': W = fixed_indegree(m, wr.n, 6, rng, sw.kc_side, wr.pn_side).W
                    cd = KCCoder(W, a.frac, False, None, arch).fit(P['tr'])
                    tx = [T(cd.encode(P[s]).astype(np.int64)) for s in ('tr', 'va', 'te')]
                    mk = (lambda: FlyLin(m, cd.k)) if arch.startswith('fly_lin') else (lambda: FlyHid(m, cd.k, h))
                    params = 10 * m + 10 if arch.startswith('fly_lin') else m * h + h + 10 * h + 10
                if arch == 'rf_lin' or arch.startswith('fly_lin'):    # lectura lineal exacta (ridge): sin confusor de optimizador
                    Dn = lambda z: z.numpy().astype(np.float32)
                    if arch == 'rf_lin': Ztr_, Zva_, Zte_ = Dn(tx[0]), Dn(tx[1]), Dn(tx[2])
                    else: Ztr_, Zva_, Zte_ = cd.feats(P['tr']), cd.feats(P['va']), cd.feats(P['te'])
                    va_a, te_a, lam = ridge_eig(Ztr_, ytr, Zva_, yva, Zte_, yte); best = (va_a, te_a, lam)
                    row = dict(tag=a.tag, mapper=a.mapper, seed=seed, budget=B, arch=arch, m=int(m), h=None, params=int(params), val=best[0], acc=best[1], lr=best[2], t=round(time.time() - t0, 1))
                    with open(a.out, 'a') as fh: fh.write(json.dumps(row) + '\n')
                    print(row, flush=True); continue
                best = None
                for lr in lrs:
                    torch.manual_seed(seed); mod = mk(); va_a, te_a = train(mod, tx[0], ytr_t, tx[1], yva_t, tx[2], yte_t, lr, a.epochs, seed=seed)
                    if best is None or va_a > best[0]: best = (va_a, te_a, lr)
                row = dict(tag=a.tag, mapper=a.mapper, seed=seed, budget=B, arch=arch, m=int(m) if m else None, h=h, params=int(params), val=best[0], acc=best[1], lr=best[2], t=round(time.time() - t0, 1))
                with open(a.out, 'a') as fh: fh.write(json.dumps(row) + '\n')
                print(row, flush=True)

if __name__ == '__main__': main()
