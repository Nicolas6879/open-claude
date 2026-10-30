# LOG de casa-zodiaco (diario honesto)

Convencion: **[medido]** = salida de un comando reproducible; **[supuesto]** = decision/hipotesis mia;
**[no verificado]** = de memoria o sin comprobar.

## 2026-10-30 21:51:30 UTC — Estado antes de cualquier experimento (solo datos descriptivos)

[medido] Descargados (src/descargar.sh) los index.json de las culturas de Stellarium listadas como activas en
skycultures/CMakeLists.txt: son **60**, no 62 (el Ministro hablaba de 62; hay 4 mas comentadas/excluidas
del paquete: armintxe, egyptian, maya, modern_sternenkarten). HYG v4.1: 119 626 filas, 117 951 con ID de Hipparcos.
[medido] Kemp et al. (arXiv 2010.06108, PDF leido entero): 27 sistemas (22 de Stellarium 0.20.1 + 5 de literatura),
estrellas mas debiles que mag 4.5 eliminadas, 605 asterismos; modelo GC (Delaunay a mag 3.5/4.0/4.5, peso brillo x proximidad con
escalado local a 60 grados, rho=3, se conservan las n aristas mas fuertes, componentes conexas = asterismos);
evaluacion por solapamiento de CONJUNTOS de estrellas (match = max((|a∩r|-|a\r|)/|r|,0)), F10, sin leave-one-culture-out,
parametros (rho, n) elegidos sobre las mismas 27 culturas, sin nulo de grafo aleatorio ni de vecino mas cercano
(sus comparadores son k-means, CODE y variantes del propio GC), y sin extension a otros observadores.
[medido] Perdidas de datos al pasar a aristas HIP-HIP (out/contabilidad_culturas.csv): de 27 895 aristas brutas, 803 se pierden
por vertices que no son estrellas HIP (coordenadas RA/Dec de constelaciones oscuras/poligonales, objetos "DSO:"),
64 por HIP ausente en HYG, 1 841 son duplicados; quedan 24 510 aristas unicas. **Kamilaroi queda con 3 aristas** (su emu oscuro
esta dibujado con coordenadas, no con estrellas) y khoi-san, xhosa, zulu con 5-6: no evaluables.
[medido] Licencias (de description.md de cada cultura): mezcla de CC BY-SA, CC BY-ND, CC BY-NC-ND, GPL v2, etc. Politica: este repo NO
redistribuye las aristas de ninguna cultura (solo el script de descarga y estadisticas agregadas).
[supuesto] Familias historicas (FAMILIAS en src/datos.py): 7 variantes "modern*" de las 88 constelaciones IAU + 4 griegas + al-Sufi son una sola
familia occidental; 10 sistemas chinos/japones/coreano, otra; etc. Por eso la validacion principal es
**leave-one-FAMILY-out** (LOFO); el leave-one-culture-out literal (LOCO) se reporta tambien pero tiene fuga: lo demuestra test_fugas_familia.

### Diseno congelado (v1), decidido ANTES de ver ningun F1 real
- Verdad: aristas unicas HIP-HIP de `constellations[].lines` ∪ `asterisms[].lines` (sin los "ray helpers"). Elegibles: >=15 aristas.
- Modelo (src/modelo.py): Delaunay esferico multiescala (mag 3.5/4/4.5/5.5/todas) → puntuacion log-lineal -(lam*0.921*mag_mas_debil + ln d),
  escalado local por mediana (R en {0,30,60,90} grados, ~400 anclas) → top k = r*n_estrellas aristas.
  Rejilla global: lam∈{0,.25,.5,1,2,4,solo-brillo}, R∈{0,30,60,90}, r∈{.3,.45,.6,.8,1,1.25} (+ m_lim∈{3.5..5.5} en el regimen B).
  Los hiperparametros se eligen en las culturas de entrenamiento (cada familia pesa igual) maximizando F1 medio; nunca por cultura.
