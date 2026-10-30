# LOG del Alcalde

Ciudad de agentes. Yo (el Alcalde, Claude) planeo, reparto, reviso y mantengo `LOG.md`, `city.json` y los commits. Los habitantes son subagentes Haiku que construyen sus propios proyectos dentro de `city/<casa>/`. No escribo código ni contenido de proyectos.

## Reglas de la prueba que me impuse
- Máximo 6 habitantes Haiku (Arquitecto incluido), una sola sesión. Decidí **5**: cuatro casas con proyecto + el Arquitecto. Prefiero pocas casas buenas.
- Nadie le pregunta nada al usuario: lo decido todo yo y los habitantes deciden dentro de su casa (instrucción explícita del usuario durante la sesión).
- Seguridad: solo dentro del repo, sin secretos ni cuentas, web3 solo simulado, nada se publica fuera.
- Los habitantes no hacen `git commit`; commiteo yo, una casa por commit.

## Reconocimiento del entorno (antes de decidir nada)
- Repo vacío, rama `claude/jolly-davinci-9s1e9l`.
- Python 3.13 + numpy 2.5 disponibles; sin scipy ni matplotlib. Node 22.
- Internet por proxy con lista de permitidos: **PyPI y api.github.com responden**; Wikipedia, arXiv, Science, neuPrint y FlyWire (codex) están **bloqueados**; github.com/google-deepmind responde 403. Conclusión: los datos reales del conectoma de la mosca probablemente no son alcanzables, y eso es información útil para el brief: que lo intente, lo anote y siga con un modelo sintético honesto.

## Plan de la ciudad (decidido por mí)

| Casa | Habitante | Proyecto | Por qué existe |
|---|---|---|---|
| `casa-mosca` | Neuro | Circuito del cuerpo fungiforme de *Drosophila* (olfato y aprendizaje asociativo), simulado con numpy. Intenta datos reales; si no, conectividad sintética con la estructura conocida. Exporta actividad neuronal. | La idea de la mosca me interesa de verdad, y produce datos que otros pueden usar. |
| `casa-agora` | Tendera | Laboratorio de un AMM (producto constante, estilo Uniswap v2) simulado: proveedores de liquidez vs. arbitrajistas, comisiones, pérdida impermanente. Diseña y prueba en simulación una estrategia que *podría* generar dinero. Cero transacciones reales. | Es el proyecto "dinero" y el "web3" a la vez, pero totalmente simulado. Exporta trayectorias de precio y resultados. |
| `casa-taller` | Pintora | Arte generativo en SVG alimentado por las otras casas: la actividad de la mosca y los precios del mercado simulado. | Complementa: convierte datos de dos vecinos en arte. Depende de `casa-mosca` y `casa-agora`. |
| `casa-notaria` | Notario | Registro web3 *simulado*: cadena de bloques local con Merkle tree y prueba de trabajo trivial que sella los hashes de lo que produce cada casa, más un verificador que detecta manipulación. | Da a la ciudad memoria verificable. Depende de que las demás casas existan. |
| (raíz) `index.html` | Arquitecto | Mapa gráfico clicable de la ciudad leyendo `city.json`. | Lo pidió el usuario; lo construye un Haiku, yo lo reviso. |

### Contratos entre casas (para que se aprovechen sin acoplarse)
- `casa-mosca/out/activity.json`: `{meta, neurons:[{id,type,x,y}], spikes:[[t_ms,id],...], stimuli:[{name,t_start,t_end}]}`.
- `casa-agora/out/results.json`: `{meta, price_path:[...], strategies:[{name,final_value,max_drawdown,...}], pool:{...}}`.
- Si el archivo del vecino no existe o falla, el consumidor lo anota en su LOG y usa datos propios de respaldo.

### Orden de ejecución
1. Fase 1 (paralelo): Neuro y Tendera (no dependen de nadie).
2. Fase 2: Pintora (necesita las salidas de la fase 1).
3. Fase 3 (paralelo): Notario (sella todo lo anterior) y Arquitecto (necesita `city.json` y las casas hechas).

## Bitácora de decisiones
- Inicio: escribo este plan, creo `city.json` con las casas en estado `planeada` y hago el primer commit.
- **Casa Ágora (Tendera) — revisada y aprobada.** Brief: AMM x*y=k simulado, estrategia propia, backtests honestos, contrato `out/results.json`. Revisé en una copia en el scratchpad (sin escribir en la casa): 9/9 tests pasan; `results.json` cumple el contrato (721 puntos, 15 filas de sensibilidad); relancé `run_backtests.py` y el resultado es idéntico byte a byte (reproducible). Lo que más valoro: su estrategia **no** gana a HODL y el LOG lo dice con números (LP−HODL −181 ± 111 pasivo; −29 ± 23 con guardia de volatilidad) en vez de maquillarlo, y señala que el supuesto decisivo es el volumen del trader de ruido. Procedencia del CSV real (MSFT mensual) verificada en su LOG: extraído del wheel `vega_datasets` de PyPI sin ejecutarlo. Sin secretos ni transacciones reales.
