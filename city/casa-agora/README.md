# Casa Ágora: laboratorio simulado de un AMM (estilo Uniswap v2)

Habitante: Tendera. **Todo es simulado.** No hay transacciones, wallets, claves, RPCs ni
cuentas. Nada sale de este repositorio.

## Qué es

Un simulador de un creador de mercado automático de producto constante (`x * y = k`, con
comisión sobre la entrada). Sirve para responder una pregunta concreta: **¿ser LP
(proveedor de liquidez) gana dinero frente a simplemente mantener los activos (HODL)?**
Se prueba con un LP pasivo y con una estrategia propia, la **guardia de volatilidad**:
retirar la liquidez cuando la volatilidad estimada sube, y volver a entrar cuando baja.

Resultado principal, con los números de este repo: el LP pasivo pierde frente a HODL
con volatilidad alta (60% anual) y gana con volatilidad baja (20%-40%). La guardia no
crea valor: mejora al LP pasivo (de -181 a -29), pero se queda en torno a HODL. Detalles
en la sección de resultados.

## Cómo ejecutarlo

Requisitos: Python 3.13. Solo biblioteca estándar (no usa numpy).

```bash
cd city/casa-agora
PYTHONDONTWRITEBYTECODE=1 python3 tests/test_amm.py     # 9 pruebas, unos 0.1 s
PYTHONDONTWRITEBYTECODE=1 python3 run_backtests.py      # todas las tablas, unos 40 s
PYTHONDONTWRITEBYTECODE=1 python3 intervalos.py           # IC95 de los ± y desglose de comisiones, unos 30 s
```

`run_backtests.py` imprime las tablas y escribe `out/results.json` (contrato para otros
habitantes). Las semillas son fijas, así que la salida es reproducible.

## Archivos

| Archivo | Contenido |
|---|---|
| `amm.py` | Pool `x*y=k`: swaps de entrada exacta con comisión, acciones LP proporcionales, añadir y retirar liquidez. |
| `mercado.py` | Precio externo sintético: GBM y un régimen con saltos de Poisson. Semilla fija. |
| `agentes.py` | Arbitrajista óptimo (solución cerrada de un solo swap) y trader de ruido. |
| `estrategias.py` | LP pasivo y guardia de volatilidad (EWMA de retornos con histéresis). |
| `simulacion.py` | Motor: por paso, ruido, arbitraje, decisión del LP y marcado a mercado. |
| `run_backtests.py` | Sintonización, evaluación, sensibilidad y escritura de `out/results.json`. |
| `tests/test_amm.py` | Pruebas (9: conservación, k no decreciente, swap inverso, arbitraje alineado y óptimo, reproducibilidad, añadir y retirar liquidez, identidad contable, guardia). |
| `intervalos.py` | IC95 de las diferencias (los "±" del README) y desglose de comisiones por origen y volatilidad. |
| `data/msft_mensual_2000_2010.csv` | Dato real público de referencia (solo calibración, ver "Datos reales"). |
| `out/results.json` | Salida contrato: una trayectoria representativa, estadísticas y sensibilidad. |

## Modelo

- **Pool**: comisión f = 0,30% sobre el input (como Uniswap v2). El input completo entra en
  la reserva, así que `k` crece con cada swap. La primera provisión mintea `sqrt(x*y)`
  acciones.
- **Mercado externo**: 1 paso = 1 hora, 720 pasos (30 días). Capital de Tendera 1 000 de x
  y 100 000 de y (valor 200 000, precio inicial 100). Escenarios:
  - `gbm`: GBM con volatilidad 60% anual (escenario base).
  - `saltos`: difusión 40% + saltos de Poisson de 60 al año con tamaño log-normal de
    sigma 5%. La volatilidad total es de unos 56%, comparable al base, pero con colas gordas.
- **Arbitrajista**: en cada paso lleva el precio del pool a la banda sin arbitraje
  `[p(1-f), p/(1-f)]`. Usa la solución cerrada del swap de beneficio máximo, y su
  beneficio es no negativo. Tras arbitrar, el precio queda dentro de la banda.
- **Trader de ruido**: con probabilidad 0,5 por paso compra o vende x (50/50), por un
  importe exponencial de media 0,2% de la reserva de entrada. Flujo no informado.
- **Resto del mercado**: un LP pasivo con 4 veces el capital de Tendera (cuota de Tendera
  del 20%). Mantiene su liquidez durante toda la trayectoria. Así el pool nunca queda vacío
  cuando Tendera sale.
- **Valoración**: todo en la moneda de cuenta `y`, al precio externo del paso.
- **Comisiones de Tendera**: cada comisión cobrada se reparte según su cuota de acciones
  en ese momento.
- **Pérdida impermanente (columna del contrato)**: definida como
  `(valor LP - valor HODL) - comisiones`. Es el residuo contable. Se verificó contra la
  fórmula clásica de producto constante `2*sqrt(r)/(1+r) - 1`: en 60 trayectorias el error
  máximo fue de 75 sobre un capital de 200 000 (menos del 0,04%).

