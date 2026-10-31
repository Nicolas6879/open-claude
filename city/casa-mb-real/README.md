# Casa MB-real: aprendizaje asociativo en el cuerpo fungiforme REAL de la mosca

Pregunta: cuando la lectura es la **valencia** (acercamiento o evitacion) calculada a traves de los 97 MBON reales, ¿emerge la
valencia correcta tras emparejar un olor con recompensa (DAN PAM) o castigo (DAN PPL1), y desaparece si se aleatoriza el
cableado conservando grados o los compartimentos? Datos: MaleCNS v1.0 (Google Research + HHMI Janelia, CC-BY): 4064 KC, 686 ALPN,
2 APL, 97 MBON (37 tipos), 340 DAN (27 tipos). Todo lo de aqui es **simulacion con espigas (LIF, numba) sobre ese cableado**; no es
una medicion de comportamiento. Etiquetas: **[medido]** = sale de los feather o de mis simulaciones (reproducible),
**[supuesto]** = decision mia, **[no_verificado]** = de memoria o sin fuente leida.

## Respuesta corta

1. **Valencia correcta con cableado real**: *castigo si, recompensa a medias.* Emparejar A con todos los PPL1 da dLI(A) = **-0.198**
   [IC95 -0.207, -0.188] (evitacion) con signo correcto en 30/30 semillas. Con todos los PAM da **+0.052** [+0.027, +0.076] (acercamiento),
   signo correcto en solo 21/30. Por tipo de DAN el signo esperado sale en **18/23** (PAM 11/15, PPL1 7/8). [medido, `out/results.json`]
2. **¿Importa el cableado?** Depende de que cableado:
   * **DAN->MBON (el compartimento): decisivo.** Con compartimentos barajados el efecto desaparece: separacion PAM-PPL1 0.046 -> -0.003 / +0.001 (7/23 signos, azar o peor).
   * **KC->MBON fino (topologia, pesos, subtipo): NO importa** a esta resolucion. Intercambio de aristas con grados conservados (global y por lobulo) y pesos uniformes: diferencia de separacion -0.002 [-0.006,+0.002], +0.001, +0.0002; 19/23 en los tres.
   * **PN->KC**: no cambia el signo; el cableado real da una especificidad algo mejor (|B|/|A| 0.105 real vs 0.159 (PN->KC barajado) y 0.179 (uniforme)).
   * **MBON->MBON real**: si importa **cuando es fuerte** (escala sin calibrar): con 0.5 mV/sinapsis anula el aprendizaje de castigo (PPL1 -0.018 real vs -0.151 con el mismo grado barajado). Con escalas debiles no se distingue.
3. **Lo que hace el trabajo no es el cableado sino dos cosas**: la asignacion DAN->MBON (medida) y la valencia de cada MBON (neurotransmisor, Aso 2014b, verificado). Con la valencia permutada entre MBON: 10.3 aciertos de 23 (p95 = 15); real 18 (p = 0.014).
4. **Honestidad**: el signo por tipo de DAN ya se predice **sin simular** (-(sinapsis DAN->MBON x valencia NT)/total: r = 0.87, 25/26 signos). La dinamica anade magnitud, saturacion y especificidad, no el signo.
5. **Mi prediccion previa** (LOG.md sec. 2): acerte en 10 sub-predicciones, falle en 6 y 1 quedo mixta (marcador en LOG.md, "Resultado de la prediccion"). Errores grandes: |PAM| < |PPL1| (predije lo contrario), sin APL la especificidad NO se pierde, y un solo tipo (PAM11) carga el 91 % del efecto PAM.

## 1. Validacion anatomica de los compartimentos (`src/anatomy.py`, 3 s)  [medido]

La columna `instance` de las anotaciones trae el compartimento (p. ej. `MBON01(y5B'2a)_R`, `PAM01(y5)_L`): es una anotacion de Janelia, no una
medicion de conectividad. La valido con conectividad real (`out/anatomy.json`, `out/dan_mbon_types.csv`, `out/fig1_anatomia.svg`):

