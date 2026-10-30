# casa-flyhash: ¿ayuda en IA el cableado REAL de la mosca, frente a uno aleatorio equivalente?

Casa autónoma de «Hash». Pregunta de **computación**, no de anatomía: el conectoma MaleCNS v1.0 (Google/Janelia) da la matriz PN→KC real
(314 PN, 4064 KC, 22 586 aristas, 390 928 sinapsis). Se usa como primera capa de un algoritmo tipo FlyHash (expansión + inhibición global top-k)
y se compara, **en tareas de IA con datos reales**, con cableados aleatorios de igual tamaño y dispersión.
Todo está en `LOG.md` (diario con predicciones previas, fallos, cementerio). Etiquetas: **medido** / **supuesto** / **no_verificado**.

## Respuesta corta (todo medido, IC95 por bootstrap sobre réplicas pareadas)

1. **No: el cableado real no mejora nada frente a su nulo.** Con el nulo que conserva los grados de cada PN y de cada KC y el hemisferio
   (97,9 % de aristas ipsilaterales), la diferencia en recuperación de vecinos (MAP) es **-0,09 % [-0,36, +0,19]** (digits, 30 réplicas),
   **-0,14 % [-0,55, +0,32]** (MNIST), **-0,10 % [-0,52, +0,27]** (Fashion-MNIST) y +0,3 % [-1,9, +2,6] (texto, n=8, potencia baja);
   en clasificación lineal **+0,10 pp [-0,12, +0,34]** (digits) y -0,22 pp [-0,68, +0,27] (MNIST). Con mapeos de entrada que ven la identidad del PN
   (glomérulo, PCA alineada al grado) el real es **peor** que su nulo (hasta -3,2 % con glomérulo, -2,9 % a -14,9 % con PCA alineada), nunca mejor.
2. **Control de potencia**: inyectando una ventaja conocida (copia del real con +25 % de KC, que da +0,72 % de MAP) se detecta en ≥99 % de las
   pruebas con 20-30 réplicas; con +100 % de KC (+1,9 %) en 100 %. El MDE (80 %) con 30 réplicas es 0,40 % relativo, de modo que
   el IC [-0,36, +0,19] excluye cualquier ventaja ≳ 0,2 % (≈ 6 % más de KC). Una mejora del 2 % se habría visto con certeza.
3. **Frente al FlyHash clásico (6 PN al azar por KC) el real es PEOR**: -4,0 % [-4,3, -3,7] en digits, -9,9 % [-10,7, -9,0] en MNIST, -8,2 % en Fashion
   con mapeo aleatorio. Causa medida: la **heterogeneidad del grado de salida de los PN** (Gini 0,53; el 10 % de PN-hub aporta el 37 % de las aristas,
   el 41 % de las sinapsis y ~46 % de la varianza de excitación; nº efectivo de PN 137 de 314), no los grados de KC (KC con grado real y PN uniformes = F6: +0,08 % [-0,10, +0,26]).
   Los **pesos de sinapsis empeoran 4-11 %** más (los PN-hub además tienen sinapsis más fuertes: Spearman 0,62 entre grado y peso medio).
4. **Los hubs pueden ser una ventaja si el mapeo los alinea con la varianza**: con PCA no blanqueada de MNIST y PC1→PN de mayor grado, los grados heterogéneos
   superan a F6 en **+28 %** (+40 % con normalización por KC); con la asignación inversa pierden -47 %. Es un filtro adaptado: requiere que la entrada tenga espectro empinado
   (MNIST sí; LSA de texto no, ahí desaparece) **y** que el mapeo esté co-adaptado; en una tarea de IA genérica no hay motivo para que ocurra (**supuesto**).
