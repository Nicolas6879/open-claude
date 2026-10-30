# Zodiaco de Alfa Centauri (casa-zodiaco)

Idea 2 del Ministro: *¿hay una gramática perceptiva de las constelaciones que se pueda exportar a otros cielos?*
Se entrena un modelo gestáltico con culturas celestes reales, se le exige predecir las constelaciones de una cultura (o familia) que no vio y,
**solo si lo logra**, se le pide que dibuje el cielo desde otra estrella.

**Veredicto corto: la compuerta preregistrada NO pasó.** El modelo predice las aristas de culturas que no vio muy por encima del azar,
pero no supera con claridad a un nulo trivial de «vecino más cercano». Por eso la extensión a otras estrellas **no se presenta como predicción**:
solo existe una demostración geométrica exploratoria, etiquetada como tal (`zodiaco.html`).

Todo lo que aparece es **generado por el modelo**: no es tradición de ningún pueblo y no se atribuye nombre, mito ni historia a nadie.

## Qué hicieron Kemp et al. y qué añade esto
**Kemp, Hamacher, Little y Cropper (2022)**, *Perceptual grouping explains similarities in constellations across cultures*, arXiv:2010.06108 (leído entero para este trabajo) [medido]:
27 sistemas (22 de Stellarium 0.20.1 + 5 de la literatura), estrellas más débiles que mag 4,5 eliminadas, 605 asterismos. Modelo «Graph Clustering»:
unión de triangulaciones de Delaunay (mag 3,5/4,0/4,5), peso brillo × proximidad con escalado local a 60°, ρ = 3, se conservan las n aristas más fuertes y las componentes conexas son los asterismos.
Se evalúa por solapamiento de *conjuntos de estrellas* (F10, Rand ajustado) frente a k-means, CODE y variantes del propio modelo.
**No** hacen validación dejando fuera culturas (ρ y n se eligen con las mismas 27), **no** usan nulos de grafo aleatorio ni de vecino más cercano, **no** corrigen por familias de culturas emparentadas y **no** mueven el observador.

**Lo que añade este trabajo:** (1) réplica ampliada a **60 culturas** de Stellarium (56 evaluables, 29 familias; el Ministro habló de 62, pero 60 son las activas en el `CMakeLists.txt`);
(2) métrica a nivel de **aristas** y validación **leave-one-family-out** (`leave-one-culture-out` literal también, con su fuga demostrada en un test); (3) nulos exigentes y **cielo ciego** (el modelo decide estrellas y aristas);
(4) prueba **sellada** por familias con preregistro con fecha y hora; (5) medida de potencia por inyección de estructura; (6) un primer intento de extensión, que se queda en exploratorio.
Esta réplica **no** reproduce el resultado de Kemp con su métrica de conjuntos; lo contrasta con otra métrica y otros comparadores.

## Datos y pérdidas  [medido: `out/contabilidad_culturas.csv`]
- 60 `index.json` de Stellarium (`skycultures/CMakeLists.txt`, 4 más comentadas y excluidas: armintxe, egyptian, maya, modern_sternenkarten) y HYG v4.1 (119 626 filas, 117 951 con ID Hipparcos).
- Verdad = aristas únicas HIP–HIP de `constellations[].lines` ∪ `asterisms[].lines` (sin *ray helpers*). De 27 895 aristas brutas: 803 se pierden por vértices que no son estrellas (coordenadas RA/Dec de constelaciones «oscuras»/polígonos y objetos `DSO:`), 64 por HIP ausente de HYG y 1 841 son duplicados → **24 510 aristas**.
- **Kamilaroi queda con 3 aristas** (su emú está dibujado con coordenadas, no con estrellas), khoi-san, xhosa y zulu con 5–6: no evaluables (elegibles: ≥ 15 aristas = 56 culturas).
  Por tanto la hipótesis del Ministro de «cielos oscuros peor que el azar» **no se puede contrastar con estos datos**; boorong (aristas estelares, 201) no sale peor que el azar (F1 0,60 frente a 0,012 de un grafo aleatorio con sus estrellas y grados en el régimen A).
- **Familias** (supuesto mío, `src/datos.py`): 7 variantes `modern*` de las 88 constelaciones IAU, 4 griegas y al-Sufi son una sola familia; 10 sistemas chinos/japonés/coreano, otra; babilonios, indios, árabes populares, polinesios, nórdicos. 29 familias elegibles.
- **Licencias** (de `description.md` de cada cultura): CC BY-SA (25 en 4.0 y 7 de otras versiones o mixtas con Free Art License), CC BY-ND 4.0 (12), GPL v2 (9), CC BY-NC-ND 4.0 (5), CC BY 4.0 (2), otras (CC BY-SA 2.0/3.0, CC BY-NC-SA para ilustraciones). Detalle por cultura en `out/contabilidad_culturas.csv`.
  17 culturas tienen cláusula ND. **Este repo no redistribuye aristas de ninguna cultura**: solo el script de descarga y estadísticas agregadas (F1 por cultura). Estrellas: HYG v4.1 (CC BY-SA 4.0). Referencia: Stellarium, <https://github.com/Stellarium/stellarium>.

