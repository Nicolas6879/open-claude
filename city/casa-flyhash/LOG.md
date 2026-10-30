# LOG de casa-flyhash (Hash)

Diario honesto. Hora siempre UTC. Etiquetas: **medido** / **supuesto** / **no_verificado**.
Ayuda recibida: nadie (casa autonoma; lei de otras casas solo la ubicacion de los datos y el formato del bus). El Alcalde fijo el marco.

## 0. Verificaciones de literatura (leidas en la fuente, 2026-10-30 21:17 UTC)
- Dasgupta, Stevens, Navlakha, *Science* 358:793-796 (2017), «A neural algorithm for a fundamental computing problem», DOI 10.1126/science.aam9868: **medido** via api.crossref.org (titulo, volumen, paginas, autores y fecha 2017-11-10 coinciden con lo que recordaba). Preprint bioRxiv 10.1101/180471 (existe en crossref). El texto del articulo no lo he podido leer (biorxiv da 429): lo que digo de sus resultados (MAP de FlyHash > LSH a igual longitud de hash) lo contrasto con el texto de Sharma & Navlakha.
- Sharma & Navlakha, arXiv:1812.01844 (2018), «Improving similarity search with high-dimensional LSH»: **medido** (leido el PDF). Convencion que uso: *longitud de hash m = nº de unidades ACTIVAS*, la dimension total es m*k con factor WTA k (k=20 -> 5 % activo). Comparan SimHash de m bits frente a FlyHash con m activos. Por eso reporto SimHash a TRES presupuestos: bits = nº de activas (convencion de la literatura), bits = almacenamiento equivalente (k*log2(M/k)) y bits = M (misma dimension).
- Ryali, Hopfield, Grinberg, Krotov, arXiv:2001.04907 (ICML 2020), BioHash: **medido** (resumen en arxiv.org): FlyHash usa proyecciones aleatorias y no aprende de los datos; BioHash aprende los pesos. Lo cito solo como contexto.

## 1. Datos (medido, 2026-10-30 21:17 UTC)
Extraido por mi (src/extract_pnkc.py) del feather MaleCNS v1.0: 4064 KC, 314 PN (class == ALPN con >=1 arista a KC), 22 586 aristas, 390 928 sinapsis. Coincide con el enunciado.
- Grado de entrada KC: media 5,56, sd 2,50, max 39; **252 KC (6,2 %) tienen grado 0** (no reciben PN olfativos significativos; probablemente reciben otras entradas: visuales, etc.). Es un hecho que cambia la comparacion: un FlyHash clasico con 4064 KC "vivas" tendria 6,6 % mas unidades. Lo trato explicitamente (ver 3).
- Grado de salida PN: media 71,9, sd 82,0, max 489 (muy heterogeneo).
- Hemisferio: 97,93 % de las aristas ipsilaterales; 158 PN izq / 156 der; 2019 KC izq / 2045 der.
- Peso por arista (sinapsis): media 17,3, mediana 16; sinapsis totales por KC: media 96, sd 47. KCg grado medio 6,37; KCab 5,09; KCa'b' 4,96.
- 88 tipos de PN (glomerulos). Fraccion de tipos PN distintos entre las entradas de una KC: real 0,967 vs nulo 0,983 (la KC real muestrea mas veces el mismo glomerulo).
- Nulo de intercambio de aristas por bloques (lado PN x lado KC): conserva grados PN y KC y el 97,9 % ipsilateral (comprobado). Solapamiento de aristas real/nulo 9,7 % (inevitable en nodos de grado alto).

## 2. PREDICCIONES v1 (escritas 2026-10-30 21:20 UTC, ANTES de los experimentos de comparacion; todas **supuesto**)
Antes de esto solo hice 1 replica de humo sobre digits con F6, SimHash(k bits) y un 'raw' defectuoso: vi F6 MAP 0,89 vs SimHash-k 0,82 (clasificacion lineal 0,984 vs 0,934). No he visto ningun numero real-vs-nulo.
Definiciones fijadas de antemano: metrica primaria de recuperacion = MAP de los 10 vecinos verdaderos (euclidea en el espacio original) con ranking completo de la base; secundaria P@10 y precision de etiqueta@10; clasificacion = lectura lineal ridge (lambda por validacion interna del train); dispersion primaria 5 % de las KC *vivas* (grado>=1: 3812 de 4064; los 252 KC sin PN se descartan en TODAS las variantes para no regalar unidades al comparador); nulo principal = intercambio de aristas por bloques lado-PN x lado-KC.
Familia de hipotesis primaria (Holm sobre las 12 pruebas: {digits, MNIST} x {recuperacion MAP, clasificacion} x {H1 real_bin vs nulo_bin, H2 real_w vs nulo_w(pesos viajan con la KC), H3 real_bin vs F6}). Todo lo demas es exploratorio (BH).
- P0 (replica de la literatura): MAP(F6,5 %) > SimHash con bits=nº de activas por >30 % relativo; vs SimHash con M bits la diferencia queda dentro de +-15 %; la gaussiana densa + top-k queda dentro de +-3 % de F6. Sin expansion con top-k (314 unidades) peor que F6 por >10 %.
- P1 (central): real_bin vs nulo_bin, recuperacion MAP @5 %, digits+MNIST: diferencia relativa dentro de +-1 % (IC95 que incluye 0), prob. subjetiva 75 %.
- P2: real_w (sinapsis) vs real_bin con top-k sobre la excitacion cruda: real_w PEOR 1-5 % (KC con mas sinapsis ganan siempre: inequidad de uso); con normalizacion por KC la diferencia desaparece (|d|<1 %).
- P3: real_bin vs F6 (misma m=3812): dentro de +-3 %; con las 252 KC muertas contadas (m=4064 para F6, 3812 vivas para real) el real queda 1-3 % por debajo.
- P4 (ley de escala): MAP crece monotono con la expansion, ~log-lineal: cada x2 de KC da +1 a +4 % relativo; a 100x todavia sube pero saturando (entre +10 % y +30 % sobre 1x). Las ventajas de dispersion frente a SimHash/denso se mantienen (no se invierten).
- P5 (dispersion): el MAP de recuperacion es maximo con 2-10 % activo; la clasificacion lineal prefiere mas denso (10-30 %).
- P6 (clasificacion): digits: lectura lineal sobre codigo KC >= lectura sobre PN crudos (+0,5 a +2 pp); real vs nulo |d| < 0,5 pp.
- P7 (robustez): real = nulo ante ruido gaussiano, mascara de pixeles y lesion de KC (|d|<1 %); codigo disperso se degrada mas suave que SimHash(k bits).
- P8 (subtipos, a igual n): KCg, KCab, KCa'b' dentro de +-2 % entre si (diferencias menores que el ruido), quiza KCg ligeramente mejor por mayor grado (6,4).
- P9 (mapeo bio-fiel por glomerulo, 88 canales repetidos por PN): el real es ligeramente peor que el nulo (-0,5 a -2 %) porque muestrea menos tipos PN distintos (0,967 vs 0,983); probablemente no detectable.
- P10 (potencia): con ~30 replicas el MDE (80 % potencia) sera ~0,5-1,5 % relativo en MAP; una ventaja inyectada del 2 % se detecta con potencia >=80 %.
- P11 (red entrenada, MNIST): a igual nº de parametros entrenables, una capa oculta densa entrenada gana a una expansion tipo mosca fija + lectura entrenada (+1 a +3 pp) cuando el presupuesto es >= 10k parametros; la mosca solo es competitiva con presupuestos < 3k. Real vs aleatorio disperso: igual.