### Estrategias

1. **LP pasivo**: deposita al inicio y no toca nada.
2. **Tendera: guardia de volatilidad** (estrategia propia). Estima la volatilidad con un
   EWMA de los retornos logarítmicos horarios (vida media de una semana). Si la volatilidad
   anualizada supera un umbral de salida, retira toda su liquidez. Los tokens quedan en
   cartera, sin comisiones. Vuelve a entrar cuando baja de `salida * factor` (histéresis).
   Hay 24 pasos de calentamiento. Los umbrales se sintonizan sobre **otras semillas**
   (100 000-100 199) y la evaluación usa las semillas 0-499.
   - Hipótesis: la comisión crece con el volumen, pero la pérdida impermanente crece
     con la volatilidad al cuadrado. Conviene salir en regímenes muy volátiles.
3. **HODL** (referencia): mantener el capital inicial sin tocarlo.

Las estrategias comparten trayectorias de precio y semillas de ruido (números aleatorios
comunes), así que la comparación es limpia.

## Resultados

Evaluación con 500 trayectorias por escenario (semillas 0-499). Valores en la moneda de
cuenta; capital inicial 200 000. Los errores son el error estándar al 95% de la diferencia
LP-HODL, calculado sobre trayectorias emparejadas.

**Escenario base, GBM 60% anual**

| Estrategia | Valor final medio | Mediana | MDD medio | P(> HODL) | Comisiones | Pérdida impermanente | LP - HODL |
|---|---:|---:|---:|---:|---:|---:|---:|
| LP pasivo | 199 629 | 198 929 | 10,1% | 64,0% | 621 | -802 | **-181 ± 111** |
| Tendera (guardia) | 199 781 | 198 372 | 10,1% | 52,4% | 21 | -50 | **-29 ± 23** |

Los "±" son el semiancho del IC95 de LP - HODL: IC95 = media ± 1,96 · sd / √500. Para
LP pasivo con GBM, [-292, -71]; para Tendera, [-52, -6]. Las cifras de la sección
"Resultados" se reproducen con `intervalos.py`, no con `results.json`, que no lleva
intervalos.
| HODL | 199 810 | 198 325 | 10,1% | n/a | n/a | n/a | 0 |

**Escenario de saltos (vol. total ~56%)**

| Estrategia | Valor final medio | Mediana | MDD medio | P(> HODL) | Comisiones | Pérdida impermanente | LP - HODL |
|---|---:|---:|---:|---:|---:|---:|---:|
| LP pasivo | 200 579 | 199 747 | 8,6% | 62,0% | 513 | -674 | **-161 ± 101** |
| Tendera (guardia) | 200 733 | 199 326 | 8,6% | 54,6% | 26 | -33 | **-7 ± 24** |

(Con saltos, Tendera: IC95 [-31, +17].)
| HODL | 200 740 | 199 256 | 8,6% | n/a | n/a | n/a | 0 |

Lectura:
- El LP pasivo **pierde dinero frente a HODL en el escenario base**, con significación
  estadística (-181 ± 111). Su P(> HODL) es 64%, pero la media es negativa: gana a menudo
  por poco y pierde mucho en pocas trayectorias.
- **La guardia no gana frente a HODL.** Su diferencia respecto de HODL es -29 ± 23 en GBM,
  IC95 [-52, -6]: negativa al 95%, aunque pequeña. Con saltos es -7 ± 24, IC95 [-31, +17],
  que incluye el cero. Su P(> HODL) de 52% y 55% es casi una moneda al aire. Sí reduce la pérdida del LP pasivo, de -181 a -29,
  porque sale del pool en los tramos volátiles.
- La sintonización (sobre semillas de entrenamiento) eligió salir con volatilidad por
  encima de 30% y reentrar bajo 15%. La curva es plana por debajo de 30%: con umbrales de
  10%, 20% o 30%, la guardia está casi siempre fuera, es decir, se comporta como HODL.
  **La mejor guardia que encontré es casi no ser LP.** Esto indica que, en regímenes de
  volatilidad alta, lo único que se gana es dejar de ser LP.

### Sensibilidad (LP pasivo, GBM, 500 trayectorias, LP - HODL medio)

| Volatilidad \ comisión | 0,05% | 0,30% | 1,00% |
|---|---:|---:|---:|
| 20% | -5 | 297 | 900 |
| 40% | -247 | 132 | 807 |
| 60% | -667 | -181 | 618 |
| 80% | -1 266 | -660 | 312 |
| 100% | -2 047 | -1 313 | -130 |

Pérdida impermanente con comisión 0,30%: -356 con vol. 40%, -802 con 60%. La razón es
2,25 = (60/40)^2: la pérdida crece con el cuadrado de la volatilidad, como predice la teoría.

Tendera frente a LP pasivo (comisión 0,30%):

