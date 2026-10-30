"""Red LIF con la conectividad REAL de MaleCNS v1.0 (PN -> KC -> APL -> KC), comparada con controles.

Mismos parametros de neurona que casa-mosca (LIF, tau_m 10 ms, umbral 1, reset 0, refractario 2 ms,
sinapsis exponencial tau 5 ms, dt 0.25 ms). Diferencias clave:
  * los pesos son sinapsis reales (n_syn por arista), no iguales;
  * el signo sale del neurotransmisor predicho del presinaptico (ACh +, GABA -);
  * hay APL reales (2) y KC->KC reales con >= 5 sinapsis (opcional).
Un unico factor de escala s se calibra UNA vez con la red real (KC activas ~5 %) y se usa igual en
todas las condiciones. No hay ajuste por condicion.

Uso: PYTHONDONTWRITEBYTECODE=1 python3 src/sim.py [--seeds 1,2] [--odors 8] [--export]
Salidas: out/sim_summary.json y, con --export, out/activity.json (formato de casa-mosca, datos REALES).
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
DT = 0.25          # ms
TAU_M = 10.0       # ms
TAU_SYN = 5.0      # ms
THR = 1.0
REFR = 2.0         # ms
B_PN = 0.8         # corriente de fondo de las PN (subumbral)
SIGMA = 0.05       # ruido de corriente (unidades de umbral)
T_TOTAL = 1200.0   # ms: 200 ms de reposo + 1000 ms de olor
T_ON = 200.0
N_CHAN = 12        # canales (glomerulos) activos por olor, como en casa-mosca
KC_ACTIVE_HZ = 5.0 # definicion de KC activa de casa-mosca (>= 5 Hz)


def build_network(ann, nt, pre, post, w, pn_list=None):
    """Devuelve dict con indices, pesos reales y listas de aristas para cada condicion."""
    cls = {b: v["cls"] for b, v in ann.items()}
    typ = {b: v["type"] for b, v in ann.items()}
    kc = sorted(b for b, v in ann.items() if v["cls"] == "Kenyon_Cell")
    apl = sorted(b for b, v in ann.items() if v["type"] == "APL")
    pk_mask = np.array([cls.get(int(p)) == "ALPN" and cls.get(int(q)) == "Kenyon_Cell" for p, q in zip(pre, post)])
    pn = sorted(set(pre[pk_mask].tolist()))
    idx = {}
    for i, b in enumerate(pn):
        idx[b] = i
    for i, b in enumerate(kc):
        idx[b] = len(pn) + i
    for i, b in enumerate(apl):
        idx[b] = len(pn) + len(kc) + i
    N = len(pn) + len(kc) + len(apl)
    return dict(N=N, pn=pn, kc=kc, apl=apl, idx=idx, cls=cls, typ=typ, pk_mask=pk_mask,
                pre=pre, post=post, w=w, nt=nt)


def make_weights(net, s, g, cond, rng):
    """Matriz densa W[pre, post] para una condicion. Signo por neurotransmisor del presinaptico.

    s: escala de sinapsis excitadoras y de APL->KC; g: escala de KC->APL (retroalimentacion) relativa a s.
    """
    idx, N = net["idx"], net["N"]
    pre, post, w, nt, cls, typ = net["pre"], net["post"], net["w"], net["nt"], net["cls"], net["typ"]
    W = np.zeros((N, N), dtype=np.float32)
    n_pn = len(net["pn"])
    pk = net["pk_mask"]
    pk_pre, pk_post, pk_w = pre[pk], post[pk], w[pk].astype(np.float64)
    if cond == "uniformW":
        pk_w = np.full_like(pk_w, pk_w.mean())
    if cond == "randTopo":
        pk_pre, pk_post, pk_w, _ = nulls.swap_null_weighted(pk_pre, pk_post, pk_w, 20 * len(pk_pre), rng)
    for p, q, x in zip(pk_pre.tolist(), pk_post.tolist(), pk_w.tolist()):
        W[idx[p], idx[q]] += s * x
    # KC -> APL y APL -> KC (APL reales; sin APL en 'noAPL')
    if cond != "noAPL":
        for p, q, x in zip(pre.tolist(), post.tolist(), w.tolist()):
            ip, iq = idx.get(p), idx.get(q)
            if ip is None or iq is None:
                continue
            if cls.get(p) == "Kenyon_Cell" and typ.get(q) == "APL":
                W[ip, iq] += g * s * x
            elif typ.get(p) == "APL" and cls.get(q) == "Kenyon_Cell":
                sign = -1.0 if nt.get(p) in ("gaba", "glutamate") else 1.0
                W[ip, iq] += sign * s * x
    if cond == "real+KCKC":
        for p, q, x in zip(pre.tolist(), post.tolist(), w.tolist()):
            if x >= 5 and cls.get(p) == "Kenyon_Cell" and cls.get(q) == "Kenyon_Cell":
                W[idx[p], idx[q]] += s * x
    return W


def odor_drive(net, rng):
    """Canal = glomerulo (token del tipo); PN multiglomerulares ('M') cada una es su propio canal."""
    pn, typ = net["pn"], net["typ"]
    chan = []
    for b in pn:
        t = typ.get(b) or ""
        tok = t.split("_")[0]
        chan.append(f"M:{b}" if tok in ("M", "") else tok)
    uniq = sorted(set(chan))
    chosen = set(rng.choice(uniq, size=min(N_CHAN, len(uniq)), replace=False).tolist())
    drive = np.zeros(len(pn), dtype=np.float32)
    amp = rng.uniform(0.3, 0.7, size=len(uniq))
    amp_map = dict(zip(uniq, amp))
    for i, c in enumerate(chan):
        if c in chosen:
            drive[i] = amp_map[c]
    return drive, sorted(chosen)


def run_trial(W, net, drive, rng, record=False):
    """Integra una prueba de T_TOTAL ms. Devuelve conteos de espigas en la ventana de olor (y opcional registro)."""
    N, n_pn = net["N"], len(net["pn"])
    V = np.zeros(N, dtype=np.float32)
    I = np.zeros(N, dtype=np.float32)
    refr = np.zeros(N, dtype=np.int32)
    ext = np.zeros(N, dtype=np.float32)
    ext[:n_pn] = B_PN
    decay = np.exp(-DT / TAU_SYN).astype(np.float32)
    refr_steps = int(round(REFR / DT))
    counts = np.zeros(N, dtype=np.int64)
    rec_t, rec_i = [], []
    nsteps = int(round(T_TOTAL / DT))
    on_step = int(round(T_ON / DT))
    dV_scale = DT / TAU_M
    noise_scale = SIGMA * np.sqrt(DT / TAU_M)
    for k in range(nsteps):
        t = k * DT
        cur = ext.copy()
        if t >= T_ON:
            cur[:n_pn] += drive
        V += dV_scale * (-V + I + cur) + noise_scale * rng.standard_normal(N).astype(np.float32)
        V[refr > 0] = 0.0
        refr[refr > 0] -= 1
        spk = np.nonzero(V >= THR)[0]
        if spk.size:
            V[spk] = 0.0
            refr[spk] = refr_steps
            I += W[spk].sum(axis=0)
            if t >= T_ON:
                counts[spk] += 1
            if record:
                rec_t.append(np.full(spk.size, t))
                rec_i.append(spk)
        I *= decay
    odor_s = (T_TOTAL - T_ON) / 1000.0
    rates = counts / odor_s
    if record:
        return rates, (np.concatenate(rec_t) if rec_t else np.array([]), np.concatenate(rec_i) if rec_i else np.array([], int))
    return rates, None


def summarize(rates_list, net):
    n_pn = len(net["pn"])
    kc_rates = np.array([r[n_pn:n_pn + len(net["kc"])] for r in rates_list])
    pn_rates = np.array([r[:n_pn] for r in rates_list])
    apl_rates = np.array([r[n_pn + len(net["kc"]):] for r in rates_list])
    active = kc_rates >= KC_ACTIVE_HZ
    frac = active.mean(axis=1)
    jac = []
    for i in range(len(rates_list)):
        for j in range(i + 1, len(rates_list)):
            a, b = active[i], active[j]
            u = np.logical_or(a, b).sum()
            jac.append(np.logical_and(a, b).sum() / u if u else 0.0)
    iu = np.triu_indices(len(rates_list), k=1)
    corr = np.nan_to_num(np.corrcoef(kc_rates)) if len(rates_list) >= 2 else np.zeros((1, 1))
    types = np.array([net["typ"].get(b) or "?" for b in net["kc"]])
    per_type = {}
    for t in sorted(set(types.tolist())):
        m = types == t
        if m.sum() >= 20:
            per_type[t] = round(float(active[:, m].mean()), 4)
    return {
        "KC_activas_frac_media": round(float(frac.mean()), 4),
        "KC_activas_frac_sd": round(float(frac.std()), 4),
        "KC_tasa_media_Hz": round(float(kc_rates.mean()), 3),
        "PN_tasa_media_Hz": round(float(pn_rates.mean()), 3),
        "APL_tasa_media_Hz": round(float(apl_rates.mean()), 3),
        "Jaccard_KC_activas_entre_olores_media": round(float(np.mean(jac)), 4) if jac else None,
        "correlacion_tasas_KC_entre_olores_media": round(float(corr[iu].mean()), 4) if len(iu[0]) else None,
        "KC_activas_frac_por_tipo_(>=20 KC)": per_type,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", default="1,2")
    ap.add_argument("--odors", type=int, default=8)
    ap.add_argument("--target", type=float, default=0.05, help="fraccion objetivo de KC activas para calibrar s")
    ap.add_argument("--export", action="store_true", help="escribe out/activity.json (red real, 3 olores)")
    ap.add_argument("--out", default=os.path.join(HERE, "out", "sim_summary.json"))
    a = ap.parse_args()
    seeds = [int(x) for x in a.seeds.split(",")]

    ann = cio.load_annotations()
    nt = cio.load_neurotransmitters()
    pre, post, w = cio.load_subcircuit(ann)
    net = build_network(ann, nt, pre, post, w)
    print(f"red: PN {len(net['pn'])}, KC {len(net['kc'])}, APL {len(net['apl'])}, N {net['N']}")

    # 1) calibracion (s, g) con la red real (sin KC->KC), olores de una semilla aparte (99)
    cal_rng = np.random.default_rng(99)
    n_pn, n_kc = len(net["pn"]), len(net["kc"])
    calib = []
    best = None
    for s in [0.05, 0.1, 0.2, 0.4]:
        for g in [0.003, 0.01, 0.03, 0.1]:
            W = make_weights(net, s, g, "real", cal_rng)
            rates = []
            for _ in range(4):
                drive, _ = odor_drive(net, cal_rng)
                r, _ = run_trial(W, net, drive, cal_rng)
                rates.append(r)
            R = np.array(rates)
            frac = float((R[:, n_pn:n_pn + n_kc] >= KC_ACTIVE_HZ).mean())
            kc_hz = float(R[:, n_pn:n_pn + n_kc].mean())
            apl_hz = float(R[:, n_pn + n_kc:].mean())
            calib.append({"s": s, "g_KC_APL": g, "KC_activas_frac": round(frac, 4),
                          "KC_tasa_media_Hz": round(kc_hz, 3), "APL_tasa_media_Hz": round(apl_hz, 2)})
            print(f"calibracion s={s} g={g}: KC activas {frac:.3f}, KC {kc_hz:.2f} Hz, APL {apl_hz:.1f} Hz")
            if best is None or abs(frac - a.target) < abs(best[2] - a.target):
                best = (s, g, frac)
    s_star, g_star = best[0], best[1]
    print(f"elegido s={s_star}, g={g_star} (KC activas {best[2]:.3f}, objetivo {a.target})")

    conds = ["real", "real+KCKC", "noAPL", "uniformW", "randTopo"]
    results = {}
    for cond in conds:
        rng_w = np.random.default_rng(1234)
        W = make_weights(net, s_star, g_star, cond, rng_w)
        allr = []
        for sd in seeds:
            rng = np.random.default_rng(sd)
            for _ in range(a.odors):
                drive, _ = odor_drive(net, rng)
                r, _ = run_trial(W, net, drive, rng)
                allr.append(r)
        results[cond] = summarize(allr, net)
        print(cond, json.dumps({k: v for k, v in results[cond].items() if k != "KC_activas_frac_por_tipo_(>=20 KC)"}, ensure_ascii=False))

    summary = {
        "descripcion": "Red LIF con conectividad real de MaleCNS v1.0 y controles (ver README)",
        "parametros": {"dt_ms": DT, "tau_m_ms": TAU_M, "tau_syn_ms": TAU_SYN, "umbral": THR, "refractario_ms": REFR,
                       "b_PN": B_PN, "sigma": SIGMA, "canales_por_olor": N_CHAN, "KC_activa_Hz": KC_ACTIVE_HZ,
                       "escala_s": s_star, "g_KC_APL": g_star, "seeds": seeds, "olores_por_semilla": a.odors},
        "calibracion": calib,
        "condiciones": results,
    }
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    with open(a.out, "w", encoding="utf-8") as fh:
        json.dump(summary, fh, ensure_ascii=False, indent=1)
        fh.write("\n")
    print("escrito:", a.out)

    if a.export:
        export_activity(net, make_weights(net, s_star, g_star, "real", np.random.default_rng(1234)), s_star, ann)


def export_activity(net, W, s, ann):
    rng = np.random.default_rng(1)
    spikes, stimuli, offset = [], [], 0.0
    ids = net["pn"] + net["kc"] + net["apl"]
    for k in range(3):
        drive, chosen = odor_drive(net, rng)
        _, (t, i) = run_trial(W, net, drive, rng, record=True)
        for tt, ii in zip((t + offset).tolist(), i.tolist()):
            spikes.append([round(tt, 1), int(ids[ii])])
        stimuli.append({"name": f"odor_{k + 1}", "t_start": round(offset + T_ON, 1), "t_end": round(offset + T_TOTAL, 1),
                        "canales": chosen})
        offset += T_TOTAL + 300.0
    coords = [ann[b]["soma"] for b in ids if ann[b]["soma"]]
    xs = np.array([c[0] for c in coords], float)
    ys = np.array([c[1] for c in coords], float)
    def norm(v, lo, hi):
        return float((v - lo) / (hi - lo)) if hi > lo else 0.5
    nx0, nx1, ny0, ny1 = xs.min(), xs.max(), ys.min(), ys.max()
    neurons = []
    for b in ids:
        c = ann[b]["soma"]
        tp = "PN" if b in set(net["pn"]) else ("KC" if ann[b]["cls"] == "Kenyon_Cell" else "APL")
        x = norm(c[0], nx0, nx1) if c else 0.5
        y = norm(c[1], ny0, ny1) if c else 0.5
        neurons.append({"id": int(b), "type": tp, "x": round(x, 4), "y": round(y, 4)})
    doc = {"meta": {"description": "Espigas de la red LIF con conectividad REAL de MaleCNS v1.0 (3 olores, semilla 1). "
                                  "Posiciones = coordenadas de soma reales normalizadas (vista x-y).",
                    "synthetic": False, "source": "MaleCNS v1.0 (CC-BY) flat-connectome, minconf 0.5 significant-only",
                    "seed": 1, "dt_ms": DT, "duration_ms": round(offset, 1), "escala_s": s,
                    "modelo": "LIF; pesos reales; signo por neurotransmisor; sin ajuste por neurona"},
           "neurons": neurons, "spikes": spikes, "stimuli": stimuli}
    p = os.path.join(HERE, "out", "activity.json")
    with open(p, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, ensure_ascii=False, separators=(",", ":"))
    print("escrito:", p, os.path.getsize(p), "bytes", len(spikes), "espigas")


if __name__ == "__main__":
    main()