## 3. PREDICCIONES v2 (escritas 2026-10-30 21:36 UTC, tras ver ~18 de 30 replicas de E1 digits/proyeccion; **supuesto**, hechas con informacion parcial)
Lo que ya vi de E1 (18 replicas, parcial; no cuento estas como predicciones acertadas): real_b ~ nulo_b; F6 mejor que real_b ~3,8 %; kcdeg_b (grado KC real, PN uniformes) = F6; real_w peor que real_b ~4 %. Mecanismo candidato medido en los datos: el grado de salida de los PN es muy heterogeneo (Gini 0,53; el 10 % de PN con mas salida acapara 37 % de aristas, 41 % de sinapsis y ~46 % de la varianza de excitacion; nº efectivo de PN 137 de 314 en binario, 113 con pesos) y la sinapsis media de un PN correlaciona con su grado (Spearman 0,62: los PN-hub tienen ademas sinapsis mas fuertes). Con un mapeo aleatorio de entrada a PN los hubs sobrerrepresentan un rasgo cualquiera.
- P12 (hubs como filtro adaptado): con PCA no blanqueada de MNIST (314 PC, varianza decreciente), si la PC1 va al PN de mayor grado ('pca_deg'), el nulo/real con grados reales SUPERA a F6 en MAP en >+2 %; con la asignacion inversa ('pca_rdeg') pierde >5 % frente a F6; con asignacion aleatoria ('pca') ~ -3 % como en E1. En los tres casos real vs nulo dentro de +-1 %.
- P13 (normalizacion homeostatica por KC, norm=1): la diferencia real_w - real_b pasa de ~-4 % a dentro de +-1,5 %; la diferencia real_b - F6 (hubs PN) NO desaparece (sigue < -2 %), porque la normalizacion por KC no corrige a los PN-hub.
- P14 (mapeo por glomerulo, L/R comparten canal): desaparece la ventaja del nulo sin hemisferio (|d|<0,5 %); real vs nulo con hemisferio sigue dentro de +-1 %.

## 4. RESULTADO E1 (2026-10-30 21:46 UTC): digits, mapeo por proyeccion gaussiana fija, 5 % activo, 30 replicas (particion x mapeo x nulos independientes), todo **medido**
Archivos: out/raw/E1_*.jsonl, out/E1_means.csv, out/E1_paired.csv (IC95 bootstrap sobre replicas, p por permutacion de signos, Holm sobre las 76 comparaciones del archivo; la familia pre-registrada son H1-H3).
| comparacion (MAP, dif. relativa, IC95) | resultado |
|---|---|
| H1 real_bin vs nulo_bin (intercambio de aristas con hemisferio) | **-0,09 % [-0,36, +0,18]** (p=0,53) -> sin diferencia |
| H2 real con sinapsis vs nulo con sinapsis | -3,8 % [-4,2, -3,5] (p_holm=0,019): el real PEOR |
| H3 real_bin vs F6 (6 PN al azar por KC) | -4,0 % [-4,3, -3,7]: el real PEOR |
| real_w vs real_bin | -4,5 % [-4,9, -4,1] |
| real_w vs mismos pesos barajados sobre la topologia real | -3,6 % [-3,9, -3,2]: los pesos reales perjudican |
| nulo (grados PN reales) vs F6 | -3,9 % ; **kcdeg_b (grado de KC real, PN uniformes) vs F6: +0,08 % [-0,10,+0,26]** -> la perdida viene de los PN-hub, no de los grados de las KC |
| nulo SIN respetar hemisferio vs con hemisferio | +1,5 % [+1,2, +1,8]: un nulo que ignora el hemisferio daria "real peor que el nulo en 1,6 %" (artefacto) |
| gaussiana densa + top-k vs F6 | +1,6 % [+1,4, +1,8] |
| F6 vs SimHash con k bits (=nº de activas) | **+9,4 % [+9,1, +9,7]** (reproduce el sentido de Dasgupta, no su magnitud) |
| F6 vs SimHash con bits de almacenamiento igual | **-2,6 %** (LSH mejor) ; vs SimHash con M bits: -4,4 % (LSH mejor) |
| F6 vs sin expansion (top-k de las 314 PN) | +33 % ; clasificacion lineal +5,8 pp |
| clasificacion lineal (acc): real_bin 0,9795 vs nulo_bin 0,9784 | +0,10 pp [-0,12,+0,34] -> sin diferencia; codigo KC 0,98 vs PN crudos 0,932 (+4,8 pp) |
Potencia (E1 solo): sd de la diferencia real-nulo en MAP = 0,0067, n=30 -> MDE (80 % potencia, alfa 5 %) = 2,8*0,0067/sqrt(30) = 0,0034 = **0,4 % relativo**. La prueba formal con ventaja inyectada es E9.
Comparacion con predicciones: P1 acertada (|d|<1 %, IC dentro de +-0,4 %). P2 (parte 'sin normalizar'): acertada (-4,5 % dentro de 1-5 %); la parte con normalizacion queda para E8. P3 FALLADA (predije +-3 %, salio -4,0 %; la causa es los PN-hub, no el real como tal). P0: SimHash(k bits) acertado en signo pero no en magnitud (+9 %, no >30 %); 'dentro de +-15 % de SimHash M bits' acertada (-4,4 %); gaussiana +-3 % acertada (+1,6 %); sin expansion -33 % acertada. P6: clasificacion KC vs PN crudos: predije +0,5 a +2 pp, salio +4,8 pp (subestime); real vs nulo |d|<0,5 pp acertada.
Sorpresa: SimHash a igual almacenamiento (log2 C(M,k) bits) supera a FlyHash en recuperacion. La literatura compara a igual numero de activas, no a igual almacenamiento; mi lectura (**supuesto**): su ventaja existe a bits=activas, pero depende de la convencion.

### Autocritica de E1 (v1 -> v2)
1. ¿Es justa? Mismo m (3812 vivas), misma dispersion, mismas particiones y mapeos para todas las variantes, pareado por replica; nulos independientes por replica. F6 y gaussiana no sufren el 6 % de KC muertas porque las quite de todos.
2. Control que invalidaria el resultado: (a) que la metrica sea ciega -> descartado, distingue diferencias del 1,5 % (hemisferio) y 4 % (hubs); aun asi la prueba formal es E9 (ventaja inyectada). (b) que el mapeo por proyeccion haga L y R independientes y tire la estructura bilateral: el artefacto del hemisferio lo sugiere -> E7 con mapeo por glomerulo. (c) que la proyeccion gaussiana (rango 64) no refleje 'entradas olfativas': probar PCA (MNIST), seleccion de canales.
3. Lo que NO es resultado: 'el real peor que F6' no significa que la anatomia sea mala; significa que con entradas arbitrarias asignadas al azar a PN heterogeneos se pierde ~4 %.

