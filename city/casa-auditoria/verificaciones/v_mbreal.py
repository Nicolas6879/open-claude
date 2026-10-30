"""Auditor: casa-mb-real (en curso): contrasta out/anatomy.json (n y neurotransmisor por tipo de MBON) con los feather crudos."""
import sys, json, pandas as pd, pyarrow.feather as f
D = sys.argv[1].rstrip("/") + "/"; casa = sys.argv[2]
A = f.read_table(D + "body-annotations-male-cns-v1.0-minconf-0.5.feather", columns=["bodyId", "type", "class"]).to_pandas().set_index("bodyId")
NT = f.read_table(D + "body-neurotransmitters-male-cns-v1.0.feather", columns=["body", "consensus_nt"]).to_pandas().set_index("body")
m = A[A["class"] == "MBON"].copy(); m["nt"] = NT.reindex(m.index)["consensus_nt"].values
g = m.groupby("type").agg(n=("nt", "size"), nts=("nt", lambda s: dict(s.value_counts())))
an = json.load(open(casa + "/out/anatomy.json"))["MBON_tipos"]
bad = 0
for t, v in an.items():
    if t not in g.index: print("tipo ausente en datos:", t); bad += 1; continue
    r = g.loc[t]; top = max(r.nts, key=r.nts.get)
    if r.n != v["n"] or top != v["nt"]: print("DISCREPA", t, "declarado", v["n"], v["nt"], "datos", r.n, r.nts); bad += 1
print("tipos MBON en anatomy.json:", len(an), "| en datos:", len(g), "| discrepancias:", bad)
print("tipos de datos no recogidos en anatomy.json:", sorted(set(g.index) - set(an)))
mixed = {t: dict(r.nts) for t, r in g.iterrows() if len(r.nts) > 1}; print("tipos con NT mixto:", mixed)
sg = {"glutamate": -1, "gaba": 1, "acetylcholine": 1}
print("valencia por NT (Aso 2014b) aplicada a las 97 neuronas: n evitacion", int((m.nt == "glutamate").sum()), "n atraccion", int(m.nt.isin(["gaba", "acetylcholine"]).sum()), "otros", int((~m.nt.isin(sg)).sum()))
