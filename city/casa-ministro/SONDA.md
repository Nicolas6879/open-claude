# Sonda de viabilidad: Idea 1, «El tambor de Gran Bretaña»

*2026-10-30, unos 25 minutos de reloj, 1 proceso con `nice` y BLAS a 1 hilo. La máquina estaba con carga ~23 en 4 CPUs.*

## Qué hice

Calculé las «notas» de varias islas como si fueran membranas.

- **Datos.** Natural Earth 10m, `ne_10m_admin_0_countries.geojson`, descargado de raw.githubusercontent.com: 13,3 MB y 258 países **[medido]**. De cada país tomé su polígono de mayor área (Gran Bretaña, Islandia, Madagascar) y lo proyecté a km con una equirrectangular local.
- **Malla.** Rasterizada a unos 60.000 puntos interiores. El paso de malla h sale 1,9 km en Gran Bretaña, 1,3 km en Islandia y 3,2 km en Madagascar.
- **Cálculo.** Laplaciano de Dirichlet con 5 puntos y los 500 primeros autovalores con `scipy.sparse.linalg.eigsh` en modo shift-invert.
- **Resto de Weyl.** Calculé R(λ) = Aλ/4π − N(λ) y ajusté su exponente log-log en el 80 % superior del espectro. Según Weyl–Berry, ese exponente es aproximadamente D/2.
- **Control.** Para cada isla, una elipse lisa con la misma área, en la misma malla.
- **Comparación.** La dimensión de box-counting del polígono vectorial densificado, a escalas de h a 32h.
- **Código y salidas** fuera del repo:
  - `/tmp/claude-0/-home-user-open-claude/e7f872ff-c04d-5af4-a3a1-8d2199c39026/scratchpad/ministro/scripts/tambor.py`
  - `/tmp/claude-0/-home-user-open-claude/e7f872ff-c04d-5af4-a3a1-8d2199c39026/tasks/bpmpcd9j9.output`

## Resultados [medido]

| Dominio | exponente del resto | exceso sobre su elipse | D box-counting (vector, h–32h) | D − 1 |
|---|---|---|---|---|
| Gran Bretaña | 0,545 | **+0,188** | 1,171 | 0,171 |
| Islandia | 0,544 | **+0,186** | 1,233 | 0,233 |
| Madagascar | 0,437 | **+0,073** | 1,059 | 0,059 |
| elipse (GB) | 0,358 | — | 1,016 | — |
| elipse (Islandia) | 0,358 | — | 1,006 | — |
| elipse (Madagascar) | 0,364 | — | 1,002 | — |

Tiempo de cálculo: 136-158 s por dominio con 60k puntos y k = 500, bajo carga. Una prueba previa con 20k puntos y k = 200 tardó unos 5 s por dominio. Australia no llegó a terminar porque se cortó por timeout a los 15 min; no hay datos de Australia.

## Lectura honesta

1. **Viable [medido].** Los datos existen y son accesibles, el cálculo cabe en un proceso y en minutos, y no hace falta ninguna librería nueva: bastan scipy y matplotlib.Path.
2. **Hay señal [medido, pero con n = 3].** Las costas recortadas «suenan» distinto de sus elipses. El exceso espectral ordena bien a Madagascar (lisa) frente a Gran Bretaña e Islandia (recortadas), y su tamaño es parecido a D − 1 en Gran Bretaña (0,19 frente a 0,17) y en Madagascar (0,07 frente a 0,06). Tres islas no permiten ninguna estadística: esto es una anécdota prometedora, no un resultado.
3. **El estimador ingenuo NO está calibrado [medido].** Una elipse lisa debería dar exponente 0,5, porque D = 1, y da 0,36. La causa probable es una mezcla de régimen pre-asintótico (500 modos son pocos), oscilaciones del conteo y el borde en escalera de la malla **[supuesto]**. Por eso solo cuento el *exceso sobre el control*, y en la idea completa hay que calibrarlo con varios controles y más modos.
4. **Fallo parcial [medido].** El espectro *no distingue* a Gran Bretaña de Islandia (0,188 frente a 0,186), aunque el box-counting sí (1,17 frente a 1,23). Con esta resolución, el oído es más grueso que la regla. El primer experimento completo debe decidir si esto se arregla con más puntos o con más modos, o si es un límite del método.
5. **Límite de datos [supuesto].** Por debajo de unos pocos km, la «fractalidad» de Natural Earth la decide su algoritmo de generalización. Esta medida mezcla geografía y cartografía.

**Veredicto de la sonda:** la idea es construible y la señal existe. La promesa fuerte («medir D de oído») todavía no está demostrada, y la calibración es el primer obstáculo real.
