"""Extrae la matriz PN->KC del conectoma MaleCNS v1.0 (Google/Janelia, CC-BY) a data/pnkc.npz.

Uso:  python -I src/extract_pnkc.py <dir con los 3 feather>  [salida.npz]
Datos: bucket publico https://storage.googleapis.com/flyem-male-cns/v1.0/connectome-data/flat-connectome/
  - body-annotations-male-cns-v1.0-minconf-0.5.feather
  - connectome-weights-male-cns-v1.0-minconf-0.5-significant-only.feather   (502 MB)
  - body-neurotransmitters-male-cns-v1.0.feather  (columna consensus_nt, NO predicted_nt)
Definiciones propias (no se reutiliza codigo de otras casas):
  KC  = cuerpos cuyo `type` empieza por 'KC' (4064)
  PN  = cuerpos con class == 'ALPN' que tienen al menos una arista significativa a una KC (314)
  peso = nº de sinapsis de la arista (columna weight)
"""
import sys, numpy as np, pyarrow as pa, pyarrow.compute as pc, pyarrow.feather as pf, pandas as pd, os

d = sys.argv[1]
out = sys.argv[2] if len(sys.argv) > 2 else os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data', 'pnkc.npz')
ann = pf.read_table(os.path.join(d, 'body-annotations-male-cns-v1.0-minconf-0.5.feather'),
                    columns=['bodyId', 'type', 'class', 'somaSide', 'instance'], memory_map=True).to_pandas()
kc = ann[ann['type'].fillna('').str.startswith('KC')].reset_index(drop=True)
pn_all = ann[ann['class'] == 'ALPN']
w = pf.read_table(os.path.join(d, 'connectome-weights-male-cns-v1.0-minconf-0.5-significant-only.feather'),
                  columns=['body_pre', 'body_post', 'weight'], memory_map=True)
m = pc.and_(pc.is_in(w['body_post'], value_set=pa.array(kc.bodyId.values)),
            pc.is_in(w['body_pre'], value_set=pa.array(pn_all.bodyId.values)))
e = w.filter(m).to_pandas()
pn = pn_all[pn_all.bodyId.isin(e.body_pre)].reset_index(drop=True)
pi = {b: i for i, b in enumerate(pn.bodyId)}; ki = {b: i for i, b in enumerate(kc.bodyId)}
def grp(t):
    if t.startswith("KCa'b'"): return 1
    if t.startswith('KCab'): return 0
    if t.startswith('KCg'): return 2
    return 3
sidemap = lambda s: 0 if s == 'L' else (1 if s == 'R' else -1)
np.savez_compressed(out,
    pn_idx=e.body_pre.map(pi).values.astype(np.int16), kc_idx=e.body_post.map(ki).values.astype(np.int16),
    weight=e.weight.values.astype(np.int16),
    pn_body=pn.bodyId.values, pn_type=np.array(pn['type'].fillna('?').tolist(), dtype='U40'), pn_side=pn.somaSide.map(sidemap).values.astype(np.int8),
    kc_body=kc.bodyId.values, kc_type=np.array(kc['type'].tolist(), dtype='U40'), kc_side=kc.somaSide.map(sidemap).values.astype(np.int8),
    kc_group=np.array([grp(t) for t in kc['type']], dtype=np.int8))  # 0=KCab 1=KCa'b' 2=KCg 3=otro
print('PN', len(pn), 'KC', len(kc), 'aristas', len(e), 'sinapsis', int(e.weight.sum()))