## Modelos
- **v1** (`src/modelo.py`): grafo candidato = unión de Delaunay esféricas (mag 3,5/4/4,5/5,5/todas) → puntuación −(λ·0,921·mag de la más débil + ln d) con escalado local (R ∈ {0,30,60,90}°) → las k = r·N aristas mejores. Hiperparámetros globales (λ, R, r, m_lim), elegidos en N−1 familias.
- **Régimen A** («estrellas conocidas»): el modelo recibe las estrellas que usa la cultura y propone aristas. **Régimen B** («cielo ciego»): recibe todo el cielo hasta m_lim; es el que exige la extensión.
- **v2** (`src/v2.py`, hecho tras ver v1, con división sellada): 17 rasgos gestálticos del cielo (ln d, magnitudes, escalado local, «rango» del vecino brillante más cercano, bloqueadores en la lente RNG, densidades…) + HistGradientBoosting, entrenado con las aristas de las demás familias (peso 1/|familia|), K elegido por validación cruzada interna.
- **Nulos:** (a) grafo aleatorio con las mismas estrellas y grados; (b) vecino más cercano (A: entre las estrellas de la cultura; B: entre las ≤ m_lim, con m_lim afinado igual que el modelo); (b2) solo proximidad; (c) subconjunto aleatorio de las aristas Delaunay con el mismo presupuesto; **techo de consenso**: aristas compartidas por las otras familias (sin geometría).
  IC95 % por *bootstrap* de constelaciones; intervalos de las fracciones por *bootstrap* de familias.

## Resultados  [medido: `out/resumen_*.json`, `out/resultados_*.csv`]
Compuerta preregistrada (LOG.md, con hora UTC): G1 = F1 ≥ 2× nulo (a) en ≥ 75 %; G2 = F1 > vecino más cercano en ≥ 75 %; por culturas **y** ponderado por familia; extensión solo si ambas pasan en A y B.

| Experimento | G1 (×2 nulo grados) | G2 (modelo > vecino más cercano) | F1 mediano modelo / vecino |
|---|---|---|---|
| v1 régimen A, 56 culturas, 29 familias | 56/56 | **20/56 = 36 %** (29 % por familias, IC95 14–45 %) | 0,61 / 0,64 |
| v1 régimen B (ciego) | 56/56 | **36/56 = 64 %** (72 % por familias, IC95 55–87 %) | 0,132 / 0,122 |
| v2 prueba **sellada** (14 familias, 34 culturas) | 34/34 | **13/34 = 38 %** (72 % por familias, IC95 50–93 %) | 0,090 / 0,121 |
| *exploratorio post hoc:* v2 con K = aristas del vecino más cercano (sellado) | 34/34 | 32/34 = 94 % (86 % por familias, IC95 64–100 %) | 0,183 / 0,121 |

- **El modelo sí predice mucho más que el azar**: F1 en B de 0,13 frente a 0,003 del nulo (a) y ~0,03 de aristas Delaunay al azar; en A 0,61 frente a 0,011 y 0,25. Pero G1 **no discrimina**: la prueba de potencia muestra que aristas Delaunay al azar ya lo superan en el 95 % de los casos.
- **Frente al vecino más cercano el resultado no alcanza el umbral**. En A el vecino más cercano gana (0,64 frente a 0,61): dadas las estrellas, la proximidad lo explica casi todo; añadir brillo y escalado local no ayuda (proximidad sola: 0,607). En B el modelo gana por poco (+6 % relativo mediano; con IC95 de la diferencia > 0 solo en el 25 % de culturas).
- **v2 en el sellado** gana en 10 de 14 familias, pero pierde con IC en las 10 culturas china/japonesa/coreana y en 9 de 10 occidentales. Mecanismo (medido): el K elegido con las demás familias fue 40–70 aristas y esas culturas tienen > 1000, así que su F1 está acotado por 2K/(K+|E|) ≈ 0,07–0,12; el vecino más cercano tiene ~200 aristas. Con presupuesto igualado (análisis **post hoc**, decidido tras ver el resultado) v2 gana casi siempre, pero esa comparación **no puede confirmarse con estos datos** (el sellado ya se usó) y el techo de consenso entre culturas (0,22 mediana) sigue por encima del modelo (0,18).
- **Exploratorio (no preregistrado):** en B (v1) el modelo gana al vecino más cercano en el 86 % de las 28 culturas orales/etnográficas/tradicionales y en el 35 % de las 23 de «catálogo» (chinas, occidentales, babilonias, egipcia, al-Sufi). Coincide con lo que Kemp et al. dicen de que estos sistemas cubren todo el cielo con figuras que no son unidades perceptivas.
- **Fuga LOCO frente a LOFO:** con v1 los hiperparámetros son idénticos en todos los pliegues (λ = 0,25, R = 0, r = 1,25 en A), así que LOCO y LOFO dan lo mismo; el test `test_fugas_familia` prueba que el LOCO literal *sí* dejaría parientes en el entrenamiento.
- **Potencia** (`out/potencia.csv`, tamaños de las 56 culturas, 3 repeticiones): con 0 % de aristas gestálticas G2 sale «positivo» en el 20 % (falsos positivos); con 30 %, 40 %; con 50 %, 71 %; con 75 %, 82 %; con 100 %, 93 %. **Que G2 falle no prueba que no haya estructura gestáltica**: solo se detecta cuando al menos la mitad de las aristas lo son. Además `tests/test_pipeline.py` inyecta estructura en cielos sintéticos y comprueba que se detecta y que el control negativo no da ventaja.

