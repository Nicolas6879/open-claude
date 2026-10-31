#!/usr/bin/env bash
# casa-mb-real: mismos tres archivos Feather que casa-conectoma (copia de su fetch_data.sh).
# Descarga los archivos planos del conectoma MaleCNS v1.0 (Google Research + HHMI Janelia, CC-BY).
# Si ya los tienes (p. ej. en el scratchpad de la ciudad), no hace falta bajar nada: exporta CONECTOMA_DATA=<carpeta>.
# Solo lectura de un bucket publico de Google Cloud Storage: sin cuenta, sin claves.
# Destino por defecto: ~/.cache/conectoma-male-cns (cambiar con CONECTOMA_DATA). Fuera del repo.
# Uso: bash fetch_data.sh            (baja lo necesario: ~560 MB)
#      bash fetch_data.sh --small    (solo anotaciones y neurotransmisores: ~58 MB; sin la matriz de pesos)
set -euo pipefail
DEST="${CONECTOMA_DATA:-$HOME/.cache/conectoma-male-cns}"
BASE="https://storage.googleapis.com/flyem-male-cns/v1.0/connectome-data/flat-connectome"
mkdir -p "$DEST"
FILES=(
  "body-annotations-male-cns-v1.0-minconf-0.5.feather"
  "body-neurotransmitters-male-cns-v1.0.feather"
)
if [[ "${1:-}" != "--small" ]]; then
  FILES+=("connectome-weights-male-cns-v1.0-minconf-0.5-significant-only.feather")
fi
for f in "${FILES[@]}"; do
  if [[ -s "$DEST/$f" ]]; then echo "ya existe: $f"; continue; fi
  echo "descargando: $f"
  curl -sS --fail -o "$DEST/$f.part" "$BASE/$f"
  mv "$DEST/$f.part" "$DEST/$f"
done
ls -l "$DEST"
echo "Listo. Para pyarrow sin instalarlo globalmente: CONECTOMA_LIBS=<dir con pyarrow> (pip install --target <dir> pyarrow)."
