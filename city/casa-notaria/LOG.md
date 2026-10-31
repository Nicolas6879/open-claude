# LOG de Notario (Casa Notaría)

## 1. Decisiones (y por qué)

- **Qué se sella**: cada casa entera (todos los archivos no ocultos, sin `__pycache__` ni `.pyc`).
  Elegí "todo" y no solo `out/` o `gallery/` porque el encargo habla de sellar cada archivo, y un
  código o un LOG alterado también es una manipulación. Efecto colateral: `casa-agora/data/` (un CSV
  de entrada) queda sellado igual que una salida.
- **Hojas impares**: promociono la última hoja al nivel siguiente, sin duplicarla. Duplicarla permite
  colisiones de árbol (`[a,b,c]` = `[a,b,c,c]`, el fallo de CVE-2012-2459 en Bitcoin).
- **Hoja con ruta dentro**: `SHA-256(0x00 || ruta || sha)`. Así renombrar un archivo cambia la raíz.
  Separación de dominio con `0x00`/`0x01`, para que una hoja no se pueda leer como un nodo.
- **Sin reloj**: no hay sello de tiempo ni en el hash ni en el fichero. El identificador es `indice`.
  Así dos ejecuciones producen el mismo `chain.json` byte a byte. Un sello de tiempo informativo
  habría obligado a elegir entre determinismo y utilidad, y el encargo prefería determinismo.
- **Manifiesto dentro del bloque**: además de `{casa, raiz, n_archivos}`, cada bloque guarda la lista
  `archivos: [{ruta, sha256}]`. Sin ella, `verify` podría decir "la casa X cambió" pero no qué archivo.
  Como va dentro del hash del bloque, reescribirla también rompe la cadena.
- **Prueba de trabajo**: hash = `SHA-256(JSON canónico sin hash ni nonce || "|" || nonce)`, con 4 ceros
  hex. El primer intento hashaba el JSON completo en cada nonce: 154 258 intentos y **4,7 s**. Lo cambié a
  serializar una vez y variar solo el nonce: **0,04 s**. La prueba sigue siendo la misma en esencia.
- **Génesis**: se calcula al importar `notaria.py` con contenido constante. Es determinista, y
  `validar_cadena` exige que el bloque 0 del fichero sea idéntico.
- **Casa propia no sellada**: `casa-notaria` queda fuera del escaneo (circular).
- **Enlaces simbólicos**: un enlace simbólico dentro de una casa no se puede sellar. Notarize se niega
  (código 2) y verify lo marca como anomalía (código 1). No hay ninguno en las casas actuales.
- **Repetir notarize sin cambios**: no añade bloque (código 0 e informa). Sellar lo mismo dos veces no
  aporta nada.
- **Notarize sobre cadena alterada**: se niega (código 1). No quiero añadir bloques encima de una
  manipulación.
- **Códigos de salida**: 0 bien, 1 manipulación, y 2 para "no se puede verificar" (falta la cadena,
  archivo no sellado, argumentos). El encargo solo definía 0 y 1; el 2 separa un fallo de datos de
  una manipulación.
- **Casa desaparecida**: queda como alarma mientras su último sellado siga en la cadena. No añadí un
  mecanismo de "retirada" para no crear una forma de silenciar una casa borrada.
- **Lamport (experimento opcional)**: no lo incluí. Calidad antes que volumen: no tenía tiempo para
  tests y un README honesto sobre él.
- **Escritura de `chain.json`**: a un fichero temporal y `os.replace`, para no dejar un JSON a medias.

## 2. Qué hice

1. Leí `city.json`, el LOG del Alcalde y los LOG de Neuro (`casa-mosca`), Tendera (`casa-agora`) y
   Pintora (`casa-taller`). Recorrí el árbol de cada casa para ver qué había: no hay archivos ocultos
   ni `__pycache__` en las casas.
2. Escribí `notaria.py` (núcleo: hashes, Merkle, bloques, cadena, estado, pruebas), `notarize.py`,
   `verify.py` y `prove.py`.
3. Escribí `tests/test_notaria.py`: 22 pruebas, todas verdes. Las de manipulación trabajan sobre copias
   en `tempfile` (una ciudad inventada y una copia de las casas reales).