## 5. RESULTADO E2 (2026-10-30 21:58 UTC): MNIST (fit 3000 / base 3000 / 400 consultas / test 2000), proyeccion gaussiana a 314 PN, 5 % activo, 12 replicas, **medido** (out/E2_paired.csv)
- H1 real_bin vs nulo_bin: MAP **-0,14 % [-0,56, +0,32]**; clasificacion -0,22 pp [-0,68,+0,27]. Sin diferencia. (La precision de etiqueta@10 sale -0,57 % [-0,82,-0,32], p=0,003 nominal / Holm 0,045 sobre 56 pruebas del archivo: secundaria, exploratoria, magnitud minuscula; no la cuento como efecto.)
- H2 real_w vs nulo_w: MAP -9,0 % [-9,9,-8,1]; H3 real_bin vs F6: MAP **-9,9 % [-10,7,-9,0]** (acc -1,02 pp [-1,33,-0,70]); real_w vs real_bin -11,1 %. La perdida por PN-hub es mucho mayor en MNIST (-9,7 % el nulo con grados PN reales vs F6) que en digits (-3,9 %), mientras KC-grado-real+PN-uniforme = F6 (+0,40 % [-0,09,+0,93]).
- gaussiana densa vs F6: +4,1 %; F6 vs SimHash(k bits) +24,7 %; vs SimHash almacenamiento igual -6,8 %; vs SimHash M bits -11,6 % (LSH mejor en recuperacion), pero en clasificacion lineal el codigo KC (0,919) gana a SimHash-M (0,897) y a los PN crudos (0,843, +7,6 pp).

## 6. RESULTADO E7 parcial (2026-10-30 22:05 UTC): MNIST, mapeos PCA no blanqueada (314 PC), 12 replicas, solo recuperacion (**medido**; out/raw/E7_mnist_*.jsonl)
MAP medio: raw (euclidea sobre las 314 PC) 0,996 | gaussiana densa+top-k 0,807 | F6 0,403 | nulo_bin: PC->PN al azar 0,351, PC1->PN de mayor grado ('pca_deg') 0,510, PC1->PN de menor grado ('pca_rdeg') 0,210 | real_bin 0,351 / 0,495 / 0,179.
- P12: ACERTADA en lo cualitativo y en las dos magnitudes grandes: con pca_deg el nulo supera a F6 en **+28,3 % [+26,3,+30,3]** (predije >+2 %), con pca_rdeg pierde **-47 %** (predije >-5 %). Fallo: con asignacion aleatoria predije ~-3 % y salio -12,9 % [-16,5,-9,3]; y predije real vs nulo dentro de +-1 % en los tres mapeos: solo se cumple con 'pca' (-0,06 % [-1,1,+1,2]); con pca_deg real es **-2,9 % [-3,4,-2,4]** peor que el nulo y con pca_rdeg **-14,9 % [-16,0,-13,8]**.
- Hallazgo inesperado: **cuando el mapeo esta alineado con el grado, el cableado real NO es equivalente al nulo que conserva grados**. Hay estructura mas alla de los grados con consecuencia funcional. Mido ahora una candidata (estadistica del cableado, no del rendimiento): el real es **disasortativo**: correlacion de Spearman entre el grado de entrada de una KC y el grado de salida medio de sus PN = -0,256 (nulos: -0,011, -0,018, -0,001, -0,012). Ademas, los pares de PN del mismo tipo (mismo glomerulo, L/R o no) se co-muestrean 1,3 veces por par frente a 0,7 en el nulo (otros pares 1,3 vs 1,3).
- Control creado: nulo `nulljdd_b` (intercambio dentro de bloques cuantil de grado PN x cuantil de grado KC x lados) que conserva la disasortatividad (-0,290 vs real -0,256 en una instancia) y los grados.

## 7. PREDICCIONES v3 (escritas 2026-10-30 22:05 UTC, ANTES de correr E7b y E8 sobre MNIST/PCA; **supuesto**)
- P15: la brecha real<nulo en pca_deg y pca_rdeg se debe sobre todo a la disasortatividad: con el nulo JDD (nulljdd_b) real_b - nulljdd_b queda dentro de +-2 % en los tres mapeos PCA (prob. subjetiva 60 %). Si no, la causa sera la estructura de co-muestreo de PN del mismo tipo u otro orden superior.
- P16: con normalizacion por KC (norm=1), las brechas real-nulo en los tres mapeos PCA se reducen a menos de la mitad (prob. 50 %): el mecanismo es desigualdad de uso de KC (las KC de mayor grado, conectadas a PN de poca salida, dominan el top-k).

## 8. RESULTADO E9 (potencia con ventaja inyectada, 2026-10-30 22:13 UTC) y E3 (dispersion), **medido**
**E9** (digits/proyeccion, 30 replicas, mismas semillas que E1; out/E9_power.csv, src/analyze_power.py, tests/test_power.py). Ventaja inyectada = copia del cableado real con +e % de KC extra con el mismo patron de grados (equivale a "ampliar la expansion"):
| copia | dif. relativa MAP frente al nulo | IC95 | deteccion (p<0,05, una cola) con n=10 / 20 / 30 replicas |
|---|---|---|---|
| real tal cual | -0,09 % | [-0,36, +0,18] | 2 % / 0,4 % / 0,4 % (falsos positivos) |
| +10 % KC | +0,30 % | [-0,01, +0,58] | 17 % / 33 % / 48 % |
| +25 % KC | +0,72 % | [+0,45, +0,98] | 76 % / 99 % / 100 % |
| +50 % KC | +1,19 % | [+0,92, +1,45] | 98 % / 100 % / 100 % |
| +100 % KC | +1,91 % | [+1,68, +2,13] | 100 % |
Lectura: con 30 replicas una ventaja del 0,7 % se habria visto casi siempre y una del 2 % (≈ duplicar las KC) con certeza; el MDE analitico (80 %) es 0,40 %. La ley de escala inicial sale de aqui: x2 de KC = +1,9 % de MAP (P4 predijo +1 a +4 %: acertada). Asi, el IC [-0,36,+0,18] del real frente al nulo equivale a "como mucho +0,18 % ≈ 6 % mas de KC" a favor del real. Prueba de integracion: tests/test_power.py (plus100_b detectado con 8 replicas).
**E3** (digits/proyeccion, 10 replicas por nivel, out/E3_*.csv y out/E3.svg; el punto 5 % reutiliza E1): dispersion de 1 % a 50 % activo.
- MAP crece con la densidad hasta 50 % (F6: 0,781 / 0,843 / 0,890 / 0,910 / 0,921 / 0,926 / 0,928 para 1/2/5/10/20/35/50 %): **P5 fallada** (predije maximo con 2-10 %). Por unidad activa el codigo disperso es mas eficiente. La exactitud lineal es plana entre 5 % y 20 % (~0,98).
- real_bin vs nulo_bin: -0,17 % ... -0,36 % a 1-10 % (IC incluyen 0 en todos) y **-0,55 % a -0,64 % a 20-50 %** (IC95 sin 0; n=10): una ligera desventaja del real cuando el codigo deja de ser disperso. real vs F6: -3,0 % (1 %) a -4,4 % (20 %).
- F6 vs SimHash(k bits=activas): +43,7 % (1 %) -> +9,5 % (5 %) -> +0,45 % (50 %): la ventaja de la expansion dispersa frente al LSH con igual nº de bits activos desaparece al densificar. F6 vs SimHash(M bits): -16 % a 1 % -> -0,2 % a 50 %.