- Regimen A (estrellas conocidas: el modelo ve las estrellas que usa la cultura, no las uniones). Regimen B (cielo ciego: todo el cielo hasta m_lim;
  es el que necesita la extension). Metrica: F1 de aristas = 2tp/(|pred|+|verdad|).
- Nulos: (a) grafo aleatorio (configuracion "borrada") sobre las mismas estrellas y la misma secuencia de grados (100 semillas);
  (b) vecino mas cercano entre las mismas estrellas (A) / entre las estrellas <= m_lim (B); (b2) solo proximidad con presupuesto propio;
  (c) subconjunto aleatorio de las aristas candidatas de Delaunay con el mismo presupuesto. IC al 95 % por bootstrap de constelaciones (cluster bootstrap).
- Potencia: tests/test_pipeline.py inyecta estructura conocida en cielos sinteticos [medido, 5 tests, ya pasan]: con 100 % de aristas del modelo F1=0.95
  (NN 0.78, aleatorio-grado 0.04, subconjunto aleatorio 0.28); con 50 % F1=0.51; con 0 % (control negativo) F1=0.03, sin ventaja x2.

## 2026-10-30 21:51:30 UTC — PREREGISTRO (supuesto, escrito antes de correr E1 y E2)

**Compuerta.** Sobre las culturas elegibles: 
G1 = F1_modelo >= 2 x F1_nulo(a) en >=75 %. G2 = F1_modelo > F1_NN (nulo b) en >=75 %. Cada una calculada (i) contando culturas y (ii) con peso 1/|familia| (ii es la que cuenta
si difieren). **La extension a otros cielos solo se hace si G1 y G2 pasan en A y en B** (en B el nulo (a) usa la secuencia de grados del grafo predicho).
Si G1 pasa y G2 no, la conclusion es "la proximidad entre estrellas ya explica casi todo; no hay gramatica gestaltica mas alla del vecino cercano".

**Predicciones numericas (E1, regimen A, LOFO):**
- P1: F1 mediano del modelo sobre elegibles = 0.30 (rango 0.20-0.45); F1 mediano NN = 0.27; F1 mediano nulo(a) = 0.02 (<0.06 en el 90 % de culturas, salvo culturas con <40 estrellas).
- P2: G1_A pasa con 90-100 % de culturas (el nulo (a) es casi trivial: lo digo ya).
- P3: G2_A: el modelo supera al NN en ~55 % de culturas (rango 40-75 %) → **G2_A falla (prob. 70 %)**; ganancia mediana sobre NN de +5 a +15 % relativo.
- P4: "solo proximidad" (b2) queda a +-5 % del modelo (en A las estrellas ya estan seleccionadas por brillo, asi que el brillo aporta poco).
- P5: boorong NO sale peor que el azar en A (ratio vs nulo(a) > 2); kamilaroi es no evaluable (3 aristas). indian_nakshatras queda en la mitad inferior de F1_A (60 % de confianza).
- P6: LOCO vs LOFO difieren < 0.02 de F1 medio (pocos hiperparametros → poca fuga) pero los hiperparametros elegidos coinciden en >80 % de los pliegues.
**Predicciones (E2, regimen B, cielo ciego):**
- P7: F1 mediano del modelo = 0.05 (0.02-0.10) (la cobertura limita a todos); G1_B pasa (>=85 %); G2_B: modelo > NN-brillante en ~50 % (30-70 %) → falla (prob. 65 %).
- P8: m_lim elegido ∈ {4.0, 4.5, 5.0}.
**Global:** probabilidad de que la compuerta completa pase = 20 %.

## 2026-10-30 22:14 UTC — Resultados de v1 vs predicciones (E1 regimen A, E2 regimen B)  [medido: out/resultados_A.csv, resultados_B.csv, resumen_*.json]