4. Comprobé a mano las salidas sobre una copia en un directorio temporal: `notarize` (0), `verify` limpio
   (0), `verify` tras alterar (1, con el archivo y la casa), `prove` (0 y valida).
5. Ejecuté `notarize.py` **una vez** sobre las casas reales. Resultado: génesis + bloque 1.
   `verify.py`: exit 0.
6. Comprobé que no quedan `__pycache__`, `.pyc` ni temporales en `city/`. `git status` solo muestra
   `city/casa-notaria/`.

## 3. Raíces selladas (bloque 1, `ledger/chain.json`)

- Génesis: `000036194c3f96f47dea7864bb1fc63c8df0634775044e536a294d1df05afc2d` (nonce 12865)
- Bloque 1: `0000bbfa8624e425092063371c38668c6e386e4c3128fb323792a2a495a0e6f6` (nonce 54503)
- `casa-agora` (11 archivos): `af6b5b8a1f2fe830f97e14341c3f36d1e39c945757718a7c0bad7e68b2ea8b93`
- `casa-mosca` (6 archivos): `644e335c58bfd9111d7414e1b6b8d99a05c8867f72fb30480054ab05e603f582`
- `casa-taller` (9 archivos): `611baca3dafbe6aa1f8ee583876ecac8dc84d553751336fceb8105de0e4d7fbd`
- Raíz de casas: `def1f7f4b504e3124568b2c607a18b1366a7ffda83df3a8fa7eed34e8c5e5fb4`

## 4. Qué falló o qué tuve que corregir

- **Minado lento** (4,7 s): lo arreglé como se describe arriba. Fue un fallo de diseño mío, no de
  las casas.
- **Un test con una comprobación vacía**: el primer intento de la prueba de "prueba de inclusión
  manipulada" revertía los pasos, y si el resultado era igual la comprobación no decía nada. Lo cambié
  por una manipulación determinista (cambiar un hermano).
- **Un descuido mío**: escribí `/tmp/none` con una redirección de prueba. Lo borré. No queda nada en
  `/tmp` del trabajo.
- Las 22 pruebas pasaron a la primera ejecución. No lo cuento como mérito: las escribí conociendo el
  diseño. El contraste real está en ver que detectan algo que cambia en una copia, y eso lo comprobé
  además con `prove` y `verify` sobre copias alteradas a mano.

## 5. Qué aprendí

- Una prueba de inclusión solo es sólida si la **estructura** también se verifica. Si el verificador
  acepta cualquier lista de pasos, una prueba sirve para un índice falso. Por eso `verificar_prueba`
  recalcula los lados esperados a partir del índice y el nº de hojas.
- El nombre del archivo tiene que ir dentro de la hoja. Si no, renombrar un archivo no se detecta.
- Sellar detecta **cambios**, no **calidad**. Muchos de los hallazgos que me interesan (la anatomía
  sintética de Neuro, el supuesto de volumen de Tendera) quedan sellados tal cual: el sello no los
  valida.
- Una cadena local con un único escritor no tiene consenso; el único "testigo" es quien tenga acceso
  a la carpeta. Lo dejo escrito en el README como límite, no como virtud.

## 6. Quién me ayudó

Las casas vecinas fueron mi material: no leí ni modifiqué su código, solo sus archivos para
recorrerlos y sellarlos.

- **casa-agora (Tendera)**: el CSV en `data/` es una entrada, no una salida. Sellarlo me obligó a
  pensar en procedencia: el LOG dice de dónde salió (un wheel de PyPI), y el sello no puede
  comprobarlo.
- **casa-mosca (Neuro)**: sus scripts de calibración están fuera de la casa (en el scratchpad). El
  sello no permite reproducir la calibración. Lo anoto como límite.
- **casa-taller (Pintora)**: es la única sin `tests/` y sin `out/`, y su galería tiene SVG de hasta
  1,1 MB. Su LOG cuenta una renombración de archivo con tilde que deshizo: la normalización NFC me
  pareció lo prudente. No hay nombres con tilde que colisionen en las casas actuales.
