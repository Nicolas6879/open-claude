"""Conjuntos de datos: digits (sklearn, sin red), MNIST y Fashion-MNIST (bucket publico de TensorFlow en
storage.googleapis.com; ver src/fetch_datasets.sh). Pixeles en [0,1], float32."""
import os, gzip, numpy as np
DL = os.environ.get('FLYHASH_DL', '/tmp/claude-0/-home-user-open-claude/e7f872ff-c04d-5af4-a3a1-8d2199c39026/scratchpad/hash/dl')

def _idx(path, img):
    with gzip.open(path, 'rb') as f: b = f.read()
    return (np.frombuffer(b, np.uint8, offset=16).reshape(-1, 784) if img else np.frombuffer(b, np.uint8, offset=8))

def load(name):
    if name == 'digits':
        from sklearn.datasets import load_digits
        d = load_digits(); return (d.data / 16.0).astype(np.float32), d.target.astype(np.int64), None, None
    if name == 'mnist':
        z = np.load(os.path.join(DL, 'mnist.npz'))
        return (z['x_train'].reshape(-1, 784) / 255.).astype(np.float32), z['y_train'].astype(np.int64), \
               (z['x_test'].reshape(-1, 784) / 255.).astype(np.float32), z['y_test'].astype(np.int64)
    if name == 'fmnist':
        g = lambda f, img: _idx(os.path.join(DL, f), img)
        return (g('train-images-idx3-ubyte.gz', 1) / 255.).astype(np.float32), g('train-labels-idx1-ubyte.gz', 0).astype(np.int64), \
               (g('t10k-images-idx3-ubyte.gz', 1) / 255.).astype(np.float32), g('t10k-labels-idx1-ubyte.gz', 0).astype(np.int64)
    if name == 'news':   # 20 Newsgroups -> TF-IDF -> SVD 400 (LSA), filas normalizadas. SVD ajustada SOLO con el subconjunto 'train' de sklearn.
        cache = os.path.join(DL, 'news_lsa400.npz')
        if not os.path.exists(cache):
            from sklearn.datasets import fetch_20newsgroups
            from sklearn.feature_extraction.text import TfidfVectorizer
            from sklearn.decomposition import TruncatedSVD
            kw = dict(remove=('headers', 'footers', 'quotes'), data_home=os.path.join(DL, 'sk_data'))
            tr, te = fetch_20newsgroups(subset='train', **kw), fetch_20newsgroups(subset='test', **kw)
            tf = TfidfVectorizer(max_features=30000, sublinear_tf=True, stop_words='english', min_df=3).fit(tr.data)
            sv = TruncatedSVD(400, random_state=0).fit(tf.transform(tr.data))
            f = lambda d: (lambda Z: Z / (np.linalg.norm(Z, axis=1, keepdims=True) + 1e-9))(sv.transform(tf.transform(d)))
            np.savez_compressed(cache, a=f(tr.data).astype(np.float32), b=tr.target, c=f(te.data).astype(np.float32), d=te.target)
        z = np.load(cache)
        return z['a'], z['b'].astype(np.int64), z['c'], z['d'].astype(np.int64)
    raise ValueError(name)

def split(name, rng, sizes=None):
    """Devuelve dict con Xfit,yfit (ajuste de mapeo/clasificador), Xdb,ydb (base de recuperacion),
    Xq,yq (consultas), Xte,yte (test de clasificacion). Todo disjunto."""
    X, y, Xt, yt = load(name)
    if name == 'digits':
        n_fit, n_db, n_q = (sizes or (900, 500, 397))
        p = rng.permutation(len(X)); a, b, c = p[:n_fit], p[n_fit:n_fit + n_db], p[n_fit + n_db:n_fit + n_db + n_q]
        return dict(Xfit=X[a], yfit=y[a], Xdb=X[b], ydb=y[b], Xq=X[c], yq=y[c],
                    Xte=np.vstack([X[b], X[c]]), yte=np.r_[y[b], y[c]])
    n_fit, n_db, n_q, n_te = (sizes or (6000, 5000, 500, 4000))
    p = rng.permutation(len(X)); q = rng.permutation(len(Xt))
    a, b = p[:n_fit], p[n_fit:n_fit + n_db]; c, e = q[:n_q], q[n_q:n_q + n_te]
    return dict(Xfit=X[a], yfit=y[a], Xdb=X[b], ydb=y[b], Xq=Xt[c], yq=yt[c], Xte=Xt[e], yte=yt[e])
