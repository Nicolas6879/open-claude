# Casa Conectoma: cableado real de la mosca (MaleCNS v1.0)

Dos partes. La **parte A** (abajo, sin cambios de conclusion) audita el modelo de casa-mosca y simula el cuerpo
fungiforme con cableado real. La **parte B** (siguiente) intenta el experimento grande: el SNC completo en bucle
cerrado con una mosca virtual. Tras la ronda de cierre, la ventaja del cableado real sobre el aleatorizado **no se sostiene** al igualar el regimen
de actividad (G 0.55 frente a 0.48, IC95 solapados). Ademas **la mosca no navega** con ninguna de las lecturas motoras
que probe, y los hubs ORN->DN (interneuronas locales del lobulo antenal) son el unico efecto medido de lesion. Todo lo de aqui es de MaleCNS v1.0 (CC-BY), salvo que se indique.

## Parte B. SNC completo en bucle cerrado (v3)

### Que se construyo
- `src/cns_graph.py`: grafo dirigido de los 211 577 cuerpos del archivo (25.6 M aristas, n de sinapsis) en CSR.
  Signo por neurotransmisor de consenso, con la convencion de Shiu et al. 2024 (PMC11446845, leido en el texto
  completo): GABA y glutamato inhibitorios; dopamina, octopamina y serotonina excitatorias; "unclear" = 0.
- `src/lif_engine.py`: LIF de todo el SNC en numba, con los parametros de Shiu et al. (verificados en su texto):
  tau_m = 20 ms (R·C = 10 kOhm cm2 x 2 uF/cm2), V_rest = V_reset = -52 mV, umbral -45 mV, refractario 2.2 ms,
  tau sinaptica 5 ms, W_syn = 0.275 mV por sinapsis (valor fijo de su modelo). dt = 1 ms (supuesto, por coste).
  Linea base 0 Hz, como en Shiu.
- `src/fly_arena.py`: arena 2D, fuente de olor en el origen, c = exp(-r/20 mm), dos antenas separadas 2 mm.
  Entrada a ORN: transduccion logaritmica log(1 + c/0.01) (ver LOG: la lineal dejaba a la mosca ciega).
  Lado de cada ORN = lado de sus PN de salida (2628 ORN: 948 izquierdas, 1680 derechas; ver "limitaciones").
  Motor: giro = K_T * (tasa DN izquierdas - tasa DN derechas - sesgo(c)), avance constante 8 mm/s.
- `src/transfer.py`: experimento de control en bucle abierto (el que si da resultado, ver abajo).
- `src/rewire.py`: cableado aleatorizado que conserva grado de entrada y de salida (intercambio de destinos).
- `src/hubs.py`, `src/experiments.py`, `src/hubs_io.py`: caminos mas cortos ORN->DN, lesiones y el bucle cerrado.
  Los subcomandos `main` y `lesions` estan escritos pero **no se ejecutaron** (ver "No hecho").

### Mapeo sensorial y motor (decisiones)
- **Sensor**: ORN de tipo `ORN_*` (2639 cuerpos; 2628 con lado asignado). Afinidad por glomerulo fija (semilla 2024),
  uniforme en [0.3, 1]. Supuesto mio: sin datos de respuesta de olor real.
- **Motor**: todas las neuronas con `superclass == descending_neuron`, por lado L/R (656 izquierdas, 648 derechas;
  10 "M" excluidas). **No** uso tipos identificados por funcion. Los tipos que sugirio el Alcalde existen en
  MaleCNS (medido, body-annotations): DNp09 (4 cuerpos, 2L/2R), MDN (4), DNa02 (2, 1L/1R), DNp20 (2), DNpe017 (2).
  Hay 1314 cuerpos DN en total, no "1303 premotoras". Su funcion (avance, retroceso, giro) en esta reconstruccion
  **no esta verificada**: lo sugirio el Alcalde desde busquedas web y no lo comprobe en la literatura primaria.

### Resultado principal: ganancia sensoriomotora (bucle abierto, `out/transfer.json`)
Olor solo a un lado; G = (A_izq - A_der)/2 en Hz por unidad de asimetria de olor; 5 semillas; IC95 bootstrap sobre semillas.

