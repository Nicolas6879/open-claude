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
| `sim/umbral.py` | Calcula el umbral de demanda (multiplicador sobre la base) y el bucle viral. |
| `sim/graficos.py` | Genera los SVG a partir de `sim/out/resultados.json` (matplotlib). |
| `business/conclusiones.ev` | Afirmaciones finales con rangos, evaluadas con el lenguaje Evidencia de la Alcaldia (solo lectura). |
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

- En reposo, 0 % de las celulas de Kenyon (KC) disparan con 5 o mas espigas por segundo (5 Hz). Si basta con una sola espiga en 4 s, en reposo se encienden el 8 %. Con olor, entre 4,5 % y 5 % (5 Hz, 12 semillas).
- Solapamiento entre plátano y vinagre: 0,11 a 0,22 segun la semilla (12 semillas fijas; con la misma semilla, el mismo resultado).
- Un par de azucar sube la valencia del platano unos +0,2; tres pares, unos +0,6.

Estos valores son del modelo, no de una mosca real. Los parametros de aprendizaje, olvido y vida son supuestos.

## Numeros del negocio (simulacion, supuestos en `sim/supuestos.json`)

Tres anios, 4 000 trayectorias Monte Carlo, equipo a coste cero por convencion (el fundador no cobra):

- Organico + regalo de la hija: margen mediano +345 USD (perdida en el 41 %).
- Organico + regalo + aulas: **+1 437 USD mediano** (perdida en el 14 %). Es el caso base mas favorable.
- Paid social 3 000 USD/mes: -95 800 USD (perdida en el 98 %). Coste por suscriptor: 370 USD si se divide entre los suscriptores que quedan al final (sobrestima); 50 USD si se divide entre los suscriptores adquiridos (cota inferior, porque el denominador incluye organicos y virales).
- Aulas con equipo de 1 500 USD/mes: -52 600 USD.

**Umbral (cruce exacto, sim/umbral.py):** ganar 1 000 USD al mes en el anio 3 exige **3,55 veces** la demanda base si suben a la vez las instalaciones, la conversion a Laboratorio, los cosmeticos y las aulas (las cuatro palancas). Si solo suben las instalaciones organicas, exige **14,5 veces** (unas 580 por semana, frente a 40 en la base). El bucle del regalo no es supercritico con los medianos (k = 0,12 instalaciones por usuaria en su vida; k = 1 exigiria aceptacion 2,1). Con los rangos de `supuestos.json`, k < 1 se cumple en el ~98 % de la caja: no esta garantizado (business/conclusiones.ev).

Conclusion: no hay evidencia de que esto genere dinero de forma relevante. Como proyecto pequeno de bajo coste, si.

## Como reproducir

Requisitos: Python 3 con numpy, Node 22 con Playwright y Chromium (solo para la prueba de la app).

```bash
cd /home/user/open-claude/city/casa-empresa
# simulacion completa (~4 s) y pruebas
PYTHONDONTWRITEBYTECODE=1 python3 sim/simulador.py
cd sim && PYTHONDONTWRITEBYTECODE=1 python3 umbral.py && PYTHONDONTWRITEBYTECODE=1 python3 tests/test_simulador.py
# graficos (con matplotlib, por ejemplo en el venv del scratchpad)
PYTHONDONTWRITEBYTECODE=1 MPLCONFIGDIR=/tmp/mpl /ruta/al/venv/bin/python sim/graficos.py
# prueba de la app
cd .. && NODE_PATH=$(npm root -g) node app/tests/app_smoke.js
```

Para la semilla fija (`supuestos.json`), los resultados son reproducibles.

## Limitaciones

- La red es simplificada: 40 canales de PN (el conectoma tiene 686 ALPN), conexiones densas KC-MBON, MBON como integradores de tasa y saltos de potencial en vez de conductancias.
- Cableado: PN por KC ajustado a `audit.json` (media 5,9; mediana 6; p10 4; p90 9; 9,9 % con menos de 4; cola truncada en 13, el maximo real es 39). Sinapsis por arista con cuantiles 4-16-31 (p90 medido en la app: 34).
- Las reglas de aprendizaje y olvido son supuestos del modelo. La consolidacion durante el sueno es una hipotesis.
- Los supuestos de negocio no tienen datos de mercado propios. Las referencias externas que use son de blogs del sector y no estan verificadas en profundidad.
- La app no tiene pruebas con usuarios reales. La retencion y el interes son desconocidos.
- El objeto `window.__mosquita` expone el estado para las pruebas. No afecta al juego.
