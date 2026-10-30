"""Experimento de condicionamiento olfativo en el cuerpo fungiforme sintetico.

Protocolo (cada ensayo = 1000 ms de olor + 500 ms en blanco):
  pre-test : A, B, C, A (repeticion)            -> linea base del MBON y de las KC
  training : N pares  [A + recompensa (DAN)] y [B sin recompensa]
  post-test: A, B, C                            -> cambio de la respuesta del MBON

Uso:
    python3 run_experiment.py                  # semilla 7, escribe out/activity.json
    python3 run_experiment.py --seeds 7,8,9    # robustez entre semillas (no escribe JSON)
"""
from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import numpy as np  # noqa: E402

from fly_mb import MushroomBody, Result, to_contract, write_contract  # noqa: E402

ODOR_MS = 1000.0
BLANK_MS = 500.0
ACTIVE_SPIKES = 5          # una KC cuenta como "activa" si dispara >= 5 veces en 1 s (>= 5 Hz)
ROLE = {"A": "CS+ (recompensa)", "B": "CS- (sin premio)", "C": "control (olor nuevo)"}


def build_schedule(n_pairs: int) -> list:
    sched = []
    t = BLANK_MS

    def trial(name, odor, reward=False):
        nonlocal t
        sched.append({"name": name, "t0": t, "t1": t + ODOR_MS, "odor": odor})
        if reward:
            sched.append({"name": "reward_" + name.split("_")[-1], "t0": t + ODOR_MS / 2,
                          "t1": t + ODOR_MS, "odor": None, "reward": True})
        t += ODOR_MS + BLANK_MS

    for name, odor in [("pre_A", "A"), ("pre_B", "B"), ("pre_C", "C"), ("pre_A_rep", "A")]:
        trial(name, odor)
    for i in range(1, n_pairs + 1):
        trial(f"train_AR_{i}", "A", reward=True)
        trial(f"train_B_{i}", "B")
    for name, odor in [("post_A", "A"), ("post_B", "B"), ("post_C", "C")]:
        trial(name, odor)
    return sched


def trial_window(res: Result, name: str):
    s = res.stim(name)
    return s["t0"], s["t1"]


def mbon_rate(res: Result, name: str) -> float:
    """Espigas por segundo del MBON medio (media sobre los MBON) durante el olor."""
    t0, t1 = trial_window(res, name)
    return float(res.window_counts("MBON", t0, t1).mean() / ((t1 - t0) / 1000.0))


def kc_active(res: Result, name: str) -> np.ndarray:
    t0, t1 = trial_window(res, name)
    return res.window_counts("KC", t0, t1) >= ACTIVE_SPIKES


def jaccard(a: np.ndarray, b: np.ndarray) -> float:
    u = np.logical_or(a, b).sum()
    return float(np.logical_and(a, b).sum() / u) if u else 0.0


def analyse(res: Result) -> dict:
    pre = {"A": ["pre_A", "pre_A_rep"], "B": ["pre_B"], "C": ["pre_C"]}
    post = {"A": "post_A", "B": "post_B", "C": "post_C"}
    out = {"odors": {}}
    for od in "ABC":
        r_pre = float(np.mean([mbon_rate(res, n) for n in pre[od]]))
        r_post = mbon_rate(res, post[od])
        out["odors"][od] = {
            "mbon_pre": r_pre, "mbon_post": r_post,
            "change_pct": 100.0 * (r_post - r_pre) / r_pre,
            "kc_active_pct": 100.0 * float(np.mean([kc_active(res, n).mean() for n in pre[od]])),
        }
    out["delta_discrim"] = out["odors"]["A"]["change_pct"] - out["odors"]["B"]["change_pct"]
    a1, a2 = kc_active(res, "pre_A"), kc_active(res, "pre_A_rep")
    out["jacc"] = {
        "A-B": jaccard(kc_active(res, "pre_A"), kc_active(res, "pre_B")),
        "A-C": jaccard(kc_active(res, "pre_A"), kc_active(res, "pre_C")),
        "B-C": jaccard(kc_active(res, "pre_B"), kc_active(res, "pre_C")),
        "A-A (repeticion)": jaccard(a1, a2),
    }
    out["learning_curve"] = [
        (i, mbon_rate(res, f"train_AR_{i}"), mbon_rate(res, f"train_B_{i}"))
        for i in range(1, sum(1 for s in res.schedule if s["name"].startswith("train_AR_")) + 1)
    ]
    # Pesos KC->MBON: cambio medio en las KC activas para A y para B (antes de aprender)
    wA = kc_active(res, "pre_A")
    wB = kc_active(res, "pre_B")
    dW = (res.W_final - res.W_init).mean(axis=0)
    out["w_change_A_KC_pct"] = 100.0 * float(dW[wA].mean() / res.W_init.mean())
    out["w_change_B_KC_pct"] = 100.0 * float(dW[wB].mean() / res.W_init.mean())
    out["n_spikes"] = int(len(res.spike_step))
    return out


