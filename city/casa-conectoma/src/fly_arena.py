"""Mosca virtual en bucle cerrado sobre el SNC completo de MaleCNS v1.0.

Mundo: plano infinito, fuente de olor en el origen, c(x) = exp(-r / LAMBDA_MM).
Sensor: dos antenas separadas ANT_SEP_MM (izq. = +90 grados del rumbo). Cada ORN recibe
  entrada sensorial kappa * afinidad_glomerulo * c(antena de su lado). Lado de cada ORN = lado de
  sus PN de salida (las ORN no traen lado en las anotaciones).
Motor: cada CHUNK_MS se mide la tasa media de las DN de cada lado (filtro EMA, tau 100 ms).
  Giro: omega = K_T * [(R_izq - R_der) - sesgo(c_media)], con sesgo(c) = asimetria L-R medida con olor
  simetrico a varios niveles c (curva medida al inicio de cada proceso e interpolada). Positivo = giro a la
  izquierda (convencion a priori).
  Avance: v = V0 constante (modo 'const') o V0 * clip(R_tot / R_base, 0, 2) (modo 'dn').
Controles: 'direct' (sin cerebro: giro proporcional al gradiente bilateral) y 'randomwalk'.
"""
import numpy as np

LAMBDA_MM = 20.0
ANT_SEP_MM = 2.0
KAPPA_MV = 20.0   # mV de entrada a ORN con c = 1 (ver orn_drive)
C0 = 0.01         # concentracion de semisaturacion de la transduccion logaritmica
V0_MM_S = 8.0
K_T = 6.0
TAU_RATE_MS = 500.0  # v3: 100 ms daba giros sin direccion (ruido de red domina la senal)
CHUNK_MS = 10.0
SUCCESS_MM = 5.0
START_R = (30.0, 45.0)


def orn_drive(c):
    """Transduccion logaritmica (tipo Weber-Fechner): entrada en mV, normalizada a KAPPA_MV para c = 1.

    Motivo (ver LOG): con entrada lineal, a 30 mm del origen (c ~ 0.2 con lambda 20 mm) las ORN no llegaban
    al umbral y la mosca era ciega. Con log(1 + c / C0) la diferencia izquierda-derecha es ~ log(c_I / c_D).
    """
    return KAPPA_MV * np.log1p(np.asarray(c) / C0) / np.log1p(1.0 / C0)


class FlyWorld:
    """Carga/indices de sensores y motor sobre un Network ya construido."""

    def __init__(self, G, net):
        types, sides, supers = G["types"], G["sides"], G["superclasses"]
        ids = G["ids"]
        self.net = net
        orn = np.nonzero(np.char.startswith(types.astype(str), "ORN_"))[0]
        # lado de ORN: suma de sinapsis hacia PN (ALPN) izquierdas vs derechas
        alpn_side = np.where(np.char.startswith(G["classes"].astype(str), "ALPN"), sides, "")
        side_of = np.array(["" for _ in range(len(ids))], dtype=object)
        keep = []
        glom = []
        indptr, indices, syn = G["indptr"], G["indices"], G["syn"]
        for i in orn:
            s, e = indptr[i], indptr[i + 1]
            tg = indices[s:e]
            ws = syn[s:e]
            sl = alpn_side[tg]
            wl = ws[sl == "L"].sum()
            wr = ws[sl == "R"].sum()
            if wl == wr:
                continue
            keep.append(i)
            side_of[i] = "L" if wl > wr else "R"
            glom.append(types[i].split("_", 1)[1].split("_")[0])
        self.orn = np.array(keep, dtype=np.int64)
        self.orn_side = np.array([side_of[i] for i in keep])
        self.orn_glom = np.array(glom)
        # afinidades por glomerulo (fijas)
        uniq = sorted(set(glom))
        rng = np.random.default_rng(2024)
        aff = dict(zip(uniq, rng.uniform(0.3, 1.0, len(uniq))))
        self.orn_aff = np.array([aff[g] for g in glom])
        dn_all = np.nonzero(supers.astype(str) == "descending_neuron")[0]
        self.dn_L = np.array([i for i in dn_all if sides[i] == "L"], dtype=np.int64)
        self.dn_R = np.array([i for i in dn_all if sides[i] == "R"], dtype=np.int64)
        self.n_orn_L = int((self.orn_side == "L").sum())
        self.n_orn_R = int((self.orn_side == "R").sum())

    def concentration(self, x, y):
        r = np.hypot(x, y)
        return np.exp(-r / LAMBDA_MM)


def antenna_positions(x, y, th):
    lx = x + ANT_SEP_MM / 2 * np.cos(th + np.pi / 2)
    ly = y + ANT_SEP_MM / 2 * np.sin(th + np.pi / 2)
    rx = x + ANT_SEP_MM / 2 * np.cos(th - np.pi / 2)
    ry = y + ANT_SEP_MM / 2 * np.sin(th - np.pi / 2)
    return (lx, ly), (rx, ry)


BASELINE_LEVELS = (0.02, 0.1, 0.25, 0.6, 1.0)


