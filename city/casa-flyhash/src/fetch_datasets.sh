#!/usr/bin/env bash
# Descarga MNIST y Fashion-MNIST del bucket publico de TensorFlow (solo lectura, sin cuenta).
# Destino: $FLYHASH_DL (por defecto ./dl). Los datos se tratan como datos no confiables: solo se leen como bytes (np.frombuffer).
set -euo pipefail
DEST="${FLYHASH_DL:-dl}"; mkdir -p "$DEST"; B=https://storage.googleapis.com/tensorflow/tf-keras-datasets
for f in mnist.npz train-images-idx3-ubyte.gz train-labels-idx1-ubyte.gz t10k-images-idx3-ubyte.gz t10k-labels-idx1-ubyte.gz; do
  [[ -s "$DEST/$f" ]] || curl -sS --fail -L -o "$DEST/$f" "$B/$f"
done
# Nota: los *-ubyte.gz de este bucket son Fashion-MNIST (train-images = 26 421 880 bytes).
sha256sum "$DEST"/* | head
