"""Auditor: compara la distribucion de PN por KC que usa la app de Mosquita (KDIST en app/index.html) con la medida en el
conectoma (v_conectoma.py -> JSON). Uso: python v_empresa_dist.py <index.html> <conectoma_mio.json>"""
import re, sys, json, numpy as np
html = open(sys.argv[1], encoding="utf-8").read()
kd = re.search(r"var KDIST=(\[\[.*?\]\]);", html).group(1); kd = json.loads(re.sub(r"(?<![0-9])\.(\d)", r"0.\1", kd))
ks = np.array([k for k, _ in kd]); ps = np.array([p for _, p in kd]); print("KDIST suma", ps.sum().round(3), "media", (ks * ps).sum().round(2), "mediana", ks[np.searchsorted(np.cumsum(ps), 0.5)], "P(k=6)", ps[ks == 6][0])
R = json.load(open(sys.argv[2])); h = R["hist_PN_por_KC_(grado: fraccion de KC con PN)"]
print("real: media %.2f mediana %.1f P(k=6) %.3f P(k<4) %.3f" % (R["PN_por_KC"]["media"], R["PN_por_KC"]["mediana"], R["PN_por_KC"]["frac6"], R["frac_KC_con_PN_<4"]))
print("k:    ", " ".join("%5d" % k for k in range(1, 14)))
print("real: ", " ".join("%5.2f" % h.get(str(k), 0) for k in range(1, 14)))
print("app:  ", " ".join("%5.2f" % (ps[ks == k][0] if k in ks else 0) for k in range(1, 14)))
print("syn/arista app: lognormal mediana 16 sigma .6 -> p10 %.1f p90 %.1f | real p10-p90 %s" % (16 * np.exp(-1.2816 * .6), 16 * np.exp(1.2816 * .6), R["sinapsis_por_arista"]["p10_p90"]))
