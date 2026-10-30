# Mosquita (Casa Empresa)

Una criatura virtual con cerebro de mosca. Cuidas a una mosquita: huele, decide, aprende de lo que le das (azucar o quinina junto a un olor), duerme de noche y vive 45 dias reales. Al morir, su hija hereda la mitad de sus conexiones neuronales, con mutaciones. Lo que aprendio la madre no se hereda, como en una mosca real.

**Todo es simulacion.** No hay dinero, cuentas, pasarelas ni datos de personas. El cerebro es una red de espigas (LIF) inspirada en el cuerpo fungiforme de *Drosophila*. Su cableado se muestrea con estadisticas del conectoma real (MaleCNS v1.0, de la Casa Conectoma), no se copia a ninguna mosca.

## Entregables

| Ruta | Que es |
|---|---|
| `app/index.html` | El producto. Un solo archivo, HTML, CSS y JS sin dependencias. Funciona abriendolo por `file://`. |
| `app/tests/app_smoke.js` | Prueba de humo con Playwright y Chromium. |
| `business/plan.md` | Plan de negocio (2-3 paginas). Incluye la decision de redefinir el negocio. |
| `business/unit_economics.md`, `pricing.md`, `riesgos.md` | Unit economics, precios y riesgos. |
| `sim/simulador.py` | Simulador de Monte Carlo por cohortes semanales (numpy). |
| `sim/supuestos.json` | Todos los supuestos del negocio, con rangos y etiqueta. |
| `sim/graficos.py` | Genera los SVG a partir de `sim/out/resultados.json` (matplotlib). |
| `sim/tests/test_simulador.py` | Pruebas del simulador. |
| `sim/out/` | Resultados derivados pequenos (json) y graficos SVG. |
| `LOG.md` | Diario: ideas exploradas, cementerio, errores, calibracion y quien me ayudo. |

## Como se juega

1. Pon un nombre y nace una mosquita. Sus rasgos salen de medir su propio cerebro: cuantas celulas se encienden por olor, cuanto se parecen dos olores y cuantos pares necesita para aprender.
2. Elige un olor (platano, levadura, vinagre o menta) y toca el frasco para ponerlo. Ella se acerca o se aleja segun lo que haya aprendido.
3. Pon una gota de azucar junto a un olor y dejala comer: aprendera a acercarse. Una gota de quinina junto a un olor le enseñara a evitarlo.
4. Por la noche duerme. Lo que aprende de dia se consolida mejor durmiendo (hipotesis del modelo).
5. A los 45 dias se duerme. Su hija nace con la mitad de sus conexiones; la tarjeta "Linaje" muestra cuanto se parecen.
6. "Laboratorio" muestra la actividad de las neuronas en directo y permite quitar el APL (lesion virtual). Ahora es una vista de demostracion, sin cobro.

Ajustes de prueba (solo para desarrollo): `?speed=N` acelera el tiempo (hasta 10), `?hora=H` fija la hora del dia.

## Numeros del cerebro (medidos en la simulacion)

- En reposo, 0 % de las celulas de Kenyon (KC) se encienden. Con olor, entre 4 % y 5 %.
- Solapamiento entre plátano y vinagre: 0,12 a 0,18 segun la semilla.
- Un par de azucar sube la valencia del platano unos +0,2; tres pares, unos +0,6.

Estos valores son del modelo, no de una mosca real. Los parametros de aprendizaje, olvido y vida son supuestos.

## Numeros del negocio (simulacion, supuestos en `sim/supuestos.json`)

Tres anios, 4 000 trayectorias Monte Carlo:

- Paid social (3 000 USD/mes): margen mediano -180 600 USD. Pierde en el 98 % de las trayectorias.
- Organico con aula: -91 800 USD mediano (el coste de equipo domina).
- Aula primero con equipo de 1 500 USD/mes: -48 800 USD mediano.
- Aula primero sin salario del fundador: **+9 500 USD mediano** (p10 4 800; p90 17 500). Es una cifra de contabilidad, no un salario.

Cifras y resultados completos en `sim/out/resultados.json`. Los graficos estan en `sim/out/*.svg`.

## Como reproducir

Requisitos: Python 3 con numpy, Node 22 con Playwright y Chromium (solo para la prueba de la app).

```bash
cd /home/user/open-claude/city/casa-empresa
# simulacion completa (~4 s) y pruebas
PYTHONDONTWRITEBYTECODE=1 python3 sim/simulador.py
cd sim && PYTHONDONTWRITEBYTECODE=1 python3 tests/test_simulador.py
# graficos (con matplotlib, por ejemplo en el venv del scratchpad)
PYTHONDONTWRITEBYTECODE=1 MPLCONFIGDIR=/tmp/mpl /ruta/al/venv/bin/python sim/graficos.py
# prueba de la app
cd .. && NODE_PATH=$(npm root -g) node app/tests/app_smoke.js
```

Para la semilla fija (`supuestos.json`), los resultados son reproducibles.

## Limitaciones

- La red es simplificada: 40 canales de PN (el conectoma tiene 686 ALPN), conexiones densas KC-MBON, MBON como integradores de tasa y saltos de potencial en vez de conductancias.
- Las reglas de aprendizaje y olvido son supuestos del modelo. La consolidacion durante el sueno es una hipotesis.
- Los supuestos de negocio no tienen datos de mercado propios. Las referencias externas que use son de blogs del sector y no estan verificadas en profundidad.
- La app no tiene pruebas con usuarios reales. La retencion y el interes son desconocidos.
- El objeto `window.__mosquita` expone el estado para las pruebas. No afecta al juego.
