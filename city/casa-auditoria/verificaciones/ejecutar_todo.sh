#!/usr/bin/env bash
# Auditor: corre TODOS los verificadores sobre una COPIA de las casas y escribe salida/*.txt.
# Variables: CITY (por defecto el repo), SP (scratchpad), DATA (feather del conectoma), FULL=1 (anade lo lento: 16 semillas de mosca,
# run_backtests de agora, sim de conectoma), WORK (carpeta de trabajo de la copia).
set -u
AQUI="$(cd "$(dirname "$0")" && pwd)"
CITY="${CITY:-/home/user/open-claude/city}"
SP="${SP:-/tmp/claude-0/-home-user-open-claude/e7f872ff-c04d-5af4-a3a1-8d2199c39026/scratchpad}"
PY="${PY:-$SP/venv/bin/python}"
DATA="${DATA:-$SP/conectoma_data}"
WORK="${WORK:-$SP/auditor/ejecucion}"
FULL="${FULL:-0}"
OUT="$AQUI/salida"
export PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1
rm -rf "$WORK"; mkdir -p "$WORK" "$OUT"; rm -f "$OUT"/*.txt
mkdir -p "$WORK/city" && tar -C "$CITY" --exclude=casa-auditoria --exclude=__pycache__ -cf - . | tar -C "$WORK/city" -xf -
echo "copia de $CITY a $WORK/city ($(date -u +%FT%TZ)); casas: $(ls $WORK/city | tr '\n' ' ')" | tee "$OUT/00_version.txt"
( cd "$CITY/.." && git log --oneline | head -3 ) >> "$OUT/00_version.txt" 2>&1
( cd "$WORK/city" && find . -type f | sort | xargs sha256sum | sha256sum ) >> "$OUT/00_version.txt"
run() { local nombre="$1"; shift; echo "== $nombre"; ( cd "$WORK" && "$@" ) > "$OUT/$nombre.txt" 2>&1; echo "   salida $? -> salida/$nombre.txt"; }

# --- casa-mosca
run 10_mosca_recomputo "$PY" -I "$AQUI/v_mosca.py" "$WORK/city/casa-mosca"
run 11_mosca_reposo_largo "$PY" "$AQUI/v_mosca_reposo.py" "$WORK/city/casa-mosca"
run 12_mosca_reproduce bash -c "cd $WORK/city/casa-mosca && cp out/activity.json $WORK/act_orig.json && $PY run_experiment.py --seeds 7 > /dev/null && md5sum out/activity.json $WORK/act_orig.json"
run 13_mosca_control_sin_entrenar "$PY" -I "$AQUI/v_mosca_semillas.py" "$WORK/city/casa-mosca" 0 1,2,3,4,5,6
if [ "$FULL" = 1 ]; then
  run 14_mosca_16_semillas "$PY" -I "$AQUI/v_mosca_semillas.py" "$WORK/city/casa-mosca" 4 1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16
  run 15_mosca_control_12_semillas "$PY" -I "$AQUI/v_mosca_semillas.py" "$WORK/city/casa-mosca" 0 1,2,3,4,5,6,7,8,9,10,11,12
fi
# --- casa-agora
run 20_agora_reimplementacion "$PY" -I "$AQUI/v_agora.py" 500
run 21_agora_extra "$PY" -I "$AQUI/v_agora_extra.py" "$WORK/city/casa-agora"
[ "$FULL" = 1 ] && run 22_agora_su_run_backtests bash -c "cd $WORK/city/casa-agora && $PY run_backtests.py && cmp out/results.json $CITY/casa-agora/out/results.json && echo results.json IDENTICO"
# --- casa-taller
run 30_taller_cifras "$PY" -I "$AQUI/v_taller.py" "$WORK/city"
run 31_taller_regenera bash -c "cd $WORK/city/casa-taller && $PY make_art.py > /dev/null && for f in gallery/*; do cmp \$f $CITY/casa-taller/\$f && echo ok \$f; done"
# --- casa-notaria
run 40_notaria_verificador_independiente "$PY" -I "$AQUI/v_notaria.py" "$WORK/city"
run 41_notaria_su_verify bash -c "cd $WORK/city/casa-notaria && $PY verify.py; echo exit=\$?"
# --- casa-conectoma y dependientes
if [ -d "$DATA" ]; then
  run 50_conectoma_desde_feather "$PY" -I "$AQUI/v_conectoma.py" "$DATA" "$WORK/conectoma_mio.json"
  run 51_empresa_distribucion_vs_conectoma "$PY" -I "$AQUI/v_empresa_dist.py" "$WORK/city/casa-empresa/app/index.html" "$WORK/conectoma_mio.json"
  run 52_mbreal_anatomia "$PY" -I "$AQUI/v_mbreal.py" "$DATA" "$WORK/city/casa-mb-real"
  if [ "$FULL" = 1 ]; then
    run 53_conectoma_su_sim bash -c "cd $WORK/city/casa-conectoma && CONECTOMA_DATA=$DATA CONECTOMA_LIBS=$SP/conectoma_libs $PY src/sim.py --seeds 1,2 --odors 8 --out $WORK/sim_rerun.json > /dev/null && $PY -c \"import json;a=json.load(open('$WORK/sim_rerun.json'));b=json.load(open('out/sim_summary.json'));print('condiciones identicas a out/sim_summary.json:',a['condiciones']==b['condiciones'])\""
  fi
else echo "sin DATA ($DATA): se salta conectoma" | tee "$OUT/50_conectoma_desde_feather.txt"; fi
# --- casa-empresa
run 60_empresa_sim "$PY" -I "$AQUI/v_empresa_sim.py" "$WORK/city/casa-empresa"
if command -v node >/dev/null 2>&1 && [ -d "$(npm root -g 2>/dev/null)/playwright" ]; then
  run 61_empresa_app_cerebro env NODE_PATH="$(npm root -g)" node "$AQUI/v_empresa_app.js" "$WORK/city/casa-empresa/app/index.html" 12
else echo "sin node/playwright: se salta la app" | tee "$OUT/61_empresa_app_cerebro.txt"; fi
# --- casa-forja
run 70_forja "$PY" -I "$AQUI/v_forja.py" "$WORK/city/casa-forja"
# --- los verificadores detectan errores inyectados
run 90_tests_verificadores "$PY" -I "$AQUI/tests/test_verificadores.py" "$WORK/city"
echo; grep -H "RESUMEN" "$OUT"/*.txt
echo "lineas DISCREPANTE por archivo:"; grep -c "^\[DISCREPANTE\]" "$OUT"/*.txt | grep -v ":0"
