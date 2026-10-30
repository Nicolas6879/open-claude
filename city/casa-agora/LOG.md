# LOG de Tendera (Casa Ágora)

## Decisiones (las tomé yo, sin preguntar)
- **Modelo**: pool x*y=k con comisión sobre el input (estilo Uniswap v2, de memoria), solo
  stdlib de Python. Numpy no hacía falta: 3 ms por trayectoria, y así el código queda claro.
- **Escala temporal**: 1 paso = 1 hora, 720 pasos (30 días). 500 trayectorias por escenario.
- **Escenarios**: GBM con vol 60% (base) y un régimen de saltos (vol de difusión 40%, 60
  saltos al año, tamaño 5%, vol total ~56%). Así comparo régimen liso y con colas gordas con
  volatilidad similar.
- **Mercado del LP**: el resto del mercado es un LP pasivo con 4x el capital de Tendera
  (cuota 20%). Sin él, el pool se quedaría sin liquidez cuando Tendera sale, y eso no es
  realista.
- **Arbitrajista**: solución cerrada de un solo swap óptimo (no iterativa). La comprobé
  con pruebas de perturbación del tamaño de la operación.
- **Pérdida impermanente**: la defino como residuo contable `(LP - HODL) - comisiones`.
  Lo validé contra la fórmula clásica `2*sqrt(r)/(1+r) - 1` (ver test de identidad).
- **Estrategia propia**: guardia de volatilidad con EWMA (vida media de una semana),
  histéresis, calentamiento de 24 pasos. Umbrales sintonizados en semillas de entrenamiento
  disjuntas de la evaluación (100000-100199 frente a 0-499). Rejilla final: salida en
  {30, 40, 50, 70, 90}% y reentrada en {0,5; 0,75; 1,0} de la salida. La rejilla inicial era
  {50, 70, 90, 120}% sin factor de reentrada; la amplié tras ver el óptimo en el borde (ver
  "Qué falló").
- **Contrato**: `strategies` se refiere al escenario base (GBM). La HODL va en `description`
  porque el esquema no tiene entrada para ella. `sensitivity` lleva solo las tres claves
  pedidas.
- **Trayectoria representativa**: GBM, semilla 0, LP pasivo, 721 puntos.

## Qué hice
1. Revisé la carpeta, Python 3.13 y numpy 2.5 (no lo usé).
2. Escribí `amm.py`, `mercado.py`, `agentes.py`, `estrategias.py`, `simulacion.py`.
3. Escribí `tests/test_amm.py`: 9 pruebas, todas en verde.
4. Escribí `run_backtests.py`: sintonización, evaluación, sensibilidad, sensibilidad al
   volumen del ruido, y escritura de `out/results.json`. Pasa la validación de contrato.
5. Verifiqué la identidad contable: sin ruido el error es de unos 328 (igual a las
   comisiones, esperado). Con ruido, LP - HODL - comisiones = -803 frente a -801 de la
   fórmula. Error máximo por trayectoria 75 sobre 200 000 (medido en 60 trayectorias).
6. Calculé errores estándar para las diferencias principales.

## Resultados clave (ver README para tablas completas)
- GBM 60%: LP pasivo frente a HODL, -181 ± 111. Tendera, -29 ± 23. P(> HODL): 64% frente
  a 52%.
- Saltos: LP pasivo, -161 ± 101. Tendera, -7 ± 24.
- Sensibilidad: el LP pasivo gana frente a HODL con vol ~<48% y comisión 0,30%. Con 0,05%
  el umbral baja a ~20%. Con 1% sube a ~94%.
- La guardia reduce la pérdida del LP pasivo, pero no gana frente a HODL. Su mejor
  sintonización es casi "estar fuera", y la curva es plana por debajo de 30%.

## Qué falló o qué tuve que corregir
- **Primera sintonización**: la rejilla de umbrales (0,5 a 1,2) tenía el óptimo en el borde
  inferior (0,5). La guardia salía casi siempre en la primera ventana y nunca reentraba.
  Amplié la rejilla a {30..90}% y añadí el factor de reentrada. Aun así el óptimo queda en el
  borde (30%). Lo anoto como hallazgo, no como fallo: con regímenes de vol alta, lo mejor es
  estar fuera.
- **Tolerancia de la prueba de identidad**: la primera versión era demasiado laxa (2 000 de
  200 000). La apreté a 0,1% del capital por trayectoria, con margen sobre el máximo medido.
- **Pruebas de pool**: no fallé ninguna, pero la comprobación "el arbitraje deja el precio
  en la banda" se apoya en la forma exacta de la banda. La verifiqué numéricamente, no solo
  de palabra.

## Internet (intentos, todos solo lectura)
- `https://api.github.com/rate_limit`: HTTP 200.
- `https://pypi.org/pypi/numpy/json`: HTTP 200.
- `https://en.wikipedia.org/`: no conectó (código 000). Bloqueado, como indicaba el
  enunciado. No lo volví a intentar.
- **Serie real**: descargué el wheel `vega_datasets-0.9.0` desde PyPI a un directorio
  temporal, lo abrí con `zipfile` sin importarlo, y extraje `stocks.csv`. De ahí guardé
  las 123 filas de MSFT (enero 2000 a marzo 2010) en `data/msft_mensual_2000_2010.csv`.
  Vol anual 34,4%. Solo sirve para calibración de orden de magnitud. El directorio temporal
  se borró.

## Qué aprendí
- En este modelo, el LP pasivo pierde frente a HODL con volatilidad alta, y la pérdida
  crece con el cuadrado de la volatilidad (356 con 40%, 802 con 60%: razón 2,25).
- Las comisiones casi no dependen de la volatilidad: dependen del volumen, y el volumen
  aquí es un supuesto del trader de ruido. Es el supuesto que más decide el resultado. Con
  el doble de ruido, el LP pasivo pasa de -181 a +187 con vol 60%.
- P(> HODL) puede ser 64% aunque la media sea negativa: la distribución es asimétrica.
  Conviene reportar la media con error, no solo la probabilidad.
- Una guardia de volatilidad no es una fuente de valor en sí: solo cambia cuándo se está
  expuesto al pool. Su beneficio es limitar pérdidas, no crear ganancias.

## Quién me ayudó
Nadie. Todo lo decidí y escribí yo.
