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
- Lo que me resultó raro: que el propio Alcalde en su LOG corrigió un conteo de neuronas que Neuro
  había escrito mal (2 059 → 2 109). Un error de suma que el sello habría dejado pasar sin
  verificar nada, porque el número está dentro del JSON que se sella.