## 9. RESULTADO E7 mapeos 'select' y 'glom' (2026-10-30 22:19 UTC), **medido** (12 replicas; out/raw/E7_*.jsonl)
'glom' = cada PN copia el canal de su tipo/glomerulo (88 canales; los PN L/R del mismo tipo comparten entrada): es el mapeo mas fiel a la biologia que puedo construir sin datos de tuning de ORN. 'select' = 314 canales de entrada elegidos al azar (con reemplazo si d<314).
| mapeo | real_bin - nulo_bin (MAP rel., IC95) | nulo - F6 | pesos reales vs binario |
|---|---|---|---|
| MNIST select | -0,22 % [-0,65,+0,22] | -21,8 % | -14,5 % |
| MNIST glom | **-3,2 % [-3,9,-2,5]** | -5,1 % | -11,1 % |
| digits select | +0,39 % [-0,04,+0,81] | -2,7 % | -8,1 % |
| digits glom | **-1,5 % [-1,8,-1,1]** | -1,9 % | -5,4 % |
- P14 FALLADA: con el mapeo por glomerulo el nulo SIN hemisferio no se iguala sino que queda **peor** que el nulo con hemisferio (MNIST -1,4 %, digits -0,7 %), y el real queda peor que el nulo con hemisferio (-3,2 % / -1,5 %). P9 (predije -0,5 a -2 %, "quiza no detectable"): direccion acertada, magnitud MNIST fuera de rango (-3,2 %) y SI fue detectable.
- La clasificacion lineal no distingue (|d|<0,2 pp, IC con 0) en ningun mapeo: la lectura lineal sobre 3812 caracteristicas es insensible a estas diferencias.
- Lectura (**supuesto**, pendiente de E7b/E8 que lo comprueban): con entradas que conservan identidad de glomerulo, el cableado real muestrea mas veces el mismo glomerulo en la misma KC (co-muestreo de PN del mismo tipo 1,3 vs 0,7 por par; tipos distintos por KC 0,967 vs 0,983), lo que da KC redundantes y mayor varianza de excitacion.

## 10. RESULTADO E8 (normalizacion homeostatica por KC, digits/proyeccion, 12 replicas, 2026-10-30 22:27 UTC) y PREDICCIONES v4, **medido**
E8 usa norm=1: la excitacion de cada KC se z-normaliza con media/sd calculadas en el conjunto de ajuste y luego top-5 %. Comparado con las mismas 12 semillas sin normalizar (out/raw/E1 y E8_digits_norm.jsonl):
| comparacion (MAP) | sin norm | con norm |
|---|---|---|
| real_bin - nulo_bin | -0,33 % [-0,75,+0,08] | **-1,10 % [-1,31,-0,90]** |
| real_w - real_bin | -4,2 % [-4,8,-3,7] | -3,2 % [-3,5,-2,9] |
| real_w - nulo_w | -3,8 % | -2,7 % [-3,1,-2,3] |
| real_bin - F6 | -4,2 % | -5,0 % [-5,3,-4,8] |
| kcdeg_b - F6 | +0,11 % | -0,13 % [-0,39,+0,13] |
- **P13 FALLADA**: predije que la normalizacion por KC dejaria la penalizacion de los pesos en +-1,5 % y solo quedaria el efecto hub; salio -3,2 %, y ademas empeora el real frente al nulo (-1,1 %). La normalizacion por KC no arregla el sobre-peso de los PN-hub (consistente con la parte 2 de P13: la brecha con F6 sigue; mi mecanismo 'desigualdad de uso de KC' para los pesos era incorrecto o incompleto: el sobrepeso esta en el lado PN).
- Nueva hipotesis (**supuesto**): lo que perjudica es que unos pocos PN (hubs, y con sinapsis mas fuertes) dominan la excitacion de muchas KC. Una compensacion presinaptica de PN (escalar cada PN por 1/sqrt(suma de w^2 de su salida), E12) deberia (a) cerrar la mayor parte de la brecha con F6, (b) eliminar la penalizacion de los pesos.
PREDICCIONES v4 (escritas 2026-10-30 22:27 UTC; ANTES de correr E12 completo. Aviso: vi UNA replica de humo con otra semilla, solo para comprobar que el codigo funciona: real_b 0,859 -> real_b_pn 0,877, real_w 0,82 -> 0,879, F6 0,892.)
- P17a: con compensacion de PN, real_bin_pn - F6 queda entre -3 % y 0 % en digits/proyeccion y MNIST/proyeccion (cierra >=60 % de la brecha). P17b: real_w_pn - real_bin_pn dentro de +-1,5 %. P17c: real_bin_pn - nulo_bin_pn dentro de +-1 %. P17d: con PCA alineada al grado (pca_deg) la compensacion borra la ventaja del filtro adaptado: nulo_bin_pn queda dentro de +-8 % de F6, muy por debajo de nulo_bin sin compensar.

## 11. RESULTADO E5 (robustez, digits/proyeccion, 8 replicas, 2026-10-30 22:30 UTC), **medido**; E8 sobre MNIST/pca_deg
Condiciones aplicadas a consultas/test (base y entrenamiento limpios): ruido gaussiano en la entrada (0,5/1/2 x sd medio de pixel), mascara de pixeles (30/60 % a cero), lesion permanente de 30/60 % de las KC (misma lesion en base, entrenamiento y consulta).
- real_bin vs nulo_bin: **todos los IC95 incluyen 0** y |d| < 0,5 % en MAP en las 8 condiciones (ruido sigma=2: +0,35 % [-0,9,+1,8]; mascara 60 %: -0,5 % [-4,4,+4,0]); clasificacion igual (|d| < 0,5 pp salvo mascara 60 %: -2,6 pp [-10,6,+5,0]). P7 acertada para real=nulo.
- La brecha del real con F6 CRECE con el dano a la entrada: MAP -4,1 % (limpio) -> -4,8 % (sigma 0,5) -> -7,4 % (1) -> -11,9 % (2); mascara 30 %: -9,5 %; mascara 60 %: -10,5 %. Exactitud: -0,2 pp (limpio) -> -3,6 pp (sigma 2), -2,8 pp (mascara 30 %). O sea: los PN-hub hacen al real mas fragil ante ruido de entrada. Con lesion de KC la brecha no cambia (-4,4 %/-4,2 %).
- F6 vs SimHash(k bits): la ventaja crece con el ruido (+9,4 % limpio -> +23 % sigma 2; +15 % con mascara 30 %) y se reduce con la lesion de KC al 60 % (+4,1 %; SimHash no sufre lesion porque no tiene KC, comparacion no simetrica). F6 vs SimHash(M bits): SimHash(M) mejor y su ventaja crece (4,3 % -> 14 % a sigma 2). Prediccion P7 (codigo disperso mas suave que SimHash(k bits)): acertada; (frente a SimHash con M bits): no.
- E8 (MNIST/pca_deg, norm=1, 10 replicas): real_bin - nulo_bin pasa de -3,0 % [-3,5,-2,5] a **-0,6 % [-1,2,+0,2]** con normalizacion por KC: **P16 acertada** (la brecha se reduce a menos de la mitad); la ventaja del filtro adaptado frente a F6 se mantiene (+39,7 % [+37,5,+41,7] el real).

