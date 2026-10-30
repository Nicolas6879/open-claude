"""Auditor: recomputo INDEPENDIENTE (desde los feather crudos, sin importar codigo de casa-conectoma) de las cifras de
README/audit.json. Uso: python v_conectoma.py <dir_datos> [salida.json]   (necesita numpy, pandas, pyarrow, scipy)"""
import sys, json, collections
import numpy as np, pandas as pd, pyarrow as pa, pyarrow.feather as f, pyarrow.compute as pc
import scipy.sparse as sp
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from veredicto import check, resumen
D = sys.argv[1].rstrip("/") + "/"
A = f.read_table(D + "body-annotations-male-cns-v1.0-minconf-0.5.feather", columns=["bodyId", "type", "class", "somaSide"]).to_pandas().set_index("bodyId")
NT = f.read_table(D + "body-neurotransmitters-male-cns-v1.0.feather", columns=["body", "consensus_nt", "predicted_nt"]).to_pandas().set_index("body")
W = f.read_table(D + "connectome-weights-male-cns-v1.0-minconf-0.5-significant-only.feather", columns=["body_pre", "body_post", "weight"])
print("filas pesos", W.num_rows)
typ = A["type"].fillna(""); cls = A["class"].fillna("")
KC = A.index[cls == "Kenyon_Cell"]; APL = A.index[typ == "APL"]; MBON = A.index[cls == "MBON"]; DAN = A.index[cls == "DAN"]; PN = A.index[cls == "ALPN"]
R = {}
R["KC"] = (len(KC), A.loc[KC, "somaSide"].value_counts().to_dict()); R["APL"] = len(APL); R["MBON"] = (len(MBON), typ[MBON].nunique()); R["DAN"] = (len(DAN), typ[DAN].nunique())
dt = typ[DAN].unique(); R["DAN_tipos_PAM_PPL"] = (sum(t.startswith("PAM") for t in dt), sum(t.startswith("PPL") for t in dt), [t for t in dt if not t.startswith(("PAM", "PPL"))])
for who, ix in (("KC", KC), ("MBON", MBON), ("DAN", DAN), ("ALPN", PN), ("APL", APL)):
    R["nt_consensus_" + who] = NT.reindex(ix)["consensus_nt"].value_counts(dropna=False).to_dict()
    R["nt_predicted_" + who] = NT.reindex(ix)["predicted_nt"].value_counts(dropna=False).to_dict()