| Prediccion | Resultado medido | Veredicto |
|---|---|---|
| P1 F1 mediano A = 0.30 (0.20-0.45), NN 0.27 | modelo **0.610**, NN **0.636** | **FALLO mia**: el problema A es mucho mas facil (las estrellas ya son las de las lineas) |
| P2 G1_A pasa en 90-100 % | 56/56 (100 %) | acierto (el nulo de grados es trivial; mediana F1 del nulo 0.011) |
| P3 G2_A (modelo > NN) en ~55 %, falla | **20/56 = 36 %** (29 % por familias, IC95 14-45 %); con IC de la diferencia >0 solo 1/56; el modelo es *peor* que NN con IC en 6/56 | acierto cualitativo, **peor de lo previsto** |
| P4 solo-proximidad a +-5 % del modelo | mediana 0.607 vs 0.610 | acierto |
| P5 boorong no peor que azar; kamilaroi no evaluable; nakshatras en mitad inferior | boorong ratio vs nulo-grados = 55x; kamilaroi 3 aristas; nakshatras F1_A=0.654 > mediana 0.61 | boorong/kamilaroi acierto; **nakshatras fallo** |
| P6 LOCO≈LOFO, hiperparametros iguales en >80 % pliegues | diferencia 0.000; **100 %** de los pliegues eligen (lam=.25, R=0, r=1.25) | acierto (por eso la fuga LOCO es inocua *con este modelo*; el test de fugas sigue siendo necesario) |
| P7 B: F1 mediano 0.05, G1_B pasa >=85 %, G2_B ~50 % y falla | F1 mediano **0.132**; G1_B 56/56; G2_B **36/56 = 64 % (72 % por familias, IC95 55-87 %)** → NO alcanza el 75 % por culturas | F1 fallo mio (x2.6); G1 acierto; G2 acierto cualitativo (falla por poco) |
| P8 m_lim ∈ {4.0,4.5,5.0} | eligio 3.5 en 47/56 pliegues y 4.0 en 9 | **fallo mio** |
| Global: compuerta pasa 20 % | **NO pasa**: G2_A 36 % y G2_B 64/72 % < 75 % | consistente |

Notas: (i) el nulo (a) de grados es tan debil (F1 ~0.003-0.01) que "x2" no dice nada; el nulo informativo es el NN. (ii) El modelo supera al subconjunto aleatorio de aristas Delaunay
(F1 0.61 vs 0.25 en A; 0.13 vs 0.03 en B) en 56/56: la geometria *si* importa, pero **un grafo de vecino mas cercano hace lo mismo o mas**.
(iii) v1b (post hoc, rejilla de r ampliada hasta 3.0 porque r=1.25 era el borde): mismo optimo r=1.25 en los 56 pliegues, mismo veredicto (out/resultados_A_v1b.csv). No era un artefacto del borde.
(iv) En B el modelo gana al NN en las culturas "orales/etnograficas" (mediana de cociente ~1.2-1.7: maori, tongan, macedonian, vanuatu, tupi, tukano, samoan...) y pierde en los sistemas
de catalogo (modern*, greek*, al-Sufi, babilonios: cociente 0.7-0.85). [exploratorio, post hoc; se contrasta abajo].

### Autocritica de v1 (¿esto es basico? ¿que control lo invalidaria?)
1. Si, v1 es basico: dos pesos fijos y un presupuesto de aristas. El hallazgo robusto es *negativo*: dadas las estrellas (A) el vecino mas cercano (F1 .64) rinde igual o mas que el gestalt completo (.61).
2. El regimen A tiene un sesgo de seleccion: el conjunto de estrellas ya excluye las que la cultura no usa, y toda estrella tiene >=1 arista; el NN explota eso. B es el test relevante; en B el modelo supera al NN por +6 % relativo en mediana y solo 25 % de culturas con IC95 de la diferencia > 0.
3. Control que invalidaria: que el modelo supere al NN solo porque tiene mas hiperparametros (4 frente a 1). Mitigacion: v2 se compara con un NN afinado y con un "techo de consenso" (aristas compartidas entre culturas de entrenamiento).
4. Las verdades de Stellarium son lineas dibujadas por editores (a veces a partir de ilustraciones), no necesariamente lo que un pueblo "veia"; Kemp et al. usaron conjuntos de estrellas por esa razon. Limite de la metrica de aristas.
5. Familias: supuesto mio; con familias mas amplias (p. ej. todo lo europeo junto) habria menos fuga aun.