| Red | G (c = 0.25) | G (c = 1.0) | Sesgo L-R comun M (c = 1.0) |
|---|---|---|---|
| **Conectoma real** | 0.11 [0.06, 0.16] | **0.55 [0.51, 0.59]** | 0.13 [0.06, 0.19] |
| Cableado aleatorizado (grados conservados) | 0.07 [0.06, 0.08] | 0.05 [-0.07, 0.15] | -6.3 [-6.5, -6.2] |
| Neurotransmisores barajados | 0.19 [0.02, 0.32] | -0.06 [-0.12, 0.00] | -2.3 [-2.5, -2.1] |

Lectura **original** (antes del control igualado; ver la ronda de cierre mas abajo, que la revisa): a concentracion alta,
el cableado real transmitia la asimetria del olor con una ganancia ~10 veces mayor que el aleatorizado, con IC95 sin solape.
Medido con 5 semillas, pero el aleatorizado estaba en otro regimen. Los controles de neurotransmisores
barajados pierden esa transmision a concentracion alta: el signo de cada neurona importa para la transmision
ipsilateral (medido, no interpretado mecanicamente). A concentracion baja no hay diferencia clara.

Advertencia: el sesgo L-R comun de la red aleatorizada (-6.3 Hz) es enorme; esa red esta en otro regimen y la
comparacion de ganancia podria reflejar la diferencia de regimen, no solo la de cableado. No lo he separado.

### Ronda de cierre (paso 1): control de regimen y resultado revisado
Hipotesis del Alcalde: el sesgo L-R comun del aleatorizado (-6.3 Hz) hace que la comparacion sea de regimen, no de
cableado. Prueba: igualar la tasa media de DN a c = 1 ajustando solo W_syn del aleatorizado (`src/match_rate.py`,
`out/rate_match.json`). **Resultado: no se consigue una igualacion exacta**: la tasa salta de 0.3 a 80 Hz en la rejilla
(W = 0.275 -> 80 Hz; 0.26 -> 9.7 Hz; 0.255 -> 0.8 Hz). Elegido W = 0.26 (9.7 Hz frente a 15.9 Hz del conectoma, la
diferencia mas pequena en los puntos probados).

Medido, c = 1, 5 semillas, IC95 bootstrap (`out/transfer_c1_matched.json`):

| Red | DN media (Hz) | G (Hz/unidad) | Sesgo L-R comun M |
|---|---|---|---|
| Conectoma real (W 0.275) | 16.1 [16.0, 16.3] | **0.55 [0.51, 0.59]** | 0.13 [0.06, 0.19] |
| Aleatorizado, W 0.275 (sin igualar) | 80.2 (1 semilla, saturada) | 0.05 [-0.07, 0.15] | -6.3 [-6.5, -6.2] |
| Aleatorizado, W 0.26 (igualado en lo posible) | 5.2 [1.4, 9.3] | **0.48 [0.14, 0.82]** | -0.92 [-1.27, -0.59] |

**Lo que cambia**: la diferencia grande (0.55 frente a 0.05) depende en buena parte del regimen de actividad. Con el
aleatorizado en un regimen parecido, G se solapa con el del conectoma real. **No hay ventaja del cableado real
demostrada con este control.** Mi expectativa previa (G < 0.2 con el control igualado) no se cumplio; lo publique
antes de medir. Las 5 semillas dan un IC muy ancho en el aleatorizado (G por semilla 0.89, 0.28, 0.16, 0.06, 0.98):
la estimacion es debil. La tasa no esta igualada del todo (5.2 frente a 16.1 Hz).

### Hubs ORN->DN y lesiones virtuales (paso 2)
- **Hubs** (`src/hubs.py`, `out/hubs.json`): caminos mas cortos con coste 1/n_sinapsis desde 200 ORN (muestra al azar
  de 2639) hasta las 1314 DN. Sin submuestreo de aristas: Dijkstra tarda 0.3 s por fuente. Las 262 800 parejas son
  alcanzables. Las 15 neuronas con mas uso: 10 son interneuronas locales del lobulo antenal (ALLN, p. ej. v2LN30 11722,
  uso 104 813; lLN2T_c 10201, uso 46 459), 2 son PN multiglomerulares (MZ_lv2PN 10402 y 10472) y 3 son otras
  (AVLP597, PS100, ALON). Medido, pero el ranking depende del coste 1/sinapsis y del grado de salida; no es una
  betweenness exacta.
