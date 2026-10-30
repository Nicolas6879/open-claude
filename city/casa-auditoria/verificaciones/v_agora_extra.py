"""Auditor: comprobaciones adicionales de casa-agora (afirmaciones del README que el codigo no produce)."""
import csv, math, statistics as st, sys, os
sys.argv = [sys.argv[0], "500"] + sys.argv[1:]
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import v_agora as A
casa = sys.argv[2] if len(sys.argv) > 2 else "/home/user/open-claude/city/casa-agora"
# 1. Volatilidad MSFT
rows = list(csv.DictReader(open(os.path.join(casa, "data", "msft_mensual_2000_2010.csv"))))
pr = [float(r["price"]) for r in rows]; rets = [math.log(b / a) for a, b in zip(pr, pr[1:])]
print("MSFT filas", len(pr), "primera", rows[0], "ultima", rows[-1], "vol anual", round(st.stdev(rets) * math.sqrt(12), 4))
# 2. Descomposicion de comisiones ruido vs arbitraje (LP pasivo, GBM)
print("-- fees por vol con ruido x1, x0 (solo arbitraje) y x2")
for v in (0.2, 0.4, 0.6, 0.8, 1.0):
    out = []
    for tam in (0.0, 0.002, 0.004):
        f = [A.run(A.precios(v, s), 0.003, s + 10_000_000, None, tam)[2] for s in range(300)]
        out.append(round(st.fmean(f), 1))
    print(f"vol {v}: fees arb-only {out[0]}, base {out[1]}, ruido x2 {out[2]}  => parte ruido base {out[1]-out[0]:.0f}")
# 3. Umbrales de la guardia no probados en la rejilla (10, 20%), y tiempo dentro del pool
print("-- guardia con umbrales fuera de la rejilla (GBM60, 500 trayectorias)")
for u in (0.1, 0.2, 0.3, 0.4, 0.5, 0.7, 0.9):
    A.resumen(f"guardia salida {u:.0%} x0.5", 0.6, 0.003, guard=(u, 0.5))
# 4. Identidad IL vs formula clasica (60 trayectorias, 0..59), error vs capital 200000
errs = []
for s in range(60):
    ps = A.precios(0.6, s); vf, h, fe = A.run(ps, 0.003, s + 10_000_000)
    r = ps[-1] / ps[0]; il_formula = h * (2 * math.sqrt(r) / (1 + r) - 1)   # IL x valor HODL final (como el test de la casa)
    errs.append(abs((vf - h - fe) - il_formula))
print("IL residuo vs formula clasica (x HODL final): error max", round(max(errs), 1), "media", round(st.fmean(errs), 1), "(declarado: max ~75)")
# media del residuo vs media de la formula en 500 trayectorias (declarado: -803 vs -801)
d=[];fm=[]
for s in range(500):
    ps = A.precios(0.6, s); vf, h, fe = A.run(ps, 0.003, s + 10_000_000); r = ps[-1]/ps[0]
    d.append(vf-h-fe); fm.append(h*(2*math.sqrt(r)/(1+r)-1))
print("media residuo", round(st.fmean(d),1), "media formula", round(st.fmean(fm),1))
# 5. La guardia en GBM60: el README dice que -29 +- 23 es "estadisticamente cero"
m, se = A.resumen("guardia 30%/x0.5 GBM60 (500)", 0.6, 0.003, guard=(0.3, 0.5))
print("IC95 de LP-HODL guardia GBM60: [%.1f, %.1f] -> %s el 0" % (m - se, m + se, "EXCLUYE" if (m + se) < 0 or (m - se) > 0 else "incluye"))
m2, se2 = A.resumen("guardia saltos (500)", 0.4, 0.003, guard=(0.3, 0.5), lam=60, ss=0.05)
print("IC95 de LP-HODL guardia saltos: [%.1f, %.1f] -> %s el 0" % (m2 - se2, m2 + se2, "EXCLUYE" if (m2 + se2) < 0 or (m2 - se2) > 0 else "incluye"))
# P(>HODL) 52,4% y 54,6% frente a 50%: z binomial con n=500
for p in (0.524, 0.546):
    z = (p - 0.5) / math.sqrt(0.25 / 500); print("P(>HODL)=%.3f: z=%.2f frente a 0,5 (p bilateral aprox %.3f)" % (p, z, math.erfc(abs(z) / math.sqrt(2))))
