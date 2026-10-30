# LOG de Pintora (casa-taller)

## Qué hice

1. Comprobé los dos inputs antes de diseñar. `activity.json`: 2109 neuronas (2000 KC, 50 ORN, 50 PN, 1 APL, 4 MBON, 4 DAN), 70 149 espigas, 19 estímulos, ids contiguos. `results.json`: 721 puntos de precio y reservas, x·y = k monótono creciente. Ambos validaron; no hice ninguna alternativa sintética.
2. Escribí `make_art.py` con stdlib + `math`/`bisect` (sin numpy ni matplotlib). Genera cinco SVG. Sin azar: dos ejecuciones dan el mismo sha256 en los cinco archivos.
3. Rendericé cada SVG con Chromium (Playwright, `chromium.launch()`), a PNG fuera de mi casa, en el scratchpad de la sesión, y los miré. Hice `index.html` y lo revisé en escritorio y en móvil de 390 px (sin scroll horizontal).

## Decisiones estéticas

- **Dos temperaturas.** La mosca va sobre fondo nocturno (#0b0d14), con colores de neurona que brillan. El mercado va sobre papel cálido (#f4efe4) con tinta oscura, como un gráfico de cuaderno. La obra cruce va sobre negro, para que el color de la MBON resalte.
- **Cada elemento viene de un dato.** Ningún adorno. En la obra 1, las bandas de alto fijo son un mapeo deliberado (el número de neuronas no se ve a escala, y lo digo en el pie). En la obra 2 el color es el conteo de espigas, recortado a 8; en la diferencia, recortado a ±5.
- **Títulos.** Describen la obra sin jerga: "Cielo de espigas", "Caminata sobre la hipérbola", "La mosca lee la cinta".
- **Números en las obras.** Los números que aparecen (90 → 31, −7 %, 0.62 %, 0.32, 0.30 %) se calculan en el script, no se escriben a mano.

## Hallazgos que cambiaron el diseño

- La nube de KC casi no cambia: 2199 espigas antes de A, 2041 después (−7 %), con 778 → 772 KC activas. En cambio, las MBON ante A pasan de 90 a 31 espigas, y ante B de 88 a 77. El aprendizaje está en la salida. Por eso la obra 2 lo dice en el texto de pie, en rojo, y no sólo lo sugiere.
- El precio marginal del pool (y/x) sigue al precio de mercado con una brecha media de 0.22 y máxima de 0.32, que es 0.30 % del precio. Esa magnitud se parece a la comisión de 0.30 %. Lo dejo como observación ("se parece"), no como causa demostrada.
- k sube de forma monótona: 2.5000 → 2.5156 · 10⁹ (+0.62 %). Lo describo como "consistente con comisiones que se quedan en el pool", porque el dato sólo muestra la tendencia.
- La caminata sobre la hipérbola casi parece recta en el rango visitado (x de 4870 a 5830). Es honesto, pero la obra es más bien sutil. No la forcé con ejes logarítmicos.

## Errores y correcciones tras mirar

1. **Obra 1 (primera render):** la leyenda "protocolo / recompensa" queda apretada a la izquierda de la franja. Se lee bien, la dejé.
2. **Obra 3:** el rótulo del eje X se superponía con las líneas de pie. Bajé el área de trazado (B 680 → 650), subí el canvas a 790 y reubiqué las tres líneas de pie.
3. **Obra 4:** el subtítulo del panel derecho se superponía con el subtítulo principal. Moví el panel a T = 175 y el encabezado a y = 128. Además cambié la brecha de líneas finas (zigzag que se leía como ruido) a puntos de r = 1.9.
4. **Obra 5:** las etiquetas "0 s" y "23 s" se pisaban arriba. Dejé una sola "0 s = 23 s". La primera línea de la leyenda se cortaba por la derecha. Partí la leyenda en cuatro líneas, y bajé el centro del anillo 40 px (cy 520 → 560) para que la etiqueta no chocara con el subtítulo.
5. **Tildes y erratas:** corregí "sintetica", "posicion", "celula", "numero", "esta en", "Ninguna elemento", "dias", "hiperbola" y "teal" (lo cambié por "turquesa"). Mi primer intento de corregir "hiperbola" con sustitución de texto también cambió el nombre del archivo de la obra 3 a `hipérbola`; lo revertí a `03-caminata-hiperbola.svg` y borré el archivo duplicado. Los nombres de archivo quedan en ASCII.
6. **Texto causal:** en la página y en el desc de la obra 3 escribí que las comisiones "son" la causa del crecimiento de k. Lo suavicé a "consistente con". Las observaciones deben quedar a nivel de dato.
7. Un intento de parche al script abortó en una aserción antes de escribir nada; el archivo quedó intacto y lo rehice con las sustituciones completas.

## Qué no funcionó o queda pendiente

- Revisé la obra 2 de nuevo con los textos finales. La obra 1 sólo cambió en tildes del pie y del desc, sin tocar maquetación; no la volví a mirar entera.
- La obra 1 pesa 1.12 MiB (límite 1.5 MB). Es cercana, pero está dentro. Si se alarga el texto, conviene recortar coordenadas.
- No hay fallback sintético: ambos inputs existen y validan. Si faltara alguno, el script termina con error en lugar de inventar datos. Esto es una decisión, no un olvido.

## Mapeos (resumen, también en el desc de cada SVG)

- 01: tiempo → x; neurona agrupada por tipo → y (banda de alto fijo); tipo → color; cada espiga es una raya.
- 02: posición x,y de la KC → posición; espigas en 1 s de A antes/después → color; diferencia → color divergente.
- 03: reserva X → x; reserva Y → y; hora → color; k inicial/final → curvas; crecimiento de k → franja.
- 04: precio de mercado → x; precio marginal y/x → y; hora → color; brecha por hora → eje y del panel derecho.
- 05: hora de mercado k → ángulo (k+½)/720 de los 23 s de la mosca; precio → radio; actividad MBON suavizada (gaussiana 100 ms) → color. Es alineación visual, no predicción.

## Quién me ayudó

- **casa-mosca**, `out/activity.json`: todo el material de las obras 1, 2 y 5 (espigas, tipos, posiciones de KC, estímulos, MBON). Sin sus datos no habría cielo ni nube.
- **casa-agora**, `out/results.json`: todo el material de las obras 3, 4 y 5 (`price_path`, `pool_path`). No usé `strategies` ni `sensitivity`; no encajaban en una obra visual sin adornos.
- No hubo errores en sus archivos: el formato coincidía con el contrato, la numeración de neuronas era contigua y las reservas eran positivas.
