# Unit economics (supuestos y salidas de simulacion)

**Supuesto** salvo que se indique. Medianas del escenario C (sim/out/resultados.json) cuando aparecen.

## Suscriptor del Laboratorio

| Concepto | Valor | Origen |
|---|---|---|
| Precio efectivo mensual | 3,2 USD (rango 2,5-3,99) | supuesto |
| Margen semanal por suscriptor | 3,2/4,33 x 0,97 - 0,03 = 0,69 USD | calculo |
| Abandono semanal | 6 % (rango 3-12 %) | supuesto |
| LTV (margen de vida) | ~9,9 USD mediana en simulacion | simulacion |

## Adquisicion pagada (escenario B)

| Concepto | Valor | Origen |
|---|---|---|
| Coste por instalacion (CPI) | 1,5 USD (mediana; sigma 0,6) | supuesto, sin referencia verificada |
| Gasto en publicidad | 750 USD/semana | decision de escenario |
| Coste por suscriptor del Laboratorio | ~370 USD (mediana) | simulacion |
| LTV / CAC | ~0,03 | calculo |

Con estos valores la publicidad pagada no se sostiene. No hace falta mas precision para decidirlo.

## Regalo de la hija (bucle viral)

| Concepto | Valor | Origen |
|---|---|---|
| P(regalar la hija al final de la vida) | 40 % (rango 20-60 %) | supuesto |
| P(el amigo instala tras el enlace) | 25 % (rango 10-50 %) | supuesto |
| Semanas de vida activa por instalacion | ~11,8 (c = 0,5, b = 0,5) | simulacion |
| Instalaciones generadas por usuaria en su vida | ~0,12 | simulacion |
| Aceptacion necesaria para k = 1 | 2,1 (imposible) | calculo |

## Aula (B2B)

| Concepto | Valor | Origen |
|---|---|---|
| Precio por aula y anio | 89 USD (rango 59-149) | supuesto |
| Ventas por semana | 0,04 (rango 0,01-0,12) | supuesto, sin dato propio |
| Abandono anual | 25 % (rango 15-40 %) | supuesto |
| Aulas a 3 anios (mediana) | 5,7 | simulacion |
| LTV por aula (margen bruto) | ~345 USD (89 x 0,97 / 0,25) | calculo |

**No modelado:** las horas del fundador para vender. Es el riesgo principal de la cifra de aula.

## Costes fijos (convencion)

| Concepto | Valor | Origen |
|---|---|---|
| Equipo | 0 en el caso base (el fundador no cobra); 1 500 USD/mes en el escenario E | convencion |
| Alojamiento y herramientas | 30 USD/mes (rango 20-60) | supuesto |
| Comision de pagos | 3 % (rango 2,5-5 %) | supuesto |