S = pa.array(sorted(set(KC) | set(APL) | set(MBON) | set(DAN) | set(PN)), type=pa.int64())
m = pc.and_(pc.is_in(W["body_pre"], value_set=S), pc.is_in(W["body_post"], value_set=S)); sub = W.filter(m).to_pandas()
sub["cpre"] = cls.reindex(sub.body_pre).values; sub["cpost"] = cls.reindex(sub.body_post).values
sub["tpre"] = typ.reindex(sub.body_pre).values; sub["tpost"] = typ.reindex(sub.body_post).values
pk = sub[(sub.cpre == "ALPN") & (sub.cpost == "Kenyon_Cell")]
R["PN_KC_aristas"] = len(pk); R["PN_KC_sinapsis_total"] = int(pk.weight.sum())
R["PN_KC_sinapsis_por_NT_consensus"] = pk.groupby(NT.reindex(pk.body_pre)["consensus_nt"].fillna("NA").values).weight.sum().to_dict()
deg = pk.groupby("body_post").body_pre.nunique(); R["KC_con_PN"] = len(deg); R["KC_sin_PN"] = len(KC) - len(deg)
R["PN_por_KC"] = dict(media=deg.mean(), mediana=deg.median(), frac6=(deg == 6).mean(), frac4_8=((deg >= 4) & (deg <= 8)).mean(), max=int(deg.max()), p10_p90=[deg.quantile(.1), deg.quantile(.9)])
R["hist_PN_por_KC_(grado: fraccion de KC con PN)"] = {int(k): round(float(v), 4) for k, v in deg.value_counts(normalize=True).sort_index().items() if k <= 14}
R["frac_KC_con_PN_<4"] = float((deg < 4).mean())
R["sinapsis_por_arista"] = dict(mediana=float(pk.weight.median()), p10_p90=[float(pk.weight.quantile(.1)), float(pk.weight.quantile(.9))], max=int(pk.weight.max()))
pside = A.somaSide.reindex(pk.body_pre).values; kside = A.somaSide.reindex(pk.body_post).values
R["PN_KC_aristas_mismo_lado"] = float((pside == kside).mean())
kk = sub[(sub.cpre == "Kenyon_Cell") & (sub.cpost == "Kenyon_Cell")]; R["KC_KC"] = dict(aristas=len(kk), mediana=float(kk.weight.median()), ge5=int((kk.weight >= 5).sum()), frac_ge5=float((kk.weight >= 5).mean()))
ka = sub[(sub.cpre == "Kenyon_Cell") & (sub.tpost == "APL")]; ak = sub[(sub.tpre == "APL") & (sub.cpost == "Kenyon_Cell")]
R["APL"] = dict(KC_a_APL_partners=ka.body_pre.nunique(), APL_a_KC_partners=ak.body_post.nunique(), sin_KC_a_APL=int(ka.weight.sum()), sin_APL_a_KC=int(ak.weight.sum()))
km = sub[(sub.cpre == "Kenyon_Cell") & (sub.cpost == "MBON")]; kms = km[km.weight >= 5]
R["KC_MBON_aristas"] = len(km); R["KC_MBON_ge5_sinapsis"] = int(kms.weight.sum()); R["KC_MBON_ge5_aristas"] = len(kms)
kms = kms.assign(kt=typ.reindex(kms.body_pre).values, mt=typ.reindex(kms.body_post).values)
bykt = kms.groupby("kt").weight.sum().sort_values(ascending=False); R["KC_MBON_ge5_por_tipo_KC"] = (bykt / bykt.sum()).round(4).head(5).to_dict()
g = kms[kms.kt == "KCg-m"].groupby("mt").weight.sum().sort_values(ascending=False); R["KCg-m_a_MBON_top"] = g.head(5).to_dict(); R["KCg-m_top4_frac"] = float(g.head(4).sum() / g.sum())
allm = kms.groupby("mt").weight.sum().sort_values(ascending=False); R["MBON_top4_frac_de_todo_KC_MBON_fuerte"] = float(allm.head(4).sum() / allm.sum()); R["MBON_top4"] = allm.head(4).to_dict()
R["n_tipos_KC_en_mapa"] = kms.kt.nunique(); R["n_tipos_MBON_en_mapa"] = kms.mt.nunique(); R["mapa_ge5_sinapsis"] = int(kms.weight.sum())
dm = sub[(sub.cpre == "DAN") & (sub.cpost == "MBON") & (sub.weight >= 5)]; R["DAN_MBON_ge5_sinapsis"] = int(dm.weight.sum())
t = dm.groupby(["tpre", "tpost"]).weight.sum().sort_values(ascending=False).head(5); R["DAN_MBON_top"] = {f"{a}->{b}": int(v) for (a, b), v in t.items()}
dk = sub[(sub.cpre == "DAN") & (sub.cpost == "Kenyon_Cell")]; R["DAN_KC"] = dict(aristas=len(dk), ge5=int((dk.weight >= 5).sum()), mediana=float(dk.weight.median()))
# --- solapamiento de pares de KC
kcs = np.array(sorted(deg.index)); pns = np.array(sorted(pk.body_pre.unique()))
ki = {b: i for i, b in enumerate(kcs)}; pi = {b: i for i, b in enumerate(pns)}
rows = pk.body_post.map(ki).values; cols = pk.body_pre.map(pi).values
M = sp.csr_matrix((np.ones(len(rows)), (rows, cols)), shape=(len(kcs), len(pns))); M.data[:] = 1
def pair_stats(M):
    n = M.shape[0]; tot = n * (n - 1) / 2; shared = 0.0; anyshare = 0; B = M @ M.T
    B = sp.triu(B, k=1).tocsr(); shared = B.data.sum(); anyshare = (B.data > 0).sum()
    return shared / tot, anyshare / tot
R["pares_observado(media, frac>=1)"] = pair_stats(M)
# nulos: (a) intercambios ignorando lado (como casa-conectoma), (b) intercambios que respetan hemisferio (KC y PN del mismo lado)
rng = np.random.default_rng(1)
edges = np.column_stack([rows, cols]); ks = A.somaSide.reindex(kcs).values; ps = A.somaSide.reindex(pns).values
def swap(edges, nswap, same_side):
    e = edges.copy(); E = len(e); seen = set(map(tuple, e.tolist())); done = 0
    for _ in range(nswap):
        i, j = rng.integers(0, E, 2)
        k1, p1 = e[i]; k2, p2 = e[j]
        if k1 == k2 or p1 == p2 or (k1, p2) in seen or (k2, p1) in seen: continue
        if same_side and not (ks[k1] == ps[p2] and ks[k2] == ps[p1]): continue
        seen.discard((k1, p1)); seen.discard((k2, p2)); seen.add((k1, p2)); seen.add((k2, p1)); e[i] = (k1, p2); e[j] = (k2, p1); done += 1
    return e
for nombre, same in (("nulo_grados_ignora_lado", False), ("nulo_grados_respeta_lado", True)):
    fr = []
    for _ in range(3):
        e2 = swap(edges, 20 * len(edges), same)
        M2 = sp.csr_matrix((np.ones(len(e2)), (e2[:, 0], e2[:, 1])), shape=M.shape); fr.append(pair_stats(M2)[1])
    R[nombre + "_frac_pares"] = (float(np.mean(fr)), float(np.std(fr)))
