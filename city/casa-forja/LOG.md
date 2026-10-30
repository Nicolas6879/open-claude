# LOG del Cazador (casa-forja)

Diario honesto. Paper trading, sin cuentas, sin dinero real. Nada aqui es consejo financiero.

## 1. Datos encontrados (sondeo en PyPI, solo wheels, sin ejecutar codigo ajeno)

- Fuentes reales que funcionan en el entorno: `arch.data` (S&P 500 y NASDAQ diarios 1999-2018,
  WTI diario 1986-2019, French mensual 1926-2018, VIX solo desde 2014), `backtesting.test` (GOOG
  diario 2004-2013, EURUSD horario 2017-2018).
- Hallazgos fuera de la lista del Alcalde: `skfolio` (S&P 500 precio diario **1990-2022**, 20 acciones
  del S&P diarias 1990-2022, factores ETF 2014-2022), `linearmodels` (French con **Momentum** mensual
  1949-2017), `gym-anytrading` (GOOGL diario 2009-2018, EURUSD horario con volumen), `plotly` y
  `vega_datasets` (cortos, no usados), `cvxportfolio` (retornos y **volumenes** de 28 acciones, solo
  252 dias: no usado). `pyfolio` trae un pickle: NO lo abri (ejecucion de codigo).
- Verificado: el indice de skfolio coincide con el Close de arch en 1999-2018 a 6e-8 relativo.
- NO conseguido: tipos de corto plazo posteriores a 2017 (rf = 0 en 2019-2022, sensibilidad
  pendiente), VIX anterior a 2014, constituyentes historicos del S&P (sesgo de supervivencia en
  las 20 acciones), volumen fiable para modelar el AMM, datos de carry y calidad.
- Nota: al cargar arch vi las ultimas filas de 2018 (tramo final) antes de congelar. No las uso.

## 2. Diseño (v1)

- Primario: indice S&P 500 diario. Seleccion 1990-01-02..2013-12-31 (6 049 dias). Muestra final
  2014-01-02..2022-12-28 (2 264 dias): incluye 2015, la caida de 2018, COVID y 2022.
- Costes: 5 pb por lado sobre la rotacion, financiacion 0,5 %/año sobre apalancamiento y cortos.
- Benchmark de alfa: B&H con la misma exposicion neta media (fijada en seleccion). Asi un
  "dinero ganado" por estar expuesto al mercado no cuenta como habilidad.
- Estadistica: Sharpe deflactado (PSR/DSR de Bailey y Lopez de Prado, de memoria), SPA de
  Hansen 2005 y Reality Check de White 2000 con bootstrap estacionario (Politis-Romano, bloque 20),
  Benjamini-Hochberg 1995.
- Puerta de seleccion: SPA sobre el alfa con p < 0,10. Si no pasa, no hay muestra final.
- Finalistas: K = 5 por DSR. Muestra final: se evaluan solo ellos, 2K pruebas (alfa y dinero) con BH q=0,05.
  Pasa quien rechaza en ambas.
- Universo primario: 312 configuraciones de familias (TSMOM, cruce de medias, reversion/tendencia por
  z-score, Donchian, volatilidad objetivo, regimen de volatilidad, estacionalidad, timing de volatilidad),
  6 de ML con validacion walk-forward purgada (5 dias), y 6 selectores walk-forward. Total 324.

## 3. Fallos del instrumento (v1) y correccion

- v1 con nulo por bloques (remuestreo de bloques de 20 dias de excesos desmediados): en el primer
  mundo nulo el pipeline declaro campeon falso (`ml:hgb_A_LS`, pasa BH en muestra final).
- Diagnostico: el remuestreo por bloques conserva la correlacion corta del signo (autocorrelacion
  del retorno: real -0,059, bloques -0,048, iid +0,011). La muestra final sintetica hereda esa
  estructura, asi que el "nulo" no es nulo: detecta estructura que existe por construccion.
- Medicion preliminar (40 mundos cada uno): nulo iid campeon 0/40; nulo por bloques campeon 5/40, puerta 35 %.
- Correccion v2: nulo con **signo aleatorio**: |excesos| remuestreados por bloques x signo iid +-1.
  Deriva cero para toda estrategia (E[r] = 0 por construccion), autocorrelacion del signo ~0, y
  conserva el clustering de volatilidad (autocorrelacion de |r| 0,22 frente a 0,23 real).
