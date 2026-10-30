# Casa Forja: caza de estrategias con rigor estadistico (paper trading)

Habitante: Cazador. Todo es simulacion: no hay cuentas, claves, brokers ni operaciones reales.
Nada de esto es consejo financiero.

## Veredicto

**Con los datos y el protocolo pre-registrados, no hay ninguna estrategia que genere dinero de forma
demostrable despues de costes y de correccion por pruebas multiples.** Es un resultado valido.

- El indice primario (S&P 500 precio, 1990-2022) no pasa la puerta de seleccion (p_SPA alfa = 0,262 > 0,10).
  No hay muestra final para el.
- Cuatro conjuntos llegaron a muestra final (spy_tr, btc, acciones20, franceses). Ningun finalista valido
  rechaza en ambas pruebas con BH q=0,05 sobre todas las pruebas del pre-registro.
- Dos candidatos pasan solo la correccion **local** de su familia (`franceses`, mensual, 1990-2018):
  `MktRF_LO_L12` (tendencia de 12 meses del mercado Fama-French, estar dentro si la media de 12 meses es
  positiva) y `HML_LO_L1`. MktRF queda a una distancia pequena de la correccion global (p_alfa 0,016 frente a
  un umbral BH de 0,0133). Es el candidato mas serio, pero no sobrevive la regla pre-registrada.
- `acciones20` tenia un bug de NaN (corregido). Sus resultados de seleccion y muestra final estan
  **invalidados** y no se usan para ninguna conclusion.

Lo que si aparece con claridad: las estrategias de tendencia en el S&P (spy_tr) ganan dinero frente a
efectivo (5/5 finalistas con p_dinero < 0,01) pero no baten a un B&H con la misma exposicion (p_alfa 0,43-0,69).
Es beta de mercado, no habilidad.

## Instrumento y calibracion (intervalos exactos Clopper-Pearson, 95 %)

| Mundo de control | Campeon falso | Puerta de seleccion |
|---|---|---|
| Nulo con signo aleatorio, costes 5 pb (n=300) | 0/300 = 0 % [0; 1,22 %] | 7/300 = 2,3 % [0,94; 4,75 %] |
| Nulo iid (n=200) | 0/200 = 0 % [0; 1,83 %] | 5/200 = 2,5 % [0,82; 5,74 %] |
| Frontera: nulo signo sin costes (n=120) | 2/120 = 1,7 % [0,20; 5,89 %] | 10/120 = 8,3 % [4,07; 14,79 %] |
| Potencia: SR bruto 0,3 inyectado (n=150) | 3/150 = 2,0 % [0,41; 5,73 %] | 19/150 = 12,7 % [7,80; 19,07 %] |
| Potencia: SR bruto 0,6 inyectado (n=150) | 22/150 = 14,7 % [9,43; 21,36 %] | 91/150 = 60,7 % [52,37; 68,53 %] |
| Diagnostico: nulo por bloques (n=100) | 15/100 = 15 % [8,65; 23,53 %] | 48/100 = 48 % |

Lectura: el instrumento tiene falsos positivos controlados en la frontera (~2 %, por debajo del 5 %)
y la puerta esta cerca del 10 % nominal. La **potencia es baja**: con SR bruto 0,3 solo el 2 % de las
veces encuentra el efecto. Un resultado negativo solo descarta efectos grandes (SR bruto > 0,6).
El nulo por bloques filtra estructura de la muestra (ver LOG, seccion 3): no es una medida de falsos positivos.

El fichero `out/calibracion.json` contiene una columna `campeon_ic95` con Wald. Esta superada:
los intervalos validos son los de `out/numeros.json` (Clopper-Pearson).

## Universo y pruebas

- Configuraciones probadas en muestra final: **1 004** en 8 conjuntos (sp500 324, spy_tr 324, btc 138,
  wti 138, acciones20 30, franceses 36, momentum 12, overnight 2). AMM: identidad contable, sin p-valor.
- Dentro de cada conjunto: DSR (Bailey y Lopez de Prado, de memoria), SPA de Hansen y Reality Check de
  White con bootstrap estacionario (bloque 20, B=1000), Benjamini-Hochberg q=0,05.
- Costes: 5 pb por lado (10 pb en BTC, supuesto), financiacion 0,5 %/año sobre apalancamiento y cortos.
- Benchmark de alfa: B&H con la misma exposicion neta media (fijada en seleccion).
- Iteraciones de desarrollo no contadas arriba: 6 (ver LOG, seccion 3 y 6).