## 12. RESULTADO E6 (subtipos de KC a igual n=650, digits/proyeccion, 5 % activo, 20 replicas, 2026-10-30 22:31 UTC), **medido**
MAP de real_bin (misma semilla/particion/mapeo en los 4 grupos): KCab vs KCa'b' dif -0,0012 +-0,0035 (IC95; sin diferencia); **KCg mejor que KCab en +0,0199 +-0,0057 y que KCa'b' en +0,0186 +-0,0049** (MAP absoluto, ~+2,6 % relativo); KCg vs un submuestreo aleatorio de 650 de todas las KC: +0,0070 +-0,0042 (p=0,004); KCab y KCa'b' ligeramente peor que el submuestreo aleatorio (-0,012/-0,013).
Frente a su propio nulo: KCab -1,1 % (IC +-0,5), KCa'b' -1,1 %, KCg +0,3 % (IC incluye 0). Frente a F6: KCab -4,4 %, KCa'b' -4,2 %, **KCg -1,8 %**.
Mecanismo medido en el cableado (no en el rendimiento): las KCg muestrean PN de forma mas plana: 30,5 % de sus aristas vienen del 10 % de PN-hub (KCab 45,2 %, KCa'b' 39,4 %), nº efectivo de PN dentro del subtipo 168 (KCab 95, KCa'b' 126), grado de entrada medio (vivas) 7,2 vs 5,3 / 5,0. P8 (diferencias <2 % entre subtipos, KCg quiza mejor): **parcialmente fallada** (KCg +2,6 % sobre los otros dos; ab y a'b' iguales). Interpretacion: no es que 'el codigo gamma sea mejor', es que sus entradas estan menos concentradas en hubs (con mapeo aleatorio; con mapeo alineado al grado seria al reves, **supuesto no probado**).

## 13. RESULTADO Fashion-MNIST (E2f, 8 replicas) y texto 20 Newsgroups (E2n/E7n, 8 replicas, 2026-10-30 22:40 UTC), **medido**
Texto = TF-IDF (30 000 terminos) + SVD de 400 dimensiones (LSA), normalizado por fila, SVD ajustada solo con el 'train' de sklearn; NO es un embedding neuronal (no pude/quise correr un modelo de frases con la CPU saturada). 20 clases; 3000 base / 400 consultas. Tarea de recuperacion mucho mas dificil (MAP absoluto ~0,07-0,08 con 5 % activo; euclidea en PN 0,21).
- Fashion/proyeccion: H1 real_bin-nulo_bin MAP **-0,10 % [-0,52,+0,27]**; clasificacion -0,22 pp [-0,54,+0,07]; H3 real-F6 -8,2 % [-9,0,-7,5]; real_w -7,3 % vs nulo_w; F6 vs SimHash(k) +30,5 %; vs SimHash(M) -11,4 %; codigo KC clasifica mejor que PN crudos (+2,7 pp F6).
- Texto/proyeccion: H1 **+0,3 % [-1,9,+2,6]** (clasificacion +0,13 pp [-0,29,+0,53]): sin diferencia pero IC ancho (n=8, 400 consultas: potencia baja, MDE ~2 %); H3 real-F6 -7,4 % [-9,0,-5,7]; clasificacion real-F6 -3,3 pp [-3,9,-2,7] (acc 0,501 vs 0,534); gaussiana +3,9 %.
- Texto con PCA (400 PC): ahora el espectro es casi plano y **el efecto de filtro adaptado desaparece**: nulo_bin - F6 = -11 % (pca), -20 % (pca_deg), -34 % (pca_rdeg). real vs nulo: +2,8 % [+1,0,+4,5] (pca), -4,1 % [-6,3,-1,7] (pca_deg), +2,2 % [+0,4,+3,9] (pca_rdeg), con n=8 y sin correccion; **inconsistente de signo entre mapeos: no lo interpreto como efecto**. Conclusion: la ventaja de los PN-hub con PC1->hub depende de que el espectro de la entrada sea muy empinado (MNIST si, LSA no).

## 14. RESULTADO E7b (MNIST/PCA: nulo de grados conjuntos y normalizacion, 12 replicas, 2026-10-30 22:49 UTC), **medido** (out/E7b_paired_pca.csv)
MAP, diferencia relativa (IC95):
| mapeo | real - nulo(plano) | real - nulo_JDD | nulo_JDD - nulo(plano) | real - nulo(plano) con norm=1 |
|---|---|---|---|---|
| pca (PC->PN al azar) | -0,06 % [-1,1,+1,2] | **-1,4 % [-2,2,-0,6]** | +1,3 % [+0,2,+2,5] | -2,7 % [-3,8,-1,7] |
| pca_deg (PC1->PN hub) | -2,9 % [-3,4,-2,3] | -1,8 % [-2,3,-1,4] | -1,1 % [-1,7,-0,6] | -0,65 % [-1,3,+0,0] |
| pca_rdeg (PC1->PN de menor grado) | **-14,9 % [-16,0,-13,7]** | **-3,7 % [-5,0,-2,3]** | **-11,6 % [-12,6,-10,7]** | -15,2 % [-17,3,-13,2] |
- **P15 parcialmente acertada**: la disasortatividad (conservada por el nulo JDD) explica ~75 % de la brecha en pca_rdeg (-14,9 -> -3,7 %), ~36 % en pca_deg (-2,9 -> -1,8 %) y nada en pca; queda un residuo significativo en los tres (-1,4 / -1,8 / -3,7 %), asi que el cableado real tiene ESTRUCTURA ADICIONAL (mas alla de grados y correlacion de grados, a resolucion de 6 cuantiles) con coste funcional pequeno pero medible.
- **P16 mayormente fallada**: la normalizacion por KC cierra la brecha solo en pca_deg (-2,9 -> -0,65 %); en pca la empeora (-0,06 -> -2,7 %) y en pca_rdeg la deja igual (-15,2 %). El mecanismo no es (solo) desigualdad de uso de KC.
- Invariante de todos los mapeos: el cableado real nunca supera a su nulo (el mejor caso es -0,06 %). Los PN-hub dan +28 % (pca_deg) / +40 % (con norm) sobre F6 solo si el mapeo les asigna las PC de mayor varianza; con la asignacion inversa -55 % / -73 %.

## 15. RESULTADO E7b glom/proj (2026-10-30 22:56 UTC) y PREDICCION v5, **medido** / **supuesto**
E7b (MNIST, 12 replicas, out/E7b_paired_glom_proj.csv): con mapeo por glomerulo la brecha real - nulo (-3,2 % [-3,9,-2,5]) NO se explica por la matriz de grados conjuntos (real - nulo_JDD -3,4 % [-4,3,-2,4]; nulo_JDD - nulo +0,1 %), ni por el nulo con subtipos (-3,3 %), ni por la normalizacion por KC (-4,0 % [-4,5,-3,5]). Con mapeo 'proj' la normalizacion por KC introduce una brecha (-2,1 % [-2,5,-1,7]) que sin normalizar no existe (-0,14 %).
Medicion de cableado: 866 de las 22 586 aristas (3,8 %) son entradas repetidas del mismo tipo de PN en una misma KC (fraccion de tipos distintos por KC 0,967 real; 0,983 nulo). Construyo el control `realdd_b`: el real sin ninguna entrada repetida de tipo (866 intercambios; conserva exactamente grados PN y KC, hemisferio por bloques; 93 % de aristas identicas al real; fraccion distinta 1,000).
PREDICCION P18 (escrita antes de correr E14; **supuesto**): con mapeo por glomerulo, realdd_b - nulo_b queda dentro de +-1,5 % en MNIST (la redundancia explica >=55 % de la brecha) y dentro de +-0,7 % en digits; realdd_b mejora a real_b en >=+1,7 % en MNIST/glom; con mapeo 'proj' realdd_b = real_b (+-0,5 %).