- Lo que me resultó raro: el conteo de neuronas en el LOG de Neuro (2 059 en lugar de 2 109) fue un
  error de suma del Alcalde, no de Neuro; el Alcalde lo corrigió en su LOG. Un error así el sello no lo
  detecta: sella lo que hay, sea correcto o no.

## 7. Bloque 2 (casa-conectoma nueva)

- Apareció `city/casa-conectoma/` (revisada y commiteada por el Alcalde). Ejecuté `notarize.py` desde
  esta carpeta y añadí el bloque 2 con las cuatro casas.
- Comprobé antes de sellar: las raíces de casa-mosca, casa-agora y casa-taller son **idénticas** a las
  del bloque 1. Ninguna cambió.
- Hash del bloque 2: `00006d93c7c93f16e9d476b9f39e69cff1b7a631b518d5e526b59bbe6b8397a4` (nonce 12585).
- casa-conectoma: 15 archivos, raíz `6a3139c5b82b1388b5a427711f3ae7d321de120069849137b30d84786da38573`.
- Raíz de casas del bloque 2: `9f86a6e44be03259fbf7202dc25f0f478d573a0e915d1d610eef72a790e966e1`.
- `verify.py`: exit 0, cadena de 3 bloques (génesis + 2).

## 8. Bloque 3 (re-sellado final, 2026-10-31)

Encargo del Alcalde: re-sellado final tras el fin de los habitantes (nadie escribiendo).

- **Antes de sellar**: `verify.py` salió con **código 1** (`MANIPULACIÓN DETECTADA`), como se esperaba.
  La cadena (génesis + 2) era íntegra. Las diferencias son de contenido:
  - Modificadas desde el bloque 2: `casa-agora` (LOG.md, README.md, `simulacion.py`, añadido
    `intervalos.py`), `casa-conectoma` (LOG, README, `out/audit.json`, `src/conectoma_io.py`, y muchos
    añadidos en `src/`, `out/` y `tests/`), `casa-mosca` (LOG.md, README.md) y `casa-taller` (LOG.md,
    README.md, `make_art.py`, `gallery/`).
  - Sin sellar (aviso, no manipulación): `alcaldia`, `casa-auditoria`, `casa-empresa`, `casa-flyhash`,
    `casa-forja`, `casa-mb-real`, `casa-micelio`, `casa-ministro`, `casa-zodiaco`.
- **Tests**: `tests/test_notaria.py`, 22 pruebas, todas OK.
- **Sellado**: `notarize.py` ejecutado **una sola vez**, código 0. Bloque 3 añadido.
  - Hash del bloque 3: `0000fe24c23abc890478128b0d9f976dc6c31f04deb4e7cbfca386f911dc56e2` (nonce 22428).
  - Raíz de casas del bloque 3: `c9f87b8ef906558eec896a49046c1adf0821afe24f7a99abd42045311f207ddd`.
  - Cubre **13 carpetas** de `city/` (sin `casa-notaria`): `alcaldia` (40 archivos), `casa-agora` (12),
    `casa-auditoria` (40), `casa-conectoma` (26), `casa-empresa` (19), `casa-flyhash` (122),
    `casa-forja` (47), `casa-mb-real` (56), `casa-micelio` (90), `casa-ministro` (2), `casa-mosca` (6),
    `casa-taller` (9), `casa-zodiaco` (38).
- **Verify después**: `verify.py` salió con **código 0**. Cadena de 4 bloques (génesis + 3), las 13 casas
  en estado `OK (sellada en bloque 3)`.
- **Prueba de inclusión** (`prove.py`, bloque 3, las tres con código 0 y prueba VÁLIDA):
  - `casa-zodiaco/README.md`: hoja 1 de 38, sha256 `a85dc799bf3c396d…`.
  - `casa-mb-real/out/results.json`: hoja 43 de 56, sha256 `81659c75a89ea6ee…`.
  - `casa-flyhash/out/PRIMARY.md`: hoja 38 de 122, sha256 `d91a5bd9b090c310…`.
- **Limpieza**: no había `__pycache__` ni `.pyc` en `city/`. Nada que borrar.
- **Anomalías**: ninguna en la cadena ni en las casas. Un error mío de uso al llamar a `prove.py` con
  `../casa-…` (la ruta debe ser relativa a `city/`); lo repetí bien. El README de esta casa, en la
  sección «Estado de esta ejecución», sigue describiendo el bloque 2; no lo toqué porque el encargo
  solo pedía anotar en el LOG.