5. **Estructura real más allá de los grados, con coste funcional**: el cableado real es disasortativo (Spearman grado KC vs grado de salida medio de sus PN = -0,26; nulos -0,01)
   y tiene 866 entradas repetidas del mismo tipo de PN dentro de una KC (3,8 % de las aristas). Quitar solo esas repeticiones hace que el real
   **iguale a su nulo con mapeo por glomérulo** (+0,4 % [-0,3, +1,1] vs -3,2 % antes) y lo mejora +3,8 % [+3,0, +4,6]: control causal (E14).
6. **Escala (hasta ×100 = 381 200 KC)**: la precisión de la expansión dispersa **satura enseguida** (F6: +1,7 % por duplicación de ×1 a ×2, +0,34 % de ×4 a ×8; ×100 solo +3,5 % sobre ×1);
   la ventaja de FlyHash sobre SimHash con el mismo nº de bits activos (+9,2 % a ×1) **se anula a ×8 y se invierte a ×16-×100 (-0,8 a -1,4 %)**; la penalización de los hubs
   (-3,8 %) no se diluye con la escala; SimHash a igual almacenamiento o con M bits gana a todos los tamaños en recuperación.
7. **Qué sí hace bien la expansión dispersa**: frente a no expandir (top-k de las 314 PN) F6 gana +33 % de MAP (digits); en clasificación lineal +5,4 pp (digits) y +12,9 pp (MNIST) frente a ese top-k,
   y +5,0 pp / +7,6 pp frente a leer los PN crudos: la expansión ayuda a la lectura lineal con **cualquier** cableado (real, nulo, F6), y el cableado real no añade nada.
8. **Red entrenada (MNIST, igual nº de parámetros entrenables, 3 semillas)**: la expansión fija tipo mosca + lectura lineal queda por debajo de una capa oculta densa entrenada desde 10k parámetros (+1,4 a +2,3 pp) y muy por debajo de características ReLU aleatorias **densas** + lectura (+11,4 pp a 2,5k, +1,6 pp a 80k); como primera capa fija de una red pequeña (fly_hid) pierde 1-3 pp frente a una capa densa. Real vs nulo en la capa fly: |d| < 0,5 pp (media) en todos los presupuestos. Con PC1→hub la capa con grados de la mosca (real o nulo) gana +4 a +6 pp a F6, pero sigue por debajo de las ReLU aleatorias densas.
9. **Comprobación con regresión logística** (digits): real - nulo +0,03 pp [-0,20, +0,26]; real - F6 -0,24 pp [-0,55, +0,07]: la lectura no cambia las conclusiones.

## Qué se hizo

- **Datos** (`src/extract_pnkc.py`, `data/pnkc.npz`, 71 KB): KC = `type` que empieza por KC (4064); PN = `class == ALPN` con ≥1 arista a KC (314); peso = nº de sinapsis. 252 KC (6,2 %) no reciben
  ningún PN: **se descartan en todas las variantes** (3812 KC vivas) para no regalar unidades al comparador (E13 las cuenta: cambia 0,2 puntos).
- **Entradas**: digits (sklearn, sin red), MNIST y Fashion-MNIST (bucket público de TensorFlow, `src/fetch_datasets.sh`), 20 Newsgroups → TF-IDF → SVD 400 (**LSA, no es un embedding neuronal**).
  Mapeos entrada→314 PN (aleatorizados por réplica; el resultado no depende de uno afortunado): `proj` (gaussiana fija), `select` (canales al azar), `pca` (PC al PN al azar), `pca_deg`/`pca_rdeg`
  (PC1 al PN de mayor/menor grado), `glom` (cada PN copia el canal de su tipo/glomérulo, 88 canales; L/R comparten canal). Todo se ajusta solo con el conjunto de ajuste.