# modelo uniforme: cada KC elige PN al azar con su grado
uni = [rng.choice(len(pns), size=int(d), replace=False) for d in deg.reindex(kcs).values]
M3 = sp.csr_matrix((np.ones(sum(map(len, uni))), (np.repeat(np.arange(len(kcs)), [len(u) for u in uni]), np.concatenate(uni))), shape=M.shape)
R["nulo_uniforme_frac_pares"] = pair_stats(M3)[1]
F = lambda x: float(x)
check("KC total", len(KC), 4064); check("KC izq", R["KC"][1].get("L"), 2019); check("KC der", R["KC"][1].get("R"), 2045)
check("APL", len(APL), 2); check("KC<->APL socios (ambos sentidos)", min(R["APL"]["KC_a_APL_partners"], R["APL"]["APL_a_KC_partners"]), 4063)
check("MBON", R["MBON"][0], 97); check("MBON tipos", R["MBON"][1], 37); check("MBON ACh", R["nt_consensus_MBON"].get("acetylcholine"), 50); check("MBON glu", R["nt_consensus_MBON"].get("glutamate"), 26); check("MBON GABA", R["nt_consensus_MBON"].get("gaba"), 21)
check("DAN", R["DAN"][0], 340); check("DAN tipos", R["DAN"][1], 27); check("DAN tipos PAM", R["DAN_tipos_PAM_PPL"][0], 15); check("DAN tipos PPL", R["DAN_tipos_PAM_PPL"][1], 12); check("DAN dopaminergicas (consensus)", R["nt_consensus_DAN"].get("dopamine"), 338)
check("PN->KC mediana PN por KC", R["PN_por_KC"]["mediana"], 6); check("PN->KC fraccion exactamente 6", R["PN_por_KC"]["frac6"], 0.19, 0.005); check("PN->KC fraccion 4-8", R["PN_por_KC"]["frac4_8"], 0.80, 0.005); check("PN->KC max", R["PN_por_KC"]["max"], 39)
check("sinapsis/arista mediana", R["sinapsis_por_arista"]["mediana"], 16); check("sinapsis/arista p10", R["sinapsis_por_arista"]["p10_p90"][0], 4); check("sinapsis/arista p90", R["sinapsis_por_arista"]["p10_p90"][1], 31); check("sinapsis/arista max", R["sinapsis_por_arista"]["max"], 89)
check("KC->KC aristas", R["KC_KC"]["aristas"], 642933); check("KC->KC >=5", R["KC_KC"]["ge5"], 33247); check("KC->KC frac>=5", R["KC_KC"]["frac_ge5"], 0.05, 0.005)
check("PN->KC sinapsis ACh", R["PN_KC_sinapsis_por_NT_consensus"]["acetylcholine"], 390321); check("PN->KC sinapsis total", R["PN_KC_sinapsis_total"], 390928); check("PN->KC % ACh", 100 * 390321 / R["PN_KC_sinapsis_total"], 99.8, 0.05)
check("ALPN GABA (consensus)", R["nt_consensus_ALPN"].get("gaba"), 209); check("ALPN total", len(PN), 686)
check("KC->MBON >=5 sinapsis (mapa)", R["KC_MBON_ge5_sinapsis"], 402850); check("tipos KC en mapa", R["n_tipos_KC_en_mapa"], 14); check("tipos MBON en mapa", R["n_tipos_MBON_en_mapa"], 36)
check("KCg-m % de KC->MBON fuerte", 100 * R["KC_MBON_ge5_por_tipo_KC"]["KCg-m"], 41, 0.5); check("KCg-m -> 4 MBON %", 100 * R["KCg-m_top4_frac"], 74, 0.5); check("4 MBON % de KC->MBON fuerte", 100 * R["MBON_top4_frac_de_todo_KC_MBON_fuerte"], 44, 0.5)
check("KCg-m->MBON09", R["KCg-m_a_MBON_top"]["MBON09"], 37313); check("KCg-m->MBON01", R["KCg-m_a_MBON_top"]["MBON01"], 30635)
check("DAN->MBON >=5 sinapsis", R["DAN_MBON_ge5_sinapsis"], 36583); check("DAN->KC aristas", R["DAN_KC"]["aristas"], 129113); check("DAN->KC >=5", R["DAN_KC"]["ge5"], 5624)
check("fraccion pares con PN comun, observado", R["pares_observado(media, frac>=1)"][1], 0.205, 0.001); check("media PN compartidas", R["pares_observado(media, frac>=1)"][0], 0.256, 0.001)
check("nulo grados (ignora hemisferio), como declarado", R["nulo_grados_ignora_lado_frac_pares"][0], 0.228, 0.001); check("nulo uniforme", R["nulo_uniforme_frac_pares"], 0.106, 0.002)
check("NULO QUE RESPETA HEMISFERIO vs observado [README concluye 'menos que el azar']", R["nulo_grados_respeta_lado_frac_pares"][0], R["pares_observado(media, frac>=1)"][1], 0.002, nota="<- si CONFIRMADA, la diferencia 0,205 vs 0,228 es un artefacto de ignorar el hemisferio")
check("aristas PN->KC mismo hemisferio", R["PN_KC_aristas_mismo_lado"], 0.98, 0.005)
rc = resumen()
print(json.dumps(R, indent=1, default=lambda o: o.item() if hasattr(o, "item") else str(o)))
if len(sys.argv) > 2: json.dump(R, open(sys.argv[2], "w"), indent=1, default=lambda o: o.item() if hasattr(o, "item") else str(o))

sys.exit(1 if rc else 0)