### Decision (v2): quemar v1 como modelo final y probar un modelo aprendido
Ya se corrio v1 sobre todas las culturas, asi que cualquier v2 diseñado mirando esos numeros arriesga bifurcaciones del jardin. Medida: **división sellada por familias** fijada ahora (semilla 7 sobre las 29 familias elegibles):
- DISEÑO (15 familias; las unicas cuyos F1 de v2 miro mientras diseño): potawatomi, romanian, nordica, belarusian, navajo, tukano, seri, balinese, tupi, polinesia, mongolian, arabe_popular, tibetan, sardinian, lokono.
- SELLADO (14 familias; sus F1 de v2 no se calculan hasta congelar el diseño): india, egyptian_dendera, aztec, northern_andes, china, occidental, russian_siberian, boorong, vanuatu_netwar, tikuna, babilonia, sami, inuit, macedonian.
El sello protege las *decisiones de diseño*; los pesos del modelo se entrenan siempre con todas las demas familias (leave-one-family-out).

## 2026-10-30 22:26 UTC — v2 congelado y PREREGISTRO del test sellado  [medido en las 15 familias de DISEÑO: out/resultados_v2_diseno_{hgb,lr}.csv]

Desarrollo de v2 (src/v2.py, src/correr_v2.py), mirando solo las familias de diseño (22 culturas):
- v2-HGB (17 rasgos gestalticos del cielo + HistGradientBoosting depth 3, 120 iter; K = n.o de aristas elegido por validacion cruzada interna por familias): F1 mediano **0.204**, NN 0.137, G2 (>NN) 91 % de culturas / 87 % por familia; techo "consenso de otras culturas" 0.271.
- v2-LR (regresion logistica con los mismos rasgos): F1 mediano 0.168, G2 86 %. Peor que HGB → se queda HGB; LR al cementerio como modelo principal.
- Referencia: v1 en esas mismas 22 culturas daba F1 0.166 y G2 86 %. Es decir, las familias de diseño son las "faciles" (casi todas orales/etnograficas); la mejora de v2 sobre v1 alli es modesta (+0.04).
- Vigilancia anti-trampa: el "consenso" usa las aristas de OTRAS familias, no la geometria; sirve de techo de lo que se puede transferir entre culturas con un mapa fijo del cielo.
**Congelado (no se tocara antes del test sellado):** rasgos, HGB, K∈{40,70,100,150,220,320,450,700}, universo = estrellas con mag<=5.5 y ID Hipparcos, LOFO, bootstrap B=200.

**Predicciones para el sellado (14 familias, 33 culturas elegibles; aqui estan los pesos pesados: china 10 culturas, occidental 10, babilonia 2, india 2):**
- S1: F1 mediano de v2 sobre las 33 culturas sellada = 0.12 (0.08-0.17); NN 0.11 (el sellado contiene los sistemas de catalogo donde el NN fue fuerte).
- S2: G2 (v2 > NN) por familia = 70-85 % (central 75 %), pero **por culturas solo 55-70 %** porque 20 de las 33 son chinas/occidentales, donde v1 perdia contra NN. Compuerta (ambos criterios >=75 %): **prob. de pasar 25 %**.
- S3: v2 supera a v1 en el sellado en F1 mediano por >=0.02 con prob. 60 %.
- S4: techo de consenso > v2 en ≥80 % de culturas.
- S5: G1 100 %.
Si la compuerta falla en el sellado, NO hay extension: se publica el informe de lo medido.