- **Comparadores** (misma m=3812 y mismo 5 % activo, salvo indicación): real binario / con sinapsis; nulo de intercambio de aristas por bloques lado-PN×lado-KC (grados PN y KC conservados); variantes del nulo
  (pesos barajados, + subtipo, sin hemisferio, matriz de grados conjuntos `nulljdd`); F6 (6 PN uniformes por KC, hemisferio respetado); grado de KC real con PN uniformes; gaussiana densa; topología real con pesos gaussianos;
  SimHash a tres presupuestos (bits = nº de activas —la convención de la literatura—, almacenamiento igual log2 C(M,k), y M bits); sin expansión (top-k de 314 PN); euclídea sobre PN (cota).
- **Métricas**: recuperación = MAP de los 10 vecinos euclídeos verdaderos con ranking completo (primaria), P@10 y precisión de etiqueta@10; clasificación = lectura lineal ridge (λ por validación interna del train; test aparte).
  Robustez: ruido gaussiano, máscara de píxeles, lesión de KC. Estadística: réplicas pareadas (partición × mapeo × nulos independientes), IC95 bootstrap, p por permutación de signos, Holm sobre la familia primaria.
- **Familia primaria pre-registrada** (`out/PRIMARY.md`): {digits, MNIST}×{MAP, acc}×{H1 real_bin-nulo_bin, H2 real_w-nulo_w, H3 real_bin-F6}; Holm sobre 12 pruebas: H1 nunca significativa (p_Holm=1,0 en las 4);
  H2 y H3 en MAP significativas (p_Holm ≤ 0,005) y H3 en acc de MNIST (-1,0 pp, p_Holm=0,005), siempre **con el real peor**.

## Resultados con números (todas las tablas en `out/*.csv`; figuras `out/*.svg`)

### 1. Núcleo (E1 digits n=30; E2 MNIST n=12; E2f Fashion n=8; E2n texto n=8) — `out/PRIMARY.md`, `out/E*_paired.csv`
| comparación (MAP, dif. relativa, IC95) | digits | MNIST | Fashion | texto |
|---|---|---|---|---|
| H1 real_bin - nulo_bin | -0,09 % [-0,36, +0,19] | -0,14 % [-0,55, +0,32] | -0,10 % [-0,52, +0,27] | +0,3 % [-1,9, +2,6] |
| H2 real_w - nulo_w | -3,8 % [-4,2, -3,5] | -9,0 % [-9,9, -8,1] | -7,3 % | -8,7 % |
| H3 real_bin - F6 | -4,0 % [-4,3, -3,7] | -9,9 % [-10,7, -9,0] | -8,2 % | -7,4 % |
| KC-grado-real+PN uniformes - F6 | +0,08 % [-0,10, +0,26] | +0,40 % [-0,09, +0,93] | | |
| nulo SIN hemisferio - nulo con hemisferio | +1,5 % [+1,2, +1,8] | | | |
| gaussiana densa - F6 | +1,6 % | +4,1 % | +3,4 % | +3,9 % |
| F6 - SimHash(k bits = nº activas) | +9,4 % | +24,7 % | +30,5 % | +17,9 % |
| F6 - SimHash(almacenamiento igual) | -2,6 % | -6,8 % | -5,4 % | |
| F6 - SimHash(M bits) | -4,4 % | -11,6 % | -11,4 % | -7,9 % |
Clasificación lineal (acc): H1 +0,10 pp [-0,12, +0,34] (digits), -0,22 pp [-0,68, +0,27] (MNIST), -0,22 pp [-0,54, +0,07] (Fashion), +0,13 pp [-0,29, +0,53] (texto).
Un nulo que **ignora el hemisferio** habría dado «real peor que el nulo en 1,6 %»: artefacto (con mapeo aleatorio, L y R son canales independientes).

