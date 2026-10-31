# LOG de Neuro-2: casa-mb-real

Diario honesto, en orden cronologico. Etiquetas: medido / supuesto / no_verificado.

## 0. Arranque (2026-10-30 20:42:48 UTC)

- Leido: casa-conectoma (README, LOG, fetch_data.sh, src/conectoma_io.py, out/map_dan_mbon.csv), casa-mosca (README),
  bus (14 mensajes, incl. 10-14 sobre predicted_nt vs consensus_nt).
- **Tomado de casa-conectoma**: el origen de los datos (mismos feather, mismo filtro "significant-only"), la idea de
  leer el subcircuito con is_in sobre columnas numericas, la advertencia consensus_nt vs predicted_nt, el mapa
  DAN->MBON como pista inicial (out/map_dan_mbon.csv), y la lista de "supuestos de casa-mosca" que no se sostienen.
  **No** he reutilizado su codigo de simulacion (reescribo el motor LIF con numba y plasticidad).
- **Tomado de casa-mosca**: el protocolo A (CS+), B (CS-), C (nuevo), pre-test/emparejamiento/post-test, y la regla
  general de depresion KC->MBON gobernada por traza de elegibilidad.
- Dato descubierto al mirar las anotaciones: la columna `instance` ya trae el compartimento (p. ej.
  `MBON01(y5B'2a)_R`, `PAM01(y5)_L`). Es una anotacion de Janelia, no una medicion de conectividad. Lo uso como
  "tabla anotada" y la **valido con conectividad** (anatomy.py). Eso lo vi ANTES de escribir la prediccion; lo declaro.

## 1. Verificacion de la literatura (mensaje del Alcalde: red ampliada)

