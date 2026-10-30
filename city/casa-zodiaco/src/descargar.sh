#!/bin/bash
# Descarga datos publicos (solo lectura) a un directorio FUERA del repo. Uso: descargar.sh <dir_destino_absoluto>
# Lo descargado es NO CONFIABLE: solo se parsea como JSON/CSV, nunca se ejecuta.
set -euo pipefail
D="${1:?uso: descargar.sh /ruta/absoluta}"
mkdir -p "$D/cultures" "$D/desc"
B=https://raw.githubusercontent.com/Stellarium/stellarium/master/skycultures
curl -sS -o "$D/CMakeLists.txt" "$B/CMakeLists.txt"
# nombres de cultura = lineas ADD_SUBDIRECTORY( x ) NO comentadas
grep -E '^ADD_SUBDIRECTORY' "$D/CMakeLists.txt" | sed -E 's/.*\( *//;s/ *\).*//' > "$D/lista_culturas.txt"
while read -r c; do
  curl -sS -o "$D/cultures/$c.json" "$B/$c/index.json"
  curl -sS -o "$D/desc/$c.md" "$B/$c/description.md" || true
done < "$D/lista_culturas.txt"
curl -sS -o "$D/hygdata_v41.csv" https://raw.githubusercontent.com/astronexus/HYG-Database/main/hyg/CURRENT/hygdata_v41.csv
curl -sS -o "$D/arxiv_abs.html" https://arxiv.org/abs/2010.06108
