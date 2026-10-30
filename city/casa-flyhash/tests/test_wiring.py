"""Cableado real y nulos.  Ejecutar:  python3 tests/test_wiring.py"""
import os, sys, unittest
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _boot  # noqa
import numpy as np
from wiring import load_real, swap_null, kc_degree_null, random_wiring, scaled_real_like, dedup_type_swaps
from engine import KCCoder, Mapper, SimHash, ridge_classify, topk_idx


class TestReal(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.wr = load_real()
    def test_dims(self):
        self.assertEqual(self.wr.W.shape, (4064, 314)); self.assertEqual(self.wr.W.nnz, 22586); self.assertEqual(int(self.wr.W.sum()), 390928)
    def test_sides_and_ipsi(self):
        pn, kc, _ = self.wr.edges(); ips = np.mean(self.wr.pn_side[pn] == self.wr.kc_side[kc])
        self.assertAlmostEqual(ips, 0.979, delta=0.002)
    def test_dead_kc(self):
        self.assertEqual(int((np.diff(self.wr.W.indptr) == 0).sum()), 252)

class TestNulls(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.wr = load_real()
    def test_swap_preserves_degrees_and_hemisphere(self):
        nl, done = swap_null(self.wr, 7, weights='kc')
        self.assertGreater(done, 0)
        self.assertTrue((np.diff(nl.W.indptr) == np.diff(self.wr.W.indptr)).all())
        self.assertTrue((np.diff(nl.W.tocsc().indptr) == np.diff(self.wr.W.tocsc().indptr)).all())
        pn, kc, _ = nl.edges(); self.assertAlmostEqual(np.mean(nl.pn_side[pn] == nl.kc_side[kc]), 0.9793, delta=1e-3)
        self.assertEqual(nl.W.nnz, 22586); self.assertEqual(int(nl.W.sum()), 390928)
        ov = (self.wr.W > 0).multiply(nl.W > 0).sum() / 22586
        self.assertLess(ov, 0.2)                                   # realmente reordena
    def test_swap_blocks_preserve_block_counts(self):
        nl, _ = swap_null(self.wr, 3, weights='none'); pn, kc, _ = self.wr.edges(); pn2, kc2, _ = nl.edges()
        blk = lambda p, k: np.bincount((self.wr.pn_side[p] * 2 + self.wr.kc_side[k]).astype(int), minlength=4)
        self.assertTrue((blk(pn, kc) == blk(pn2, kc2)).all())
    def test_random_wiring_no_duplicates(self):
        w = random_wiring(np.full(500, 6), self.wr.kc_side[:500], self.wr.pn_side, None, 0.979, None, np.random.default_rng(0))
        self.assertTrue((np.diff(w.W.indptr) == 6).all()); self.assertEqual(w.W.max(), 1)
    def test_scaled_degree_pattern(self):
        w = scaled_real_like(self.wr, 3, np.random.default_rng(0))
        self.assertEqual(w.m, 3 * 4064); self.assertEqual(w.W.nnz, 3 * 22586)

class TestControls(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.wr = load_real(); cls.wa = cls.wr.subset(np.flatnonzero(np.diff(cls.wr.W.indptr) > 0))
    def test_jdd_null_preserves_degrees_and_disassortativity(self):
        from scipy.stats import spearmanr
        nl, _ = swap_null(self.wa, 2, weights='none', blocks='jdd')
        self.assertTrue((np.diff(nl.W.indptr) == np.diff(self.wa.W.indptr)).all())
        self.assertTrue((np.diff(nl.W.tocsc().indptr) == np.diff(self.wa.W.tocsc().indptr)).all())
        def rho(w):
            pn, kc, _ = w.edges(); od = np.bincount(pn, minlength=w.n); idg = np.diff(w.W.indptr)
            return spearmanr(idg, np.bincount(kc, weights=od[pn], minlength=w.m) / np.maximum(idg, 1))[0]
        plain, _ = swap_null(self.wa, 2, weights='none')
        self.assertLess(rho(self.wa), -0.2); self.assertLess(abs(rho(plain)), 0.06); self.assertLess(rho(nl), -0.2)   # el nulo JDD conserva la disasortatividad
    def test_dedup_removes_repeated_types_and_keeps_degrees(self):
        d, before, after = dedup_type_swaps(self.wa, 1)
        self.assertGreater(before, 500); self.assertEqual(after, 0)
        self.assertTrue((np.diff(d.W.indptr) == np.diff(self.wa.W.indptr)).all())
        self.assertTrue((np.diff(d.W.tocsc().indptr) == np.diff(self.wa.W.tocsc().indptr)).all())
        self.assertEqual(d.W.nnz, self.wa.W.nnz); self.assertEqual(d.W.max(), self.wa.W.max())

class TestEngine(unittest.TestCase):
    def test_topk_exact_k_and_dead_excluded(self):
        wr = load_real(); cd = KCCoder(wr.W, 0.05)
        P = np.random.default_rng(0).standard_normal((20, 314)).astype(np.float32); idx = cd.encode(P)
        self.assertEqual(idx.shape, (20, cd.k)); self.assertFalse(cd.dead[idx].any())
        self.assertTrue(all(len(set(r)) == cd.k for r in idx))
    def test_mapper_uses_only_fit_data(self):
        rng = np.random.default_rng(0); X = rng.random((300, 64)).astype(np.float32); T = rng.random((50, 64)).astype(np.float32)
        m1 = Mapper('proj', 1).fit(X); a = m1(T); m2 = Mapper('proj', 1).fit(X); b = m2(T * 1.0)
        self.assertTrue(np.allclose(a, b)); m3 = Mapper('proj', 1).fit(X); _ = m3(T + 5); self.assertTrue(np.allclose(m1(T), m3(T)))  # transform no reajusta
    def test_ridge_classifier_learns(self):
        rng = np.random.default_rng(1); y = rng.integers(0, 3, 600); Z = rng.standard_normal((600, 20)); Z[np.arange(600), y] += 3
        acc, _ = ridge_classify(Z[:400], y[:400], Z[400:], y[400:]); self.assertGreater(acc, 0.9)
        Zs = Z.copy(); ys = rng.permutation(y); acc2, _ = ridge_classify(Zs[:400], ys[:400], Zs[400:], ys[400:]); self.assertLess(acc2, 0.5)  # etiquetas barajadas -> azar

if __name__ == '__main__': unittest.main(verbosity=2)