### 2. Potencia con ventaja inyectada (E9) — `out/E9_power.csv`, `out/fig_power.svg`, `tests/test_power.py`
| copia del real | dif. MAP vs nulo | IC95 | detección n=10 / 20 / 30 |
|---|---|---|---|
| real | -0,09 % | [-0,36, +0,18] | 2 % / 0,4 % / 0,4 % (falsos positivos) |
| +10 % KC | +0,30 % | [-0,01, +0,58] | 17 / 33 / 48 % |
| +25 % KC | +0,72 % | [+0,45, +0,98] | 76 / 99 / 100 % |
| +50 % KC | +1,19 % | [+0,92, +1,45] | 98 / 100 / 100 % |
| +100 % KC | +1,91 % | [+1,68, +2,13] | 100 % |
Limitación: la ventaja inyectada es «más KC», no una mejora de cableado; sirve para calibrar la sensibilidad del procedimiento a una diferencia de MAP conocida.

### 2b. Eficiencia (E1) — `out/E1_eficiencia.csv`
Coste de codificar = nº de pesos no nulos: real 22 586, F6 22 872, gaussiana/SimHash(M) 1 196 968, SimHash(k bits) 59 974. MAP por 1000 multiplicaciones-suma: real 0,0377, nulo 0,0378, F6 0,0388, gaussiana 0,00075. El cableado disperso (real o aleatorio) da el 94-98 % del MAP de la proyección densa con el 1,9 % del cómputo: la eficiencia es de la dispersión, no del cableado real.

### 3. Dispersión 1-50 % (E3, digits n=10) — `out/E3.svg`
MAP de F6: 0,781 / 0,843 / 0,890 / 0,910 / 0,921 / 0,926 / 0,928 (1/2/5/10/20/35/50 %); crece con la densidad (predicción de máximo en 2-10 % fallada); la exactitud lineal es plana (~0,98) entre 5 y 20 %.
real - nulo: entre -0,2 % y -0,4 % a 1-10 % (IC con 0) y **-0,55 a -0,64 %** a 20-50 % (IC95 sin 0). F6 - SimHash(k bits): +43,7 % (1 %) → +9,5 % (5 %) → +0,45 % (50 %).

### 4. Escala (E4, digits n=6, ×1/16 … ×100) — `out/E4.svg`, `out/E4_*.csv`
MAP: ×1/16 / ×1 / ×4 / ×16 / ×100 = F6 0,590 / 0,891 / 0,914 / 0,919 / 0,922; patrón de grados real (`real_like`) 0,562 / 0,858 / 0,879 / 0,885 / 0,887; SimHash(k bits) 0,271 / 0,815 / 0,901 / 0,926 / 0,935;
SimHash(M bits) 0,832 / 0,930 / 0,935 / 0,936; euclídea sobre PN 0,967. Ganancia relativa por duplicación de F6: 3,7 % (½→1), **1,7 % (1→2)**, 0,9 %, 0,34 %, 0,14 %, 0,24 %, 0,05 %. Detalle y salvedades en `LOG.md` §16.

### 5. Robustez (E5, digits n=8) — `out/E5_paired.csv`
real - nulo: |d| < 0,5 % en MAP con IC95 que incluye 0 en las 8 condiciones (ruido σ=0,5/1/2, máscara 30/60 %, lesión de KC 30/60 %). La brecha real - F6 **crece con el ruido de entrada**: -4,1 % (limpio) → -7,4 % (σ=1) → -11,9 % (σ=2); máscara 30 %: -9,5 %.
F6 - SimHash(k bits) crece de +9,4 % a +23 % (σ=2).

### 6. Subtipos de KC (E6, a igual n=650, digits n=20) — `out/E6_paired.csv`
KCab ≈ KCa'b' (dif. MAP -0,0012 ± 0,0035); **KCg mejor en +0,020 ± 0,006 (≈ +2,6 %)**. Frente a su nulo: KCab -1,1 %, KCa'b' -1,1 %, KCg +0,3 % (IC con 0). Las KCg muestrean PN de forma más plana
(30,5 % de aristas desde hubs frente a 45,2 % en KCab; nº efectivo de PN 168 vs 95): es el mismo mecanismo de los hubs, no una virtud intrínseca del código γ.

