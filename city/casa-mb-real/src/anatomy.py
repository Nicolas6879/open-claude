"""Validacion anatomica: ¿los DAN contactan de verdad a los MBON de "su" compartimento?

Salidas: out/anatomy.json, out/dan_mbon_types.csv, out/anatomy_heatmap.svg.
Etiquetas: medido = calculado de los feather; la tabla de compartimentos sale de las anotaciones (instance).
"""
import json
import os
import sys
from collections import Counter, defaultdict

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import compartments as comp
import mbdata as md

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "out")


def kc_class(t):
    if t.startswith("KCg"):
        return "g"
    if t.startswith("KCa'b'"):
        return "a'b'"
    if t.startswith("KCab"):
        return "ab"
    return "?"


def lobe_class_of_comp(c):
    if c.startswith("g"):
        return "g"
    if c.startswith("b'") or c.startswith("a'"):
        return "a'b'"
    if c.startswith("b") or c.startswith("a"):
        return "ab"
    return "?"


def type_tables(nodes):
    """dict tipo -> info para MBON y DAN: indices, NT mayoritario, compartimentos anotados."""
    out = {}
    for cls in (md.MBON, md.DAN):
        idx = np.where(nodes["cls"] == cls)[0]
        by = defaultdict(list)
        for i in idx:
            by[nodes["type"][i]].append(i)
        for t, ii in by.items():
            nt = Counter(nodes["nt_consensus"][ii]).most_common(1)[0][0]
            prim, sec = comp.parse_instance(nodes["instance"][ii[0]])
            out[t] = dict(cls=cls, idx=np.array(ii), n=len(ii), nt=nt, prim=prim, sec=sec)
    return out


def valence_by_nt(nt):
    """Aso 2014b (verificado en PMC4273436): glutamato -> evitacion; GABA/ACh -> atraccion. Otro -> 0."""
    if nt == "glutamate":
        return -1
    if nt in ("gaba", "acetylcholine"):
        return +1
    return 0


def type_matrix(nodes, edges, tt, pre_types, post_types, post_cls, pre_cls, wmin=1):
    P = {t: i for i, t in enumerate(pre_types)}
    Q = {t: i for i, t in enumerate(post_types)}
    M = np.zeros((len(pre_types), len(Q)))
    m = (nodes["cls"][edges["pre"]] == pre_cls) & (nodes["cls"][edges["post"]] == post_cls) & (edges["w"] >= wmin)
    for a, b, w in zip(edges["pre"][m], edges["post"][m], edges["w"][m]):
        M[P[nodes["type"][a]], Q[nodes["type"][b]]] += w
    return M