def print_table(seed: int, n_pairs: int, a: dict) -> None:
    print(f"\n=== Semilla {seed} | {n_pairs} pares A+R / B | ensayos de 1000 ms ===")
    print(f"{'Olor':<5}{'Papel':<22}{'MBON pre (Hz)':>15}{'MBON post (Hz)':>16}"
          f"{'Cambio':>10}{'KC activas':>13}")
    for od in "ABC":
        o = a["odors"][od]
        print(f"{od:<5}{ROLE[od]:<22}{o['mbon_pre']:>15.1f}{o['mbon_post']:>16.1f}"
              f"{o['change_pct']:>9.1f}%{o['kc_active_pct']:>12.1f}%")
    print(f"Discriminacion (cambio A - cambio B): {a['delta_discrim']:+.1f} puntos porcentuales")
    print("Solapamiento de KC activas (Jaccard, pre-entrenamiento):")
    for k, v in a["jacc"].items():
        print(f"  {k:<18} {v:.3f}")
    print("Curva de aprendizaje (Hz del MBON medio, durante el olor):")
    print(f"  {'par':<5}{'A + R':>10}{'B':>10}")
    for i, ra, rb in a["learning_curve"]:
        print(f"  {i:<5}{ra:>10.1f}{rb:>10.1f}")
    print(f"Cambio medio del peso KC->MBON: KC de A {a['w_change_A_KC_pct']:+.1f}%, "
          f"KC de B {a['w_change_B_KC_pct']:+.1f}%")
    print(f"Espigas totales simuladas: {a['n_spikes']}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--seeds", default="7", help="semillas separadas por comas (default 7)")
    ap.add_argument("--pairs", type=int, default=4, help="pares de entrenamiento A+R / B")
    ap.add_argument("--no-json", action="store_true", help="no escribe out/activity.json")
    args = ap.parse_args()

    seeds = [int(s) for s in args.seeds.split(",")]
    summ, first = {}, None
    for seed in seeds:
        mb = MushroomBody(seed)
        sched = build_schedule(args.pairs)
        res = mb.run(sched, t_end_ms=max(s["t1"] for s in sched) + BLANK_MS)
        a = analyse(res)
        summ[seed] = a
        print_table(seed, args.pairs, a)
        if first is None:
            first = (seed, res)

    if len(seeds) > 1:
        print("\nResumen por semilla (cambio %: A / B / C):")
        for seed in seeds:
            o = summ[seed]["odors"]
            print(f"  semilla {seed}: A {o['A']['change_pct']:+.1f}  B {o['B']['change_pct']:+.1f}  "
                  f"C {o['C']['change_pct']:+.1f}  | KC activas A {o['A']['kc_active_pct']:.1f}%")

    if not args.no_json and first is not None:
        seed, res = first
        desc = ("SINTETICO: circuito olfativo LIF de Drosophila (ORN->PN->KC->MBON, APL, DAN). "
                "Conectividad y parametros aproximados, no datos reales. Protocolo: pre-test A/B/C, "
                f"{args.pairs} pares A+recompensa y B, post-test A/B/C.")
        out_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out")
        os.makedirs(out_dir, exist_ok=True)
        path = os.path.join(out_dir, "activity.json")
        write_contract(to_contract(res, desc), path)
        print(f"\nEscrito contrato: {path} ({os.path.getsize(path) / 1e6:.2f} MB)")


if __name__ == "__main__":
    main()