| Volatilidad | 20% | 40% | 60% | 80% | 100% |
|---|---:|---:|---:|---:|---:|
| LP pasivo | 297 | 132 | -181 | -660 | -1 313 |
| Tendera | 268 | 6 | -29 | -60 | -103 |

Tendera protege en regímenes volátiles (60% a 100%) y cuesta comisiones en regímenes
tranquilos (20% y 40%). Con 40% de volatilidad pierde casi todo el beneficio del LP.

Volumen del trader de ruido (x0,5 / x1 / x2 del base), LP pasivo, comisión 0,30%:

| Volatilidad | x0,5 | x1 | x2 |
|---|---:|---:|---:|
| 40% | -39 | 132 | 517 |
| 60% | -343 | -181 | 187 |

## Cuándo ser LP tiene sentido (en este modelo)

Ser LP gana frente a HODL cuando las comisiones superan la pérdida impermanente:

- Con comisión 0,30%, el punto de equilibrio está en torno a una volatilidad anual del
  **48%** (interpolado). Con 0,05% está en torno al 20%. Con 1% está en torno al 94%.
- La pérdida impermanente crece con el cuadrado de la volatilidad. Las comisiones
  crecen con la volatilidad, pero a través del arbitraje: el volumen del arbitrajista sube
  con la volatilidad. Medido con LP pasivo, GBM, comisión 0,30% (500 trayectorias):

  | Volatilidad | Comisiones totales | Del arbitraje | Del ruido |
  |---|---:|---:|---:|
  | 20% | 386 | 169 | 216 |
  | 40% | 488 | 271 | 216 |
  | 60% | 621 | 404 | 216 |
  | 80% | 771 | 554 | 216 |
  | 100% | 930 | 713 | 216 |

  Las comisiones totales se multiplican por 2,4 entre 20% y 100%. La parte del ruido es
  plana porque su volumen no depende de la volatilidad. Su importe (216) cuadra con el
  volumen de ruido de la configuración: unos 500 y por paso sobre un pool de unos 1 M,
  con una cuota de 20%. El supuesto decisivo sigue siendo el volumen del ruido, que no se
  calibra con datos reales.
- Conclusión práctica: las comisiones crecen lentamente con la volatilidad (lineal en el
  arbitraje, constante en el ruido), mientras que la pérdida impermanente crece con su
  cuadrado. **Ser LP tiene sentido cuando el volumen que atraviesa el pool es alto respecto
  al capital (volumen / TVL) y la volatilidad es baja.** Un pool poco volátil y muy usado
  es lo que paga. En este modelo, un pool volátil con poco volumen
  pierde frente a HODL.
- Esta conclusión depende del supuesto de volumen. Es el supuesto más débil del modelo: en
  el mundo real el volumen por unidad de liquidez varía en órdenes de magnitud.

## Limitaciones (qué NO modela)

- **MEV**: no hay sándwich, ni front-running, ni orden de transacciones. El arbitrajista
  actúa una vez por paso, sin competencia.
- **Gas y costes de transacción**: cero. Sin ellos, las entradas y salidas de la guardia
  son gratuitas, lo que la favorece.
- **Liquidez concentrada** (estilo Uniswap v3) y otros tipos de pool.
- **Protocol fee** (la comisión para el protocolo de Uniswap v2): no existe.
- **Competencia entre LPs**: el resto del mercado es un LP pasivo fijo, 4 veces el capital
  de Tendera. No reacciona.
- **Volumen de ruido exógeno**: no depende del precio, de la volatilidad ni de la comisión.
  Es el supuesto que más decide el resultado (ver sensibilidad).
- **Precio externo**: GBM o saltos, sin deriva (mu = 0). No hay régimen de tendencia. Los
  saltos son independientes del resto del proceso.
- **Horizonte**: 30 días, pasos horarios.
- **Un solo pool y un solo par**: sin enrutado entre pools ni tokens con correlación.
- **Estimación de volatilidad**: la guardia usa el precio externo, que en la realidad no se
  observa directamente. Aquí es una aproximación optimista.
- **Sintonización**: solo cuatro parámetros, sobre semillas distintas de las de evaluación.
  No hay validación sobre datos reales de cripto.

## Datos reales y seguridad

- **Dato real**: se usó una serie mensual pública de MSFT (enero 2000 a marzo 2010, 123
  precios), obtenida del archivo `stocks.csv` del paquete `vega_datasets` 0.9.0 (PyPI).
  Solo sirve para **calibrar un orden de magnitud**: su volatilidad anual es de 34,4%,
  dentro del rango que barre la sensibilidad. No se usa como entrada del modelo y no es un
  activo cripto.
- **Internet**: `api.github.com` y PyPI respondieron (HTTP 200). `en.wikipedia.org` no es
  alcanzable desde el proxy. Solo se hicieron lecturas.
- **Seguridad**: todo es simulado. No hay claves, cuentas, RPCs ni transacciones. Nada se
  publica fuera del repo.
- El espíritu de Uniswap v2 (x*y=k, comisión sobre el input, acciones LP proporcionales)
  se reproduce de memoria. No se citan enlaces.