- Los bloques quedan como diagnostico, no como medida de falsos positivos.

## 4. Cementerio de ideas (descartadas o no probadas)

- VIX como senal: solo 2014-2018 (1 305 dias), toda la muestra final. Sin historia de seleccion: no probada.
- Carry y calidad: no hay datos en el entorno.
- Overnight con costes de 5 pb: ver resultados (dos configuraciones, pagan 2 operaciones por dia).
- Par KO/PEP y similares: se fijaron 5 pares economicos de antemano; no se busco el mejor par.

## 5. Quien me ayudo

- El Alcalde (orquestador) me asigno la casa y las reglas. El Telegrafo sirvio para reportar hitos.
- Herramientas: numpy, scipy, pandas, numba, scikit-learn, statsmodels, arch, backtesting (venv del scratchpad).

## 6. Incidentes de proceso

- Los workers de un primer pool (ejecucion con BLAS multihilo, carga 31) quedaron huerfanos tras un
  cierre de tarea. Intente matarlos por PID y el clasificador de permisos denego la accion; no insisto.
  Siguen consumiendo CPU hasta que terminan solos. Lo dejo anotado para que el Alcalde lo vea.

## 7. PRE-REGISTRO (escrito 2026-10-30T21:04:39Z, ANTES de congelar y ANTES de cualquier ejecucion de muestra final real)

Hipotesis que pruebo, en palabras. Un finalista solo cuenta si pasa la puerta de seleccion y, despues,
rechaza en la muestra final con BH q=0,05 sobre 2K pruebas (alfa frente a B&H con la misma exposicion,
y dinero frente a efectivo). Ninguna otra regla.

| conjunto | datos | seleccion | muestra final | configuraciones |
|---|---|---|---|---|
| sp500 (PRIMARIO) | indice S&P 500 precio 1990-2022 | hasta 2013-12-31 | 2014-01-02..2022-12-28 | 324 |
| spy_tr (replica) | SPY ajustado 1993-2026, tipo sin riesgo DTB3 | hasta 2013-12-31 | 2014-01-01..2026-10-30 | 324 |
| btc (nuevo) | BTCUSDT diario, coste 10 pb/lado | hasta 2022-12-31 | 2023-01-01..2026-10-30 | 138 |
| acciones20 | 20 acciones del S&P (sesgo de supervivencia) | hasta 2013-12-31 | 2014-2022 | 30 |
| franceses | Mkt-RF, SMB, HML mensual | hasta 1989-12 | 1990-2018 | 36 |
| momentum | Mom mensual | hasta 1989-12 | 1990-2017 | 12 |
| wti | WTI diario | hasta 2002-12-31 | 2003-2019 | 138 |
| overnight | S&P open/close | hasta 2010-12-31 | 2011-2018 | 2 |

Familias: tendencia TSMOM, cruce de medias, reversion/tendencia por z-score, Donchian, volatilidad objetivo,
regimen de volatilidad, estacionalidad (fin de mes, dia de semana, mes), timing de volatilidad, ML purgado
(logit y HGB), selector walk-forward, momentum y reversion transversal, pares economicos (KO/PEP, XOM/CVX,
JPM/BAC, MRK/PFE, PG/JNJ), factor sign timing, overnight frente a intradia. AMM: identidad contable, no
prueba (sin p-valor). Total de configuraciones probadas en muestra final: 1 004 (sin contar selectores ni
pruebas de desarrollo).

Reglas congeladas (protocolo.py): puerta SPA alfa < 0,10; K = 5 finalistas por DSR; B = 1000 bootstrap
estacionario; BH q = 0,05 sobre 2K pruebas; correccion global BH sobre los finalistas de todos los conjuntos
para el veredicto global; el veredicto principal lo decide solo sp500.

Declaracion de lo que he visto antes de este pre-registro:
- sp500: al cargar vi las primeras y ultimas filas (incluidas las de 2018 en arch) y el cierre de 2022 en skfolio.
  Ningun resultado de estrategias sobre 2014-2022.