def measure_baseline(world, levels=BASELINE_LEVELS, seed=12345, warm_ms=300.0, dur_ms=1000.0):
    """Sesgo L-R de la red con olor SIMETRICO a varios niveles de concentracion (una vez por proceso).

    Con olor simetrico, cualquier diferencia L-R es sesgo de la red (incluido el desequilibrio de lados de
    la reconstruccion), no gradiente. El sesgo depende del nivel (medido: +0.4 Hz a c=0.22 y -0.5 Hz a c=1),
    asi que se guarda una curva (niveles, sesgos) y en cada paso se interpola con la concentracion media.
    Devuelve (levels, offsets) como arrays.
    """
    net = getattr(world, "net", None)
    offs = []
    for lev in levels:
        rng = np.random.default_rng(seed)
        net.V[:] = rng.uniform(-52.0, -45.0, net.N)
        net.g[:] = 0.0
        net.refr[:] = 0
        net.counts[:] = 0
        net.alive[:] = 1
        net.ext[:] = 0.0
        net.ext[world.orn] = world.orn_aff * orn_drive(lev)
        net.advance(warm_ms)
        net.counts[:] = 0
        net.advance(dur_ms)
        c = net.counts.astype(float) / (dur_ms / 1000.0)
        offs.append(float(c[world.dn_L].mean() - c[world.dn_R].mean()))
    net.ext[:] = 0.0
    return np.asarray(levels, dtype=float), np.asarray(offs, dtype=float)


def run_trial(world, seed, mode="connectome", K_T=0.0, turn_sign=1.0, forward="const", off_idx=None,
              max_t_s=8.0, record_every=10, rate_base=None, baseline=(0.0, 0.0)):
    """Una prueba de quimiotaxis con la misma semilla para posicion inicial en todas las condiciones."""
    rng = np.random.default_rng(seed)
    r0 = rng.uniform(*START_R)
    a0 = rng.uniform(0, 2 * np.pi)
    x, y = r0 * np.cos(a0), r0 * np.sin(a0)
    th = rng.uniform(0, 2 * np.pi)
    net = getattr(world, "net", None)
    if mode == "connectome":
        net.V[:] = rng.uniform(-52.0, -45.0, net.N)
        net.g[:] = 0.0
        net.refr[:] = 0
        net.counts[:] = 0
        net.ext[:] = 0.0
        net.alive[:] = 1
        if off_idx is not None and len(off_idx):
            net.alive[off_idx] = 0
    t_ms = 0.0
    n_chunks = int(max_t_s * 1000 / CHUNK_MS)
    rL = rR = 0.0
    traj = []
    success = False
    t_success = None
    dn_L, dn_R = world.dn_L, world.dn_R
    alpha = CHUNK_MS / TAU_RATE_MS
    rng_walk = np.random.default_rng(seed + 7)
    omega_rw = 0.0
    orn, aff = world.orn, world.orn_aff
    side_L = world.orn_side == "L"
    dt = CHUNK_MS / 1000.0
    for k in range(n_chunks):
        (lx, ly), (rx, ry) = antenna_positions(x, y, th)
        cL = float(world.concentration(lx, ly))
        cR = float(world.concentration(rx, ry))
        if mode == "connectome":
            net.ext[:] = 0.0
            net.ext[orn] = orn_drive(np.where(side_L, cL, cR)) * aff
            net.advance(CHUNK_MS)
            cnt = net.counts
            rate_L = cnt[dn_L].sum() / (len(dn_L) * dt)
            rate_R = cnt[dn_R].sum() / (len(dn_R) * dt)
            cnt[:] = 0
            rL = (1 - alpha) * rL + alpha * rate_L
            rR = (1 - alpha) * rR + alpha * rate_R
            cbar = 0.5 * (cL + cR)
            T = (rL - rR) - float(np.interp(cbar, baseline[0], baseline[1]))
            omega = turn_sign * K_T * T
        elif mode == "direct":
            omega = turn_sign * K_T * (cL - cR) / (cL + cR + 1e-9)
        elif mode == "randomwalk":
            omega_rw = 0.9 * omega_rw + 0.1 * rng_walk.normal(0, 6.0)
            omega = omega_rw
        else:
            raise ValueError(mode)
        if forward == "dn" and rate_base and mode == "connectome":
            v = V0_MM_S * float(np.clip((rL + rR) / rate_base, 0, 2))
        else:
            v = V0_MM_S
        th += omega * dt
        x += v * np.cos(th) * dt
        y += v * np.sin(th) * dt
        t_ms += CHUNK_MS
        if k % record_every == 0:
            traj.append((round(t_ms, 1), round(x, 2), round(y, 2), round(th, 3), round(rL, 2), round(rR, 2)))
        if np.hypot(x, y) < SUCCESS_MM:
            success = True
            t_success = t_ms
            break
    dist = float(np.hypot(x, y))
    return dict(seed=seed, success=success, t_s=(t_success or t_ms) / 1000.0, final_dist_mm=round(dist, 2),
                start_r_mm=round(float(r0), 2), traj=traj)