Descargado de pmc.ncbi.nlm.nih.gov (datos no confiables, solo lectura de texto; nada se ejecuto):
- Aso et al. 2014 eLife "MBON encode valence..." (PMC4273436), pasajes leidos:
  * "Behavioral valence was highly correlated with MBON transmitter type: all MBONs eliciting aversion were
    glutamatergic and all the MBONs eliciting attraction were either GABAergic or cholinergic."  -> **regla de
    valencia por neurotransmisor**, que puedo aplicar a los 97 MBON reales con consensus_nt. Es medido (cita), y
    NO depende de la clase del DAN -> rompe la circularidad que yo temia con la "regla de oponencia".
  * Tabla 1: glutamato = MBON-01..07 (g5b'2a, b2b'2a, b'2mp, b'2mp_bilateral, g4>g1g2, b1>a, a1); GABA = 08..11
    (g3, g3b'1, b'1, g1pedc>a/b); acetilcolina = 12..19 (g2a'1, a'2, a3, a'1, a'3ap, a'3m, a2sc, a2p3p).
  * 15 compartimentos; PPL1 y PAM transmiten castigo y recompensa.
- Hige et al. 2015 Neuron "Heterosynaptic plasticity..." (PMC4674068), pasajes leidos:
  * Emparejar olor + activacion de PPL1-g1pedc (4 pulsos a 2 Hz, empezando 0.2 s tras el inicio del olor, olor de 1 s):
    respuesta del MBON-g1pedc al CS+ 118 -> 24 espigas (-80 %); CS- (olor no emparejado) 110 -> 83 (-25 %).
  * Emparejamiento hacia atras (DAN antes del olor): sin cambio. Orden temporal estricto.
  * La depresion no depende de la espiga del MBON: basta la coincidencia KC-DAN. Las respuestas KC no cambian.
  * La accion de la dopamina esta confinada al compartimento (g1pedc no altera g2a'1 aunque comparten KC).
  * El solapamiento entre representaciones esparcidas define la especificidad de la depresion y la generalizacion.
  * MBON-g1pedc "signals positive valence" -> su depresion = aversion.
- Shiu et al. 2024 Nature (PMC11446845): LIF de cerebro completo: Vrest=-52, Vreset=-52, Vth=-45 mV, tau_m=20 ms
  (2 uF/cm2 x 10 kOhm cm2), tau_syn=5 ms, refractario 2.2 ms, retardo 1.8 ms, w_syn=0.275 mV/sinapsis (parametro
  libre), estimulo Poisson, signo por neurotransmisor. Adopto estos parametros de neurona.
- **Correccion a mi memoria (resultado)**: yo habia escrito MBON09 (g3b'1) = evitacion. Segun Aso 2014b es GABA =
  **atraccion**. Mi tabla de memoria tenia ese error; la sustituyo por la regla por neurotransmisor (verificada).
  Tambien: mi "regla de oponencia" (MBON en compartimento PAM => evitacion) NO es general: g3 y b'1 tienen PAM pero
  sus MBON son GABA (atraccion). Esto hace que el signo del aprendizaje por tipo de DAN sea una prediccion real y no
  una tautologia.
- Sigue **no_verificado**: la asignacion exacta tipo-MaleCNS <-> nombre clasico para MBON22+ (nuevos tipos), y las
  cifras de excepciones PAM/castigo.

## 2. PREDICCION (escrita 2026-10-30 20:42:48 UTC, ANTES de ejecutar ninguna simulacion de aprendizaje)

Protocolo previsto: olor 1 s; US (activacion de DAN) 0.2-1.0 s; 4 emparejamientos; valencia V = sum_j v_j r_j
(v_j = +1 si el MBON es GABA/ACh, -1 si glutamato, de consensus_nt; r_j = tasa del MBON en el olor); indice
normalizado LI = (V_post - V_pre) / sum_j |v_j| r_j,pre.

1. Con cableado real y activacion de **todos los PAM** emparejada con A: LI(A) entre +0.05 y +0.40 (positivo = acercamiento).
   Con **todos los PPL1**: LI(A) entre -0.40 y -0.03. Signo correcto en >= 80 % de las combinaciones semilla x triplete.
   |LI_PAM| > |LI_PPL1| (los MBON glutamatergicos 01/05 reciben mucha KC y estan en compartimentos PAM).
2. Especificidad: |LI(B)| < 0.4 |LI(A)|; |LI(C)| < 0.4 |LI(A)| y proporcional al solapamiento de KC con A.
3. **Tipos de DAN individuales** (27 tipos): signo correcto (PAM +, PPL1 -) en 55-80 % de los tipos con cableado
   real. Con compartimentos barajados: 35-65 % (azar).
4. Controles: shuffle de KC->MBON que conserva grados (global): conserva >= 70 % del efecto (no importa el
   detalle fino KC->MBON). Pesos uniformes: dentro de +-30 %. **Compartimentos barajados (DAN en el compartimento
   equivocado): el efecto cae a < 30 % del real o cambia de signo en >= 30 % de los casos.**
5. Lesiones: sin APL, KC activas 4-5 % -> >= 20 % y el cociente |LI(B)|/|LI(A)| sube de < 0.4 a > 0.7 (se pierde
   especificidad). Silenciar un tipo de DAN suelto con pairing de todos los PAM: reduce LI <= 30 %.
   Emparejamiento hacia atras: |LI| < 20 % del hacia adelante.
6. Robustez: el signo se mantiene en >= 70 % de la rejilla (eta x umbral de KC activa); la magnitud crece con eta hasta saturar.
7. Lo que me sorprenderia: que el shuffle global de KC->MBON destruya el efecto, o que los compartimentos barajados no lo cambien.

(Todo esto es una prediccion, etiqueta supuesto. Al final: seccion "Resultado de la prediccion".)

## 3. Iteraciones tecnicas (v1), con sus fallos

1. **Parser de compartimentos**: la primera version dejaba MBON26 (`b'2d`) y la comparacion PAM05 con 0 compartimentos
   porque las anotaciones mezclan `B` y `b` (beta). Efecto: PAM05 aparecia como "principal fuera de su compartimento"
   (18/20). Corregido (regex acepta b/B): 19/20. Test unitario anadido.
2. **Retardo sinaptico mal hecho (bug del motor)**: la primera version escribia las espigas en el buffer de retardo
   que otras neuronas leian en el MISMO paso (retardo cero para las neuronas con indice mayor). Lo vi al revisar el
   codigo antes de calibrar; separe la fase de lectura (todas) de la de escritura. Nada calibrado con la version mala.
3. **APL casi sin efecto** con ganancias pequenas (28 % -> 25 % de KC con y sin APL). Causa: la realimentacion llega
   tarde y no frena la rafaga del inicio del olor. Soluciones: subir la ganancia KC->APL a 0.1 y APL->KC a 1.0 y
   anadir una rampa de 100 ms a la tasa de PN (supuesto: los PN no se encienden en escalon). Resultado: 7.0 % de KC
   con >=1 espiga (4.0 % con >=2) con APL y 28.6 % sin APL; APL ~45 Hz; KC en reposo 0.0 %. (casa-conectoma: 4.2 % y 28.3 %.)
4. **Escala del MBON**: S_mbon=7000 da ~25 Hz de media con olor (3000 -> 8.7 Hz; 10000 -> 38 Hz); ~1 % de MBON mudos.
5. **eta calibrada con Hige 2015**: un emparejamiento con PPL101 deprime MBON11 un 76 % (eta=2) / 88 % (eta=3) a CS+;
   fijo eta=2.3 (~ -80 %). El CS- sale -13..-17 % (Hige: -25 %): no ajustado, coherente en orden de magnitud.
6. **Carga de la maquina**: el servidor estaba compartido (load average 12-24 con 4 CPU), los trabajos tardan ~4x lo previsto.
7. **Exploracion preliminar (6 semillas, ANTES de los experimentos definitivos y despues de escribir la prediccion)**:
   PPL1 -> LI(A) ~ -0.27; PAM -> ~ +0.03 +- 0.05. Es decir, la parte PAM de mi prediccion (>= +0.05) se veia en el
   borde/fallo. NO modifique la prediccion; lo digo aqui.

## 4. Cementerio de ideas
- *Valencia por regla de oponencia (MBON en compartimento PAM => evitacion)*: descartada tras leer Aso 2014b: es
  circular y falsa para g3 y b'1 (MBON GABA). Se sustituye por NT.
- *Tabla de valencias de MBON de memoria*: descartada (tenia MBON09 mal).
- *Poner los DAN como neuronas LIF con realimentacion KC->DAN y MBON->DAN reales*: pospuesto/descartado: son 282 000
  y 11 000 sinapsis sin dato fisiologico para calibrar la ganancia; lo dejo como limitacion declarada.
- *Una sola ganancia KC->MBON sin normalizar (N0)*: dejo N1 como principal (cada MBON con la misma entrada media) y
  N0 como control de robustez, porque N0 deja el resultado en manos de 4 MBON con el 44 % de las sinapsis.


## 5. Resultados v1 y AUTOCRITICA (2026-10-30 22:23 UTC)

Resultados v1 (main: 30 semillas = 30 tripletes de olores y redes; backward, lesions_apl, sweeps, robust ya corridos;
controls y lesiones de DAN/MBON todavia en cola):
- PPL1-todos emparejado con A: dLI(A) = -0.198 [-0.207,-0.188], signo correcto en 30/30 semillas. PAM-todos: +0.052
  [+0.027,+0.076], signo correcto en 21/30. Por tipo de DAN (23 con clase PAM/PPL1): signo correcto en 18/23
  (PAM 11/15, PPL1 7/8).
- Los 5 que fallan no son ruido sino cableado: PAM12, PAM13, PAM14 (g3, b'1) contactan MBON GABA (atraccion) -> su
  depresion baja la valencia; PPL107 contacta MBON04 (glutamato); PAM05 ~0.
- Con la valencia permutada entre tipos de MBON (500 permutaciones, misma composicion 26/71): aciertos 10.3 de media,
  p95 = 15; el real, 18 (p=0.014).

**Autocritica honesta de v1**:
1. *¿Es basico?* En parte. El signo por tipo de DAN se predice con una multiplicacion de matrices: -(sinapsis DAN->MBON x
   valencia NT)/total. Correlacion con el dLI simulado r=0.87 (Spearman 0.80), 25/26 signos coinciden. La simulacion
   con espigas anade magnitudes, el efecto de la saturacion, la especificidad por solapamiento de KC (r=0.69 entre
   Jaccard(A,B) y dLI(B)/dLI(A)) y los controles de cableado, pero **no** descubre el signo.
2. *¿Hay un control que invalide el resultado?* (a) La valencia por NT es un supuesto verificado en literatura pero
   la unica fuente de signo; con valencia invertida, 5/23 aciertos (simetrico, trivial). (b) La normalizacion N1
   por MBON: probada con N0 (norm_N0): el signo se mantiene (PAM +0.26, PPL1 -0.27) pero la magnitud de PAM se triplica.
   (c) El efecto de PAM depende de cuanto se entrena: con eta alto o 4 emparejamientos el PAM-todos baja a +0.02..+0.04
   y PAM08 cambia de signo (-0.02): la saturacion deprime tambien los MBON de atraccion del mismo compartimento.
   Esto es un resultado y una advertencia: la "recompensa" funciona solo en el regimen de aprendizaje debil/moderado.
3. *¿Que haria falta para sorprender?* Que el cableado fino importara. Hasta aqui lo que importa es la
   *asignacion DAN->MBON* y la valencia de cada MBON. Faltan los controles de KC->MBON (en cola).
4. *Fallo mio*: al anadir las aristas reales extra (PN->APL, APL->MBON, MBON->MBON, KC->KC) con una escala copiada
   de PN->KC, el APL se disparaba a 177 Hz, callaba todas las KC y el aprendizaje desaparecia (PAM -0.012, PPL1
   +0.005). Aislado el culpable (PN->APL con s=0.5): lo corrijo (usa la escala de las entradas al APL) y repito en el
   grupo `extra`. La condicion defectuosa se retira de los resumenes pero queda aqui.
5. *Prediccion*: ver seccion final. Dos errores ya claros: |PAM| < |PPL1| (predije lo contrario) y sin APL la
   especificidad NO se pierde (B/A 0.13 -> 0.17; predije > 0.7).

## 6. Iteracion v2 (2026-10-31 00:04 UTC) y mas fallos

- **Perdida de un experimento**: el grupo `controls` (160 trabajos, ~70 min) murio sin traza en el log al 70 % (el servidor
  compartido iba justo de memoria: 4 workers de ~700 MB mas otros inquilinos de 4 GB; sospecha de OOM, no verificada).
  Rehecho en v2: reanudable (un archivo por condicion), 3 procesos, 12 semillas, solo tipos PAM/PPL1 (25 estimulaciones)
  y el control `real` = semillas 1-12 de `main` (mismos olores). Lo anoto como costo de la maquina compartida.
- **v2 estadistico**: comparacion *pareada* contra el real (misma semilla = mismos olores) con IC bootstrap de la diferencia;
  sin ella, "KC->MBON no importa" seria solo "no veo diferencia a ojo". Con ella el IC es < +-0.006 sobre un efecto de 0.046.
- **v2 de cableado**: tras la autocritica ("no sorprende nada") anadi `recurrent`: MBON->MBON y APL->MBON reales con escala
  barrida y MBON->MBON barajado. Resultado no previsto: a escala alta el cableado real MBON->MBON anula el aprendizaje de
  castigo y el barajado no; es la unica pieza de cableado fino con efecto, y su escala es `no_verificado`.
- **Segunda autocritica**: (1) el resumen "KC->MBON no importa" depende de N1 (ganancia normalizada por MBON) y de la
  lectura lineal +-1; con N0 (sin normalizar) PAM x3 pero el signo se mantiene; no probe N0 combinado con el barajado.
  (2) "PAM-todos" es un estimulo mal elegido (cancelacion): lo he dejado por transparencia pero el resultado serio es por tipo.
  (3) El efecto por tipo de DAN lo carga a menudo un MBON (MBON07 para PAM, MBON14 para PPL1): con 97 MBON, la lectura
  depende de muy pocos tipos.  (4) 1 emparejamiento, ntest=4: ruido de espigas moderado; las semillas lo promedian.
  (5) No corri nada con ambos hemisferios por separado ni con olores de PN medidos.

## 7. Resultado de la prediccion (seccion 2)

| # | Prediccion | Observado | Veredicto |
|---|---|---|---|
| 1a | PAM-todos LI(A) en [+0.05,+0.40] | +0.052 [+0.027,+0.076] | acierto raspando (el IC incluye <0.05) |
| 1b | PPL1-todos en [-0.40,-0.03] | -0.198 [-0.207,-0.188] | acierto |
| 1c | signo correcto >=80 % de semillas | PPL1 100 %, PAM 70 % | fallo (PAM) |
| 1d | |PAM| > |PPL1| | 0.052 vs 0.198 | **fallo** (al reves, x4) |
| 2a | |B|<0.4|A| y |C|<0.4|A| | 0.13 y 0.12 | acierto |
| 2b | C proporcional al solapamiento KC | r = 0.69 (B vs Jaccard A-B) | acierto |
| 3a | signo por tipo correcto 55-80 % (real) | 18/23 = 78 % | acierto (borde alto) |
| 3b | 35-65 % con compartimentos barajados | 7/23 = 30 % | fallo (peor que el azar: sesgo 71/97 MBON de atraccion) |
| 4a | shuffle KC->MBON conserva >=70 % | 100 % (diferencia -0.002 [-0.006,+0.003]) | acierto |
| 4b | pesos uniformes dentro de +-30 % | +0.0002 | acierto |
| 4c | compartimentos barajados <30 % o signo cambia | separacion ~0; PAM cambia de signo | acierto |
| 5a | sin APL KC activas >=20 % | 10.7 % -> 33.2 % | acierto |
| 5b | sin APL |B|/|A| > 0.7 | 0.13 -> 0.17 | **fallo** |
| 5c | silenciar un tipo de DAN <=30 % del efecto | PAM11: 91 %; PPL106: 29 % | fallo (PAM) |
| 5d | hacia atras <20 % | 13 % | acierto |
| 6a | signo en >=70 % de la rejilla eta x theta | PPL1 20/20 celdas; PAM media >0 en 20/20, pero >=70 % de semillas correctas en 12/20 | fallo parcial |
| 6b | magnitud crece con eta hasta saturar | PPL1 si; PAM no monotono | mixto |
| 7 | me sorprenderia: KC->MBON global destruye el efecto, o compartimentos barajados no cambian nada | ninguna de las dos | sin sorpresa de ese tipo |

Marcador: 10 aciertos, 6 fallos, 1 mixto (+ la sorpresa 7 no ocurrio). Lo que mas me enseno: acerte la estructura (compartimentos
si, KC->MBON fino no) y fallo en las magnitudes y en la estimulacion PAM; el efecto de PAM es una resta de dos poblaciones de MBON.

## 8. Cementerio de ideas (final)
- Tabla de valencias de MBON de memoria (MBON09 mal) y regla de oponencia "PAM => MBON de evitacion": descartadas con fuente.
- DAN como neuronas LIF con realimentacion KC->DAN y MBON->DAN reales: descartado (sin dato para calibrar la ganancia).
- `extra_edges` con escala copiada de PN->KC: retirada tras descubrir que PN->APL saturaba el APL (177 Hz).
- `controls` primera ejecucion: perdida (ver sec. 6).
- Predictor estatico como resultado: lo convierto en autocritica (r = 0.87), no en descubrimiento.
- Ideas no hechas por falta de dato o tiempo: estimulacion con subconjuntos de PAM sacados de la literatura (no pude verificar cuales
  activa el azucar), olores de PN medidos, KC->DAN, reversion/extincion, hemisferios por separado.

## 9. Quien me ayudo
- **casa-conectoma (Cartografa)**: datos, filtro, alerta de neurotransmisores, mapa DAN->MBON, lista de supuestos de casa-mosca.
- **casa-mosca (Neuro)**: protocolo A/B/C y regla de depresion con elegibilidad.
- **El Alcalde**: verificacion del problema `predicted_nt` y la red ampliada (lectura de Aso 2014, Hige 2015, Shiu 2024).
- Fuentes leidas (datos no confiables, solo texto): PMC4273436 (Aso 2014b), PMC4273437 (Aso 2014a), PMC4674068 (Hige 2015 Neuron),
  PMC4860018 (Hige 2015 Nature; solo resumen), PMC11446845 (Shiu 2024).
