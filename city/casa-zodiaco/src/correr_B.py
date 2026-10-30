"""E2: regimen B (cielo ciego). El modelo recibe todo el cielo (HIP, mag<=m_lim) y decide estrellas y aristas.
Uso: python correr_B.py [B_bootstrap]. Escribe out/resultados_B.csv."""
import os, sys, time
sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, pandas as pd
import datos, modelo as M, evaluacion as E
from correr_A import cargar_culturas, OUT, TMP

B = int(sys.argv[1]) if len(sys.argv) > 1 else 300


def main():
    t0 = time.time()
    cult = cargar_culturas()
    df = datos.cargar_hyg()
    d = df[df.hip.notna()].copy()
    d["hip"] = d.hip.astype(int)
    vec = datos.radec_a_vec(d.ra.values * 15.0, d.dec.values)
    univ = E.Universo(d.hip.values.astype(np.int64), vec, d.mag.values, mag_max=6.5)
    nombres = [c.nombre for c in cult]
    fam = {c.nombre: c.familia for c in cult}
    el = np.array([c.eligible for c in cult])
    keys = [c.keys for c in cult]
    f = os.path.join(TMP, "gridB.npy")
    if os.path.exists(f):
        Mg = np.load(f)
    else:
        Mg = E.rejilla_B(univ, keys)
        np.save(f, Mg)
    print("grid B", time.time() - t0, flush=True)
    # NN-brillante: F1 por (cultura, m_lim)
    Mnn = np.array([[M.f1_claves(univ.nn(ml), k) for ml in M.MLIMS] for k in keys])
    # solo-proximidad: rebanada lam=0,R=0 -> [c, m, r]
    Mprox = Mg[:, :, 0, 0, :]
    rng = np.random.default_rng(20261031)
    res = {}
    for modo in ("familia", "cultura"):
        res[modo] = (E.lofo_indices(Mg, nombres, fam, el, modo), E.lofo_indices(Mnn, nombres, fam, el, modo),
                     E.lofo_indices(Mprox, nombres, fam, el, modo))
    filas = []
    cache = {}
    for i, c in enumerate(cult):
        (ch, cnn, cpx) = res["familia"]
        (chc, _, _) = res["cultura"]
        a, li, ri, ki = ch[i]
        ml, lam, R, r = M.MLIMS[a], M.LAMS[li], M.RADIOS[ri], M.RATIOS[ki]
        ml_nn = M.MLIMS[cnn[i][0]]
        mp, rp = M.MLIMS[cpx[i][0]], M.RATIOS[cpx[i][1]]
        key = (ml, lam, R, r, ml_nn, mp, rp)
        if key not in cache:
            pred = univ.pred(ml, lam, R, r)
            nulos_a = [univ.aleatorio_grado(ml, pred, rng) for _ in range(E.NSEM_NULO)]
            kk = len(pred)
            nulos_c = [univ.sub_aleatorio(ml, kk, rng) for _ in range(30)]
            cache[key] = dict(modelo=[pred], nn=[univ.nn(ml_nn)], prox=[univ.pred(mp, 0.0, 0, rp)],
                              aleatorio_grado=nulos_a, sub_aleatorio=nulos_c)
        P = cache[key]
        fila = dict(cultura=c.nombre, familia=c.familia, elegible=c.eligible, n_aristas=c.n_aristas,
                    m_lim=ml, lam=lam, R=R, r=r, m_lim_nn=ml_nn, m_lim_prox=mp, r_prox=rp,
                    n_pred=len(P["modelo"][0]),
                    m_lim_loco=M.MLIMS[chc[i][0]], lam_loco=M.LAMS[chc[i][1]], R_loco=M.RADIOS[chc[i][2]], r_loco=M.RATIOS[chc[i][3]],
                    f1_loco=Mg[i][chc[i]])
        for nm, lst in P.items():
            fila["f1_" + nm] = float(np.mean([M.f1_claves(p, c.keys) for p in lst]))
        # recall maximo alcanzable (aristas de la cultura con ambos extremos en el universo del modelo)
        idx, _ = univ.candidatas(ml)
        hs = set(univ.hips[idx].tolist())
        fila["frac_aristas_en_universo"] = float(np.mean([(a in hs) and (b in hs) for a, b in zip(c.a, c.b)]))
        if c.eligible and B > 0:
            bs = E.bootstrap_B(c, P, rng, B=B)
            for nm, x in bs.items():
                fila[f"ic_{nm}_lo"], fila[f"ic_{nm}_hi"] = np.percentile(x, [2.5, 97.5])
            dm = bs["modelo"] - bs["nn"]
            fila["dif_nn_lo"], fila["dif_nn_hi"] = np.percentile(dm, [2.5, 97.5])
            rat = bs["modelo"] / np.maximum(bs["aleatorio_grado"], 1e-9)
            fila["ratio_lo"], fila["ratio_hi"] = np.percentile(rat, [2.5, 97.5])
        filas.append(fila)
        print(f"{c.nombre}: mod={fila['f1_modelo']:.3f} nn={fila['f1_nn']:.3f} prox={fila['f1_prox']:.3f} aleat={fila['f1_aleatorio_grado']:.4f} {time.time()-t0:.0f}s", flush=True)
    pd.DataFrame(filas).to_csv(os.path.join(OUT, "resultados_B.csv"), index=False)
    print("fin", time.time() - t0)


if __name__ == "__main__":
    main()
