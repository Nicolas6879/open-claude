# Casa Notaría

Registro notarial **simulado y local**, en forma de cadena de bloques. Sella con
SHA-256 todo lo que producen las casas de `city/` (código, README, LOG, datos y
salidas) y, cuando se vuelve a verificar, dice qué cambió, qué apareció y qué
desapareció, y en qué casa.

Habitante: Notario. Solo biblioteca estándar de Python 3.13. Sin red, sin
wallets, sin claves, sin tokens, sin cuentas. Nada sale de este repo.

> **Qué NO es.** No es una blockchain distribuida. No hay nodos, ni consenso,
> ni red. No hay seguridad real frente a un atacante que reescriba toda la
> cadena. Sellar **no prueba que el contenido sea correcto**: prueba que **no
> cambió desde el sellado**.

## Uso

Todos los comandos se ejecutan desde esta carpeta. Con `PYTHONDONTWRITEBYTECODE=1`
no se genera `__pycache__`.

```bash
export PYTHONDONTWRITEBYTECODE=1
python3 notarize.py        # añade un bloque con el estado actual de city/
python3 verify.py          # comprueba cadena y casas; sale con 0 o 1
python3 prove.py casa-agora/out/results.json   # prueba de inclusión de un archivo
python3 tests/test_notaria.py                  # 22 pruebas (sobre copias temporales)
```

Opciones comunes: `--ciudad DIR` (por defecto, `city/`) y `--cadena FICHERO`
(por defecto, `ledger/chain.json`). Sirven para probar sobre copias.

### Códigos de salida

| Código | Significado |
|---|---|
| 0 | Todo bien (`verify`), bloque añadido o sin cambios (`notarize`), prueba válida (`prove`) |
| 1 | Manipulación detectada: cadena alterada, casa modificada/desaparecida/anómala, archivo alterado |
| 2 | No se puede verificar o probar: falta la cadena, el archivo no está sellado, error de argumentos o E/S |

### Ejemplo de salida de `verify.py` tras alterar copias

```
CADENA: 2 bloques (génesis + 1)
  integridad: OK (enlaces, hashes, génesis y prueba de trabajo de 4 ceros)
CASAS:
  casa-agora: MODIFICADA (sellada en bloque 1)
    modificado: README.md
  casa-mosca: MODIFICADA (sellada en bloque 1)
    desaparecido: LOG.md
  casa-taller: MODIFICADA (sellada en bloque 1)
    añadido: NUEVA.md
RESULTADO: MANIPULACIÓN DETECTADA
```

## Qué se sella

Cada casa es una carpeta de primer nivel de `city/`. Se descubren dinámicamente:
si aparece una casa nueva, `notarize.py` la incluye.

- **Dentro de cada casa** se sella cada archivo, recorrido de forma determinista:
  rutas relativas con `/`, normalizadas a NFC y ordenadas.
- **Se ignoran** `__pycache__`, los `*.pyc` y cualquier componente oculto
  (que empiece por punto, como `.git`).
- **Los enlaces simbólicos no se pueden sellar.** Si aparece uno, el sellado se
  niega y `verify` lo marca como anomalía.
- **Esta casa (`casa-notaria`) no se sella.** Sellarse a sí misma sería circular.
  Su estado se verifica con su propio código y tests, no con la cadena.

## Diseño

### Hojas y árboles de Merkle

- **Hoja de archivo**: `SHA-256(0x00 || ruta || sha256_del_archivo)`. La ruta
  va dentro de la hoja: renombrar un archivo cambia la raíz aunque su contenido
  no cambie. El prefijo `0x00` separa dominios de los nodos internos.
- **Nodo interno**: `SHA-256(0x01 || izquierda || derecha)`.
- **Raíz de una casa**: el árbol de Merkle de sus archivos, ordenados por ruta.
- **Hojas impares**: la última hoja de un nivel se **promociona** tal cual al
  nivel siguiente. **No se duplica**: duplicarla permite que `[a, b, c]` y
  `[a, b, c, c]` tengan la misma raíz (fallo de Bitcoin, CVE-2012-2459).
- **Casa sin archivos**: raíz constante `SHA-256(0x02 || "vacio")`.
- **Árbol de casas**: hojas `(nombre de casa, raíz de la casa)`, ordenadas por
  nombre. Su raíz es `raiz_casas` del bloque.
- **Pruebas de inclusión**: `prove.py` construye la cadena de pasos
  `archivo → raíz de la casa → raíz de casas del bloque`. Cada paso lleva el
  lado (`izq`/`der`) del hermano. El verificador exige que los lados coincidan
  con la estructura que implican (índice y nº de hojas), así que una prueba no
  puede tener pasos de más, de menos ni en el lado equivocado.

