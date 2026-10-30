"""Control de potencia: ¿el procedimiento de comparacion detecta una ventaja inyectada?  Ejecutar:  python3 tests/test_power.py
1) sintetico: diferencias pareadas con sd conocida; la prueba detecta un desplazamiento >= MDE y no dispara (FPR ~5 %) sin desplazamiento.
2) extremo a extremo (digits, pocas replicas): una copia del cableado real con +100 % de KC extra ('plus100_b') SI se detecta como mejor que el nulo
   de igual tamano que el real; el real contra su nulo no se declara distinto de si mismo (comparar el real con el real da dif exactamente 0)."""
import os, sys, unittest
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _boot  # noqa
import numpy as np, pandas as pd
from stats import paired, mde, empirical_power
import exp as E
from argparse import Namespace


class TestSynthetic(unittest.TestCase):
    def test_detects_shift_and_controls_fpr(self):
        rng = np.random.default_rng(0); sd, n = 0.01, 30
        def rows(shift):    # efecto de replica COMPARTIDO por a y b (pareado); ruido propio de cada variante sd
            eff = rng.normal(0, 0.02, n)
            return pd.DataFrame([dict(rep=r, variant=v, MAP=0.8 + eff[r] + (shift if v == 'a' else 0) + rng.normal(0, sd), dataset='d', mapper='m')
                                 for r in range(n) for v in ('a', 'b')])
        det = np.mean([paired(rows(0.008), 'a', 'b', 'MAP', nboot=300).p.iloc[0] < 0.05 for _ in range(40)])
        fpr = np.mean([paired(rows(0.0), 'a', 'b', 'MAP', nboot=300).p.iloc[0] < 0.05 for _ in range(60)])
        self.assertGreater(det, 0.7); self.assertLess(fpr, 0.15)
        self.assertGreater(empirical_power(rng.normal(0, 0.01 * np.sqrt(2), 200), 0.01, 30, nsim=300), 0.8)


class TestInjectedAdvantage(unittest.TestCase):
    def test_plus100_detected(self):
        a = Namespace(dataset='digits', mapper='proj', seed0=70000, frac=0.05, norm=0, mfrac=1.0, keep_dead=0, subtype=None, m_cap=0,
                      variants=['null_b', 'plus100_b', 'real_b'], tasks=['ret'], conds=[('clean', 0.0)], sizes=(500, 300, 250), tag='t')
        df = pd.DataFrame([r for rep in range(8) for r in E.run_rep(a, rep)])
        d = paired(df, 'plus100_b', 'null_b', 'MAP', nboot=1000)
        self.assertGreater(d['diff'].iloc[0], 0); self.assertLess(d['p'].iloc[0], 0.05, d[['diff', 'p']].to_string())
        self.assertTrue((paired(df, 'real_b', 'real_b', 'MAP', nboot=200)['diff'].abs() < 1e-12).all())

if __name__ == '__main__': unittest.main(verbosity=2)