### 7. Mapeos, hubs y estructura (E7, E7b, E8, E12, E14) — `out/E7_paired.csv`, `out/E7b_paired.csv`, `out/E8_paired.csv`, `out/E12_paired.csv`, `out/E14_paired.csv`, `out/fig_forest.svg`
- PCA no blanqueada MNIST: nulo - F6 = -12,9 % (pca), **+28,3 %** (pca_deg), **-47,3 %** (pca_rdeg); real - nulo = -0,06 % [-1,1, +1,2], -2,9 % [-3,4, -2,3], -14,9 % [-16,0, -13,7].
- Nulo de grados conjuntos (conserva la disasortatividad): real - nulo_JDD = -1,4 % / -1,8 % / -3,7 %: explica ~75 % de la brecha en pca_rdeg y ~36 % en pca_deg; queda residuo significativo.
- Mapeo por glomérulo: real - nulo = -3,2 % [-3,9, -2,5] (MNIST), -1,5 % [-1,8, -1,1] (digits); no lo explica la matriz de grados conjuntos ni la normalización por KC; **sí lo explican las 866 entradas repetidas de tipo (E14)**.
- Normalización por KC (E8): no elimina la penalización de los pesos (-4,2 % → -3,2 %) ni mejora al real (-0,3 % → -1,1 %); solo cierra la brecha con pca_deg (-3,0 % → -0,6 %).
- Compensación presináptica de PN (E12, escalar cada PN por 1/√Σw²): la brecha del real con F6 baja de -4,2 % a **-1,7 %** (digits) y de -9,9 % a **-3,4 %** (MNIST), es decir se cierra ~60-66 %; con compensación los pesos de sinapsis dejan de perjudicar (-0,01 % [-0,31, +0,22]; -0,41 % [-0,95, +0,08]) y real - nulo queda en -0,6 % / -0,7 % (residuo: disasortatividad + repeticiones). Con pca_deg la compensación aumenta la ventaja del filtro adaptado (+48 % frente a F6) y con glomérulo empeora (-14,9 %).
- Texto (LSA): espectro casi plano → el efecto de filtro adaptado desaparece (nulo - F6 = -20 % con pca_deg). Una señal inicial de «real > nulo» (+2,8 %, n=8, p=0,04 sin corregir, con pca) se **replicó con 32 réplicas nuevas y se desvaneció** (+0,05 % [-0,74, +0,88]); con pca_deg se replica que el real es peor (-3,4 % [-4,3, -2,5], n=40). Predicción P20 acertada.

### 8. Posición del real entre 30 nulos con mapeo fijo (E11, digits, 12 mapeos × 30 nulos) — `out/E11_rank.csv`
z medio del real = -0,25 (sd 1,29), fracción de nulos ≥ real = 0,55 (0,5 si fuese intercambiable); real - media del nulo = -0,10 % (IC ±0,32 %). sd entre instancias de nulo 0,0033; sd entre mapeos 0,0102: **hay que emparejar por mapeo**.
Dos de 12 mapeos dan z ≈ -2,4 (sd de z 1,29 > 1: el real interactúa algo más con el mapeo que un nulo típico).