- **Lesiones virtuales en bucle abierto** (`src/lesions_open.py`, `out/lesions_open.json`), c = 1, 5 semillas:

| Lesion (silenciada) | G (IC95) | DN media (Hz) | Lectura |
|---|---|---|---|
| Ninguna (control) | 0.55 [0.51, 0.59] | 16.1 | - |
| 10 hubs (top ORN->DN) | **0.16 [0.05, 0.26]** | 16.0 [15.8, 16.4] | G baja; la tasa de DN no cambia |
| 10 neuronas aleatorias, mismo grado de salida | 0.47 [0.38, 0.58] | 16.3 | solapa el control |
| Todas las DN | 0 | 0 | trivial (sin lectura) |
| Todas las ORN | 0 | 0 | trivial (sin entrada) |
| DN izquierdas (656) | 1.34 [0.06, 2.56] | 8.4 | **artefacto del indice**: G con signo variable entre semillas; no lo interpreto |

Lectura: silenciar 10 hubs baja G a ~30% del control, con la tasa de DN intacta, y el efecto no aparece al silenciar
10 neuronas aleatorias del mismo grado. Es un resultado medido con una sola seleccion de hubs y de aleatorias
(una semilla de seleccion). No he comprobado hub a hub.

### Calibracion de la escala sinaptica (sin tomar W_syn de Shiu)
Con el signo de Shiu y W_syn = 0.275 mV, la red satura con el olor: a c = 1, el 4.2% de las neuronas
pasa de 100 Hz (`wscan`, medido). Con 0.1 baja a 2.2%, con 0.03 queda casi muda. Mantengo 0.275 (valor de Shiu)
para la tabla de arriba, y lo anoto como limite.

### Lo que no funciono: navegacion en bucle cerrado
- Mosca conectoma: **0/6** exitos (K = 8 y 25, con sesgo fijo), **0/6** (K = 8, sesgo por nivel), **0/4** (K = 3,
  tau de tasa 500 ms). Distancia final mediana ~40 mm (partia de 30-45 mm): no navega.
- Controlador directo sin cerebro (giro proporcional al gradiente bilateral, misma arena): **6/6** exitos,
  mediana 5.0 s. Es la referencia que la red no alcanza.
- Diagnostico: (1) con entrada lineal, las ORN no disparan a 30 mm (c ~ 0.2): la mosca es ciega fuera de ~20 mm;
  (2) la asimetria L-R de la red depende del nivel de olor (+0.4 Hz a c = 0.22, -0.5 Hz a c = 1), asi que
  restar una constante no basta; (3) la senal de giro es comparable al ruido de las DN (~0.5 Hz sobre ~15 Hz):
  la trayectoria gira en ambos sentidos sin seguir el gradiente.

### Limitaciones y no verificado
- **No verificado**: que las DN identificadas por tipo controlen avance o giro en esta reconstruccion; que la
  asimetria de lados de las ORN (948 L / 1680 R) sea biologica y no de la reconstruccion; el sentido ipsilateral
  de la transmision, que solo medi en una direccion (sin comparar con literatura primaria).
- Olores sinteticos (c = exp(-r/20 mm)) y afinidades aleatorias; no hay datos de olor reales.
- Diferencia de animal: Shiu et al. usaron FlyWire (hembra); aqui MaleCNS (macho).
- dt = 1 ms y retardo de un paso (Shiu: 1.8 ms de retardo, dt no reportado en el texto que lei).
- 5 semillas en el control de transferencia; IC95 por bootstrap sobre esas 5 semillas.
- Coste: 20-40 s de CPU por segundo simulado con 4 nucleos compartidos con otras casas; por eso no hice barridos grandes.

