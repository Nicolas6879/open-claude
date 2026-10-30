# Unit economics (supuestos y salidas de simulacion)

Todo es **supuesto** salvo que se indique "simulacion". Valores medianos del escenario correspondiente (sim/out/resultados.json).

## Suscriptor del Laboratorio

| Concepto | Valor | Origen |
|---|---|---|
| Precio efectivo mensual | 3,2 USD (rango 2,5-3,99) | supuesto |
| Precio semanal | 3,2 / 4,33 = 0,74 USD | calculo |
| Comision de pagos | 3 % (rango 2,5-5 %) | supuesto |
| Coste de soporte y servidores | 0,03 USD/sem (rango 0,01-0,08) | supuesto |
| Margen por semana | 0,74 x 0,97 - 0,03 = 0,69 USD | calculo |
| Abandono semanal | 6 % (rango 3-12 %) | supuesto |
| Vida media | 1 / 0,06 = 17 semanas | calculo |
| **LTV (margen de vida)** | **~11,5 USD con medianas; 9,9 USD mediana en simulacion** | calculo y simulacion |

## Adquisicion pagada (escenario B)

| Concepto | Valor | Origen |
|---|---|---|
| Coste por instalacion (CPI) | 1,5 USD (mediana; lognormal sigma 0,6) | supuesto |
| Activacion (instalacion que cuida a su mosquita) | 45 % (rango 30-65 %) | supuesto |
| Gasto de paid social | 750 USD/semana | decision de escenario |
| **Coste por suscriptor del Laboratorio** | **~255 USD (mediana simulada)** | simulacion |
| LTV / CAC | ~0,04 | calculo con los valores anteriores |

Conclusion: la adquisicion pagada destruye valor con estos supuestos, incluso con una conversion mejor que la mediana.

## Aula (B2B, escenario F)

| Concepto | Valor | Origen |
|---|---|---|
| Precio por aula y anio | 129 USD (rango 89-199) | supuesto |
| Abandono anual | 25 % (rango 15-40 %) | supuesto |
| Vida media | 4 anios | calculo |
| Margen anual por aula tras comision | ~125 USD | calculo |
| **LTV por aula** | **~500 USD** | calculo |
| Ventas por semana | 0,3 (rango 0,1-0,6) | supuesto |
| Aulas a 3 anios | 35 (mediana simulada) | simulacion |
| Margen a 3 anios sin coste de equipo | 9 500 USD (p10 4 800; p90 17 500) | simulacion |

**Lo que no esta modelado:** el coste de vender (horas del fundador, viajes, material). Es el riesgo principal de esta cifra. Si cada aula exige 10 horas de venta, el margen real baja de forma notable.

## Costes fijos

| Concepto | Valor | Origen |
|---|---|---|
| Equipo a tiempo parcial | 1 500 USD/mes (rango 1 000-2 500) | supuesto; es el supuesto que mas pesa |
| Alojamiento y herramientas | 30 USD/mes (rango 20-60) | supuesto |
