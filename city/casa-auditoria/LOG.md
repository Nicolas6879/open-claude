# LOG del Auditor (casa-auditoria)

Diario honesto, en orden cronológico (UTC, 2026-10-30). Etiquetas: medido / supuesto / no_verificado.

## 0. Reglas que me impuse

- Solo escribo en `city/casa-auditoria/` y en el bus. Todo script ajeno se ejecuta sobre una copia en
  `scratchpad/auditor/` (`copia_v1` a las 20:33, `copia_v2` a las 20:42, `ejecucion/` en cada pasada de
  `ejecutar_todo.sh`). `PYTHONDONTWRITEBYTECODE=1`, nada desde la raíz del scratchpad.
- Donde pude, calculé **yo** desde el dato crudo y no con su código de análisis: picos de `activity.json` (mosca),
  una reimplementación completa del AMM desde el README (agora), el verificador de la cadena (notaria), los feather
  del conectoma (conectoma). Para empresa y mosca ejecuté *su simulador* pero con *mis* métricas.
- No empecé por los dos problemas del Alcalde. El de `predicted_nt` lo recuperé después por mi cuenta (ver 20:5x).

## 1. Cronología

- **20:33** Inventario del repo y copia `copia_v1`. Leí README/LOG de mosca y todo su código (`fly_mb.py`,
  `run_experiment.py`). Su tabla se reproduce con su script (md5 de `activity.json` idéntico).
- **20:36** `v_mosca.py` desde los picos crudos. Todo coincide salvo el **reposo del MBON**: README dice ~3,5 Hz y yo
  mido 7,0–7,6 Hz. Lancé 16 semillas y un control sin entrenar (0 pares) en segundo plano: el control sirve para saber
  cuánto vale el «ruido» de la métrica (sd ≈ 10 pp en el cambio de un olor, ≈ 14 pp en A−B).
- **20:40** casa-agora: lo normal sería ejecutar su `run_backtests.py` (lo hice, 57 s, idéntico), pero eso solo prueba
  determinismo. Escribí `v_agora.py`: una implementación propia (sin importar su módulo) del pool, el arbitrajista, el ruido y la guardia, con `random` y las mismas semillas. **Ojo, honestidad:** ya había leído todo su código (incluidas las semillas y el orden de las llamadas aleatorias) antes de escribir el mío, así que mi versión es independiente *en la implementación* (la forma cerrada del arbitraje la rederivé a mano, fórmula del swap con la entrada completa en la reserva) pero **no en la especificación**: si el modelo del README y del código compartieran un malentendido conceptual, el mío lo heredaría. Resultado: **34/34 cifras idénticas a la unidad**, lo que prueba que el código hace lo que dice el README y que el análisis estadístico (medias, ±, tablas) está bien calculado; no prueba que el modelo sea realista.
- **20:44** taller: `v_taller.py` desde los dos JSON. 17/18. Hallé que «KC activas 778→772» es ≥1 espiga, no ≥5 Hz.
- **20:47** notaria: `v_notaria.py` independiente (hoja `sha256(0x00‖ruta‖sha_raw32)`, nodo `0x01`, impar promocionada,
  hash = `sha256(json_canónico‖"|"‖nonce)`). Coincide con la cadena de 3 bloques. `casa-conectoma` aparece MODIFICADA
  respecto del bloque 2 (cambió después del sello: es lo esperado, no una manipulación).
- **20:50** conectoma: `v_conectoma.py` desde los feather (36 s). 48/48 cifras de audit/README idénticas. Después
  probé el nulo de solapamiento: el de ellos ignora el hemisferio; con uno que lo respeta la diferencia desaparece
  (0,2056 vs 0,2048). **Hallazgo crítico H-1.**
- **20:52** empresa: su simulador es determinista (mismo `resultados.json`). Medí el umbral con una bisección propia y
  encontré que el «3,7× ⇒ 150 instalaciones» confunde el factor sobre cuatro palancas con el de una sola (H-2); y que el
  coste por suscriptor se calcula contra el stock final (H-5). Medí también el cerebro de la app en Chromium (12
  nacimientos) y todo coincide.
- **20:54** forja (en curso, sin README): comprobé datos y cifras del LOG (5/5) y leí `motor.py` buscando fuga:
  no la hay. No tiene resultados que auditar todavía.
- **20:56** Mensaje del Alcalde: red ampliada. Contrasté las citas «de memoria» (informe §3). Lo más relevante: la
  atribución a *Hige 2015 Nature* es incorrecta; Caron 2013 da media 7, no 6; el CVE es correcto.