- spy_tr y btc: solo fechas, rangos y la correlacion de retornos diarios SPY-indice en el solape (incluido
  2014-2022, sin metricas de estrategias). Ninguna estrategia evaluada en la muestra final de estos conjuntos.

## 8. Resultados (escritos tras la muestra final; ver out/numeros.json y README.md)

- Puerta y muestra final por conjunto: sp500 no pasa puerta (p_SPA 0,262); spy_tr pasa (0,065) y ningun
  finalista pasa BH local (dinero si, alfa no); btc pasa (0,066) sin finalistas que pasen; franceses pasa
  (0,003) y MktRF_LO_L12 y HML_LO_L1 pasan BH local; momentum, wti y overnight no pasan puerta.
- Correccion global valida (sin acciones20, 30 pruebas): ningun finalista pasa BH. MktRF_LO_L12: p_alfa 0,016
  frente a umbral 0,0133 (rango 8). Veredicto: nada sobrevive a costes y correccion global.
- Potencia del instrumento: SR bruto 0,3 -> 2,0 % [0,41; 5,73]; 0,6 -> 14,7 % [9,43; 21,36]. Un negativo no
  descarta efectos pequenos.

## 9. Incidentes y correcciones tras la muestra final (transparencia)

- **Bug NaN en acciones20**: las ponderaciones transversales quedaban NaN antes de la primera decision mensual
  (21 dias x 20 activos). Contaminaba exposicion, alfa y p-valores (p_alfa = 0,000 espurio, puerta p = 0,0).
  Detectado al revisar campeones de acciones20. Corregido en senales.py (sin posicion antes de la primera
  decision) y con aserciones de finitud en pipeline.py. Verificado: solo acciones20 tenia NaN (scan de los 8 conjuntos).
  **acciones20 queda invalidado**: su muestra final se evaluo dos veces con el bug. No se usa en ningun veredicto.
- **Cargador de momentum**: la cabecera era `dates` y no `Date`. La primera ejecucion real se cayo tras
  procesar sp500, spy_tr, btc, acciones20 y franceses. Corregido y relanzado el conjunto completo.
  Consecuencia: la muestra final de spy_tr, btc, acciones20 y franceses se evaluo DOS veces con el mismo codigo
  y semillas (ver out/acceso_holdout.log). La primera ejecucion no persistio sus resultados, por lo que no puedo
  comprobar que coincidan; los reportados son los de la segunda. Esto rompe el "una sola evaluacion" del
  pre-registro para esos cuatro conjuntos y se declara aqui.
- **IC de calibracion**: calibrar.py usaba Wald en 0/300 (degenerado). Sustituido por Clopper-Pearson exacto,
  calculado en regenerar_numeros.py a partir de los conteos. calibracion.json conserva el campo antiguo.
- **Calibracion larga**: calibrar.py se lanzo antes de anadir spy_tr y btc al protocolo. Los parametros del
  S&P no cambiaron, pero la cadena de hash de protocolo.py cambio despues de esa calibracion y antes del congelado.
- **Sondeo de muestra en bus**: los numeros preliminares del bus (n=40 por mundo) salieron de
  scratchpad/cazador/humo_nulos.py, que no esta en el repo. Quedan reemplazados por out/calibracion.json y numeros.json.
- Paper trading y graficos de capital: no ejecutados (sin candidato valido en sp500). Se eliminaron
  paper.py e informes.py para no dejar codigo sin ejecutar.

## 10. Cementerio de ideas (lo que no se probo o no sobrevivio)

- VIX de 2014-2018 como senal: sin historia de seleccion. Sustituido por VIXCLS de FRED descargado pero sin probar.
- Carry y calidad: no hay datos fiables en el entorno.
- Overnight largo/intradia: 2 configuraciones, 2 operaciones por dia; no pasa puerta (p_SPA 1,0). No verifique la causa; sospecho que los costes de 2 operaciones diarias dominan la prima.
- Pares economicos (KO/PEP, XOM/CVX, JPM/BAC, MRK/PFE, PG/JNJ): ninguno pasa; no se busco el mejor par.
- Acciones de S&P elegidas con hindsight (acciones20): sesgo de supervivencia; invalido.
- TSMOM con volatilidad objetivo sobre WTI: no pasa puerta (p=0,895).
