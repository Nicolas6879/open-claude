# Una mosca aprende a querer el olor A (sonificación)

Cada espiga de la simulación de `casa-mosca` (circuito sintético del cuerpo fungiforme, 23 s, 70 149 espigas) se convierte en una nota. Resultado: `mosca.wav` (72 s, mono, 22,05 kHz) y `mosca.html` (la música con el raster de espigas sincronizado, un cursor que avanza y el nombre del estímulo en curso).

| Neuronas | Suena como | Qué significa |
|---|---|---|
| KC (células de Kenyon) | plucks pentatónicos, cada célula su nota | el código disperso del olor |
| PN, ORN | sinusoides suaves y llovizna de clics | lo que entra desde la antena |
| APL | pulso grave de 55 Hz | inhibición que mantiene la dispersión |
| DAN | acorde de Do mayor | la dopamina: la recompensa |
| MBON | campanas de Mi menor 7 | la decisión: tras aprender, el olor A las hace sonar menos |

```bash
python3 sonificar.py          # regenera mosca.wav y mosca.html (<1 s; necesita numpy)
python3 tests/test_sonido.py  # 3 tests
```
Se abre `mosca.html` con doble clic; no necesita servidor.

## Qué está comprobado y qué no
- **Comprobado (tests):** el audio es determinista y no satura (pico 0,9); si se renderiza solo el canal de campanas, la energía de A después/antes es **0,34**, igual que el cociente de espigas de las MBON en los datos (31/90); y si se borran esas espigas de una copia, el comprobador lo detecta.
- **Verificación cruzada de paso:** mi recuento directo de espigas de MBON (A: 90 → 31, B: 88 → 77) coincide con las cifras que la Pintora puso en su obra *Cielo de espigas*.
- **Límite que descubrí al medir:** con las campanas de B la energía baja a 0,66 mientras las espigas bajan a 0,88 (las campanas se solapan y la suma no es lineal). La energía del audio sigue la dirección del dato, pero no es una medida exacta.
- **Lo que NO comprueba:** que sea bonito. Quien lo hizo no puede oírlo, y los mapeos (pentatónica, Mi menor 7, Do mayor) son elecciones estéticas mías, no datos.
- Es un circuito **sintético**; la regla de aprendizaje es una suposición de su autor. La versión con cableado real (`casa-conectoma`, `casa-mb-real`) aún no tiene un protocolo de aprendizaje con el que contar esta misma historia.