## 16. RESULTADO E4 (escalado, digits/proyeccion, 6 replicas, expansion x1/16 ... x100, 5 % activo, 2026-10-30 22:58 UTC), **medido** (out/E4_*.csv, out/E4.svg)
Para factores <1 'real_like' = submuestreo aleatorio del cableado real; para >=1 = red con el patron de grados real (grado de entrada KC, grado de salida PN ∝ real, hemisferio) replicado f veces con PN al azar (NO es el cableado real: no existe a 100x). x100 = 381 200 KC. Clasificacion en forma dual (nucleo). SimHash(M bits) y gaussiana densa solo hasta x16 (memoria).
MAP medio: | factor | real_like_b | F6 | gaussiana | SimHash k bits | SimHash almac. | SimHash M bits |
|---|---|---|---|---|---|---|
| x1/16 | 0,562 | 0,590 | 0,601 | 0,271 | 0,650 | 0,832 |
| x1 | 0,858 | 0,891 | 0,901 | 0,815 | 0,911 | 0,930 |
| x4 | 0,879 | 0,914 | 0,927 | 0,901 | 0,930 | 0,935 |
| x16 | 0,885 | 0,919 | 0,934 | 0,926 | 0,935 | 0,936 |
| x100 | 0,887 | 0,922 | - | 0,935 | 0,936 | - |
(euclidea sobre PN: 0,967; sin expansion con top-k: 0,663.)
- Ley de escala de F6: ganancia relativa por duplicacion 21,6 % (1/16->1/8), 12,1 %, 6,7 %, 3,7 % (1/2->1), **1,7 % (1->2)**, 0,9 %, 0,34 % (4->8), 0,14 %, 0,24 %, 0,05 % (32->100): saturacion rapida; x100 solo da **+3,5 %** sobre x1. P4: la parte 'x2 da +1 a +4 %' acertada (1,7 %); 'a x100 +10 a +30 %' **fallada** (+3,5 %); 'las ventajas frente a SimHash/denso no se invierten' **fallada**: F6 supera a SimHash(k bits=activas) en +9,2 % a x1, +4,1 % a x2, +1,5 % a x4, 0 a x8 y **pierde -0,8 % a x16 y -1,4 % a x100** (SimHash con k=5 % de M bits tambien crece), y SimHash a igual almacenamiento o M bits gana a todos los tamanos (-4,2 % a x1, -1,8 % a x16 el F6 frente a M bits). La gaussiana densa gana +1,1 a +1,6 % a F6 en todo el rango.
- La penalizacion de los PN-hub NO se diluye con la escala: real_like_b - F6 = -3,7 % (x1) ... -3,8 % (x100), IC95 [-4,6,-3,0] a x100. Exactitud lineal: satura en 0,985 (F6) y 0,984 (real_like) desde x2: la expansion mejora la clasificacion lineal hasta ~x2 y nada despues.
- Precaucion: al pasar de factor <1 a >=1 cambia la naturaleza del 'real_like' (real submuestreado vs patron de grados); la caida del efecto de los pesos reales (-4,1 % a x1/2 vs -0,7 % a x>=1) es ese cambio (pesos reales vs pesos barajados dentro de cada KC), no un efecto de escala.

## 17. RESULTADO E13 (KC muertas contadas) y E14 (control de redundancia de tipo), 12 replicas, 2026-10-30 23:03 UTC, **medido**
- **E13** (digits/proyeccion; F6 y gaussiana con 4064 KC vivas, real y nulo con 3812 vivas + 252 muertas; k = 5 % de las vivas de cada red): real_bin - F6 = **-4,4 % [-4,8,-3,9]** (con 3812 para todos: -4,2 %). Diferencia de apenas 0,2 puntos: **P3 (segunda parte, 'el real queda 1-3 % mas abajo') fallada**; las 252 KC sin PN pesan poco. real - nulo -0,33 % [-0,75,+0,08].
- **E14** (src/wiring.py::dedup_type_swaps, out/E14_paired.csv): quitar al real las 866 entradas repetidas de un mismo tipo de PN en una KC (3,8 % de las aristas; 7 % de aristas cambian):
| mapeo | real_bin - nulo | realdd_bin - nulo | realdd - real |
|---|---|---|---|
| MNIST glom | -3,2 % [-3,9,-2,5] | **+0,4 % [-0,3,+1,1]** | **+3,8 % [+3,0,+4,6]** |
| digits glom | -1,5 % [-1,8,-1,1] | **+0,2 % [-0,2,+0,7]** | +1,7 % [+1,5,+1,9] |
| MNIST proj | -0,14 % | -0,02 % [-0,5,+0,5] | +0,12 % [-0,3,+0,5] |
 **P18 ACERTADA** (las tres cotas). Con mapeo por glomerulo la desventaja del real frente a su nulo es **toda** la redundancia de entradas del mismo tipo (el cableado real muestrea mas de una vez el mismo glomerulo en la misma KC; un nulo que respeta grados pero reparte al azar casi nunca lo hace). Con mapeos que no ven el tipo, esa redundancia es invisible. Es la unica estructura 'mas alla de grados' que he identificado causalmente con consecuencia funcional en el mapeo bio-fiel; resulta contraproducente para la tarea (supuesto: en la mosca la redundancia puede servir a otra cosa: robustez, ruido sinaptico, entradas L/R; no probado).

## 18. E10 v1 (red entrenada) y autocritica, 2026-10-30 23:07 UTC; PREDICCIONES v6 para E10 v2 (escritas 2026-10-30 23:07 UTC, **supuesto**)
E10 v1 (2 semillas, out/raw/E10v1_net.jsonl; mapeo PCA a 314 PN no blanqueada; lecturas con Adam 12 epocas, 20 000 muestras): fly_lin_f6 0,71-0,92 (2,5k-80k parametros), real/nulo 0,63-0,88, dense (hidden entrenada) 0,69-0,965, rf_lin (ReLU aleatorias densas + lectura) 0,92-0,96. **Descartado por dos fallos mios**: (1) la lectura con Adam estaba subajustada (la ridge de E2 con 3000 muestras ya daba 0,919 para 3812 KC; aqui Adam con 20 000 daba 0,899 para 3999); (2) elegi PCA no blanqueada, que es el mapeo MAS desfavorable para F6 (E7: MAP 0,40 vs 0,65 con proyeccion). v2: lecturas lineales (fly_lin_*, rf_lin) en forma cerrada (ridge, una eigh, lambda en validacion), dense y fly_hid con Adam (3 lr, 25 epocas, 10 000 muestras de entrenamiento), mapeo principal 'proj' (el de E2) y un secundario 'pca_deg' (solo lecturas lineales).
- P19a: rf_lin (ReLU aleatorias densas sobre pixeles) >= fly_lin_f6 + 2 pp en todos los presupuestos >= 5k. P19b: |fly_lin_real - fly_lin_null| < 1 pp en todos los presupuestos. P19c: dense (Adam) supera a fly_lin_f6 desde 20k parametros (>= +1 pp). P19d: fly_lin_f6 - fly_lin_real >= +1 pp desde 20k parametros (penalizacion de hubs). P19e (pca_deg): fly_lin_real y fly_lin_null superan a fly_lin_f6 en >= 2 pp desde 20k parametros (prob. subjetiva 50 %).