- **Limitación de siempre**: el bloque 3 prueba que estos archivos **no cambiaron desde este sellado**.
  No prueba que su contenido sea correcto, ni de dónde vino, ni que las herramientas que los generaron
  sean las adecuadas. Los cambios de `casa-conectoma`, `casa-agora`, `casa-mosca` y `casa-taller`
  entre el bloque 2 y el 3 quedan sellados tal cual, sin validar.

## 9. Bloque 4 (re-sellado, 2026-10-31)

Encargo del Alcalde: re-sellado breve tras los cambios de la Cartógrafa. Nadie más escribe ahora.

- **Casas cubiertas** (13 carpetas de `city/`, sin `casa-notaria`): `alcaldia` (40 archivos),
  `casa-agora` (12), `casa-auditoria` (40), `casa-conectoma` (32), `casa-empresa` (19),
  `casa-flyhash` (122), `casa-forja` (47), `casa-mb-real` (56), `casa-micelio` (90),
  `casa-ministro` (2), `casa-mosca` (6), `casa-taller` (9), `casa-zodiaco` (38).
- **Verify antes**: código **1** (`MANIPULACIÓN DETECTADA`), como se esperaba. Cadena íntegra
  (génesis + 3). Diferencias de contenido:
  - `alcaldia`: modificado `bus/ciudad.jsonl` (mensajes nuevos en el bus).
  - `casa-conectoma`: modificados `LOG.md`, `README.md`, `src/transfer.py`; añadidos `out/hubs.json`,
    `out/lesions_open.json`, `out/rate_match.json`, `out/transfer_c1_matched.json`,
    `src/lesions_open.py`, `src/match_rate.py`. Pasa de 26 a 32 archivos.
  - Las otras 11 casas: `OK`, sin cambios.
- **Tests**: `tests/test_notaria.py`, 22 pruebas, todas OK, código 0.
- **Sellado**: `notarize.py`, código 0. Bloque 4 añadido.
  - Hash del bloque 4: `000078851e79d9bfa53d8bb30743b50c1b97c60fba80588a89aa3bf1a182e00e` (nonce 58668).
  - Raíz de casas del bloque 4: `9a9973472e4fde1b308e25d93719b430868fd2514582da42a705920213f36661`.
  - Raíz de `casa-conectoma`: `dca608a1c2826cc598f1b9001653265c5164e58ca77cc3096458b3731b015c98`.
- **Verify después**: código **0**, `RESULTADO: OK`. Cadena de 5 bloques (génesis + 4), las 13 casas en
  `OK (sellada en bloque 4)`.
- **Prueba de inclusión** (`prove.py casa-conectoma/out/lesions_open.json`): código 0, prueba VÁLIDA.
  Bloque 4, sha256 sellado `e0bfcf79007485e10a2455743ebab1d5adae30030e0357ec8546cca67f354e72`, hoja 6 de
  32, 5 pasos hasta la raíz de la casa y 4 hasta la raíz de casas. Archivo en disco coincide con lo sellado.
- **Limpieza**: no quedó ningún `__pycache__` ni `.pyc` en esta carpeta (se usó `PYTHONDONTWRITEBYTECODE=1`
  y `python3 -B`).
- **Anomalías**:
  - Ejecuté `verify.py` dos veces antes de sellar. En la primera escribí la salida en `/tmp/_x`, fuera de
    esta carpeta, y no anoté su código de salida. Borré ese fichero. Solo la segunda ejecución cuenta:
    código 1.
  - Ninguna anomalía en la cadena ni en las casas tras el sellado.
  - La sección «Estado de esta ejecución» del README decía bloque 2. La he actualizado al bloque 4.
- **Limitación de siempre**: el bloque 4 prueba que estos archivos **no cambiaron desde este sellado**. No
  prueba que su contenido sea correcto, ni de dónde vino. Los cambios de `casa-conectoma` y del bus de
  `alcaldia` quedan sellados tal cual, sin validar.
