"""Auditor: comparador comun valor-recomputado vs valor-declarado. Imprime CONFIRMADA / DISCREPANTE y deja el recuento."""
RES = []
def check(nombre, valor, declarado, tol=None, rel=None, nota=""):
    tol = tol if tol is not None else (abs(declarado) * rel if rel is not None else 0.0)
    ok = abs(float(valor) - float(declarado)) <= tol + 1e-12
    print(f"[{'CONFIRMADA' if ok else 'DISCREPANTE'}] {nombre}: recomputado {float(valor):.5g} | declarado {float(declarado):.5g} | tolerancia {tol:.3g} {nota}".rstrip(), flush=True)
    RES.append(ok); return ok
def resumen():
    n = len(RES); c = sum(RES); print(f"RESUMEN: {c} confirmadas, {n - c} discrepantes de {n}", flush=True); return n - c