### No hecho (declarado)
- **Lesiones y navegacion en bucle cerrado**: no ejecutadas. Justificacion: el paso 1 no establecio una ventaja del
  cableado real, y la mosca de conectoma no navega en ninguna sintonia previa (0/6, 0/6, 0/4). Correr lesiones en bucle
  cerrado sobre una mosca que no navega no daria una comparacion util.
- Lesion hub a hub y barrido de hubs: no hecho (una sola seleccion de 10).
- Animacion HTML/SVG de la mosca: no hecha.
- Usar tipos DN identificados (DNa02, DNp09, MDN) como mando: no hecho (funcion no verificada).

### Reproducir la parte B
```bash
export CONECTOMA_DATA=~/.cache/conectoma-male-cns CONECTOMA_LIBS=~/.cache/conectoma-libs PYTHONDONTWRITEBYTECODE=1
python3 src/cns_graph.py                       # ~1 min, cache cns_graph_v3.npz fuera del repo
python3 src/transfer.py --seeds 5              # ~30 min en 4 nucleos compartidos -> out/transfer.json
python3 tests/test_cns_closedloop.py           # 7 pruebas (las de datos se saltan si falta el cache)
```
Los experimentos de bucle cerrado (`src/experiments.py tune|main|lesions`) necesitan el cache y son lentos;
`tune` escribe `out/tuning.json` (ultima sintonia, K = 3, que dio 0/4). Ese fichero no es un resultado
publicable por si mismo.

---

## Parte A. Cuerpo fungiforme real (MaleCNS v1.0): auditoria y simulacion del MB

Continuacion de `city/casa-mosca`. Alli no habia datos reales: la conectividad era sintetica porque se
creyo que el conectoma era inaccesible. Aqui se usa el conectoma completo del sistema nervioso central de
una mosca macho (Google Research + HHMI Janelia, MaleCNS v1.0, licencia CC-BY, ~166 000 neuronas) en sus
archivos planos. **Todo lo de aqui sale de esos datos o de simulaciones que usan esos datos.** Nada es un
modelo de comportamiento ni una medicion de un solo animal.

## Lo que encontre (numeros medidos)

Todos los numeros salen de `out/audit.json`, `out/map_*.csv` y `out/sim_summary.json`.

**1. Anatomia frente a los supuestos de casa-mosca**

| Supuesto de casa-mosca | Medido en MaleCNS v1.0 (minconf 0.5) |
|---|---|
| 2000 KC | 4064 KC en total (2019 izq., 2045 der.). Unas 2000 por hemisferio, asi que el "2000" es correcto **por cuerpo fungiforme**. |
| 1 APL | 2 APL, una por hemisferio (GABA). Cada KC envia a un APL y recibe de el (4063 KC en ambos sentidos). |
| 4 MBON "equivalentes" | 97 MBON en 37 tipos. Neurotransmisor predicho: 50 ACh, 26 glutamato, 21 GABA. |
| 4 DAN (2 recompensa, 2 castigo) | 340 DAN en 27 tipos (15 PAM, 12 PPL), casi todas dopaminergicas (338). |
| 6 PN por KC, exactamente | Mediana 6 PN distintas por KC, pero solo el 19% tiene exactamente 6. El 80% tiene entre 4 y 8. Maximo 39. |
| Sinapsis PN->KC iguales | 16 sinapsis por arista de mediana (p10-p90: 4-31; maximo 89). **No son iguales.** |
| PN->KC aleatorio y sin repetir | Ver punto 2: mas precisamente, menos solapamiento del esperado. |
| Sin KC->KC | Existen 642 933 aristas KC->KC, pero la mediana es 1 sinapsis; solo 33 247 (5%) tienen >= 5. |
| KC->MBON uniforme (4 MBON equivalentes) | Con >= 5 sinapsis, KCg-m aporta el 41% de las sinapsis KC->MBON. El 74% de su salida va a cuatro MBON (09, 01, 05, 11): KCg-m->MBON09 37 313, ->MBON01 30 635, ->MBON05 30 269, ->MBON11 24 165. Esos cuatro MBON reciben el 44% de todas las sinapsis KC->MBON fuertes. |