### Bloques y cadena

Cada bloque en `ledger/chain.json` tiene:

- `indice`: posición (0, 1, 2…). Es el identificador lógico; **no hay relojes**.
- `anterior`: hash del bloque anterior.
- `casas`: lista ordenada de `{casa, raiz, n_archivos, archivos: [{ruta, sha256}]}`.
  El campo `archivos` guarda el manifiesto, así `verify` puede decir **qué**
  archivo cambió, no solo que cambió algo.
- `raiz_casas`: raíz del árbol de casas.
- `dificultad`, `nonce`, `hash`.

El **hash del bloque** es `SHA-256(JSON canónico sin "hash" ni "nonce" || "|" || nonce)`.
El JSON canónico tiene las claves ordenadas y sin espacios. La **prueba de
trabajo** exige que el hash empiece por **4 ceros hexadecimales**. Minar un
bloque tarda unas decenas de milisegundos.

El **génesis** es fijo: `notaria.py` lo calcula al importar a partir de un
contenido constante (un mensaje y ninguna casa), y da siempre el mismo hash.
`validar_cadena` exige que el bloque 0 del fichero sea idéntico a ese génesis.

### Determinismo

- Sin relojes en el hash ni en el fichero. Dos ejecuciones de `verify.py`
  dan la misma salida exacta, y el mismo contenido da el mismo `chain.json`
  byte a byte (hay un test para cada cosa).
- `chain.json` se escribe con claves ordenadas e indentación fija.

### Qué pasa cuando una casa cambia

1. `verify.py` marca la casa como `MODIFICADA`, con cada archivo cambiado,
   añadido o desaparecido. Sale con código 1.
2. Si el cambio es legítimo (por ejemplo, un vecino actualiza su LOG), se
   ejecuta `notarize.py` de nuevo: se añade un bloque nuevo. El historial
   anterior queda intacto.
3. Una casa que **desaparece** se marca como `DESAPARECIDA` mientras su último
   sellado siga en la cadena. Es una alarma intencionada.

## Pruebas (`tests/test_notaria.py`)

22 comprobaciones, entre ellas:

- Merkle con 1, 2, 3 y 4 hojas (raíces por fórmula); pruebas válidas para
  todas las hojas de árboles de 1 a 9 hojas; pruebas manipuladas rechazadas
  (hoja, índice, hermano, lado, paso de más y de menos); hoja impar no duplicada.
- PoW del génesis válida y rechazo de un nonce alterado.
- Cadena rota: un bloque alterado se detecta, y reescribirlo con hash y PoW
  nuevos rompe el enlace con el siguiente.
- Archivo modificado, añadido, desaparecido y casa desaparecida, detectados
  en una **copia temporal**.
- Copia de las casas reales: sellada, verificada en 0 y manipulada en una copia.
- Ignorar `__pycache__`, `.pyc` y ocultos.
- Determinismo: dos `verify` con la misma salida; mismo contenido, mismo `chain.json`.

Todas las pruebas que manipulan algo trabajan sobre copias en `tempfile`. Nunca
tocan `city/` real ni `ledger/chain.json`.

## Límites (lo que esto no es)

- **No es una cadena distribuida.** Un único archivo local. Nadie más la
  replica ni la comprueba.
- **No hay consenso.** Cualquiera con acceso a la carpeta puede añadir bloques.
- **No resiste a un atacante que reescriba toda la cadena.** Quien reescriba el
  último bloque y el `chain.json` a la vez, con PoW nueva, no deja rastro. El
  génesis está en el código, pero el código también es editable en el mismo
  repo. El sellado detecta cambios *ingenuos*, no un adversario con acceso total.
- **Sellar no prueba que el contenido sea correcto.** Un LOG con datos falsos
  queda sellado tal cual. Sellar prueba que **no cambió después**.
- **Sellar no prueba la procedencia.** Por ejemplo, `casa-agora/data/` contiene un
  CSV que el habitante extrajo de un paquete de PyPI. El sello prueba que ese
  CSV no ha cambiado desde entonces, pero no puede comprobar de dónde vino.
- **No se sellan las herramientas que generaron las salidas.** En `casa-mosca`,
  los scripts de calibración están fuera de la casa; el sello no permite
  reproducir cómo se calibró el modelo.
- **Solo se sella lo que hay en el disco.** Un archivo borrado antes de sellar
  nunca llega a la cadena.
- **No hay firmas.** Un experimento de firmas de un solo uso (Lamport) se
  consideró y no se incluyó: no salió limpio y probado en el tiempo disponible.

## Estado de esta ejecución

El bloque 1 sella las tres casas que existían al ejecutar `notarize.py` (ver `LOG.md`).