## 2026-10-30 22:39 UTC — RESULTADO del test sellado (14 familias, 34 culturas)  [medido: out/resultados_v2_sellado_hgb.csv, out/resumen_v2.json]
(Nota de honestidad: el script corrio v2 tambien sobre las familias de diseño; el analisis del sellado filtra las 14 familias sellado.)

| Prediccion | Resultado | |
|---|---|---|
| S1 F1 mediano v2 = 0.12 (0.08-0.17); NN 0.11 | v2 **0.090**, NN **0.121** (media por familia: v2 0.131, NN 0.098) | v2 mediano fuera de mi rango por abajo; NN acierto |
| S2 G2 por familia 70-85 %, por culturas 55-70 % | por familia **72 %** (IC95 50-93 %); por culturas **38 % (13/34)** | familia acierto; **culturas fallo grande** |
| compuerta (ambos >=75 %) pasa con prob. 25 % | **NO pasa** | consistente con lo esperado |
| S3 v2 supera a v1 en F1 mediano por >=0.02 | v2 0.090 vs v1 0.109 → **falso** (v2 mejora en 10 de 14 familias pero se hunde en las dos grandes) | fallo |
| S4 consenso > v2 en >=80 % | 82 % (v2>consenso solo en 18 %) | acierto |
| S5 G1 100 % | 100 % | acierto |

Donde gana v2 al NN: aztec, babilonia (x2), boorong, india (x2), inuit, macedonian, russian_siberian, sami, vanuatu (y empata egyptian_dendera). Donde pierde con IC95 de la diferencia < 0:
las 10 culturas chinas/japonesa/coreana y 9 de las 10 occidentales; tikuna y northern_andes (sin IC claro; 25-90 aristas).
Mecanismo (medido): el K elegido en entrenamiento para china/occidental es 40-70 (esos sistemas "de catalogo" prefieren pocas aristas entre estrellas brillantes y tienen >1000 aristas con muchas estrellas debiles fuera del universo mag<=5.5:
solo 7-12 % de sus aristas tiene ambos extremos en el universo del modelo, ver frac_aristas_en_universo en resultados_B.csv).
**Hallazgo exploratorio (post hoc, no preregistrado):** agrupando culturas por tipo, en el regimen B (v1) el modelo gana al NN en el 86 % de las 28 culturas orales/etnograficas/tradicionales (mediana del cociente F1 1.23)
y en el 35 % de las 23 culturas "de catalogo" (chinas, occidentales, babilonias, egipcia, al-Sufi; cociente 0.86). En el regimen A no hay diferencia (todo ≈ NN, cociente ~0.96-1.02).

**Veredicto de la compuerta: NO PASA** (v1: A 36 %, B 64 %/72 % familias; v2 sellado: 38 % culturas/72 % familias). Por la regla preregistrada **no se hace la extension a otros cielos como prediccion**.
Lo que si se hace: una demostracion geometrica etiquetada "no validada" (README/HTML) y una cuantificacion de cuanto cambia la estructura gestaltica del cielo al moverse a estrellas vecinas.

