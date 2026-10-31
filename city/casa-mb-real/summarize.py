"""Resumenes estadisticos de out/raw/*.npz -> out/results.json.  Uso: python summarize.py [grupo ...]"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "src"))
import numpy as np

import analysis as an
import experiments as ex
import mbdata as md

OUT = os.path.join(HERE, "out")
rngb = np.random.default_rng(12345)


def ci(x, n=2000):
    x = np.asarray(x, float)
    x = x[np.isfinite(x)]
    if len(x) == 0:
        return [None, None, None]
    bs = rngb.choice(x, size=(n, len(x))).mean(1)
    return [round(float(x.mean()), 4), round(float(np.quantile(bs, .025)), 4), round(float(np.quantile(bs, .975)), 4)]


def cls_sign(stim):
    t = stim.replace("type:", "")
    if t.startswith("PAM"):
        return +1
    if t.startswith("PPL1"):
        return -1
    return 0


def type_metrics(d, stims):
    """d: [seeds, stims, 3]  -> dict con metricas por tipo y agregadas (para una condicion)."""
    ty = [i for i, s in enumerate(stims) if s.startswith("type:") and cls_sign(s) != 0]
    sg = np.array([cls_sign(stims[i]) for i in ty])
    A = d[:, ty, 0]                                      # [seeds, types]
    corr = (np.sign(A.mean(0)) == sg)
    pam = A[:, sg > 0].mean(1); ppl = A[:, sg < 0].mean(1)
    sep = pam - ppl                                      # por semilla
    B = np.abs(d[:, ty, 1]).mean(); Cc = np.abs(d[:, ty, 2]).mean(); Aa = np.abs(A).mean()
    return dict(n_tipos=len(ty), acierta_signo=int(corr.sum()), pam_acierta=int(corr[sg > 0].sum()), pam_n=int((sg > 0).sum()),
                ppl1_acierta=int(corr[sg < 0].sum()), ppl1_n=int((sg < 0).sum()), separacion_PAM_menos_PPL1=ci(sep),
                abs_A=round(float(Aa), 4), cociente_B_sobre_A=round(float(B / max(Aa, 1e-9)), 3),
                cociente_C_sobre_A=round(float(Cc / max(Aa, 1e-9)), 3))


def seed_metrics(dc, stims):
    """por semilla: separacion PAM-PPL1 en dLI(A) por tipo, y cociente |B|/|A| medio entre tipos."""
    ty = [i for i, s in enumerate(stims) if s.startswith("type:") and cls_sign(s) != 0]
    sg = np.array([cls_sign(stims[i]) for i in ty])
    A = dc[:, ty, 0]
    sep = A[:, sg > 0].mean(1) - A[:, sg < 0].mean(1)
    ba = np.abs(dc[:, ty, 1]).mean(1) / np.maximum(np.abs(A).mean(1), 1e-9)
    return sep, ba


def block(raw, v, label=None):
    d, stims = ex.dli(raw, v)           # [C,S,T,3]
    conds = [str(c) for c in raw["conds"]]
    out = {}
    for ci_, c in enumerate(conds):
        o = {}
        for si, s in enumerate(stims):
            if s in ("PAM", "PPL1") or (s.startswith("type:") and sum(x.startswith("type:") for x in stims) < 10):
                o[s] = dict(A=ci(d[ci_, :, si, 0]), B=ci(d[ci_, :, si, 1]), C=ci(d[ci_, :, si, 2]),
                            signo_correcto_A=round(float((np.sign(d[ci_, :, si, 0]) == cls_sign(s)).mean()), 3) if cls_sign(s) else None)
        if sum(s.startswith("type:") for s in stims) >= 10:
            o["tipos"] = type_metrics(d[ci_], stims)
        out[c] = o
    return out, d, stims, conds


def per_type_table(d, stims):
    t = {}
    for si, s in enumerate(stims):
        if s.startswith("type:"):
            t[s[5:]] = dict(clase=cls_sign(s), A=ci(d[:, si, 0]), B=ci(d[:, si, 1]), C=ci(d[:, si, 2]),
                            signo_correcto_A=(round(float((np.sign(d[:, si, 0]) == cls_sign(s)).mean()), 3) if cls_sign(s) else None))
    return t


def load_parts(g):
    import glob
    parts = sorted(glob.glob(os.path.join(OUT, "raw", g + "__*.npz")))
    if not parts:
        return None
    P = [ex.load_raw(p) for p in parts]
    raw = dict(ntest=P[0]["ntest"], meta=P[0]["meta"], stims=P[0]["stims"], seeds=P[0]["seeds"],
               conds=np.array([str(p["conds"][0]) for p in P]))
    for k in ("pre", "post", "f_mean", "kc_bits"):
        raw[k] = np.concatenate([p[k] for p in P], axis=0)
    return raw


def load_controls():
    """Une out/raw/controls__*.npz y anade 'real' = semillas 1..12 de main (mismos olores) con las mismas estimulaciones."""
    import glob
    parts = sorted(glob.glob(os.path.join(OUT, "raw", "controls__*.npz")))
    mp = os.path.join(OUT, "raw", "main.npz")
    if not parts or not os.path.exists(mp):
        return None
    P = [ex.load_raw(p) for p in parts]
    stims = [str(x) for x in P[0]["stims"]]
    seeds = list(P[0]["seeds"])
    M = ex.load_raw(mp)
    ms = [str(x) for x in M["stims"]]
    si = [list(M["seeds"]).index(sd) for sd in seeds]
    ti = [ms.index(s) for s in stims]
    real = {k: M[k][:, si][:, :, ti] for k in ("pre", "post", "f_mean")}
    real["kc_bits"] = M["kc_bits"][:, si]
    order = ["real"] + [str(p["conds"][0]) for p in P]
    raw = dict(ntest=P[0]["ntest"], meta=P[0]["meta"], stims=np.array(stims), seeds=np.array(seeds), conds=np.array(order))
    for k in ("pre", "post", "f_mean", "kc_bits"):
        raw[k] = np.concatenate([real[k]] + [p[k] for p in P], axis=0)
    return raw


def main(groups):
    nodes, _ = md.load()
    v = an.valence_vector(nodes, "nt")
    res = json.load(open(os.path.join(OUT, "results.json"))) if os.path.exists(os.path.join(OUT, "results.json")) else {}
    for g in groups:
        path = os.path.join(OUT, "raw", g + ".npz")
        if g == "controls":
            raw = load_controls()
            if raw is None:
                print("faltan partes de controls"); continue
        elif g == "recurrent":
            raw = load_parts("recurrent")
            if raw is None:
                print("faltan partes de recurrent"); continue
        elif not os.path.exists(path):
            print("falta", path); continue
        else:
            raw = ex.load_raw(path)
        b, d, stims, conds = block(raw, v)
        b = {k: x for k, x in b.items() if k != "extra_edges"}   # condicion retirada: ver LOG (escala PN->APL mal elegida)
        r = dict(semillas=int(len(raw["seeds"])), resultados=b)
        if g == "controls":
            ref = conds.index("real")
            sr, br = seed_metrics(d[ref], stims)
            dif = {}
            for ci_, c in enumerate(conds):
                if c == "real":
                    continue
                sc, bc = seed_metrics(d[ci_], stims)
                bits = np.unpackbits(raw["kc_bits"][ci_], axis=2)[:, :, :4064].astype(bool)
                jab = [(bits[k, 0] & bits[k, 1]).sum() / max((bits[k, 0] | bits[k, 1]).sum(), 1) for k in range(len(bits))]
                dif[c] = dict(delta_separacion=ci(sc - sr), delta_B_sobre_A=ci(bc - br), jaccard_AB=ci(jab), kc_activas=ci(bits.mean(2).mean(1)))
            r["pareado_vs_real"] = dif
        if g == "main":
            r["por_tipo"] = per_type_table(d[0], stims)
            # variantes de valencia sobre los mismos datos crudos
            var = {}
            for name, vv in (("nt_consensus", v), ("nt_predicted", an.valence_vector(nodes, "nt_predicted")), ("signo_invertido", -v)):
                dd, st = ex.dli(raw, vv)
                var[name] = type_metrics(dd[0], st)
                var[name]["PAM_A"] = ci(dd[0, :, st.index("PAM"), 0]); var[name]["PPL1_A"] = ci(dd[0, :, st.index("PPL1"), 0])
            # nulo: permutar el vector de valencia entre tipos de MBON (conserva composicion 26/71)
            mb = np.flatnonzero(nodes["cls"] == md.MBON); mt = nodes["type"][mb]
            ut = sorted(set(mt)); rng = np.random.default_rng(7)
            nul_sep, nul_acc = [], []
            for _ in range(500):
                perm = rng.permutation(len(ut))
                vt = {t: v[np.flatnonzero(mt == ut[perm[i]])[0]] for i, t in enumerate(ut)}
                vv = np.array([vt[t] for t in mt])
                dd, st = ex.dli(raw, vv)
                m = type_metrics(dd[0], st)
                nul_sep.append(m["separacion_PAM_menos_PPL1"][0]); nul_acc.append(m["acierta_signo"])
            real_m = type_metrics(d[0], stims)
            var["nulo_valencia_permutada"] = dict(sep_media=round(float(np.mean(nul_sep)), 4), sep_p95=round(float(np.quantile(nul_sep, .95)), 4),
                                                  acc_media=round(float(np.mean(nul_acc)), 2), acc_p95=float(np.quantile(nul_acc, .95)),
                                                  p_valor_sep=float((np.array(nul_sep) >= real_m["separacion_PAM_menos_PPL1"][0]).mean()),
                                                  p_valor_acc=float((np.array(nul_acc) >= real_m["acierta_signo"]).mean()))
            r["variantes_valencia"] = var
            # contribucion de cada tipo de MBON al dLI(A) (control sin DAN restado), para PAM-todos y PPL1-todos
            mbn = np.flatnonzero(nodes["cls"] == md.MBON); mtn = nodes["type"][mbn]
            ntest = raw["ntest"]; pre = raw["pre"][0] / ntest; post = raw["post"][0] / ntest
            den = (np.abs(v) * pre[:, 0:1, 0, :]).sum(-1)               # [S,1]: sum|v| r_pre del olor A (control)
            i0 = [str(x) for x in raw["stims"]].index("none")
            contrib = {}
            for sname in ("PAM", "PPL1"):
                ti = [str(x) for x in raw["stims"]].index(sname)
                dd = (post[:, ti, 0, :] - pre[:, ti, 0, :]) - (post[:, i0, 0, :] - pre[:, i0, 0, :])   # [S, mbon]
                contrib[sname] = {}
                for t in sorted(set(mtn)):
                    j = np.flatnonzero(mtn == t)
                    contrib[sname][t] = round(float((dd[:, j] * v[j]).sum(1).mean() / den.mean()), 4)
            r["contribucion_MBON_a_dLI_A"] = contrib
            # ¿aporta la dinamica algo mas que la anatomia estatica? predictor = -(valencia media de los blancos del DAN)
            an_json = json.load(open(os.path.join(OUT, "anatomy.json")))
            mT = an_json["DAN_clase_vs_valencia_MBON"]["valencia_media_de_objetivos_por_tipo"]
            tt = [(k, r["por_tipo"][k]["A"][0]) for k in r["por_tipo"] if k in mT]
            xs = np.array([-mT[k] for k, _ in tt]); ys = np.array([y for _, y in tt])
            from scipy.stats import spearmanr, pearsonr
            r["estatico_vs_dinamico"] = dict(n=len(tt), pearson=round(float(pearsonr(xs, ys)[0]), 3), spearman=round(float(spearmanr(xs, ys)[0]), 3),
                                             signo_coincide=int((np.sign(xs) == np.sign(ys)).sum()),
                                             nota="predictor estatico = -(media ponderada por sinapsis de la valencia NT de los MBON que contacta el tipo de DAN); y = dLI(A) medio simulado")
            # especificidad vs solapamiento de KC
            kb = raw["kc_bits"][0]                       # [S,3,508]
            bits = np.unpackbits(kb, axis=2)[:, :, :4064].astype(bool)
            jab = [(bits[s, 0] & bits[s, 1]).sum() / max((bits[s, 0] | bits[s, 1]).sum(), 1) for s in range(len(bits))]
            jac = [(bits[s, 0] & bits[s, 2]).sum() / max((bits[s, 0] | bits[s, 2]).sum(), 1) for s in range(len(bits))]
            r["kc_pre"] = dict(activas_A=ci(bits[:, 0].mean(1)), jaccard_AB=ci(jab), jaccard_AC=ci(jac))
            si = stims.index("PPL1")
            r["especificidad_PPL1"] = dict(
                corr_jaccardAB_vs_dLI_B_sobre_A=round(float(np.corrcoef(jab, d[0, :, si, 1] / np.minimum(d[0, :, si, 0], -1e-3))[0, 1]), 3),
                nota="correlacion entre solapamiento KC (A,B) y dLI(B)/dLI(A) por semilla")
        if g == "lesions_apl":
            apl = {}
            for ci_, c in enumerate(conds):
                bits = np.unpackbits(raw["kc_bits"][ci_], axis=2)[:, :, :4064]
                bb = bits.astype(bool)
                jab = [(bb[k, 0] & bb[k, 1]).sum() / max((bb[k, 0] | bb[k, 1]).sum(), 1) for k in range(len(bb))]
                apl[c] = dict(kc_activas=ci(bits.mean(2).mean(1)), jaccard_AB=ci(jab))
            r["kc_activas"] = apl
        if g == "lesions_dan":
            base = {s: d[0, :, stims.index(s), 0] for s in ("PAM", "PPL1")}
            les = {}
            for si, s in enumerate(stims):
                if "-minus:" in s:
                    b0, rm = s.split("-minus:")
                    les[rm] = dict(clase=b0, A=ci(d[0, :, si, 0]), perdida_vs_completo=ci((base[b0] - d[0, :, si, 0])))
            r["leave_one_out"] = les
        if g == "lesions_mbon":
            i0 = conds.index("mbon_intact")
            les = {}
            for ci_, c in enumerate(conds):
                if c.startswith("mbon_sil_"):
                    t = c[9:]
                    les[t] = {s: dict(A=ci(d[ci_, :, stims.index(s), 0]), cambio_vs_intacto=ci(d[ci_, :, stims.index(s), 0] - d[i0, :, stims.index(s), 0]))
                              for s in ("PAM", "PPL1")}
            r["silenciar_tipo_MBON"] = les
        res[g] = r
    json.dump(res, open(os.path.join(OUT, "results.json"), "w"), indent=1)
    return res


if __name__ == "__main__":
    gs = sys.argv[1:] or ["main", "controls", "sweeps", "lesions_apl", "lesions_apl2", "lesions_dan", "lesions_mbon", "backward", "robust", "extra", "recurrent", "ntsource"]
    main(gs)
