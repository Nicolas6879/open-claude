"""Comprobaciones basicas del modelo. Ejecutar con:  python3 tests/test_basic.py"""
import json
import os
import sys
import unittest

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)

import numpy as np  # noqa: E402

from fly_mb import MushroomBody, POP_NAMES, to_contract  # noqa: E402
import run_experiment as rx  # noqa: E402


def short_schedule():
    return [{"name": "A", "t0": 500, "t1": 1500, "odor": "A"}]


class TestMushroomBody(unittest.TestCase):

    def test_reproducible_with_seed(self):
        """Misma semilla -> mismas espigas, distinta semilla -> resultado distinto."""
        r1 = MushroomBody(3).run(short_schedule(), t_end_ms=2000)
        r2 = MushroomBody(3).run(short_schedule(), t_end_ms=2000)
        self.assertGreater(len(r1.spike_step), 0)
        np.testing.assert_array_equal(r1.spike_step, r2.spike_step)
        np.testing.assert_array_equal(r1.spike_id, r2.spike_id)
        r3 = MushroomBody(4).run(short_schedule(), t_end_ms=2000)
        self.assertFalse(len(r1.spike_step) == len(r3.spike_step)
                         and np.array_equal(r1.spike_step, r3.spike_step))

    def test_kc_sparsity_in_range(self):
        """Durante un olor, ~5% de las KC activas (>= 5 espigas/s); en reposo casi ninguna."""
        res = MushroomBody(7).run(short_schedule(), t_end_ms=1500)
        kc_odor = res.window_counts("KC", 500, 1500) >= rx.ACTIVE_SPIKES
        kc_blank = res.window_counts("KC", 0, 400) >= rx.ACTIVE_SPIKES
        frac = kc_odor.mean()
        self.assertGreaterEqual(frac, 0.02)
        self.assertLessEqual(frac, 0.12)
        self.assertLess(kc_blank.mean(), 0.01)

    def test_learning_lowers_MBON_for_A_not_B(self):
        """El entrenamiento A+recompensa reduce la respuesta del MBON a A mucho mas que a B."""
        sched = rx.build_schedule(4)
        res = MushroomBody(7).run(sched, t_end_ms=max(s["t1"] for s in sched) + 500)
        pre_A = np.mean([rx.mbon_rate(res, n) for n in ("pre_A", "pre_A_rep")])
        post_A = rx.mbon_rate(res, "post_A")
        pre_B = rx.mbon_rate(res, "pre_B")
        post_B = rx.mbon_rate(res, "post_B")
        self.assertLess(post_A, 0.75 * pre_A, f"A: {pre_A:.1f} -> {post_A:.1f} Hz")
        chg_A = (post_A - pre_A) / pre_A
        chg_B = (post_B - pre_B) / pre_B
        self.assertLess(chg_A - chg_B, -0.30, f"cambio A {chg_A:.2f} vs B {chg_B:.2f}")

    def test_contract_json_shape(self):
        """El JSON exportado cumple el contrato: meta, neurons, spikes, stimuli."""
        res = MushroomBody(5).run(short_schedule(), t_end_ms=1500)
        d = json.loads(json.dumps(to_contract(res, "prueba")))
        self.assertEqual(set(d), {"meta", "neurons", "spikes", "stimuli"})
        meta = d["meta"]
        self.assertEqual(meta["seed"], 5)
        self.assertIs(meta["synthetic"], True)
        self.assertAlmostEqual(meta["dt_ms"], 0.25)
        self.assertAlmostEqual(meta["duration_ms"], 1500.0)
        ids = [n["id"] for n in d["neurons"]]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual({n["type"] for n in d["neurons"]}, set(POP_NAMES))
        for n in d["neurons"]:
            self.assertIn(n["type"], POP_NAMES)
            self.assertTrue(0.0 <= n["x"] <= 1.0 and 0.0 <= n["y"] <= 1.0)
        valid = set(ids)
        self.assertGreater(len(d["spikes"]), 0)
        for t, i in d["spikes"][:5000]:
            self.assertIn(i, valid)
            self.assertGreaterEqual(t, 0.0)
        for s in d["stimuli"]:
            self.assertEqual(set(s), {"name", "t_start", "t_end"})
        self.assertEqual(d["stimuli"][0]["name"], "A")

    def test_published_activity_json_if_present(self):
        """Si existe out/activity.json, debe cumplir el contrato y pesar menos de 3 MB."""
        path = os.path.join(HERE, "out", "activity.json")
        if not os.path.exists(path):
            self.skipTest("out/activity.json no generado todavia (ejecutar run_experiment.py)")
        self.assertLess(os.path.getsize(path), 3_000_000)
        with open(path, encoding="utf-8") as f:
            d = json.load(f)
        self.assertEqual(set(d), {"meta", "neurons", "spikes", "stimuli"})
        names = {s["name"] for s in d["stimuli"]}
        for needed in ("pre_A", "pre_B", "post_A", "post_B"):
            self.assertIn(needed, names)
        self.assertTrue(any(n.startswith("train_AR_") for n in names))


if __name__ == "__main__":
    unittest.main(verbosity=2)