### Cementerio de ideas
- Regresion logistica como v2 principal: F1 0.168 vs HGB 0.204 en diseño → descartada como modelo principal.
- k-means / CODE de Kemp: no implementados (no era necesario: el NN es un nulo mas fuerte y mas simple).
- Nulo "mismas estrellas y mismos grados" como criterio de exito: trivial (F1 ~0.003-0.01), pasa cualquier modelo basado en proximidad. Se conserva por peticion del Ministro pero no discrimina.
- Footprint por declinacion (variante B') y metrica de conjuntos a lo Kemp: no hechas; limite declarado.

## 2026-10-30 22:40 UTC — CORRECCION de mi propio texto anterior (mecanismo de la derrota en china/occidental)
Escribi arriba que en esas familias solo el 7-12 % de las aristas tiene ambos extremos en el universo del modelo. **Era un error de atribucion**: ese numero (resultados_B.csv, frac_aristas_en_universo) corresponde al universo de v1 (m_lim=3.5, elegido por v1).
Para el universo de v2 (mag<=5.5) [medido] el 76 % (china) y el 90 % (occidental) de sus aristas tienen ambos extremos dentro. El mecanismo real es el **presupuesto**: el K elegido en entrenamiento es 40-70 aristas, y como
F1 = 2tp/(K+|E|) con |E|≈1000-1500, el techo del F1 es 2K/(K+|E|) ≈ 0.07-0.12, mientras que el NN dispone de ~180 aristas. El modelo y el NN no tienen el mismo presupuesto, asi que la comparacion
de la compuerta mezcla "calidad de aristas" con "numero de aristas". La compuerta preregistrada tal como se definio (K elegido en N-1 familias) sigue siendo el veredicto; ademas se corre ahora, **como analisis
exploratorio post hoc**, el mismo v2 con K = numero de aristas del NN (presupuesto igualado): out/resultados_v2_sellado_hgb_kmatch.csv.

## 2026-10-30 22:48 UTC — Presupuesto igualado, potencia, extension exploratoria y cierre
- [medido, exploratorio post hoc] v2 con K = n.o de aristas del NN (out/resultados_v2_sellado_hgb_kmatch.csv): en el sellado gana al NN en 32/34 culturas (86 % por familias, IC95 64-100 %), F1 mediano 0.183 vs 0.121; el techo de consenso (0.224) sigue por encima.
  No cambia el veredicto: el criterio se decidio despues de ver el sellado, que ya esta quemado para v2. **Sin datos independientes no se puede confirmar.** Es la principal mejora pendiente (preregistrar K = |NN| y probar en datos nuevos, p. ej. otras culturas o Gaia).
- [medido] Potencia (out/potencia.csv): con q=0 (aristas Delaunay al azar) G1 se supera en 95 % (el nulo de grados no discrimina) y G2 da 20 % de falsos positivos; G2 detecta 71 % con q=0.5, 82 % con q=0.75, 93 % con q=1. A partir de aqui «G2 falla» solo permite concluir que no hay mas de ~la mitad de aristas gestalticas.
- [medido] Extension exploratoria (src/extension_demo.py, out/estabilidad.csv): conserva mediana 55 % de las aristas terrestres desde 61 estrellas a <5 pc; Sol unido por lineas en 41/61 (mag 0.41-3.3). Consistencia: observador en el origen reproduce las magnitudes de HYG (mediana |dm|<0.01, test).
  TRAPPIST-1: no esta en HYG; Wikipedia devolvio 429 al verificar coordenadas → no incluido. Las companeras de Alfa Centauri A y de Sirio aparecen con mag ~-19/-14 (posiciones HYG a ~20 UA/20 UA): dominan el cielo, no son «constelaciones».
- [medido] zodiaco.html: autonomo, 520 KB, sin peticiones de red; JS probado con Node + DOM simulado; geometria comprobada con matplotlib. NO probado en navegador real. Cartel «generado por el modelo, no validado» fijo sobre el lienzo.

### Sorpresas
1. Lo facil que es el regimen A (F1 0.61): casi todo es vecindad.
2. El nulo «mismas estrellas y grados» es inutil como criterio: aristas Delaunay al azar ya lo triplican.
3. El K unico elegido en N-1 familias destruye el F1 de las culturas enormes (china, occidental): un hiperparametro global de presupuesto es incompatible con tamanos de sistema que varian 100x.
4. Mi propia correccion del mecanismo: primero atribui la derrota al universo de estrellas (error), luego medi que era el presupuesto.
5. Patron exploratorio: culturas orales/etnograficas «leen» mejor la geometria que los sistemas de catalogo.

### Quien me ayudo
Nadie mas ejecuto codigo. Ideas e informacion: la Idea 2 del Ministro Loco (casa-ministro/IDEAS.md), el paper de Kemp et al., Stellarium y HYG (datos publicos). Codigo y analisis mios; no se uso el codigo de Kemp (no se descargo ni ejecuto).
