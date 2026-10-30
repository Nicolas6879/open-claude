# LOG de Neuro: casa-mosca

## 1. Decisiones (y por que)

- **Modelo**: LIF con corriente sinaptica exponencial, dt = 0.25 ms. Espigas explicitas, como pide el
  encargo. Un modelo de tasa habria sido mas rapido, pero no tendria espigas.
- **Anatomia**: 50 ORN -> 50 PN (1:1 por glomerulo), 2000 KC con 6 PN al azar (sin repetir), 1 APL con
  inhibicion global, 4 MBON, 4 DAN (2 de recompensa, 2 de castigo). Mantengo el castigo en el codigo
  (`eta_pot`) pero no lo pruebo, para no ampliar el alcance.
- **Olores**: A, B y C como vectores de afinidad sinteticos (12 de 50 glomerulos fuertes, resto <0.15).
  Son aleatorios pero fijos por semilla.
- **Plasticidad**: la dopamina de los DAN de recompensa deprime KC->MBON de forma proporcional a una
  traza de elegibilidad de las KC (tau 1 s). Con elegibilidad lineal, el olor B tambien bajaba un 66%
  (ver seccion 3), asi que cambie la regla (ver mas abajo).
- **Escala temporal del experimento**: ensayos de 1000 ms de olor y 500 ms en blanco; 4 pares de
  entrenamiento. Mas pares daban mas aprendizaje pero el coste en tiempo subia sin mejorar la
  conclusion.
- **Lectura del MBON**: espigas por segundo de la media de los 4 MBON durante el olor. Elegi espigas y no
  corriente porque el encargo pide espigas.
- **Definicion de KC activa**: al menos 5 espigas en 1 s (>= 5 Hz). Con "al menos 1 espiga" el 40 a 60%
  de las KC contaban como activas, y eso no es dispersion. Asi uso la misma definicion en el experimento,
  en las pruebas y en la tabla.
- **Carpeta**: `city/` no existia; la cree con `mkdir -p`. Todo lo escribo dentro de `casa-mosca/`.
- **Scripts de calibracion**: estan en el scratchpad de la sesion (fuera de la casa), no en la casa.
- **Ejecucion**: `OMP_NUM_THREADS=1` acelera ~6x (ver README). Lo documente en el README; no lo forzo
  dentro del codigo para no depender del orden de imports.

## 2. Intentos de Internet (max. ~10 min de esfuerzo)

| Intento | Respuesta | Resultado |
|---------|-----------|-----------|
| `pip download --no-deps flybody` (PyPI) | "Could not find a version that satisfies the requirement flybody (from versions: none)" | No esta en PyPI con ese nombre. No lo busque con otros nombres. |
| `pip download --no-deps neuprint-python` (PyPI) | 200, wheel `neuprint_python-0.6.4` (118 kB) | Descargado en un directorio nuevo del scratchpad. Lo inspeccione con `zipfile` (solo listado y lectura de texto, no lo instale ni ejecute). Borrado al terminar. |
| `curl https://api.github.com/` | 200 | Responde. |
| `api.github.com/repos/google-deepmind/flybody/readme` | 403: "GitHub access to this repository is not enabled for this session. Use add_repo to request access." | No llame a `add_repo`: cambia el conjunto de repos de la sesion y no era necesario para esta tarea. Anotado como bloqueo. |
| `api.github.com/search/repositories?q=hemibrain...` | 403 | Igual que arriba. |
| `github.com/` | 400 | Bloqueado. |
| `raw.githubusercontent.com/` | 301 | No lo seguí. |
| `neuprint.janelia.org` | 000 (sin conexion) | Bloqueado, como dice el encargo. |
| `arxiv.org`, `en.wikipedia.org`, `flywire.ai` | 000 | Bloqueados. |
| `pip index versions fafbseg/navis/flybrain` | Solo salio la advertencia de `pip index` (experimental) | Resultado no concluyente; no seguí. |

**Lo que sacé de neuprint-python** (docs y docstrings, no datos): menciona el dataset `hemibrain:v1.2.1`
y subtipos de KC (KCab-p, KCab-sc, KCg, KCa'b'). Hay una matriz de ejemplo de conectividad KC-KC en un
docstring de `utils.py`. Es una salida de ejemplo en la documentacion, no un conjunto de datos verificado.
**No la use para parametrizar nada**: solo muestra KC->KC, y lo que necesitaba era PN->KC.
**Conclusion**: no obtuve datos reales de conectividad PN->KC ni de MBON-DAN. La anatomia es sintetica.

## 3. Calibracion: lo que hice y lo que falle

Antes de tocar la casa, midi con scripts en el scratchpad. Pasos y fallos, en orden:

1. **Primera pasada con parametros por defecto**: las KC saturaban (60% con >=1 espiga; 2 Hz medios)
   y el APL iba a 150 Hz. Ademas, el MBON respondia a casi todos los olores igual y el aprendizaje
   colapsaba todos los pesos a cero (`W_mean_change` = 0.01). *Causa*: excitacion demasiado alta y tasa
   de plasticidad lineal sin control.