### 9. Red entrenada a igual nº de parámetros entrenables (E10 v2, MNIST, 3 semillas) — `out/E10_summary.csv`, `out/E10_paired.csv`, `out/fig_net.svg`
| parámetros | dense (entrenada) | ReLU aleatorias densas + lectura | fly_lin F6 | fly_lin real | fly_lin nulo | fly_hid F6 / real / nulo |
|---|---|---|---|---|---|---|
| 2,5k | 0,783 | **0,890** | 0,776 | 0,754 | 0,751 | - |
| 10k | 0,917 | **0,940** | 0,894 | 0,885 | 0,881 | 0,703 / 0,690 / 0,662 |
| 20k | 0,940 | **0,953** | 0,920 | 0,914 | 0,915 | 0,908 / 0,897 / 0,898 |
| 40k | 0,952 | **0,959** | 0,935 | 0,932 | 0,932 | 0,939 / 0,930 / 0,933 |
| 80k | **0,961** | 0,963 | 0,947 | 0,941 | 0,940 | 0,941 / 0,935 / 0,935 |
fly_lin = expansión fija (3812 KC o submuestra: m=(B-10)/10) + lectura lineal exacta (ridge); fly_hid = expansión fija de 3812 KC + capa oculta entrenada. Las diferencias real-nulo son de ±0,3-0,4 pp en media (rangos por semilla ±1 pp); con n=3 no doy p-valores.
Primera versión (v1, `out/raw/E10v1_net.jsonl`) **descartada**: lectura con Adam subajustada y PCA no blanqueada (el mapeo peor para F6); ver `LOG.md` §18.

## Predicciones frente a resultados (detalle en `LOG.md`)
| id | predicción (resumen) | resultado |
|---|---|---|
| P0 | F6 > SimHash(k bits) en >30 %; ≈ SimHash(M) ±15 %; gaussiana ±3 % de F6; sin expansión peor >10 % | **parcial**: +9,4 % (falló la magnitud), -4,4 % (ok), +1,6 % (ok), -33 % (ok) |
| P1 | real = nulo (±1 %) | **acertada** (IC dentro de ±0,6 % en 4 conjuntos) |
| P2 | pesos sinapsis -1 a -5 % sin normalizar | **acertada** (-4,5 % digits; en MNIST -11 %, fuera de rango) |
| P3 | real vs F6 ±3 %; con KC muertas -1 a -3 % más | **fallada** (-4,0 %/-9,9 %; las muertas añaden -0,2 pp) |
| P4 | ×2 da +1-4 %; ×100 da +10-30 %; ventajas no se invierten | **parcial/fallada**: ×2 = +1,7 % (ok); ×100 = +3,5 % (fallo); ventaja sobre SimHash(k) se invierte a ×16 (fallo) |
| P5 | MAP máximo con 2-10 % activo; clasificación prefiere más denso | **fallada** (MAP crece hasta 50 %); clasificación plana |
| P6 | clasificación KC ≥ PN crudos (+0,5 a +2 pp); real=nulo | real=nulo ok; la ganancia fue mayor (+4,8 pp digits, +7,6 pp MNIST) |
| P7 | real = nulo ante ruido; disperso más suave que SimHash(k) | **acertada** (frente a SimHash con M bits no) |
| P8 | subtipos ±2 %, quizá KCg mejor | **parcial**: KCg +2,6 % sobre ab y a'b' |
| P9 | glomérulo: real -0,5 a -2 %, quizá no detectable | dirección ok; -3,2 % MNIST fuera de rango y detectable |
| P10 | MDE 0,5-1,5 %; +2 % detectado ≥80 % | **acertada** (MDE 0,4 %; +2 % → 100 %) |
| P12 | pca_deg: nulo > F6 en >2 %; pca_rdeg < -5 %; real = nulo ±1 % | ok las dos primeras (+28 %, -47 %); **fallada** la tercera (-2,9 %, -14,9 %) |
| P13 | normalización por KC quita la penalización de los pesos | **fallada** (-4,2 % → -3,2 %) |
| P14 | glomérulo: desaparece el artefacto del nulo sin hemisferio | **fallada** (cambia de signo: -1,4 %) |
| P15 | nulo JDD cierra la brecha (±2 %) | **parcial** (75 % en rdeg, 36 % en deg; residuo) |
| P16 | normalización reduce la brecha a < la mitad | **mayormente fallada** (solo pca_deg) |
| P17 | compensación de PN cierra ≥60 % de la brecha con F6, quita el efecto de los pesos | **acertada** (a: cierra 60 % digits/66 % MNIST; b: pesos -0,01 %/-0,41 %); **fallada** la parte d (pca_deg: la compensación AUMENTA la ventaja) |
| P18 | quitar entradas repetidas iguala real y nulo (glom) | **acertada** (+0,4 % / +0,2 %; real +3,8 % / +1,7 %) |
| P19 | red entrenada v2: (a) ReLU densas ≥ F6+2 pp desde 5k; (b) real=nulo <1 pp; (c) dense > F6 desde 20k; (d) F6-real ≥1 pp desde 20k; (e) pca_deg: real/nulo > F6 ≥2 pp | a ok hasta 40k (80k: +1,6 pp); b **acertada**; c **acertada** (desde 10k); d **fallada** (0,3-0,6 pp); e **acertada** (+4 a +6 pp) |
| P21 | logística: real=nulo ±0,5 pp; real-F6 en [-0,6, 0] pp | **acertada** (+0,03 pp; -0,24 pp) |
| P20 | la señal texto+PCA «real>nulo» se desvanece | **acertada** |

