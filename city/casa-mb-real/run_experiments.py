"""Orquestador de experimentos.  Uso:  python run_experiments.py <grupo> [--seeds N] [--procs P]

Grupos: main, controls, sweeps, lesions_apl, lesions_dan, lesions_mbon, backward, robust
Cada grupo escribe out/raw/<grupo>.npz (conteos de espigas por MBON, uint16) y el resumen se hace en summarize.py.
"""
import argparse
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "src"))
import numpy as np

import experiments as ex
import mbdata as md
import network as nw

ALL_TYPES = None


def all_dan_types():
    nodes, _ = md.load()
    return sorted(set(nodes["type"][nodes["cls"] == md.DAN]))


def type_stims():
    return ["PAM", "PPL1"] + ["type:" + t for t in all_dan_types()]


def group(name):
    if name == "main":
        return [ex.Cond("real", stims=tuple(type_stims()))], 30
    if name == "controls":
        st = tuple(["PAM", "PPL1"] + ["type:" + t for t in all_dan_types() if t.startswith(("PAM", "PPL1"))])
        # el control 'real' son las semillas 1..12 de `main` (mismos olores); aqui solo los controles aleatorizados
        C = [
            ex.Cond("comp_shuf_type", params={"g_mode": "shuf_type"}, stims=st),
            ex.Cond("kcmbon_global", rewire={"kcmbon": "global"}, stims=st),
            ex.Cond("kcmbon_lobe", rewire={"kcmbon": "lobe"}, stims=st),
            ex.Cond("kcmbon_uniform", params={"kc_mbon_uniform": True}, stims=st),
            ex.Cond("comp_shuf_mbon", params={"g_mode": "shuf_mbon"}, stims=st),
            ex.Cond("pnkc_global", rewire={"pnkc": True}, stims=st),
            ex.Cond("pnkc_uniform", params={"pn_kc_uniform": True}, stims=st),
            ex.Cond("comp_flat", params={"g_mode": "flat"}, stims=st),
            ex.Cond("comp_none", params={"g_mode": "none"}, stims=st),
        ]
        return C, 12
    if name == "sweeps":
        C = []
        for eta in (0.3, 1.0, 2.3, 6.0, 15.0):
            for th in (0.1, 0.3, 1.0, 2.0):
                C.append(ex.Cond(f"eta{eta}_th{th}", eta=eta, theta=th, stims=("PAM", "PPL1", "type:PPL101", "type:PAM08")))
        for npairs in (2, 4):
            C.append(ex.Cond(f"pairs{npairs}", n_pairs=npairs, stims=("PAM", "PPL1", "type:PPL101", "type:PAM08")))
        return C, 12
    if name == "lesions_apl":
        return [ex.Cond("apl_intact", stims=("PAM", "PPL1", "type:PPL101")),
                ex.Cond("apl_silenced", silence={"apl": True}, stims=("PAM", "PPL1", "type:PPL101"))], 24
    if name == "lesions_dan":
        nodes, _ = md.load()
        pam = ["PAM-minus:" + t for t in all_dan_types() if t.startswith("PAM")]
        ppl = ["PPL1-minus:" + t for t in all_dan_types() if t.startswith("PPL1")]
        return [ex.Cond("dan_leave_one_out", stims=tuple(["PAM", "PPL1"] + pam + ppl))], 16
    if name == "lesions_mbon":
        nodes, _ = md.load()
        mt = sorted(set(nodes["type"][nodes["cls"] == md.MBON]))
        return [ex.Cond("mbon_intact", stims=("PAM", "PPL1"))] + [
            ex.Cond("mbon_sil_" + t, silence={"mbon_types": [t]}, stims=("PAM", "PPL1")) for t in mt], 10
    if name == "lesions_apl2":
        st = ("PAM", "PPL1", "type:PPL101")
        return [ex.Cond("apl_silenced_S2500", params={"S_mbon": 2500.0}, silence={"apl": True}, stims=st),
                ex.Cond("apl_silenced_S4000", params={"S_mbon": 4000.0}, silence={"apl": True}, stims=st)], 24
    if name == "backward":
        return [ex.Cond("forward", stims=("PAM", "PPL1", "type:PPL101")),
                ex.Cond("backward", us_mode="backward", stims=("PAM", "PPL1", "type:PPL101"))], 24
    if name == "ntsource":
        st = ("PAM", "PPL1", "type:PPL101", "type:PAM08")
        return [ex.Cond("consensus", stims=st), ex.Cond("predicted", params={"nt_source": "predicted"}, stims=st)], 12
    if name == "robust":
        st = ("PAM", "PPL1", "type:PPL101", "type:PAM08")
        C = [ex.Cond("base", stims=st)]
        for w in (3, 5):
            C.append(ex.Cond(f"wmin_kcmbon{w}", params={"wmin_kcmbon": w}, stims=st))
        C.append(ex.Cond("norm_N0", params={"norm": "N0"}, stims=st))
        for sp in (0.4, 0.62):
            C.append(ex.Cond(f"s_pn{sp}", params={"s_pn": sp}, stims=st))
        for nch in (6, 24):
            C.append(ex.Cond(f"channels{nch}", params={"n_channels_active": nch}, stims=st))
        for g in (0.02, 0.2, 0.5):
            C.append(ex.Cond(f"gthr{g}", params={"gthr": g}, stims=st))
        for sm in (4000.0, 12000.0):
            C.append(ex.Cond(f"S_mbon{sm:.0f}", params={"S_mbon": sm}, stims=st))
        C.append(ex.Cond("tau_e250", params={"tau_e_ms": 250.0}, stims=st))
        C.append(ex.Cond("tau_e1000", params={"tau_e_ms": 1000.0}, stims=st))
        C.append(ex.Cond("us_hz20", params={"dan_us_hz": 20.0}, stims=st))
        return C, 12
    if name == "recurrent":
        st = ("PAM", "PPL1", "type:PPL101", "type:PAM08")
        C = [ex.Cond("base", stims=st)]
        for sm in (0.02, 0.05, 0.15, 0.5):
            C.append(ex.Cond(f"mm{sm}_real", params={"extra": ("MBON_MBON",), "s_mbonmbon": sm}, stims=st))
            C.append(ex.Cond(f"mm{sm}_shuf", params={"extra": ("MBON_MBON",), "s_mbonmbon": sm}, rewire={"mbonmbon": True}, stims=st))
        for sa in (0.05, 0.2):
            C.append(ex.Cond(f"aplmbon{sa}", params={"extra": ("APL_MBON",), "s_aplmbon": sa}, stims=st))
        return C, 12
    if name == "extra":
        st = ("PAM", "PPL1", "type:PPL101", "type:PAM08")
        C = [ex.Cond("base", stims=st)]
        for e in ("PN_APL", "APL_MBON", "MBON_MBON", "KC_KC5"):
            C.append(ex.Cond("extra_" + e, params={"extra": (e,)}, stims=st))
        C.append(ex.Cond("extra_all", params={"extra": ("PN_APL", "APL_MBON", "MBON_MBON", "KC_KC5")}, stims=st))
        return C, 12
    raise SystemExit("grupo desconocido " + name)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("grupo")
    ap.add_argument("--seeds", type=int, default=None)
    ap.add_argument("--procs", type=int, default=4)
    a = ap.parse_args()
    conds, ns = group(a.grupo)
    if a.seeds:
        ns = a.seeds
    seeds = list(range(1, ns + 1))
    os.makedirs(os.path.join(HERE, "out", "raw"), exist_ok=True)
    p0 = nw.Params()
    split = a.grupo in ("controls", "recurrent")          # grupos largos: una condicion por archivo (reanudable)
    batches = [[c] for c in conds] if split else [conds]
    for batch in batches:
        tag = a.grupo + ("__" + batch[0].name if split else "")
        path = os.path.join(HERE, "out", "raw", tag + ".npz")
        if split and os.path.exists(path):
            print(f"[{tag}] ya existe, se salta", flush=True)
            continue
        t0 = time.time()
        print(f"[{tag}] {len(batch)} condiciones x {len(seeds)} semillas", flush=True)
        res = ex.run_all(batch, seeds, procs=a.procs, log=sys.stdout)
        raw = ex.pack_raw(res, batch, seeds)
        meta = dict(grupo=a.grupo, seeds=seeds, params=dict(p0.__dict__), conds=[
            dict(name=c.name, params=c.params, rewire=c.rewire, silence=c.silence, us_mode=c.us_mode, eta=c.eta, theta=c.theta,
                 n_pairs=c.n_pairs) for c in batch], tiempo_s=round(time.time() - t0))
        ex.save_raw(path, raw, p0.ntest, meta)
        print(f"[{tag}] listo en {time.time()-t0:.0f}s", flush=True)


if __name__ == "__main__":
    main()