def main():
    nodes, edges = md.load()
    tt = type_tables(nodes)
    mbon_types = sorted([t for t, v in tt.items() if v["cls"] == md.MBON])
    dan_types = sorted([t for t, v in tt.items() if v["cls"] == md.DAN])
    res = {"descripcion": "Validacion anatomica de compartimentos con conectividad MaleCNS v1.0 (medido)."}

    # --- A. tipo MBON: NT, valencia, compartimentos anotados
    mb = {}
    for t in mbon_types:
        v = tt[t]
        mb[t] = dict(n=v["n"], nt=v["nt"], valence=valence_by_nt(v["nt"]), comp=list(v["prim"]),
                     sec=list(v["sec"]))
    res["MBON_tipos"] = mb
    res["MBON_NT_conteo_neuronas"] = dict(Counter(nodes["nt_consensus"][nodes["cls"] == md.MBON]))

    # --- B. KC subtipo -> MBON: ¿coincide el lobulo anotado con el subtipo de KC que mas sinapsis aporta?
    kc_idx = np.where(nodes["cls"] == md.KC)[0]
    kcc = np.array([kc_class(t) for t in nodes["type"]])
    classes = ["g", "a'b'", "ab"]
    Fk = {}
    m = (nodes["cls"][edges["pre"]] == md.KC) & (nodes["cls"][edges["post"]] == md.MBON)
    acc = defaultdict(lambda: Counter())
    for a, b, w in zip(edges["pre"][m], edges["post"][m], edges["w"][m]):
        acc[nodes["type"][b]][kcc[a]] += w
    kc_disc = []
    hits = 0
    tot = 0
    for t in mbon_types:
        c = acc[t]
        s = sum(c.values()) or 1
        fr = {k: round(c[k] / s, 3) for k in classes}
        dom = max(fr, key=fr.get)
        annot = sorted(set(lobe_class_of_comp(x) for x in tt[t]["prim"] if x != "calyx"))
        ok = (dom in annot) if annot else None
        Fk[t] = dict(frac=fr, dominante=dom, anotado=annot, coincide=ok, sinapsis=int(s))
        if ok is not None:
            tot += 1
            hits += int(ok)
            if not ok:
                kc_disc.append(t)
    res["KC_subtipo_a_MBON"] = Fk
    res["KC_subtipo_coincidencia"] = dict(coinciden=hits, total=tot, discrepancias=kc_disc)

    # --- C. DAN tipo x MBON tipo (sinapsis, w>=1)
    W = type_matrix(nodes, edges, tt, dan_types, mbon_types, md.MBON, md.DAN, 1)
    W3 = type_matrix(nodes, edges, tt, dan_types, mbon_types, md.MBON, md.DAN, 3)
    ndan = np.array([tt[t]["n"] for t in dan_types])
    with open(os.path.join(OUT, "dan_mbon_types.csv"), "w") as f:
        f.write("DAN\\MBON," + ",".join(mbon_types) + "\n")
        for i, t in enumerate(dan_types):
            f.write(t + "," + ",".join(str(int(x)) for x in W[i]) + "\n")

    def share_comp(a, b):
        return len(set(a) & set(b)) > 0

    rng = np.random.default_rng(0)
    lab_m = [tt[t]["prim"] for t in mbon_types]
    dan_lab = {t: tt[t]["prim"] for t in dan_types if tt[t]["prim"]}
    unlab = [t for t in dan_types if not tt[t]["prim"]]

    def match_frac(Wm, labs):
        fr = []
        for t, pc in dan_lab.items():
            i = dan_types.index(t)
            row = Wm[i]
            if row.sum() == 0:
                continue
            ok = np.array([share_comp(pc, labs[j]) for j in range(len(mbon_types))])
            fr.append(row[ok].sum() / row.sum())
        return np.array(fr)

    obs = match_frac(W, lab_m)
    obs3 = match_frac(W3, lab_m)
    nulls = []
    for _ in range(5000):
        p = rng.permutation(len(mbon_types))
        nulls.append(match_frac(W, [lab_m[j] for j in p]).mean())
    nulls = np.array(nulls)
    per_dan = {}
    for t in dan_lab:
        i = dan_types.index(t)
        row = W[i]
        if row.sum() == 0:
            per_dan[t] = dict(match=None)
            continue
        ok = np.array([share_comp(dan_lab[t], lab_m[j]) for j in range(len(mbon_types))])
        top = int(np.argmax(row))
        per_dan[t] = dict(compartimento_anotado=list(dan_lab[t]), frac_sinapsis_a_MBON_del_mismo_compartimento=round(
            float(row[ok].sum() / row.sum()), 3), MBON_principal=mbon_types[top],
            frac_principal=round(float(row[top] / row.sum()), 3), principal_en_su_compartimento=bool(ok[top]),
            sinapsis_a_MBON=int(row.sum()))
    res["DAN_a_MBON_validacion"] = dict(
        n_tipos_anotados=len(dan_lab), frac_media_observada=round(float(obs.mean()), 3),
        frac_mediana=round(float(np.median(obs)), 3), frac_media_w3=round(float(obs3.mean()), 3),
        nulo_permutando_etiquetas_MBON=dict(media=round(float(nulls.mean()), 3), p95=round(float(np.quantile(nulls, .95)), 3),
                                          max=round(float(nulls.max()), 3), p_valor=float((nulls >= obs.mean()).mean())),
        principal_en_su_compartimento=sum(1 for v in per_dan.values() if v.get("principal_en_su_compartimento")),
        por_tipo=per_dan)

    # --- D. DAN sin anotacion: compartimento inferido por conectividad
    inf = {}
    for t in unlab:
        i = dan_types.index(t)
        row = W[i]
        order = np.argsort(-row)[:4]
        inf[t] = dict(sinapsis_a_MBON=int(row.sum()), neuronas=int(tt[t]["n"]),
                      principales=[(mbon_types[j], int(row[j]), list(lab_m[j])) for j in order if row[j] > 0])
    res["DAN_sin_anotar_inferidos"] = inf

    # --- E. DAN -> KC por subtipo (conexion escasa; solo como segunda prueba)
    m = (nodes["cls"][edges["pre"]] == md.DAN) & (nodes["cls"][edges["post"]] == md.KC)
    dk = defaultdict(Counter)
    for a, b, w in zip(edges["pre"][m], edges["post"][m], edges["w"][m]):
        dk[nodes["type"][a]][kcc[b]] += w
    tot_all = Counter()
    for t in dan_types:
        tot_all.update(dk[t])
    sall = sum(tot_all.values())
    base = {k: tot_all[k] / sall for k in classes}
    dkres = {}
    hit = n = 0
    for t in dan_types:
        c = dk[t]
        s = sum(c[k] for k in classes)
        if s < 30:
            continue
        fr = {k: round(c[k] / s, 3) for k in classes}
        dom = max(fr, key=fr.get)
        ann = sorted(set(lobe_class_of_comp(x) for x in tt[t]["prim"] if x != "calyx"))
        ok = (dom in ann) if ann else None
        enr = {k: round(fr[k] / max(base[k], 1e-9), 2) for k in classes}
        dkres[t] = dict(frac=fr, enriquecimiento_vs_base=enr, anotado=ann, dominante=dom, coincide=ok, sinapsis=int(s))
        if ok is not None:
            n += 1
            hit += int(ok)
    res["DAN_a_KC_subtipo"] = dict(base=base, por_tipo=dkres, coincide_dominante=hit, evaluados=n)

    # --- F. clase de DAN vs valencia (NT) de los MBON que contacta
    vm = np.array([valence_by_nt(tt[t]["nt"]) for t in mbon_types], float)
    rows = {}
    for i, t in enumerate(dan_types):
        if W[i].sum() > 0:
            rows[t] = float((W[i] * vm).sum() / W[i].sum())
    pam = [v for t, v in rows.items() if t.startswith("PAM")]
    ppl = [v for t, v in rows.items() if t.startswith("PPL1")]
    # nulo: permutar valencias entre tipos MBON
    nulld = []
    for _ in range(5000):
        vp = rng.permutation(vm)
        r = {t: float((W[dan_types.index(t)] * vp).sum() / W[dan_types.index(t)].sum()) for t in rows}
        nulld.append(np.mean([v for t, v in r.items() if t.startswith("PAM")]) - np.mean([v for t, v in r.items() if t.startswith("PPL1")]))
    d_obs = float(np.mean(pam) - np.mean(ppl))
    res["DAN_clase_vs_valencia_MBON"] = dict(
        valencia_media_de_objetivos_por_tipo={k: round(v, 3) for k, v in rows.items()},
        PAM_media=round(float(np.mean(pam)), 3), PPL1_media=round(float(np.mean(ppl)), 3), diferencia_PAM_menos_PPL1=round(d_obs, 3),
        nulo_p95=round(float(np.quantile(nulld, .95)), 3), nulo_p05=round(float(np.quantile(nulld, .05)), 3),
        p_valor_dos_colas=float(min(1, 2 * min((np.array(nulld) <= d_obs).mean(), (np.array(nulld) >= d_obs).mean()))),
        lectura="Si PAM->MBON de evitacion (valencia -1) y PPL1->MBON de atraccion (+1), esperamos PAM negativo y PPL1 positivo.")
    # --- G. clustering de MBON por perfil de DAN (independiente de las anotaciones)
    from scipy.cluster.hierarchy import fcluster, linkage
    from scipy.spatial.distance import pdist
    X = W.T / np.maximum(W.T.sum(1, keepdims=True), 1)
    keep = W.sum(0) > 0
    Z = linkage(pdist(X[keep], "cosine"), "average")
    names = [t for t, k in zip(mbon_types, keep) if k]
    labs_ann = [tuple(sorted(tt[t]["prim"])) for t in names]
    # pares de MBON: ¿mismo cluster <-> comparten compartimento anotado?
    best = None
    for k in range(6, 20):
        cl = fcluster(Z, k, "maxclust")
        tp = fp = fn = tn = 0
        for a in range(len(names)):
            for b in range(a + 1, len(names)):
                same = cl[a] == cl[b]
                sh = share_comp(labs_ann[a], labs_ann[b])
                tp += same and sh
                fp += same and not sh
                fn += (not same) and sh
                tn += (not same) and not sh
        prec = tp / max(tp + fp, 1)
        rec = tp / max(tp + fn, 1)
        f1 = 2 * prec * rec / max(prec + rec, 1e-9)
        if best is None or f1 > best[0]:
            best = (f1, k, prec, rec)
    res["clustering_MBON_por_DAN"] = dict(mejor_F1_pares=round(best[0], 3), k=int(best[1]), precision=round(best[2], 3),
                                          recall=round(best[3], 3),
                                          nota="Pares de MBON: ¿mismo cluster por perfil de DAN <-> comparten compartimento anotado?")
    json.dump(res, open(os.path.join(OUT, "anatomy.json"), "w"), indent=1, ensure_ascii=False, default=str)
    return res


if __name__ == "__main__":
    r = main()
    print(json.dumps({k: r[k] for k in ["KC_subtipo_coincidencia", "clustering_MBON_por_DAN"]}, ensure_ascii=False, indent=1))
    v = r["DAN_a_MBON_validacion"]
    print({k: v[k] for k in v if k != "por_tipo"})
    print(json.dumps(r["DAN_clase_vs_valencia_MBON"], ensure_ascii=False)[:1500])