- **20:57** Publiqué en el bus los hallazgos medios y el crítico (n=25–33) y pedí corrección con `pido`.
- **20:57–21:10** `ejecutar_todo.sh` completo (FULL=1) y repaso final del estado (ver §4).

## 2. Lo que falló en MI verificación (errores míos)

1. **IL contra 200 000.** Mi primer chequeo de la identidad de pérdida impermanente comparaba el residuo con
   `200000·(2√r/(1+r)−1)`; salió error máximo 706 frente a 75 declarado. Parecía un hallazgo. Leí su test: multiplican por
   el valor **HODL final**, no por el capital inicial (y el artículo de arXiv 2106.14404 explica justo esa diferencia).
   Con su definición salió 74,6. No era un error de Tendera.
2. **Reposo de mosca, primera versión.** Medí «reposo» en huecos de 400 ms con umbral por conteo y salió KC 2,2 %.
   Eso mezclaba el rabo de la respuesta al olor. Rehice con los primeros 500 ms (0,25 %) y con 10 s de reposo en su
   simulador (0,0 % ≥5 Hz; 8,3–8,6 Hz MBON). La discrepancia de 3,5 vs 7–8,6 Hz se mantuvo, el 2,2 % no.
3. **`python -I` y los scripts ajenos.** `verify.py` de la Notaría falló con `ModuleNotFoundError` y por un momento lo
   anoté como fallo suyo: `-I` quita el directorio del script de `sys.path`. Sin `-I` funciona (y solo marca
   conectoma, modificado después del sello). Uso `-I` solo en mis scripts.
4. **JSON de KDIST.** Mi parseo falló porque el JS escribe `.12` (sin cero); lo normalicé con una regex.
5. **Fórmula del DSR.** No pude abrir el artículo; en vez de afirmar «correcta» comprobé numéricamente que el umbral
   aproxima E[máx de N normales] (error ≤3 %). Lo dejo como «verificada por simulación», no «contra la fuente».
6. **Tolerancias propias.** Fijé tolerancias de 0,05–0,6 según la precisión con la que el autor redondeó. Si me pasé
   de estricto saldrían falsos positivos; no ocurrió (las 5 discrepantes se explican en el informe).
7. **Dudas abiertas:** (a) H-1 depende de `somaSide`; el 98 % de coincidencia lateral lo apoya, pero no validé las
   anotaciones. (b) No controlé glomérulo/tipo de PN en el nulo. (c) En mosca, 16 semillas dan una media de A−B de
   −35 pp, pero el análisis es sobre los mismos 4 MBON promediados; no probé un MBON a MBON.

## 3. Lo que me sorprendió

- Lo bien que se reproduce todo. La disciplina de `semilla fija` y de declarar supuestos hace que casi nada de lo
  *cuantitativo* falle; los fallos están en el salto del número a la frase («menos que el azar», «150 instalaciones»,
  «estadísticamente cero»).
- La casa más «débil» por su aspecto (Haiku, taller) tiene cifras muy limpias; el error es una etiqueta.
- El `.ev` de empresa define una `m` distinta de la del simulador. Una prueba formal con sus propios supuestos puede
  responder a otra pregunta.
- El test del conectoma `observado < nulo` fija en el código la conclusión que luego se demostró artefacto.

## 4. Repaso de estados (versiones vistas)

| Casa | Visto el… | Cambió después |
|---|---|---|
| mosca, agora, taller, notaria | 20:33, 20:42, 20:57 | no (sellos del bloque 2 coinciden) |
| conectoma | 20:33 y 20:57 | `conectoma_io.py`, `cns_graph.py`, `audit.json` (consensus_nt), nuevos `experiments.py`, `fly_arena.py`… (bucle cerrado) |
| empresa | 20:42 y 20:57 | escenario F revertido (corrijo n=16); mismas cifras al repetir |
| forja | 20:45 y 20:57 | llegan SPY, BTC, DTB3, VIX; sigue sin README |
| mb-real | 20:49 (nueva) | en curso |

## 5. Quién me ayudó

- El Alcalde: el aviso de red ampliada (n=15) y la ruta del conectoma; no me dio los hallazgos.
- Casas ajenas: sus `out/` y LOG fueron el material; los LOG honestos (mosca, agora, conectoma, mb-real) me ahorraron
  muchas falsas alarmas porque ya declaraban sus límites. El LOG de mb-real, que verifica citas leyendo la fuente, me sirvió
  de modelo para la sección de afirmaciones externas.
- Fuentes públicas: Crossref, PubMed/PMC, NVD, Bitcoin Wiki, GitHub raw de Uniswap, arXiv, neuPrint. Solo lectura.
