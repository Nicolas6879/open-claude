"""v2 (regimen B): propension de arista aprendida. LOFO, cross-fitting interno para elegir K.
Uso: python correr_v2.py diseno|sellado   ('diseno' solo imprime/guarda las familias de DISEÑO)."""
import os, sys, time, json
sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, pandas as pd
import datos, modelo as M, evaluacion as E, v2
from correr_A import cargar_culturas, OUT, TMP

MODO = sys.argv[1] if len(sys.argv) > 1 else "diseno"
TIPO = sys.argv[2] if len(sys.argv) > 2 else "hgb"
BOOT = int(sys.argv[3]) if len(sys.argv) > 3 else 200
KMATCH = len(sys.argv) > 4 and sys.argv[4] == "kmatch"  # exploratorio: K del modelo = n.o de aristas del NN (presupuesto igualado)
DISENO = ['potawatomi', 'romanian', 'nordica', 'belarusian', 'navajo', 'tukano', 'seri', 'balinese', 'tupi', 'polinesia',
          'mongolian', 'arabe_popular', 'tibetan', 'sardinian', 'lokono']
KS = (40, 70, 100, 150, 220, 320, 450, 700)


def main():
    t0 = time.time()
    cult = cargar_culturas()
    nombres = [c.nombre for c in cult]
    fam = np.array([c.familia for c in cult])
    el = np.array([c.eligible for c in cult])
    df = datos.cargar_hyg()
    d = df[df.hip.notna()].copy(); d["hip"] = d.hip.astype(int)
    vec = datos.radec_a_vec(d.ra.values * 15.0, d.dec.values)
    univ = E.Universo(d.hip.values.astype(np.int64), vec, d.mag.values, mag_max=5.5)
    f = os.path.join(TMP, "v2_X.npz")
    cand, X = v2.rasgos(univ.v, univ.mag)
    keys_e = M.clave(univ.hips[cand.e[:, 0]], univ.hips[cand.e[:, 1]])
    Y = np.stack([np.isin(keys_e, c.keys) for c in cult]).astype(np.uint8)
    print("aristas candidatas", len(keys_e), "positivos medios", Y[el].sum(1).mean(), f"{time.time()-t0:.0f}s", flush=True)
    # F1 de top-K para cada cultura dado un puntaje p
    ntruth = np.array([c.n_aristas for c in cult])

    def f1_topk(p, K, c):
        idx = np.argpartition(-p, K - 1)[:K]
        tp = Y[c, idx].sum()
        # tp solo cuenta aristas candidatas; las aristas de la cultura fuera del candidato son recall perdido igual
        return 2.0 * tp / (K + ntruth[c])

    fams_el = sorted(set(fam[el]))
    objetivo = [f for f in fams_el if (MODO == "sellado" or f in DISENO)] if MODO != "todo" else fams_el
    filas = []
    Mnn = {ml: univ.nn(ml) for ml in M.MLIMS}
    Mnn_f1 = np.array([[M.f1_claves(Mnn[ml], c.keys) for ml in M.MLIMS] for c in cult])
    rng = np.random.default_rng(777)
    for fo in fams_el:
        if fo not in objetivo:
            continue
        ent = el & (fam != fo)
        ent_idx = np.where(ent)[0]
        w_all = np.zeros(len(cult))
        for ff in set(fam[ent]):
            m = ent & (fam == ff); w_all[m] = 1.0 / m.sum()
        wk = w_all[ent_idx] / w_all[ent_idx].sum()
        ml_nn = M.MLIMS[int(np.argmax(wk @ Mnn_f1[ent_idx]))]
        if KMATCH:
            elegidos = {"modelo": len(Mnn[ml_nn]), "consenso": len(Mnn[ml_nn])}
        else:
            # --- cross-fitting por familias de entrenamiento -> p fuera de muestra para elegir K
            fts = sorted(set(fam[ent])); rng.shuffle(fts)
            folds = [fts[i::5] for i in range(5)]
            P_oof = {"modelo": np.zeros((len(cult), len(keys_e))), "consenso": np.zeros((len(cult), len(keys_e)))}
            for fl in folds:
                tr = ent & ~np.isin(fam, fl); te = ent & np.isin(fam, fl)
                mdl = v2.ajustar(X, Y[tr], w_all[tr], tipo=TIPO)
                pm = mdl(X)
                pc = v2.consenso(Y[tr], w_all[tr])
                for c in np.where(te)[0]:
                    P_oof["modelo"][c] = pm; P_oof["consenso"][c] = pc
            elegidos = {}
            for nm in P_oof:
                F = np.array([[f1_topk(P_oof[nm][c], K, c) for K in KS] for c in ent_idx])
                wk = w_all[ent_idx] / w_all[ent_idx].sum()
                elegidos[nm] = KS[int(np.argmax(wk @ F))]
            # NN-brillante: m_lim elegido en entrenamiento
            wk = w_all[ent_idx] / w_all[ent_idx].sum()
            ml_nn = M.MLIMS[int(np.argmax(wk @ Mnn_f1[ent_idx]))]
        # --- modelo final entrenado en todo el entrenamiento y evaluado en la familia retenida
        mdl = v2.ajustar(X, Y[ent], w_all[ent], tipo=TIPO)
        pm = mdl(X); pc = v2.consenso(Y[ent], w_all[ent])
        for c in np.where(el & (fam == fo))[0]:
            res = dict(cultura=nombres[c], familia=fo, n_aristas=cult[c].n_aristas, elegible=True, K_modelo=elegidos["modelo"], K_consenso=elegidos["consenso"], m_lim_nn=ml_nn)
            out = {}
            for nm, p in (("modelo", pm), ("consenso", pc)):
                K = elegidos[nm]
                idx = np.argpartition(-p, K - 1)[:K]
                out[nm] = keys_e[idx]
            out["nn"] = Mnn[ml_nn]
            Kk = elegidos["modelo"]
            idx_nodes = np.unique(cand.e[np.argpartition(-pm, Kk - 1)[:Kk]])
            # nulo (a): mismos nodos y grados que el grafo predicho
            e_pred = cand.e[np.argpartition(-pm, Kk - 1)[:Kk]]
            hips_n = univ.hips
            g = np.bincount(e_pred.ravel(), minlength=len(univ.hips))
            nodos = np.where(g > 0)[0]
            nul_a = []
            for _ in range(100):
                ee = M.grado_aleatorio(g[nodos], nodos, rng)
                nul_a.append(M.claves_de(ee, univ.hips))
            nul_c = [keys_e[rng.choice(len(keys_e), Kk, replace=False)] for _ in range(30)]
            for nm in ("modelo", "consenso", "nn"):
                res["f1_" + nm] = M.f1_claves(out[nm], cult[c].keys) if False else M.f1_claves(np.unique(out[nm]), cult[c].keys)
            res["f1_aleatorio_grado"] = float(np.mean([M.f1_claves(x, cult[c].keys) for x in nul_a]))
            res["f1_sub_aleatorio"] = float(np.mean([M.f1_claves(np.unique(x), cult[c].keys) for x in nul_c]))
            if BOOT:
                bs = E.bootstrap_B(cult[c], dict(modelo=[np.unique(out["modelo"])], nn=[out["nn"]], consenso=[np.unique(out["consenso"])], aleatorio_grado=nul_a), rng, B=BOOT)
                dm = bs["modelo"] - bs["nn"]
                res["dif_nn_lo"], res["dif_nn_hi"] = np.percentile(dm, [2.5, 97.5])
                res["ratio_lo"], res["ratio_hi"] = np.percentile(bs["modelo"] / np.maximum(bs["aleatorio_grado"], 1e-9), [2.5, 97.5])
            filas.append(res)
        print(f"familia {fo}: K={elegidos} nn_m={ml_nn} {time.time()-t0:.0f}s", flush=True)
    etq = {"diseno": "_diseno", "sellado": "_sellado", "todo": "_todo"}[MODO] + f"_{TIPO}" + ("_kmatch" if KMATCH else "")
    pd.DataFrame(filas).to_csv(os.path.join(OUT, f"resultados_v2{etq}.csv"), index=False)
    t = pd.DataFrame(filas)
    w = 1.0 / t.groupby("familia")["cultura"].transform("count")
    for nm in ("modelo", "consenso", "nn", "aleatorio_grado", "sub_aleatorio"):
        print(nm, "mediana F1", round(t["f1_" + nm].median(), 4), "media fam", round(float((t["f1_" + nm] * w).sum() / w.sum()), 4))
    print("G2 modelo>NN: cultura", round(float((t.f1_modelo > t.f1_nn).mean()), 3), "familia", round(float(((t.f1_modelo > t.f1_nn) * w).sum() / w.sum()), 3))
    print("G1 modelo>=2*aleatorio:", round(float((t.f1_modelo >= 2 * t.f1_aleatorio_grado).mean()), 3))
    print("consenso>NN:", round(float((t.f1_consenso > t.f1_nn).mean()), 3), " modelo>consenso:", round(float((t.f1_modelo > t.f1_consenso).mean()), 3))


if __name__ == "__main__":
    main()