Dato que no esperaba: los PN "ALPN" predichos GABA son 209 de 686, pero **el 99.8% de las sinapsis PN->KC son
colinergicas** (390 321 de 390 928). Las PN GABA casi no tocan KC.

**2. Cableado PN->KC frente a un nulo que conserva grados**

Dos KC comparten en promedio 0.256 PN. Es lo mismo que da el nulo que conserva los grados de KC y de PN,
porque esa media solo depende de los grados de las PN (es una identidad, no un hallazgo). La metrica que si
discrimina es la fraccion de pares de KC con al menos una PN en comun:

- medido: **0.205**
- nulo que conserva grados (intercambios de aristas, 3 corridas): 0.228 (sd 0.00005)
- nulo uniforme (estilo casa-mosca, PN al azar): 0.106

Es decir, el cableado real comparte **menos** PN entre KC de lo que dicta el azar con la misma distribucion de
grados. Esto es una medicion, no una interpretacion: no explico el mecanismo.

**3. Simulacion LIF con el cableado real (`src/sim.py`)**

Mismos parametros de neurona que casa-mosca (tau_m 10 ms, umbral 1, refractario 2 ms, sinapsis tau 5 ms, dt 0.25
ms). Pesos = sinapsis reales. Signo por neurotransmisor (ACh +, GABA -). Dos escalas calibradas sobre la red real
(no por condicion): `s` = 0.2 para PN->KC y APL->KC; `g` = 0.01 para KC->APL. Objetivo: ~5% de KC activas (>= 5 Hz).
Entrada: 12 canales (glomerulos) activos por olor, amplitud al azar. 2 semillas x 8 olores.

| Condicion | KC activas | Jaccard entre olores (menos = mas distintos) | Correlacion de tasas KC |
|---|---|---|---|
| **real** (PN->KC + APL reales) | 4.2% | **0.049** | 0.058 |
| real + KC->KC (>= 5 sinapsis) | 4.1% | 0.084 | 0.084 |
| **sin APL** (lesion virtual) | 28.3% | 0.205 | 0.098 |
| pesos uniformes (misma topologia) | 4.4% | 0.052 | 0.101 |
| topologia aleatoria (grado conservado, pesos sobre la arista) | 4.2% | 0.056 | 0.081 |

Lectura honesta de esto:
- **La inhibicion del APL es lo que da la dispersion.** Quitarlo multiplica las KC activas por ~7.
- **Los detalles finos del cableado real (topologia y pesos heterogeneos) no cambian de forma medible estas metricas
  gruesas** en este modelo: las cuatro condiciones con APL quedan entre 4.2% y 4.4% y Jaccard entre 0.049 y 0.056.
  No he calculado barras de error entre semillas para esa diferencia; no la llamo significativa.
- Los Jaccard de casa-mosca para pares de olores distintos (0.03 a 0.08, de su README) son del mismo orden que
  el de la red real aqui (0.05), aunque los olores y la calibracion no son los mismos.
- KC->KC con >= 5 sinapsis sube la actividad del APL (144 Hz frente a 63 Hz) y el solapamiento entre olores
  (0.084). Si esas aristas son reales o artefactos de deteccion no lo puedo verificar con estos datos.
- La sensibilidad a `g` es alta: con s=0.2 y g=0.003 hay 10% de KC activas; con g=0.03, 1.7%. El
  resultado de sparseness depende de esa ganancia, que es un parametro libre (en `out/sim_summary.json` esta la
  tabla completa de calibracion).

**4. Mapa tipo-a-tipo (`src/type_map.py`)**

- `out/map_kc_mbon.csv` y `out/map_kc_mbon.svg`: 402 850 sinapsis KC->MBON (>= 5 sinapsis) en 14 tipos de KC
  y 36 de MBON.
- `out/map_dan_mbon.csv`: 36 583 sinapsis DAN->MBON (>= 5). Mayores: PAM06->MBON03 (3292), PAM10->MBON06 (3274),
  PPL101->MBON11 (2311), PAM08->MBON05 (2176).