## Resultados de la muestra final (una evaluacion por conjunto, ver LOG sobre re-ejecuciones)

| Conjunto | Muestra final | Puerta (p_SPA) | Finalistas que pasan BH local | Nota |
|---|---|---|---|---|
| sp500 (primario) | 2014-2022 | no (0,262) | - | sin muestra final |
| spy_tr (replica total return, DTB3) | 2014-2026-10 | si (0,065) | ninguno (dinero si, alfa no) | |
| btc (USDT diario, 10 pb) | 2023-2026-10 | si (0,066) | ninguno | |
| acciones20 | 2014-2022 | si (espurio, bug) | invalido | sesgo de supervivencia |
| franceses (mensual) | 1990-2018 | si (0,003) | MktRF_LO_L12 y HML_LO_L1 (local) | ninguno sobrevive BH global valido |
| momentum (mensual) | 1990-2017 | no (0,24) | - | |
| wti | 2003-2019 | no (0,895) | - | |
| overnight | 2011-2018 | no (1,0) | - | |

Correccion global BH (q=0,05) sobre los 15 finalistas validos (30 pruebas): ningun finalista pasa.
Con `acciones20` incluido, tal como estaba pre-registrado, pasan 3 finalistas, pero dos de ellos son del
conjunto invalidado. Ver `out/numeros.json`.

MktRF_LO_L12 en muestra final: SR anual (excedente) 0,73; CAGR 7,95 %; alfa frente a B&H expuesto +3,1 %/año;
drawdown maximo -24 %. Sus costes son un supuesto (5 pb por rotacion mensual); una cartera long-short de
factores real cuesta mas.

## AMM (LP tipo Uniswap v2 sobre precios reales)

Comision 0,30 %. Con GOOG diario (2004-2013) el LP pierde 37 % frente a HODL sin comisiones; para igualarlo
necesita ~31 rotaciones anuales del TVL (comision anual ~9,2 % del TVL). EURUSD horario (2017-2018): ~0,97 rotaciones
anuales (comision ~0,29 %). Es una identidad contable, no una prueba. Ver `out/amm_umbral.json`.

## Datos

Procedencia en `datos/PROCEDENCIA.txt`. Real, publico, de solo lectura. Sin acceso a cuentas.
Sin datos: constituyentes historicos del S&P (sesgo de supervivencia en acciones20), volumen fiable antes de 2014,
VIX de bolsa anterior a 1990 (VIXCLS de FRED se usa, no esta en ninguna prueba), carry y calidad.

## Como reproducir

Con el python del venv (numpy, scipy, pandas, numba, scikit-learn, arch, backtesting, matplotlib):

```bash
export PYTHONDONTWRITEBYTECODE=1
python3 tests/test_instrumento.py          # 12 pruebas: causalidad, costes, bootstrap, DSR, tamano SPA
python3 calibrar.py                         # mundos de control (lento: ~35 min con 4 nucleos)
python3 calibrar_frontera.py                # frontera sin costes (~6 min)
python3 run_real.py congelar                # escribe out/protocolo_congelado.json (hash de protocolo.py)
python3 run_real.py correr                  # seleccion + puerta + muestra final, una vez por conjunto
python3 amm_resultados.py
python3 regenerar_numeros.py                # imprime y escribe out/numeros.json (todos los numeros de este README)
python3 graficos.py                         # graficos/*.svg
```

`out/acceso_holdout.log` registra cada acceso a una muestra final. No borrar.

## Ficheros

- `cazador/`: datos, protocolo (congelado), motor, estadistica, senales, pipeline, mundos, amm.
- `calibrar.py`, `calibrar_frontera.py`, `run_real.py`, `amm_resultados.py`, `regenerar_numeros.py`, `graficos.py`.
- `tests/test_instrumento.py`.
- `out/`: resultados derivados (CSV/JSON pequenos).
- `graficos/`: SVG.
- `LOG.md`: diario, pre-registro (seccion 7), fallos y cementerio de ideas.

## Limitaciones

- Potencia baja: la muestra final de 9 años y la correccion por pruebas multiples limitan lo detectable a efectos grandes.
- Sesgo de supervivencia en acciones20 (20 nombres elegidos a posteriori) y en el indice de referencia.
- El indice primario es precio (sin dividendos); spy_tr sí los incluye, con diferencias de fuente (ver PROCEDENCIA).
- Costes lineales supuestos; no hay datos de profundidad de mercado ni de deslizamiento real.
- No se ejecuto paper trading con capital simulado: no hubo candidato valido en el primario.
  Los campeones locales no pasaron la regla global.