## 19. RESULTADO E12 (compensacion presinaptica de PN, 12 replicas, 2026-10-30 23:16 UTC), **medido** (out/E12_paired.csv)
Variantes con sufijo _pn: cada PN se escala por 1/sqrt(suma de w^2 de su salida) (binario: 1/sqrt(grado de salida)); mismo cableado, solo ganancia por PN.
| comparacion (MAP) | digits proj | MNIST proj | MNIST pca | MNIST pca_deg | MNIST glom |
|---|---|---|---|---|---|
| real_bin - F6 (sin compensar) | -4,2 % | -9,9 % | -12,9 % | +24,6 % | -8,2 % |
| real_bin_pn - F6 | -1,7 % [-2,0,-1,4] | **-3,4 % [-4,0,-2,7]** | -1,5 % [-4,1,+1,5] | +43,7 % | -14,9 % |
| nulo_bin_pn - F6 | -1,1 % | -2,7 % | -2,3 % | +48,2 % | -10,6 % |
| real_bin_pn - nulo_bin_pn | -0,59 % [-0,83,-0,33] | -0,67 % [-1,12,-0,25] | +0,86 % [-0,17,+1,87] | -3,0 % [-3,8,-2,2] | -4,9 % [-5,3,-4,3] |
| real_w_pn - real_bin_pn | -0,01 % [-0,31,+0,22] | -0,41 % [-0,95,+0,08] | +16,6 % [+14,3,+18,9] | -2,4 % | -0,7 % |
- **P17a ACERTADA (justa)**: la compensacion cierra el 60 % (digits) y el 66 % (MNIST) de la brecha del real con F6 (umbral predicho >=60 %). **P17b ACERTADA**: con compensacion los pesos de sinapsis dejan de perjudicar (-0,01 % / -0,41 %, IC con 0 o casi). **P17c ACERTADA** (|d|<1 % en proj, aunque -0,6 % es distinguible de 0). **P17d FALLADA**: con pca_deg la compensacion no borra el filtro adaptado, lo AUMENTA (nulo_pn +48 % vs F6, antes +28 %): la compensacion corrige la sobre-representacion de los hubs pero la asignacion PC1->hub sigue ayudando. Con glomerulo la compensacion empeora (-14,9 % frente a -8,2 %): ahi los PN duplicados por tipo ya estaban equilibrados por construccion.
- Efecto raro (no lo busque): con pca (PC->PN al azar) y compensacion, las sinapsis reales SI ayudan (+16,6 % sobre el binario), pero tambien en el nulo con pesos (0,476 vs 0,394): es heterogeneidad de pesos en general, no el peso real (real_w_pn 0,463 vs nulo_w_pn 0,476 = -2,8 %).
- Conclusion: **la brecha del real con F6 es en sus 2/3 un problema de ganancia por PN (hubs)** que una normalizacion presinaptica simple elimina; el resto (~1/3) lo explican la disasortatividad y las entradas repetidas de tipo.

## 20. Senal exploratoria a confirmar (texto LSA con PCA, 2026-10-30 23:17 UTC) y PREDICCION P20
En E7n (texto, n=8) el real sale **por encima** del nulo con 'pca' (+2,8 % [+1,0,+4,5], p=0,040 sin corregir) y 'pca_rdeg' (+2,2 % [+0,4,+3,9], p=0,10) y por debajo con 'pca_deg' (-4,1 %). Es lo unico en todo el estudio donde el real supera nominalmente a su nulo; con 3 comparaciones Holm daria p=0,12 para pca. Lo trato como exploratorio y lo **replico con 32 replicas nuevas** (semillas 1008..1039, independientes de las 8 primeras; mismos mapeos/variantes; solo recuperacion).
- P20 (escrita antes de correr): la senal se desvanece (real - nulo en 'pca' dentro de +-1,5 % con IC que incluye 0), prob. subjetiva 70 %.
- RESULTADO P20 (**acertada**): con 32 replicas nuevas real - nulo en 'pca' = **+0,05 % [-0,74, +0,88]**, en 'pca_rdeg' -0,01 % [-1,2, +1,1]: la senal se desvanecio (regresion a la media / ruido de n=8). En 'pca_deg' se **replica** que el real es peor: -3,2 % [-4,1, -2,3] (combinado 40 replicas: -3,4 % [-4,3, -2,5]; pca +0,6 % [-0,2, +1,4]; rdeg +0,4 % [-0,6, +1,4]). Lectura: no hay ningun caso en que el real supere a su nulo.

## 21. Eficiencia (2026-10-30 23:22 UTC), **medido** (out/E1_eficiencia.csv; digits/proyeccion, E1, 30 replicas)
Costo de codificar una consulta = nº de pesos no nulos (multiplicaciones-suma): real 22 586, F6 22 872, SimHash(k bits) 59 974, SimHash(almacenamiento) 341 632, gaussiana densa y SimHash(M) 1 196 968.
MAP / acc: real 0,852 / 0,980 ; nulo 0,853 / 0,978 ; F6 0,888 / 0,982 ; gaussiana 0,902 / 0,982 ; SimHash(k) 0,812 / 0,927 ; SimHash(alm.) 0,911 / 0,963 ; SimHash(M) 0,928 / 0,978.
MAP por 1000 MAC: real 0,0377, nulo 0,0378, F6 0,0388, SimHash(k) 0,0135, SimHash(alm.) 0,0027, gaussiana 0,00075, SimHash(M) 0,00078. Es decir: el cableado disperso (real o aleatorio) alcanza el 94-98 % del MAP de la proyeccion densa con el 1,9 % de las multiplicaciones: **la eficiencia es de la dispersion, no del cableado real** (real = nulo en eficiencia, y F6 es 3 % mas eficiente).

## 22. Comprobacion con regresion logistica: PREDICCION P21 (2026-10-30 23:23 UTC; **supuesto**)
La clasificacion de todo el estudio usa lectura ridge. Para ver si las conclusiones dependen de ella: regresion logistica L2 (sklearn lbfgs, C elegido en validacion interna) sobre el codigo binario, digits/proyeccion, 12 replicas (semillas 1000-1011, las de E1), variantes real_b, null_b, F6, SimHash(M).
- P21: H1 real - nulo |d| < 0,5 pp (IC con 0); real - F6 entre -0,6 y 0 pp; el orden de F6 / SimHash(M) coincide con ridge (F6 >= SimHash(M) en +0,0 a +0,6 pp).

## 23. Cementerio de ideas (2026-10-30 23:23 UTC)
- «raw» = coseno sobre PN como cota de referencia: era la metrica equivocada (la verdad es euclidea); sustituida por euclidea (humo, antes de ningun resultado).
- «Los pesos de sinapsis reales mejoran el codigo»: muerta (-4 a -11 % sin compensar; con compensacion presinaptica solo quedan en paridad con el binario).
- «La normalizacion homeostatica por KC arregla pesos y hubs» (P13/P16): muerta; el sobrepeso esta en el lado PN.
- Mecanismo «desigualdad de uso de KC» para la penalizacion: descartado (E8).
- «Real vs nulo mejora con texto/PCA» (E7n, n=8, +2,8 %): regresion a la media con 32 replicas nuevas (P20).
- Nulo sin respetar hemisferio: artefacto (+1,5 % de ventaja ficticia del nulo con mapeo aleatorio; -1,4 % con glomerulo).
- E10 v1 (red entrenada): lectura con Adam subajustada + PCA no blanqueada (el mapeo peor para F6): descartada, rehecha como v2 con ridge exacto y mapeo 'proj'.
- Prueba de potencia con «ventaja inyectada»: pense primero en inyectar una ventaja de cableado (KC rewired a las PC), la sustitui por «+e % de KC» porque su efecto se calibra con la ley de escala (limitacion declarada en README).
- No ejecutado (no_verificado): optimizacion del mapeo por busqueda/gradiente (co-adaptacion cableado-mapeo), tuning real ORN->glomerulo (DoOR), embeddings neuronales de texto (CPU saturada), CIFAR-10, ley de escala con datos mas grandes que digits para x100.
- Quien me ayudo: nadie (casa autonoma). Lei de otras casas solo la ubicacion de los datos y el formato del bus.

