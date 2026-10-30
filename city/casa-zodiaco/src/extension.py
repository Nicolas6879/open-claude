"""Cielo visto desde otra estrella: recalcula direcciones y magnitudes aparentes con las posiciones 3D de HYG.

Supuestos (documentados en el README):
  - posiciones/paralajes de HYG v4.1 (derivadas de Hipparcos/Gliese); estrellas con paralaje desconocido
    (dist >= 99999 pc, ~2 % de las estrellas con mag < 6) conservan su direccion y magnitud terrestres
    (error esperado < 1 grado y < 0.01 mag para observadores a < 15 pc de nosotros) [no verificado];
  - la luminosidad es la absmag de HYG (sin extincion interestelar);
  - sin movimiento propio: todas las epocas = J2000 de HYG.
"""
import numpy as np
import datos


class Cielos:
    def __init__(self, df):
        self.df = df.reset_index(drop=True)
        self.xyz = df[["x", "y", "z"]].values.astype(float)
        self.absmag = df.absmag.values.astype(float)
        self.mag_tierra = df.mag.values.astype(float)
        self.dist = df.dist.values.astype(float)
        self.valido = (self.dist < 99999) & np.isfinite(self.absmag)
        self.hip = df.hip.values
        self.ids = df.id.values

    def desde(self, pos, excluir_id=None, mag_max=6.5):
        """Cielo desde la posicion pos (pc, marco ecuatorial J2000 de HYG).
        Devuelve (idx_en_df, vec_unitarios, mag_aparente) de las estrellas con mag <= mag_max."""
        pos = np.asarray(pos, dtype=float)
        r = self.xyz - pos
        d = np.linalg.norm(r, axis=1)
        mag = np.where(self.valido & (d > 1e-5), self.absmag + 5 * np.log10(np.maximum(d, 1e-9) / 10.0), self.mag_tierra)
        vec = np.where((self.valido & (d > 1e-5))[:, None], r / np.maximum(d, 1e-9)[:, None], np.nan)
        # estrellas sin paralaje: direccion terrestre
        sin = ~(self.valido & (d > 1e-5))
        if sin.any():
            ra = np.radians(self.df.ra.values[sin] * 15.0)
            de = np.radians(self.df.dec.values[sin])
            vec[sin] = np.stack([np.cos(de) * np.cos(ra), np.cos(de) * np.sin(ra), np.sin(de)], axis=1)
        ok = (mag <= mag_max) & np.isfinite(mag)
        if excluir_id is not None:
            ok &= self.ids != excluir_id
        ok &= ~((np.linalg.norm(pos) < 1e-9) & (self.ids == 0) & False)  # el Sol no se excluye desde fuera
        # desde la Tierra/Sol: la fila Sol (id 0) esta en el origen y d=0 -> se excluye
        ok &= ~(d < 1e-5)
        idx = np.where(ok)[0]
        return idx, vec[idx], mag[idx]


def radec_de_vec(v):
    ra = (np.degrees(np.arctan2(v[:, 1], v[:, 0])) % 360.0) / 15.0
    de = np.degrees(np.arcsin(np.clip(v[:, 2], -1, 1)))
    return ra, de