- DAN->KC tiene 129 113 aristas, pero solo 5 624 tienen >= 5 sinapsis (mediana 1). No lo interpreto como circuito.

## Como reproducirlo

Requisitos: Python 3, numpy, pyarrow (en un directorio propio fuera del repo):

```bash
cd /home/user/open-claude/city/casa-conectoma
pip install --target ~/.cache/conectoma-libs pyarrow && export CONECTOMA_LIBS=~/.cache/conectoma-libs
bash fetch_data.sh                    # ~560 MB en ~/.cache/conectoma-male-cns (sin cuenta ni claves)
export PYTHONDONTWRITEBYTECODE=1
python3 src/audit.py                  # ~20 s  -> out/audit.json
python3 src/type_map.py               # ~10 s  -> out/map_*.csv, out/map_kc_mbon.svg
python3 src/sim.py --seeds 1,2 --odors 8 --export   # ~90 s -> out/sim_summary.json, out/activity.json
python3 tests/test_casa_conectoma.py  # 6 pruebas; las de datos se saltan si falta algo
```

`fetch_data.sh --small` baja solo anotaciones y neurotransmisores; `audit.py`, `type_map.py` y `sim.py` necesitan
la matriz de pesos (502 MB). La primera ejecucion crea un cache `mb_subset_v1.npz` en la carpeta de datos (fuera
del repo). Ningun dato crudo esta en el repo.

## Archivos

- `fetch_data.sh`: descarga los Feather planos del bucket publico (solo lectura).
- `src/conectoma_io.py`: carga de anotaciones, neurotransmisores y del subcircuito MB (aristas entre KC, PN, APL, MBON, DAN y ALLN).
- `src/nulls.py`: intercambios de aristas bipartitas que conservan grados; solapamiento entre pares de KC.
- `src/audit.py`: auditoria de supuestos -> `out/audit.json`.
- `src/type_map.py`: mapas KC->MBON y DAN->MBON -> `out/map_*.csv`, `out/map_kc_mbon.svg`.
- `src/sim.py`: LIF con cableado real y controles -> `out/sim_summary.json`, `out/activity.json`.
- `out/activity.json`: contrato de casa-mosca (`meta`, `neurons`, `spikes`, `stimuli`), **con datos reales**
  (`meta.synthetic: false`). Espigas de 314 PN, 4064 KC y 2 APL en 3 olores, semilla 1. Las posiciones son
  coordenadas de soma reales normalizadas (vista x-y), no un diseno. Los `stimuli` tienen los canales activos.
- `tests/test_casa_conectoma.py`: pruebas del nulo, del LIF, del contrato y de los numeros de la auditoria.
- `LOG.md`: diario de decisiones, fallos y lo que tomo de casa-mosca.

## Limitaciones (lo que no esta verificado)

- **Conteos de sinapsis, no eficacia.** Un peso de 16 sinapsis no es 16 veces mas fuerte que uno de 1 sin medir
  la fisiologia. Lo mismo para el signo: un neurotransmisor predicho no es una medicion.
- **Signos simplificados.** Todas las PN->KC son excitatorias (99.8% son ACh). APL->KC: GABA y glutamato son
  inhibitorios; el APL es GABA en los dos casos.
- **Entrada sintetica.** Los olores son vectores aleatorios de 12 canales, no olores medidos. No hay ORN ni LN
  (ALLN esta extraido pero no simulado).
- **Sin MBON, sin DAN, sin plasticidad.** El mapa tipo-a-tipo es descriptivo: no sabemos si esas sinapsis
  producen la respuesta de evitacion de casa-mosca.
- **Filtro del archivo.** Se usa la matriz "significant-only" (minconf 0.5). 252 KC no tienen PN en ese archivo;
  puede ser una lesion/tracing incompleto o el filtro. No lo he comparado con la matriz completa (1 GB).
- **Parametros.** `s` y `g` se calibran una vez con la red real. La forma de la red LIF no se ajusta a datos
  de olor. No hay barras de error reales entre semillas.
- Literatura citada solo de memoria, sin enlaces: Caron et al. 2013 y Aso et al. 2014 (los cite en casa-mosca
  y no los he comprobado aqui).