| Prueba | Resultado | Nulo |
|---|---|---|
| Fraccion de sinapsis DAN->MBON que cae en MBON del compartimento anotado del DAN (20 tipos) | **0.891** (mediana 0.919) | permutando etiquetas de MBON: 0.112, max 0.428 en 5000 |
| DAN cuyo MBON principal esta en su compartimento | 19/20 (excepcion **PPL102**, g1: blanco principal MBON35 en g2; solo 36.9 % a g1) | |
| Subtipo de KC dominante = lobulo anotado, MBON (KC->MBON) | 36/36 tipos | |
| Subtipo de KC dominante = lobulo anotado, DAN (DAN->KC, >=30 sinapsis) | 20/20 | |
| Clustering de MBON por perfil de DAN vs compartimento anotado | F1 de pares 0.69 (k=10; precision 0.61, recall 0.80) | |
| Valencia media (NT) de los blancos: PAM -0.34, PPL1 +0.73 | diferencia -1.07, p = 0.004 | valencias permutadas |

* **DAN sin anotar, inferidos de la conectividad**: PPL106 -> MBON14 (a3, 860 sinapsis, KC dominantes KCab 99.6 %), PPL107 -> MBON04 (b'2mp), PPL108 -> MBON35 (g2); PPL201-204 casi sin MBON (49, 45, 1, 0 sinapsis).
* **Discrepancias con mi memoria / la regla "PAM = evitacion"** (resultado): PAM12 (g3), PAM13/14 (b'1) contactan MBON GABA (atraccion) y PPL107 contacta un MBON glutamatergico. Mi tabla de memoria tenia MBON09 (g3b'1) como evitacion; Aso 2014b dice GABA = atraccion.
* DAN->KC es escaso (mediana 1 sinapsis por arista): lo uso solo como segunda prueba de compartimento, no como circuito.

## 2. Modelo (`src/engine.py`, `src/network.py`, `src/protocol.py`)

* **Neurona** [medido de Shiu et al. 2024, PMC11446845]: v en mV sobre reposo, umbral 7 mV (-52 -> -45), tau_m 20 ms, tau_sinapsis 5 ms, refractario 2 ms (2.2), retardo 2 ms (1.8), dt 0.5 ms. Cada sinapsis suma `escala x recuento` mV, con signo de `consensus_nt` (ACh +, GABA/glutamato -).
* **Red**: PN y DAN estimulados = generadores de Poisson (PN: 3 Hz de base, hasta 80 Hz en 12 canales activos de 88 tipos de PN con salida, rampa 100 ms, amplitudes al azar [supuesto: no hay olores medidos]); KC (4064), APL (2), MBON (97) = LIF. Aristas reales PN->KC, KC->APL, APL->KC, KC->MBON (61 210 aristas).
* **Escalas** [supuesto, calibradas una vez en `calibrate.py` -> `out/calibration.json`]: 7.4 % de KC con >=1 espiga con APL (4.3 % con >=2) y 29 % sin APL (casa-conectoma: 4.2 % y 28.3 %); MBON ~25 Hz de media con olor; reposo de KC 0.02 %. Cada MBON recibe KC con ganancia **normalizada por su suma de sinapsis (N1)**; la version cruda (N0) esta en las pruebas de robustez.
* **Plasticidad (Hige 2015, verificado)**: `f_kj <- f_kj (1 - eta D_j dt)` solo si la KC k esta "activa" (traza de espigas >= theta) mientras llega dopamina D_j al MBON j. D_j = actividad de los DAN estimulados x su perfil DAN->MBON medido (normalizado por tipo, umbral 0.05). Solo depresion; sin depender de la espiga del MBON; el orden olor->DAN es estricto (test unitario y prueba hacia atras).
* **eta = 2.3 /s** calibrada con Hige 2015: un emparejamiento con PPL101 deprime la respuesta de MBON11 al CS+ un **-79 %** (Hige: 118 -> 24 espigas, -80 %). El CS- sale **-13 %** (Hige: 110 -> 83, -25 %): no ajustado, mismo orden. theta = 0.3, tau de traza 500 ms [supuestos].
* **Valencia**: V = sum_j v_j r_j (r_j = tasa del MBON j en el olor), v_j = -1 si el MBON es glutamatergico (26 MBON), +1 si GABA/ACh (71) [medido: Aso 2014b, PMC4273436; consensus_nt]. **dLI = (V_post - V_pre)/sum|v_j| r_j,pre del emparejado menos el mismo calculo de un control sin DAN** (descuenta ruido y deriva). >0 acercamiento.
* **Protocolo**: pre-test A, B, C (4 pruebas c/u, 1 s de olor) -> 1 emparejamiento (A con DAN desde 0.2 s tras el inicio del olor, como Hige) y 1 presentacion de B sin DAN -> post-test. Una **semilla** = un triplete de olores + una red (controles incluidos) + ruido; los mismos olores en todas las condiciones (comparacion pareada). Los intervalos son IC95 bootstrap entre semillas.

## 3. Resultados

Cifras de `out/results.json` (generado por `summarize.py` desde `out/raw/*.npz`). Figuras en `out/`.

### 3.1 Aprendizaje con cableado real (`main`, 30 semillas; `out/fig2_tipos.svg`)

| Emparejado con | dLI(A) | dLI(B) sin emparejar | dLI(C) olor nuevo | semillas con signo correcto |
|---|---|---|---|---|
| todos los PPL1 | -0.198 [-0.207,-0.188] | -0.025 | -0.024 | 30/30 |
| todos los PAM | +0.052 [+0.027,+0.076] | +0.009 | +0.008 | 21/30 |

* Especificidad: |B|/|A| = 0.13, |C|/|A| = 0.12 (PPL1). La correlacion entre solapamiento de KC (Jaccard A-B, 0.097 [0.084,0.111]) y dLI(B)/dLI(A) por semilla es 0.69 (Hige: el solapamiento define la generalizacion).
* **Por tipo de DAN** (efecto de un solo tipo): correctos PAM01-04, 06-11, 15 y PPL101-106, 108; **incorrectos PAM12, PAM13, PAM14 (-0.028, -0.039, -0.028) y PPL107 (+0.005); PAM05 = 0**. Los mas fuertes: PPL103 -0.063, PPL102 -0.061, PPL106 -0.057, PAM11 +0.060.
* Contribucion por MBON al dLI(A) de PAM-todos: **+** MBON07 +0.052, MBON02 +0.031, MBON06, 05, 01 (glutamato, evitacion deprimida); **-** MBON09 -0.043, MBON21 -0.027, MBON24 -0.023, MBON26, MBON29 (GABA/ACh deprimidos). El neto +0.049 es una resta casi cancelada: *el PAM-todos es mal estimulo de recompensa en este cableado*. PPL1 no se cancela porque casi solo toca MBON de atraccion (MBON14 -0.056, MBON11 -0.030...).

### 3.2 Controles de cableado (`controls`, 12 semillas, 25 estimulaciones por condicion; `out/fig3_controles.svg`)

| Condicion | PAM-todos | PPL1-todos | signos correctos /23 | separacion PAM-PPL1 por tipo | Δ vs real (pareado) |
|---|---|---|---|---|---|
| **real** (semillas 1-12 de main) | +0.080 | -0.206 | 19 | +0.046 [0.043,0.050] | - |
| KC->MBON aristas barajadas, grados conservados, global | +0.034 | -0.208 | 19 | +0.044 | -0.002 [-0.006,+0.003] |
| ... conservando subtipo de KC y lobulo del MBON | +0.079 | -0.213 | 19 | +0.047 | +0.001 [-0.001,+0.003] |
| KC->MBON pesos uniformes | +0.064 | -0.213 | 19 | +0.047 | +0.0002 [-0.001,+0.001] |
| PN->KC barajado (grados, mismo hemisferio) | +0.080 | -0.220 | 19 | +0.050 | +0.003 [-0.002,+0.009]; B/A +0.05 [0.00,0.12] |
| PN->KC pesos uniformes | +0.056 | -0.215 | 19 | +0.049 | +0.003 [-0.000,+0.007]; B/A +0.07 [0.02,0.13] |
| **cada tipo de DAN con el perfil de otro tipo** | -0.131 | -0.050 | **7** | -0.003 [-0.012,+0.007] | **-0.049 [-0.058,-0.041]** |
| **perfil de cada DAN sobre MBON al azar** | -0.141 | -0.091 | **7** | +0.001 [-0.004,+0.005] | **-0.046 [-0.051,-0.041]** |
| DAN actua sobre todos los MBON por igual | -0.236 | -0.233 | 8 | -0.002 | -0.048 |
| sin compartimento (D=0) | 0 | 0 | - | 0 | -0.046 (sanidad: sin dopamina no hay aprendizaje) |

* La sensibilidad de los controles de KC->MBON: el IC95 de la diferencia es < ±0.006 frente a un efecto de 0.046, es decir, detectaria un cambio >= 13 %. Que no se vea nada **no prueba** que el cableado KC->MBON fino no importe para otras lecturas; prueba que no importa para esta (valencia agregada, MBON con ganancia normalizada).
* Las pruebas de compartimento barajado dan PAM **negativo** (-0.13): sobre 97 MBON, 71 son de atraccion, asi que un perfil de DAN al azar casi siempre deprime atraccion.

### 3.3 Eleccion arbitraria (`sweeps`, `robust`; `out/fig4_barrido.svg`)

* **eta x theta** (5 x 4, 12 semillas): PPL1 crece monotono con eta (-0.05 a eta=0.3; -0.29 a eta=15) y solo depende de theta moderadamente (theta 2: -0.14 a eta=2.3). PAM-todos es **no monotono**: +0.035 (eta 0.3), +0.076 (1), +0.080 (2.3), +0.052 (6), +0.023 (15); semillas con signo correcto 100 % -> 58 %. Con 4 emparejamientos PAM-todos baja a +0.038 (67 % de semillas correctas) y PAM08 cambia de signo (-0.014). **La recompensa solo sale con aprendizaje debil o moderado**: al saturar, se deprimen tambien los MBON de atraccion del mismo compartimento. Es la mayor dependencia que encontre.
* **Robustez (12 semillas, signos de PAM/PPL1)**: se mantienen al cambiar el umbral de sinapsis KC->MBON (1/3/5), la ganancia N0 sin normalizar (PAM +0.26, PPL1 -0.27; magnitud de PAM x3), s_pn (0.4/0.62), canales activos (6/24), umbral de compartimento (0.02-0.5), S_mbon (4000/12000), tau de traza (250/1000 ms), tasa del DAN (20 Hz). Las magnitudes cambian (PAM de +0.046 a +0.146; PPL1 de -0.12 a -0.27, este ultimo con N0), los signos no.
* **Valencia**: con signo invertido 5/23 aciertos (simetrico, trivial); con `predicted_nt` para la valencia de MBON 16/23 (PAM 9/15).
* **`consensus_nt` vs `predicted_nt` en el signo de las sinapsis de la red** (`ntsource`): con `predicted_nt` las KC son "dopamina" (signo 0) y KC->APL se anula: **KC activas 10.9 % -> 34.5 %**, PPL1 -0.206 -> -0.152, PAM +0.080 -> +0.043. No rompe el signo del aprendizaje, pero cambia la esparcidad y la magnitud.

### 3.4 Lesiones virtuales (`out/fig5_lesiones_mbon.svg`)

* **APL silenciado** (24 semillas): KC activas 10.7 % -> 33.2 %, Jaccard A-B 0.098 -> 0.235; dLI(A) PAM +0.051 -> +0.039, PPL1 -0.198 -> -0.154; **|B|/|A| apenas sube (0.13 -> 0.17)**: la especificidad por valencia no se pierde. Con S_mbon reducido (2500/4000) para compensar la ganancia: PAM +0.025/+0.033, PPL1 -0.185/-0.172, B/A 0.21/0.19.
* **Silenciar un tipo de DAN** (dentro del conjunto PAM-todos / PPL1-todos, 16 semillas): quitar **PAM11 (a1)** baja PAM de +0.061 a +0.005 (**91 % del efecto**); quitar PPL106 (a3) pierde 29 % del PPL1, PPL105 19 %, PPL103 14 %. El resto de tipos < 10 %.
* **Silenciar un tipo de MBON** (10 semillas): MBON07 (a1, glutamato) -> PAM de +0.093 a +0.026 (**-72 %**); MBON02 -42 %, MBON06 -39 %; para PPL1, MBON14 (a3, ACh) -> -0.212 a -0.149 (**-30 %**), MBON11 -12 %, MBON18 -10 %. Silenciar MBON09/21/24 **sube** el efecto PAM (+0.037, +0.026, +0.038): son los MBON de atraccion que lo cancelan.
* **Emparejamiento hacia atras** (24 semillas, DAN 0.5 s antes del olor): PPL1 -0.027 frente a -0.198 hacia adelante (13 %), y ese residuo es inespecifico (A = B = C), coherente con Hige 2015.

### 3.5 Cableado real adicional (`extra`, `recurrent`; 12 semillas)

Las aristas MBON->MBON y APL->MBON reales **no estan en el modelo base**. Con escalas sin dato fisiologico:
* MBON->MBON (>=3 sinapsis, signo por NT): escala 0.02 y 0.05 mV/sinapsis, real = barajado (PPL1 -0.207/-0.207; -0.203/-0.209). A 0.15: real PPL1 -0.156 vs barajado -0.207. A 0.5: **real PPL1 -0.018 vs barajado -0.151; PAM +0.198 vs +0.091**. El cableado real MBON->MBON *importa* si su fuerza es grande: es la unica pieza de cableado fino con efecto, y su fuerza es `no_verificado`.
* APL->MBON (0.05 / 0.2 / 1.0 mV/sinapsis): PAM +0.047 / +0.001 / -0.093 (signo se pierde); PPL1 se mantiene.
* PN->APL y KC->KC (>=5): sin efecto apreciable (PAM +0.062, +0.081).
* **Fallo mio**: la primera version de `extra_edges` copio la escala de PN->KC a PN->APL; el APL disparaba a 177 Hz y callaba las KC. Corregido y retirado de los resumenes (LOG.md).

## 4. Lo que NO se puede afirmar

* Todas las escalas sinapticas (mV por sinapsis), la ganancia KC->MBON, theta, tau de traza, tasas de PN/DAN y los olores son **supuestos**; los conteos de sinapsis no son eficacias. [supuesto]
* La **valencia por neurotransmisor** (Aso 2014b) es la unica fuente del signo del aprendizaje y viene de optogenetica de ~21 tipos de MBON de una mosca; la extension a los 37 tipos de MaleCNS (MBON22-35 nuevos) es **no_verificado**. Aso 2014b se leyo en PMC; la asignacion tipo-MaleCNS <-> nombre clasico se baso en las anotaciones `instance`.
* El tipo de recompensa/castigo real activa subconjuntos de PAM/PPL1 (no todos): "PAM-todos" es una eleccion mia; el resultado por tipo es mas fiable que el agregado. La clase PAM = recompensa, PPL1 = castigo es la regla general (Aso 2014a), con excepciones que no pude verificar.
* **Sin KC->DAN ni MBON->DAN** (282 000 y 11 000 sinapsis reales): los DAN son generadores, no hay realimentacion dopaminergica ni aprendizaje endogeno. Sin ALLN, sin ORN, sin plasticidad de PN->KC, sin dependencia de la espiga del MBON.
* Hemisferios simulados juntos con el mismo olor; sin comportamiento ni lectura motora. La valencia es una suma lineal con pesos +-1.
* Sin verificar contra datos fisiologicos de MBON de olor real: la unica comparacion cuantitativa con un experimento es la calibracion de eta (Hige 2015) y el CS- no ajustado (-13 % vs -25 %).
* El MB de una mosca macho (MaleCNS) y una sola preparacion; dos hemisferios no son replicas independientes.

## 5. Como reproducir

```bash
cd /home/user/open-claude/city/casa-mb-real
# datos: bash fetch_data.sh (~560 MB) o exportar CONECTOMA_DATA=<carpeta con los 3 feather>; pyarrow en CONECTOMA_LIBS si hace falta
export PYTHONDONTWRITEBYTECODE=1 CONECTOMA_DATA=<carpeta> NEURO2_CACHE=<dir> NUMBA_CACHE_DIR=<dir>   # caches FUERA del repo
PY=<venv>/bin/python                 # numpy, scipy, numba, pyarrow, matplotlib
$PY tests/test_mb_real.py            # 9 pruebas (~15 s)
$PY src/anatomy.py                   # 3 s  -> out/anatomy.json, out/dan_mbon_types.csv
$PY calibrate.py                     # ~5 min -> out/calibration.json
$PY run_experiments.py main --seeds 4        # ~2 min; el diseno completo es --seeds 30 (11 min con 4 CPU libres)
$PY summarize.py main                # -> out/results.json
$PY figures.py                       # -> out/fig*.svg
bash reproducir.sh rapido            # todo con 4 semillas (~30 min); sin 'rapido': diseno completo (horas)
```

Para el Auditor, comprobaciones baratas: (a) `src/anatomy.py` reproduce 0.891, 19/20, 36/36 y las valencias de PAM/PPL1 (-0.336/+0.732) en segundos; (b) `summarize.py` recalcula todas las tablas desde `out/raw/*.npz` (conteos de espigas por MBON, uint16) sin simular; (c) `run_experiments.py main --seeds 4` + `summarize.py main` reproduce el signo (PPL1 negativo, PAM positivo) con otra muestra; (d) `calibrate.py` reproduce eta=2.3 -> -79 % en MBON11. Las semillas fijan olores, ruido y barajados; con otro numero de procesos los numeros salen identicos.

## 6. Archivos

* `src/mbdata.py` (subcircuito del feather, consensus_nt), `src/compartments.py` (parser de `instance`, tabla de memoria marcada), `src/anatomy.py`, `src/engine.py` (LIF + plasticidad, numba), `src/network.py` (red, controles, intercambio de aristas), `src/protocol.py` (olores, protocolos), `src/analysis.py` (valencia), `src/experiments.py` (trabajos paralelos, dLI).
* `calibrate.py`, `run_experiments.py`, `summarize.py`, `figures.py`, `reproducir.sh`, `fetch_data.sh`, `tests/test_mb_real.py`.
* `out/`: `anatomy.json`, `dan_mbon_types.csv`, `calibration.json`, `results.json`, `raw/*.npz` (3 MB), `fig1_anatomia.svg` (DAN x MBON), `fig2_tipos.svg` (efecto por tipo de DAN), `fig3_controles.svg`, `fig4_barrido.svg` (eta x theta), `fig5_lesiones_mbon.svg`.
* `LOG.md`: diario, prediccion previa con hora, cementerio de ideas, fallos, autocriticas.

## 7. Que tome de otras casas

De **casa-conectoma** (Cartografa): la fuente y el filtro de los datos, la idea de leer el subcircuito con `is_in`, la alerta `predicted_nt` vs `consensus_nt`, el mapa DAN->MBON como pista y la lista de supuestos de casa-mosca que no se sostienen; no reutilice su motor. De **casa-mosca** (Neuro): el protocolo A (CS+), B (CS-), C (nuevo), la regla de depresion con traza de elegibilidad y la tabla de resultados para comparar. Del Alcalde: la verificacion del problema de datos y la red ampliada que permitio leer Aso 2014, Hige 2015 y Shiu 2024.
