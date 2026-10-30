"""Auditoria: que supone el modelo de casa-mosca (Neuro) frente a la anatomia medida en MaleCNS v1.0.

Escribe out/audit.json (pequeno) y muestra una tabla. Requiere los datos (ver fetch_data.sh).
Uso: PYTHONDONTWRITEBYTECODE=1 python3 src/audit.py [--seed 1] [--swaps 20]
"""
import argparse
import collections
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import conectoma_io as cio  # noqa: E402
import nulls  # noqa: E402

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--swap-runs", type=int, default=3)
    ap.add_argument("--swap-factor", type=int, default=20, help="intercambios = factor x numero de aristas PN-KC")
    ap.add_argument("--out", default=os.path.join(HERE, "out", "audit.json"))
    a = ap.parse_args()

    ann = cio.load_annotations()
    nt = cio.load_neurotransmitters()
    pre, post, w = cio.load_subcircuit(ann)
    cls = {b: v["cls"] for b, v in ann.items()}
    typ = {b: v["type"] for b, v in ann.items()}
    side = {b: v["side"] for b, v in ann.items()}

    by_cls = collections.Counter(v["cls"] for v in ann.values())
    kc = [b for b, v in ann.items() if v["cls"] == "Kenyon_Cell"]
    kc_side = collections.Counter(side[b] for b in kc)
    apl = [b for b, v in ann.items() if v["type"] == "APL"]
    mbon = [b for b, v in ann.items() if v["cls"] == "MBON"]
    dan = [b for b, v in ann.items() if v["cls"] == "DAN"]
    alpn = [b for b, v in ann.items() if v["cls"] == "ALPN"]

    c_pre = np.array([cls.get(int(p)) for p in pre])
    c_post = np.array([cls.get(int(q)) for q in post])
    is_apl = np.array([typ.get(int(q)) == "APL" for q in post])

    # --- PN -> KC ---
    m_pk = (c_pre == "ALPN") & (c_post == "Kenyon_Cell")
    pk_pre, pk_post, pk_w = pre[m_pk], post[m_pk], w[m_pk]
    n_pn_per_kc = collections.Counter()
    syn_per_kc = collections.Counter()
    pn_sets = collections.defaultdict(set)
    for p, q, x in zip(pk_pre.tolist(), pk_post.tolist(), pk_w.tolist()):
        pn_sets[q].add(p)
        syn_per_kc[q] += x
    deg = np.array([len(pn_sets.get(k, ())) for k in kc])
    kc_with = deg[deg > 0]
    same_side = sum(1 for p, q in zip(pk_pre.tolist(), pk_post.tolist()) if side[p] == side[q])
    w_edges = pk_w.astype(float)  # sinapsis por arista PN->KC

    # --- PN out-degree (cuantas KC recibe cada PN) ---
    pn_out = collections.Counter(pk_pre.tolist())

    # --- Nulo que conserva grados (PN y KC) ---
    universe = sorted(pn_out)
    kcs_sets = {k: pn_sets[k] for k in pn_sets}
    kcs, M = nulls.shared_matrix(kcs_sets, universe)
    obs_mean, obs_frac = nulls.pair_overlap(M)
    rng = np.random.default_rng(a.seed)
    null_fracs, null_means = [], []
    n_edges = sum(len(s) for s in kcs_sets.values())
    for _ in range(a.swap_runs):
        ns, done = nulls.swap_null([(k, p) for k in kcs_sets for p in kcs_sets[k]], a.swap_factor * n_edges, rng)
        _, Mn = nulls.shared_matrix(ns, universe)
        mm, ff = nulls.pair_overlap(Mn)
        null_means.append(mm)
        null_fracs.append(ff)
    # Nulo uniforme (como el de casa-mosca): PN elegidas al azar con el mismo grado por KC
    uni = {}
    for k in kcs:
        uni[k] = set(rng.choice(universe, size=len(kcs_sets[k]), replace=False).tolist())
    _, Mu = nulls.shared_matrix(uni, universe)
    uni_mean, uni_frac = nulls.pair_overlap(Mu)

    # --- KC -> APL, APL -> KC ---
    m_ka = (c_pre == "Kenyon_Cell") & is_apl
    m_ak = np.array([typ.get(int(p)) == "APL" for p in pre]) & (c_post == "Kenyon_Cell")
    apl_in_syn = int(w[m_ka].sum())
    apl_out_syn = int(w[m_ak].sum())
    kc_to_apl_partners = len(set(pre[m_ka].tolist()))
    apl_to_kc_partners = len(set(post[m_ak].tolist()))

    # --- KC -> KC ---
    m_kk = (c_pre == "Kenyon_Cell") & (c_post == "Kenyon_Cell")
    kk_edges = int(m_kk.sum())
    kk_strong = int((w[m_kk] >= 5).sum())

    # --- KC -> MBON ---
    m_km = (c_pre == "Kenyon_Cell") & (c_post == "MBON")
    kmbon_per = collections.Counter(int(q) for q in post[m_km].tolist())
    kmbon_partners_kc = collections.Counter(int(q) for q in pre[m_km].tolist())
    kmbon_strong_kc_per_mbon = collections.Counter()
    for p, q, x in zip(pre[m_km].tolist(), post[m_km].tolist(), w[m_km].tolist()):
        if x >= 5:
            kmbon_strong_kc_per_mbon[q] += 1
    mbon_nt = collections.Counter(nt.get(b, "?") for b in mbon)
    dan_nt = collections.Counter(nt.get(b, "?") for b in dan)
    kc_nt = collections.Counter(nt.get(b, "?") for b in kc)
    apl_nt = collections.Counter(nt.get(b, "?") for b in apl)
    pn_nt = collections.Counter(nt.get(b, "?") for b in alpn)
    pn_kc_nt = collections.Counter()
    for p, x in zip(pk_pre.tolist(), pk_w.tolist()):
        pn_kc_nt[nt.get(p, "?")] += x

    # --- Tipos ---
    mb_types = collections.Counter(typ[b] for b in mbon)
    dan_types = collections.Counter(typ[b] for b in dan)
    n_dan_types = len(dan_types)

    def q(x, p):
        return float(np.percentile(x, p))

    res = {
        "descripcion": "Auditoria de supuestos de casa-mosca frente a MaleCNS v1.0 (minconf 0.5)",
        "conteos": {
            "KC_total": len(kc), "KC_por_lado": dict(kc_side),
            "APL": len(apl), "MBON": len(mbon), "MBON_tipos": len(mb_types),
            "DAN": len(dan), "DAN_tipos": n_dan_types,
            "PN_ALPN_total": len(alpn), "PN_con_salida_a_KC": len(universe),
            "ORN_olfativas": by_cls.get("olfactory", 0),
        },
        "PN_KC": {
            "aristas_PN_KC": int(len(pk_pre)),
            "KC_con_al_menos_1_PN": int(len(kc_with)),
            "KC_sin_PN_en_archivo_significativo": int(len(kc) - len(kc_with)),
            "PN_distintas_por_KC_media_(KC_con_PN)": float(kc_with.mean()),
            "PN_distintas_por_KC_mediana_(KC_con_PN)": float(np.median(kc_with)),
            "PN_distintas_por_KC_p10_p90": [q(kc_with, 10), q(kc_with, 90)],
            "PN_distintas_por_KC_max": int(kc_with.max()),
            "fraccion_KC_con_exactamente_6_PN": float((kc_with == 6).mean()),
            "fraccion_KC_con_4_a_8_PN": float(((kc_with >= 4) & (kc_with <= 8)).mean()),
            "sinapsis_por_arista_mediana": float(np.median(w_edges)),
            "sinapsis_por_arista_p10_p90": [q(w_edges, 10), q(w_edges, 90)],
            "sinapsis_por_arista_max": int(w_edges.max()),
            "aristas_mismo_lado": float(same_side / max(1, len(pk_pre))),
            "PN_out_grado_mediana": float(np.median(list(pn_out.values()))),
            "PN_out_grado_max": int(max(pn_out.values())),
            "nt_de_PN_en_sinapsis_a_KC": dict(pn_kc_nt),
        },
        "solapamiento_entre_pares_de_KC": {
            "observado_media_PN_compartidas": obs_mean,
            "observado_fraccion_pares_con_alguna_PN": obs_frac,
            "nulo_conserva_grados_media": float(np.mean(null_means)),
            "nulo_conserva_grados_fraccion_pares": float(np.mean(null_fracs)),
            "nulo_conserva_grados_fraccion_pares_sd": float(np.std(null_fracs)),
            "nulo_uniforme_media": uni_mean,
            "nulo_uniforme_fraccion_pares": uni_frac,
            "nota": "La media de PN compartidas es identica a la del nulo que conserva grados por construccion "
                    "(depende solo de los grados de las PN). La fraccion de pares si discrimina.",
        },
        "APL": {
            "KC_a_APL_partners": kc_to_apl_partners, "KC_a_APL_sinapsis": apl_in_syn,
            "APL_a_KC_partners": apl_to_kc_partners, "APL_a_KC_sinapsis": apl_out_syn,
            "nt_APL": dict(apl_nt),
        },
        "KC_KC": {
            "aristas": kk_edges, "aristas_con_>=5_sinapsis": kk_strong,
            "mediana_sinapsis_por_arista": float(np.median(w[m_kk])),
        },
        "KC_MBON": {
            "aristas": int(m_km.sum()),
            "KC_distintas_por_MBON_mediana": float(np.median(list(kmbon_strong_kc_per_mbon.values()))) if kmbon_strong_kc_per_mbon else None,
            "MBON_que_reciben_KC_con_>=5_sinapsis": len(kmbon_strong_kc_per_mbon),
        },
        "neurotransmisores": {
            "KC": dict(kc_nt), "MBON": dict(mbon_nt), "DAN": dict(dan_nt), "ALPN": dict(pn_nt),
        },
        "tipos_MBON": dict(mb_types),
        "tipos_DAN": dict(dan_types),
    }
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    with open(a.out, "w", encoding="utf-8") as fh:
        json.dump(res, fh, ensure_ascii=False, indent=1)
        fh.write("\n")
    print(json.dumps({k: res[k] for k in ("conteos", "PN_KC", "solapamiento_entre_pares_de_KC", "APL", "KC_KC")}, ensure_ascii=False, indent=1))
    print("escrito:", a.out)


if __name__ == "__main__":
    main()