2. **Velocidad**: 650 us por paso con BLAS multihilo; 117 us con `OMP_NUM_THREADS=1`. Causa: hilos de
   BLAS en matrices pequenas. Solucion: documentarlo en el README.
3. **Barrido de excitacion** (`bias_kc`, `w_pn_kc`, `w_apl_kc`): elegi `bias_kc=0`, `w_pn_kc=2.0`,
   `w_apl_kc=1.5` (inhibicion APL->KC), que dan ~5% de KC activas (>= 5 Hz) y ~0.2% en reposo.
4. **Error mio** al fijar los defaults: `w_apl_kc` (inhibicion APL->KC) y `w_kc_apl` (KC->APL) quedaron
   invertidos. Lo detecte porque el APL no coincidia con la calibracion; lo corregi y re-verifique.
5. **Tasa de aprendizaje**: `eta` de 3e-4 a 3e-3 (lineal) saturaba todos los pesos. Bajar a 1e-5 - 1e-6
   dio efectos en el rango util, pero la especificidad era mala: B bajaba un 66% con A entrenado.
   *Causa*: la traza lineal alcanza a las KC con actividad de fondo (0.5 a 2 Hz), que son muchas.
6. **Coincidencia no lineal** (traza al cuadrado): mejoro un poco. Aun asi B bajaba ~37%.
7. **Umbral de elegibilidad** (`elig_thr` = 2, 3, 4): con 4 y `eta_dep` = 3e-5, A baja 66%, B 13%, C 29%.
   Elegi esta configuracion: A baja mucho y B lo menos posible. Con umbral 3 (`eta` 1e-5) la separacion
   es casi la misma (A -72%, B -17%), asi que la eleccion entre 3 y 4 es marginal.

**Residual que no resolvi**: el olor C (nuevo, no entrenado) baja un 28% en la semilla 7 y hasta un 21%
en otras semillas. Creo que es generalizacion por solapamiento de KC (Jaccard 0.05 con A; 0.08 con B) y
por la inhibicion global, que cambia el nivel medio de todas las respuestas. No he verificado esta
explicacion por separado. Lo reporto tal cual.

**Semilla 8**: la discriminacion es solo de 14 puntos (A -44%, B -30%). No la "arregle" con parametros
hechos a medida para esa semilla; la dejo como hallazgo.

## 4. Que aprendi

- La dispersion de KC depende mas de la inhibicion y del umbral que de los pesos PN->KC; con 6 PN por KC,
  el mismo peso excitatorio puede saturar o silenciar.
- La forma de la regla de plasticidad importa mas que la tasa: con elegibilidad lineal, el aprendizaje
  se generaliza a todo el MB; con un umbral y coincidencia no lineal, se concentra en las KC del olor
  entrenado.
- Medir la dispersion con "al menos 1 espiga" engana: parece dispersa al 40%, pero no lo es.
- Un error en el signo o el nombre de un parametro se ve rapido en las tasas del APL; comparar siempre
  contra la configuracion medida.

## 5. Quien me ayudo

Nadie. Trabaje sin ayuda, solo con las herramientas de la sesion; no consulte a otros agentes ni al Alcalde.

## 6. Literatura citada de memoria (sin verificar, sin enlaces)

- Caron, Ruta, Abbott, Axel (2013), sobre convergencia aleatoria de entradas olfativas en el MB:
  motiva los 6 PN por KC.
- Aso et al. (2014, eLife), arquitectura del cuerpo fungiforme y de las neuronas de salida (MBON) y
  dopaminergicas (DAN): motiva el papel de los DAN de recompensa y de castigo.
- Hige, Aso, Rubin, Turner (2015, Nature): la dopamina deprime las sinapsis KC->MBON de las MBON que
  promueven evitar el olor. Es la base de la regla de plasticidad que uso.
- Turner, Bazhenov, Laurent (2008): representacion de olores en las KC (dispersion).
- Eichler et al. (2017, Nature): conectoma del centro de aprendizaje de la larva, para la idea general
  de la conectividad.

Repito: son citas de memoria. No las he comprobado (sin acceso a Internet a los articulos).

## 7. Lo que falta / limitaciones

- Sin datos reales. Todos los parametros son aproximaciones calibradas a mano; en el README se dice.
- Sin LN, sin gamma, sin castigo probado, sin MBON especificos.
- Tres semillas adicionales con discriminacion variable (14 a 38 puntos). Solo una cantidad pequena de
  semillas: no es una estimacion de la varianza.
- `out/activity.json` pesa 1.04 MB (por debajo de 3 MB). No submuestree nada.
- Los tests tardan ~12 s con `OMP_NUM_THREADS=1`.

## 8. Procedimiento

- Descargas temporales en el scratchpad de la sesion (no en /tmp, por la instruccion del sistema) y
  borradas al terminar.
- Ejecuciones con `PYTHONDONTWRITEBYTECODE=1`. Comprobado: no hay `__pycache__` en la casa.
- Verificado: `python3 tests/test_basic.py` (5 de 5 OK); `run_experiment.py` imprime la tabla y escribe
  el JSON; dos ejecuciones dan el mismo md5 de `out/activity.json`; el JSON cumple el contrato.