## Extensión a otros cielos (exploratoria, NO validada)
Como la compuerta no pasó, **no se afirma qué dibujaría un observador humano** en otro cielo. `src/extension_demo.py` aplica el grafo de v2 (K = tamaño del grafo vecino-más-cercano de las estrellas ≤ 3,5 de ese cielo) a los cielos recalculados (`src/extension.py`: posiciones 3D de HYG, magnitud aparente = absmag + 5 log10(d/10), estrellas sin paralaje conservan su dirección terrestre) y mide propiedades geométricas [medido, `out/estabilidad.csv`]:
- Desde 61 estrellas a menos de 5 pc se conserva una mediana del 55 % (46–75 %) de las aristas que el modelo dibuja desde la Tierra: a 1,3 pc (Próxima) el 75 %, a 5 pc ~48 %. Hay duplicados por estrellas dobles, así que no son 61 sistemas independientes.
- El Sol queda unido por líneas en 41 de esos 61 cielos (su magnitud aparente va de 0,41 a 3,3). [medido] Desde Alfa Centauri A el Sol queda en RA 2,66 h, Dec +60,8° (desde Próxima: 2,50 h, +62,7°; magnitud 0,46 y 0,41), la dirección antípoda de Alfa Centauri; [no verificado, de memoria] que esa posición cae dentro de los límites IAU de Casiopea.
- TRAPPIST-1 no está en HYG y no se pudo verificar su posición (Wikipedia devolvió 429): **no incluido**.
- `zodiaco.html` (autónoma, sin red, 520 KB) muestra el informe y un visor de cielo completo (proyección de Hammer, zoom y arrastre) desde 8 estrellas, con las aristas «nuevas» frente a la Tierra resaltadas y cartel permanente «generado por el modelo, no validado». Probada con Node (lógica y dibujo con un DOM simulado) y comprobada la geometría con matplotlib; **no se probó en un navegador real**.

## Qué no se pudo verificar o falló
- Todo F1 depende de que las líneas de Stellarium sean lo que cada pueblo «veía»: son figuras dibujadas por editores, a veces desde ilustraciones; Kemp et al. usaron conjuntos de estrellas precisamente por eso. [supuesto]
- La agrupación en familias es mía; con familias más amplias (todo lo europeo junto) la validación sería más estricta.
- No se probó una variante con huella de declinación por cultura, ni la métrica de conjuntos de Kemp, ni k-means/CODE.
- HYG no sirve para observadores a más de ~50 años luz; sin movimiento propio ni extinción interestelar.
- Mis predicciones: acerté la dirección de G2 (falla) y de G1 (trivial); me equivoqué en las magnitudes (F1 de A 0,61 y no 0,30; F1 de B 0,13 y no 0,05; m_lim; nakshatras; S2 por culturas; S3). Ver LOG.md.

## Cómo reproducir (un proceso, venv con numpy/scipy/pandas/scikit-learn/matplotlib)
```bash
bash src/descargar.sh /ruta/fuera/del/repo/data           # descarga (lo bajado es no confiable; solo se parsea)
export ZODIACO_DATOS=/ruta/fuera/del/repo/data ZODIACO_TMP=/ruta/fuera/del/repo/tmp OMP_NUM_THREADS=1
python -I src/contabilidad.py                                  # out/contabilidad_culturas.csv
python -I src/correr_A.py 150  && python -I src/analizar.py A  # E1
python -I src/correr_B.py 300  && python -I src/analizar.py B  # E2
python -I src/correr_v2.py diseno hgb 0 ; python -I src/correr_v2.py sellado hgb 200 ; python -I src/correr_v2.py sellado hgb 100 kmatch
python -I src/analizar_v2.py ; python -I src/analizar_v2.py _kmatch
python -I src/potencia.py ; python -I src/extension_demo.py ; python -I src/hacer_html.py
python -I tests/test_pipeline.py ; python -I tests/test_v2_extension.py
```
Código: `src/` (datos, modelo, evaluación, v2, extensión). Resultados pequeños en `out/` (~0,8 MB). Diario con preregistros y errores: `LOG.md`.
