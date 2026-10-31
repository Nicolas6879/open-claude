#!/usr/bin/env bash
# Reproduce todo casa-mb-real.  Requiere python con numpy, numba, scipy, pyarrow, matplotlib (un venv fuera del repo).
#   PY=/ruta/venv/bin/python CONECTOMA_DATA=/ruta/datos bash reproducir.sh [rapido]
# Con 'rapido' usa pocas semillas (~15 min); sin argumento, el diseno completo (horas en una maquina compartida).
set -euo pipefail
cd "$(dirname "$0")"
PY="${PY:-python3}"
export PYTHONDONTWRITEBYTECODE=1
export NEURO2_CACHE="${NEURO2_CACHE:-$HOME/.cache/neuro2-mbreal}"
export NUMBA_CACHE_DIR="${NUMBA_CACHE_DIR:-$HOME/.cache/neuro2-numba}"
SEEDS=""; [[ "${1:-}" == "rapido" ]] && SEEDS="--seeds 4"
$PY tests/test_mb_real.py
$PY src/anatomy.py
$PY calibrate.py
for g in main backward lesions_apl lesions_apl2 sweeps robust extra recurrent ntsource controls lesions_dan lesions_mbon; do
  $PY run_experiments.py $g $SEEDS
done
$PY summarize.py
$PY figures.py
