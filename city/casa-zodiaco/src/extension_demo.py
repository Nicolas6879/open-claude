"""Demostracion EXPLORATORIA (la compuerta confirmatoria NO paso): el grafo de v2 (HGB entrenado con todas las
familias elegibles; K = n.o de aristas del grafo NN de las estrellas mag<=3.5 de ese cielo) aplicado al cielo visto
desde estrellas vecinas. No es una prediccion de ninguna cultura. Salidas: out/extension.json, out/estabilidad.csv."""
import os, sys, json
sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, pandas as pd
import datos, modelo as M, evaluacion as E, v2, extension
from correr_A import cargar_culturas, OUT

MAG_CIELO = 5.5
EMBEBER = [("Tierra (Sol)", None), ("Rigil Kentaurus", 71683), ("Proxima Centauri", 70890), ("Barnard's Star", 87937),
           ("Sirius", 32349), ("Ran", 16537), ("Tau Ceti", 8102), ("Procyon", 37279)]
NOMBRE_ES = {"Tierra (Sol)": "Tierra (Sol)", "Rigil Kentaurus": "Alfa Centauri A", "Proxima Centauri": "Próxima Centauri",
             "Barnard's Star": "Estrella de Barnard", "Sirius": "Sirio", "Ran": "Epsilon Eridani", "Tau Ceti": "Tau Ceti", "Procyon": "Proción"}


def k_nn(v, mag):
    idx = np.where(mag <= 3.5)[0]
    return len(M.nn_aristas(v, idx))


def main():
    cult = [c for c in cargar_culturas() if c.eligible]
    df = datos.cargar_hyg().reset_index(drop=True)
    cielos = extension.Cielos(df)
    # --- entrenamiento v2 con todas las familias elegibles (cielo terrestre)
    idx0, v0, m0 = cielos.desde([0, 0, 0], mag_max=MAG_CIELO)
    hip0 = df.hip.values[idx0]
    ok = ~np.isnan(hip0)
    cand0, X0 = v2.rasgos(v0, m0)
    ids0 = np.where(np.isnan(hip0), -1, hip0).astype(np.int64)
    keys_e = M.clave(ids0[cand0.e[:, 0]], ids0[cand0.e[:, 1]])
    Y = np.stack([np.isin(keys_e, c.keys) for c in cult]).astype(np.uint8)
    fam = np.array([c.familia for c in cult])
    w = np.zeros(len(cult))
    for f in set(fam):
        w[fam == f] = 1.0 / (fam == f).sum()
    mdl = v2.ajustar(X0, Y, w, tipo="hgb")
    print("entrenado con", len(cult), "culturas;", len(keys_e), "aristas candidatas")
    # --- observadores
    obs = []
    d5 = df[(df.dist > 0) & (df.dist <= 5.0)]
    for i, r in d5.iterrows():
        nombre = r.proper if isinstance(r.proper, str) else (r.gl if isinstance(r.gl, str) else f"HYG {int(r.id)}")
        obs.append((nombre, int(r.id), df.loc[i, ["x", "y", "z"]].values.astype(float), float(r.dist)))
    nombres_emb = {h: n for n, h in EMBEBER if h}
    graf = {}
    filas = []

    def grafo(pos, excl=None):
        idx, v, m = cielos.desde(pos, excluir_id=excl, mag_max=MAG_CIELO)
        cand, X = v2.rasgos(v, m)
        p = mdl(X)
        K = max(k_nn(v, m), 10)
        top = np.argpartition(-p, K - 1)[:K]
        e = cand.e[top]
        return idx, v, m, e, K

    idxT, vT, mT, eT, KT = grafo(np.zeros(3))
    idsT = df.id.values[idxT]
    keysT = {tuple(sorted((int(idsT[a]), int(idsT[b])))) for a, b in eT}
    graf["Tierra (Sol)"] = (idxT, vT, mT, eT, 0.0)
    filas.append(dict(observador="Tierra (Sol)", dist_pc=0.0, K=KT, aristas_terrestres_conservadas=1.0, mag_sol=np.nan, sol_con_lineas=np.nan, mag_min_cielo=float(mT.min())))
    for nombre, hid, pos, dist in sorted(obs, key=lambda t: t[3]):
        idx, v, m, e, K = grafo(pos, excl=hid)
        ids = df.id.values[idx]
        kk = {tuple(sorted((int(ids[a]), int(ids[b])))) for a, b in e}
        # arista terrestre conservada: ambas estrellas siguen en el cielo y la arista esta en el grafo del observador
        cons = len(kk & keysT) / max(len(keysT), 1)
        # el Sol visto desde aqui (id 0)
        pos_sol = np.where(ids == 0)[0]
        mag_sol = float(m[pos_sol[0]]) if len(pos_sol) else np.nan
        sol_lineas = bool(len(pos_sol) and (e == pos_sol[0]).any())
        filas.append(dict(observador=nombre, dist_pc=round(dist, 3), K=K, aristas_terrestres_conservadas=cons,
                          mag_sol=mag_sol, sol_con_lineas=sol_lineas, mag_min_cielo=float(m.min())))
        for n_es, h in EMBEBER:
            if h is not None and df.loc[df.id == hid, "hip"].values[0] == h:
                graf[n_es] = (idx, v, m, e, dist)
    t = pd.DataFrame(filas)
    t.to_csv(os.path.join(OUT, "estabilidad.csv"), index=False)
    print(t.round(3).to_string())
    # --- exportar cielos embebidos (compacto)
    out = {"mag_max": MAG_CIELO, "observadores": []}
    for n_es, h in EMBEBER:
        if n_es not in graf:
            continue
        idx, v, m, e, dist = graf[n_es]
        ra, de = extension.radec_de_vec(v)
        ids = df.id.values[idx]
        nombres = []
        for k in range(len(idx)):
            pr = df.proper.values[idx[k]]
            nombres.append(pr if (isinstance(pr, str) and m[k] < 2.3) or ids[k] == 0 else "")
        # persistencia de la arista respecto a la Tierra (para colorear)
        pers = [1 if tuple(sorted((int(ids[a]), int(ids[b])))) in keysT else 0 for a, b in e]
        out["observadores"].append(dict(
            nombre=NOMBRE_ES[n_es], dist_pc=round(float(dist), 3), dist_al=round(float(dist) * 3.2616, 2),
            ra=[round(float(x) * 15.0, 2) for x in ra], de=[round(float(x), 2) for x in de], mag=[round(float(x), 2) for x in m],
            sol=[int(k) for k in np.where(ids == 0)[0]], nombres=nombres, aristas=[[int(a), int(b)] for a, b in e], persiste=pers))
    json.dump(out, open(os.path.join(OUT, "extension.json"), "w"), separators=(",", ":"))
    print("extension.json", os.path.getsize(os.path.join(OUT, "extension.json")) // 1024, "KB")


if __name__ == "__main__":
    main()
