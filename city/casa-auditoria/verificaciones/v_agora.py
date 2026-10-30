"""Auditor: reimplementacion INDEPENDIENTE del AMM de casa-agora (solo desde la especificacion del README),
con los mismos flujos aleatorios (stdlib random, mismas semillas) para comparar cifra a cifra.
No importa nada de casa-agora. Uso: python v_agora.py [N_EVAL=500]"""
import math, random, statistics as st, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

N = int(sys.argv[1]) if len(sys.argv) > 1 else 500
PASOS, P0, CX, CY = 720, 100.0, 1000.0, 100000.0
H = 8760

def precios(sigma, seed, lam=0.0, ss=0.0):
    r = random.Random(seed); dt = 1 / H; ps = lam * dt; p = P0; out = [p]
    for _ in range(PASOS):
        z = r.gauss(0, 1); u = r.random(); j = r.gauss(0, 1)
        ret = -0.5 * sigma * sigma * dt + sigma * math.sqrt(dt) * z
        if u < ps: ret += ss * j
        p *= math.exp(ret); out.append(p)
    return out

def run(ps, fee, nseed, guard=None, tam=0.002, mkt=4.0):
    """pool = (x,y) con acciones; Tendera y mercado. guard=(salida, factor) o None."""
    X, Y = CX * mkt, CY * mkt
    S_mkt = math.sqrt(X * Y)
    # Tendera entra proporcional: su cuota = CX/X -> acciones
    shares_T = S_mkt * min(CX / X, CY / Y)
    X += CX; Y += CY; S = S_mkt + shares_T
    cart = [0.0, 0.0]; inpool = True
    r = random.Random(nseed); fees = 0.0
    var = None; n = 0
    lam = 1 - 2 / 169; salida = entrada = None
    if guard: salida, entrada = guard[0], guard[0] * guard[1]
    pprev = ps[0]; vf = CX * P0 + CY
    for p in ps[1:]:
        frac = shares_T / S
        u = r.random(); lado = r.random(); e = r.expovariate(1.0)
        ev = []
        if u < 0.5:
            if lado < 0.5:
                dy = Y * tam * e; dx = X * (dy * (1 - fee)) / (Y + dy * (1 - fee)); Y += dy; X -= dx; ev.append(dy * fee)
            else:
                dx = X * tam * e; dy = Y * (dx * (1 - fee)) / (X + dx * (1 - fee)); X += dx; Y -= dy; ev.append(dx * fee * p)
        pp = Y / X
        if pp < p * (1 - fee):
            yb = math.sqrt((1 - fee) * X * Y * p); yin = (yb - Y) / (1 - fee)
            dx = X * (yin * (1 - fee)) / (Y + yin * (1 - fee)); Y += yin; X -= dx; ev.append(yin * fee)
        elif pp > p / (1 - fee):
            xb = math.sqrt((1 - fee) * X * Y / p); xin = (xb - X) / (1 - fee)
            dy = Y * (xin * (1 - fee)) / (X + xin * (1 - fee)); X += xin; Y -= dy; ev.append(xin * fee * p)
        fees += frac * sum(ev)
        if guard:
            rl = math.log(p / pprev); r2 = rl * rl
            var = r2 if var is None else lam * var + (1 - lam) * r2; n += 1
            if n >= 24:
                sh = math.sqrt(var * H)
                if inpool and sh > salida:
                    dx = shares_T * X / S; dy = shares_T * Y / S
                    X -= dx; Y -= dy; S -= shares_T; shares_T = 0.0; cart[0] += dx; cart[1] += dy; inpool = False
                elif (not inpool) and sh < entrada and cart[0] > 0 and cart[1] > 0:
                    s = min(cart[0] * S / X, cart[1] * S / Y)
                    ux = s * X / S; uy = s * Y / S
                    X += ux; Y += uy; S += s; shares_T += s; cart[0] -= ux; cart[1] -= uy; inpool = True
        pprev = p
        vf = (shares_T / S) * (X * p + Y) + cart[0] * p + cart[1]
    return vf, CX * pprev + CY, fees

def resumen(nombre, sigma, fee, guard=None, lam=0.0, ss=0.0, tam=0.002, seeds=None):
    seeds = seeds if seeds is not None else range(N)
    d, vf_, f_ = [], [], []
    for s in seeds:
        ps = precios(sigma, s, lam, ss)
        vf, h, fe = run(ps, fee, s + 10_000_000, guard, tam)
        d.append(vf - h); vf_.append(vf); f_.append(fe)
    m = st.fmean(d); se = 1.96 * st.stdev(d) / math.sqrt(len(d))
    il = st.fmean(a - b for a, b in zip(d, f_))
    print(f"{nombre:34s} LP-HODL {m:9.1f} +-{se:6.1f} | fees {st.fmean(f_):7.1f} | IL {il:8.1f} | P(>HODL) {sum(x > 0 for x in d)/len(d):.3f} | vf medio {st.fmean(vf_):10.0f} med {st.median(vf_):10.0f}", flush=True)
    return m, se

if __name__ == "__main__":
    from veredicto import check, resumen as resumen_v
    print("N =", N)
    # (nombre, sigma, fee, guard, lam, ss, tam, declarado LP-HODL, declarado +-)
    casos = [("GBM60 pasivo", 0.6, 0.003, None, 0, 0, 0.002, -181, 111), ("GBM60 guardia 30%/x0.5", 0.6, 0.003, (0.3, 0.5), 0, 0, 0.002, -29, 23),
             ("saltos pasivo", 0.4, 0.003, None, 60, 0.05, 0.002, -161, 101), ("saltos guardia", 0.4, 0.003, (0.3, 0.5), 60, 0.05, 0.002, -7, 24)]
    sens = {(0.2, 0.0005): -5, (0.2, 0.003): 297, (0.2, 0.01): 900, (0.4, 0.0005): -247, (0.4, 0.003): 132, (0.4, 0.01): 807, (0.6, 0.0005): -667,
            (0.6, 0.003): -181, (0.6, 0.01): 618, (0.8, 0.0005): -1266, (0.8, 0.003): -660, (0.8, 0.01): 312, (1.0, 0.0005): -2047, (1.0, 0.003): -1313, (1.0, 0.01): -130}
    for nom, sg, fee, g, lam, ss, tam, dm, dse in casos:
        m, se = resumen(nom, sg, fee, guard=g, lam=lam, ss=ss, tam=tam)
        check(nom + " LP-HODL", m, dm, 0.6); check(nom + " +-95%", se, dse, 0.6)
    for (v, f), dm in sens.items():
        m, se = resumen(f"sens vol{v} fee{f}", v, f); check(f"sensibilidad vol {v} fee {f}", m, dm, 0.6)
    for v, dm in zip((0.2, 0.4, 0.6, 0.8, 1.0), (268, 6, -29, -60, -103)):
        m, _ = resumen(f"guardia vol{v}", v, 0.003, guard=(0.3, 0.5)); check(f"Tendera guardia vol {v}", m, dm, 0.6)
    for v, dd in ((0.4, (-39, 132, 517)), (0.6, (-343, -181, 187))):
        for k, dm in zip((0.5, 1.0, 2.0), dd):
            m, _ = resumen(f"ruido x{k} vol{v}", v, 0.003, tam=0.002 * k); check(f"ruido x{k} vol {v}", m, dm, 0.6)
    import sys as _s; _s.exit(1 if resumen_v() else 0)
