"""E1: regimen A (estrellas conocidas), validacion LOFO y LOCO, nulos y bootstrap.
Uso: python correr_A.py [B_bootstrap]. Escribe out/resultados_A.csv y out/resumen_A.json.
Cache intermedia en el scratchpad (ZODIACO_TMP)."""
import os, sys, json, time
sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, pandas as pd
import datos, modelo as M, evaluacion as E

TMP = os.environ.get("ZODIACO_TMP", "/tmp/claude-0/-home-user-open-claude/e7f872ff-c04d-5af4-a3a1-8d2199c39026/scratchpad/zodiaco/tmp")
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "out")
ETQ = os.environ.get("ZODIACO_ETQ", "")  # sufijo de salida (p. ej. _v1b)
TMP = TMP + ETQ
os.makedirs(TMP, exist_ok=True)
try:
    B = int(sys.argv[1]) if len(sys.argv) > 1 else 150
except ValueError:  # importado desde otro script
    B = 150


def cargar_culturas():
    df = datos.cargar_hyg()
    d = df[df.hip.notna()].copy()
    d["hip"] = d.hip.astype(int)
    vec = datos.radec_a_vec(d.ra.values * 15.0, d.dec.values)
    h2v = {h: v for h, v in zip(d.hip.values, vec)}
    h2m = dict(zip(d.hip.values, d.mag.values))
    hs = set(h2m)
    cult = []
    for c in datos.lista_culturas():
        ar, _ = datos.parsear_cultura(c, hs)
        cult.append(E.Cultura(c, datos.familia_de(c), ar, h2v, h2m))
    return cult


def main():
    t0 = time.time()
    cult = cargar_culturas()
    nombres = [c.nombre for c in cult]
    fam = {c.nombre: c.familia for c in cult}
    el = np.array([c.eligible for c in cult])
    f = os.path.join(TMP, "gridA.npy")
    if os.path.exists(f):
        Mg = np.load(f)
    else:
        Mg = np.zeros((len(cult), len(M.LAMS), len(M.RADIOS), len(M.RATIOS)))
        for i, c in enumerate(cult):
            if c.n_aristas >= 4:
                Mg[i] = E.f1_grid_A(c)
            print(f"grid {c.nombre} {time.time()-t0:.0f}s", flush=True)
        np.save(f, Mg)
    res = {}
    for modo in ("familia", "cultura"):
        ch = E.lofo_indices(Mg, nombres, fam, el, modo=modo)
        # presupuesto propio del baseline 'solo proximidad' (lam=0,R=0), tambien en LOFO
        chp = E.lofo_indices(Mg[:, 0:1, 0:1, :], nombres, fam, el, modo=modo)
        res[modo] = (ch, chp)
    filas = []
    rng = np.random.default_rng(20261030)
    for i, c in enumerate(cult):
        ch, chp = res["familia"]
        chc, _ = res["cultura"]
        li, ri, ki = ch[i]
        par = (M.LAMS[li], M.RADIOS[ri], M.RATIOS[ki])
        r_prox = M.RATIOS[chp[i][2]]
        v, m = c.estrellas(c.hips)
        if len(c.hips) < 4:
            continue
        o = E.nulos_A(c.keys, c.hips, v, m, par, r_prox, rng)
        fila = dict(cultura=c.nombre, familia=c.familia, elegible=c.eligible, n_aristas=c.n_aristas, n_estrellas=len(c.hips),
                    lam=par[0], R=par[1], r=par[2], r_prox=r_prox,
                    lam_loco=M.LAMS[chc[i][0]], R_loco=M.RADIOS[chc[i][1]], r_loco=M.RATIOS[chc[i][2]],
                    f1_loco=Mg[i][chc[i]], f1_modelo=o["modelo"], f1_nn=o["nn"], f1_prox=o["prox"],
                    f1_aleatorio_grado=o["aleatorio_grado"], f1_sub_aleatorio=o["sub_aleatorio"])
        # bootstrap por cluster
        if c.eligible and B > 0:
            bs = E.bootstrap_A(c, par, r_prox, rng, B=B)
            for k, nm in (("modelo", "modelo"), ("nn", "nn"), ("prox", "prox"), ("aleatorio_grado", "aleatorio_grado"), ("sub_aleatorio", "sub_aleatorio")):
                x = np.array([b[k] for b in bs])
                fila[f"ic_{nm}_lo"], fila[f"ic_{nm}_hi"] = np.percentile(x, [2.5, 97.5])
            dm = np.array([b["modelo"] - b["nn"] for b in bs])
            fila["dif_nn_lo"], fila["dif_nn_hi"] = np.percentile(dm, [2.5, 97.5])
            rat = np.array([b["modelo"] / max(b["aleatorio_grado"], 1e-9) for b in bs])
            fila["ratio_lo"], fila["ratio_hi"] = np.percentile(rat, [2.5, 97.5])
        filas.append(fila)
        print(f"{c.nombre}: modelo={o['modelo']:.3f} nn={o['nn']:.3f} prox={o['prox']:.3f} aleat={o['aleatorio_grado']:.3f} {time.time()-t0:.0f}s", flush=True)
        pd.DataFrame(filas).to_csv(os.path.join(OUT, f"resultados_A{ETQ}.csv"), index=False)
    print("fin", time.time() - t0)


if __name__ == "__main__":
    main()