## 24. RESULTADO E10 v2 (red entrenada a igual nº de parametros entrenables, MNIST, 3 semillas, 2026-10-30 23:33 UTC) y E15 (logistica), **medido**
Protocolo v2: 10 000 muestras de entrenamiento, 5000 de validacion, 5000 de test; presupuestos 2,5k-80k parametros entrenables; lecturas lineales en forma cerrada (ridge, lambda en validacion); dense/fly_hid con Adam (3 lr, 25 epocas, lr elegido en validacion). Mapeo 'proj'. n=3 semillas: se dan medias y rango de las diferencias pareadas (sin p-valores). out/E10_summary.csv, out/E10_paired.csv, out/fig_net.svg.
Exactitud media (test): | parametros | dense (trained) | rf_lin (ReLU aleatorias + lectura) | fly_lin F6 | fly_lin real | fly_lin nulo | fly_hid F6 / real / nulo |
|---|---|---|---|---|---|---|
| 2,5k | 0,783 | **0,890** | 0,776 | 0,754 | 0,751 | - |
| 10k | 0,917 | **0,940** | 0,894 | 0,885 | 0,881 | 0,703 / 0,690 / 0,662 |
| 20k | 0,940 | **0,953** | 0,920 | 0,914 | 0,915 | 0,908 / 0,897 / 0,898 |
| 40k | 0,952 | **0,959** | 0,935 | 0,932 | 0,932 | 0,939 / 0,930 / 0,933 |
| 80k | **0,961** | 0,963 | 0,947 | 0,941 | 0,940 | 0,941 / 0,935 / 0,935 |
- fly_lin_real - fly_lin_null: media entre -0,26 y +0,43 pp en los 6 presupuestos (rangos por semilla -1,3 a +1,1 pp): **sin diferencia** (P19b acertada). fly_hid_real - fly_hid_null: -0,09 / -0,29 / -0,05 pp a 20k/40k/80k (a 10k, +2,8 pp con rango 0,4-7,1: inestable, h=2).
- fly_lin_f6 - fly_lin_real: +2,2 / +1,7 / +0,9 / +0,6 / +0,3 / +0,6 pp (2,5k...80k): la penalizacion de los hubs es de **0,3-0,6 pp** desde 20k (P19d: predije >= 1 pp: **fallada** la cota, correcta la direccion).
- rf_lin - fly_lin_f6: +11,4 / +6,7 / +4,6 / +3,3 / +2,4 / +1,6 pp: **las caracteristicas aleatorias DENSAS ReLU sobre los pixeles baten a la expansion tipo mosca a igual nº de parametros entrenables en todos los presupuestos** (P19a: >=+2 pp desde 5k: acertada hasta 40k, a 80k +1,6 pp). dense - fly_lin_f6: +0,7 / +0,8 / +2,3 / +2,0 / +1,7 / +1,4 pp (P19c acertada: la capa densa entrenada supera a la mosca fija desde 10k). dense - rf_lin: -10,7 pp (2,5k) ... -0,2 pp (80k): una capa densa entrenada solo alcanza a las caracteristicas aleatorias con ~80k parametros.
- fly_hid (expansion fija + capa oculta densa entrenada pequena): dense - fly_hid_f6 = +21 / +3,2 / +1,3 / +2,0 pp (10k/20k/40k/80k): como primera capa de una red pequeña, la expansion de tipo mosca NO ayuda frente a una capa densa a igual nº de parametros entrenables.
- Mapeo 'pca_deg' (solo lecturas lineales, 2 semillas, presupuestos 10k/20k/40k): fly_lin_real y fly_lin_null superan a F6 en **+5,7 / +4,1 / +4,4 pp** (real - F6) -> **P19e acertada** (efecto filtro adaptado tambien en una red entrenada); real - nulo: -0,14 / -0,96 / +0,10 pp (sin ventaja). rf_lin sigue por encima de todas (0,940/0,952/0,957).
- **E15** (regresion logistica L2, digits/proyeccion, 12 replicas, out/E15_logreg_paired.csv): real - nulo **+0,03 pp [-0,20, +0,26]**; real - F6 -0,24 pp [-0,55, +0,07]; F6 - SimHash(M) +0,42 pp [+0,18, +0,63]. **P21 acertada** (las tres cotas): la conclusion de clasificacion no depende de ridge vs logistica.
- P11 (red entrenada): predije que dense gana con >= 10k (+1 a +3 pp): **acertada** (+2,3 / +2,0 / +1,7 / +1,4 pp) y que la mosca solo compite < 3k: con 2,5k dense apenas supera (+0,7 pp) a F6; el aleatorio-vs-real igual: acertada.

## 25. Balance final (2026-10-30 23:34 UTC)
**Respuesta**: el cableado real PN->KC de la mosca NO mejora, como algoritmo, ni la recuperacion de vecinos, ni la clasificacion lineal, ni la robustez, ni la eficiencia frente a un cableado aleatorio equivalente (nulo de intercambio que conserva grados y hemisferio): real - nulo = -0,09 % [-0,36, +0,19] (digits, n=30), -0,14 % [-0,55, +0,32] (MNIST), -0,10 % [-0,52, +0,27] (Fashion); con mapeos sensibles a la identidad del PN es peor (hasta -14,9 %). Mi potencia: MDE 0,40 % relativo con 30 replicas; +25 % de KC (+0,72 %) detectado >= 99 %.
**Escala**: no; la expansion satura (x2 +1,7 %, x100 +3,5 % sobre x1) y la ventaja sobre SimHash con igual nº de bits activos se invierte desde x16. **Red entrenada**: a igual nº de parametros entrenables, la expansion fija tipo mosca pierde frente a una capa densa entrenada desde 10k parametros (+1,4 a +2,3 pp) y frente a ReLU aleatorias densas siempre (+11 pp a 2,5k, +1,6 pp a 80k); real = nulo (|d| < 0,5 pp).
**Lo que si encontre (todo con control)**: (i) la heterogeneidad de grado de los PN-hub cuesta 4-10 % de MAP con mapeo aleatorio (cierra ~2/3 una compensacion presinaptica 1/sqrt(sum w^2)) y da +28-48 % si la PC1 va a los hubs (filtro adaptado, depende del espectro); (ii) el cableado real es disasortativo (explica ~75 % de la brecha con pca_rdeg) y tiene 866 entradas repetidas del mismo glomerulo en una KC; quitarlas iguala real y nulo con mapeo por glomerulo (+0,4 % vs -3,2 %); (iii) un nulo que ignora el hemisferio fabrica un artefacto de +1,5 %.
**Aciertos/fallos de predicciones**: acertadas P1, P7(parte), P10, P12(dos primeras), P15(parte), P17(a-c), P18, P19(b,c,e), P20, P21; falladas P3, P4(parte), P5, P13, P14, P16(casi), P17d, P19d, P0(magnitud); parciales P2, P8, P9. Tabla en README.
**Sorpresas**: la ventaja de FlyHash sobre LSH desaparece a igual almacenamiento; MAP crece hasta 50 % activo; la normalizacion por KC no arregla nada de lo que yo creia; las ReLU aleatorias densas ganan a todo a bajo presupuesto.
**No verificado**: tuning ORN->glomerulo real; embeddings neuronales de texto; co-adaptacion mapeo-cableado optimizada; estructura de orden superior (pares de PN) mas alla de las dos identificadas; si la redundancia por glomerulo tiene una funcion que mi banco de pruebas no mide.