## Límites y lo que NO está verificado
- **Mapeo entrada→PN arbitrario**: no hay datos de sintonía ORN→glomérulo (DoOR) accesibles aquí; cualquier ventaja ligada a identidades concretas de glomérulo **no se puede descartar** (no_verificado). `glom` es el mejor sustituto.
- Una sola red real (la del macho adulto), con sus 252 KC sin PN olfativos; el 'real' no es una muestra de una población: la comparación es contra su familia de nulos (E11 lo trata).
- Texto = LSA, no embeddings neuronales (no_verificado que un embedding neuronal con espectro distinto cambie algo); MNIST/Fashion con 12/8 réplicas (p mínimo de la permutación ≈ 0,0005-0,008); texto con n=8 y 400 consultas: MDE ≈ 2 %.
- «Real vs nulo» en MAP es exacto a 6 cuantiles de grado conjunto; no descarto estructura de orden superior (p. ej. co-muestreo de pares de PN) más allá de las dos identificadas.
- Los nombres de PN/glomérulo vienen de la anotación `type`; las 88 clases incluyen subtipos `lPN`/`adPN` etc. (no fusionadas por glomérulo exacto).
- Citas de literatura leídas en la fuente (crossref, arXiv): Dasgupta et al. *Science* 358:793 (2017) por crossref (su texto no lo pude leer: bioRxiv da 429); Sharma & Navlakha arXiv:1812.01844 (leído, de ahí la convención «hash length = nº de activas» y los 6 PN/KC, 5 % top); Ryali et al. arXiv:2001.04907 (resumen).
- SimHash no sufre lesión de KC (no tiene KC): en E5 la comparación bajo lesión no es simétrica.

## Reproducir (≈ 5 h de CPU compartida)
```
bash src/fetch_datasets.sh                      # MNIST/Fashion (FLYHASH_DL=dir)
python -I src/extract_pnkc.py <dir_feather>     # ya incluido: data/pnkc.npz
bash run_all.sh                                 # lista de comandos (ver también out/COMANDOS.txt)
python -I src/analyze_all.py                    # regenera out/*.csv, out/PRIMARY.md y figuras
python3 tests/test_wiring.py; python3 tests/test_power.py
```
Sin cuentas ni claves; solo lectura de datos públicos (GCS de Janelia/TensorFlow, sklearn/figshare); lo descargado se trata como datos (np.frombuffer / np.load sin pickle). PYTHONDONTWRITEBYTECODE=1.

## Archivos
`src/wiring.py` (carga, nulos, dedup), `src/engine.py` (mapeos, codificadores, métricas, lecturas), `src/exp.py` (réplicas), `src/exp_scale.py`, `src/exp_rank.py`, `src/exp_net.py`,
`src/stats.py`, `src/analyze*.py`, `src/figs.py`, `tests/`, `out/` (CSV + SVG + `raw/*.jsonl`), `LOG.md`.
