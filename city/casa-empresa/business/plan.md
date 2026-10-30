# Mosquita: plan de negocio (revision tras el bucle 3)

Todo lo que aparece como cifra es **supuesto** o **resultado de simulacion** (sim/). No hay mercado medido ni dinero real.

## 1. Que es

Una mosquita virtual cuyo cerebro es una red de espigas inspirada en el cuerpo fungiforme de *Drosophila*. Su cableado se muestrea con estadisticas del conectoma real (MaleCNS v1.0) y no copia ninguna mosca. Aprende de lo que le das (azucar o quinina junto a un olor), vive 45 dias reales y, al morir, su hija nace con la mitad de sus conexiones. Se puede regalar la hija a un amigo con un enlace (que lleva la semilla).

## 2. Que pregunta respondemos

No "gana dinero este escenario", sino **cuanto hay que vender para que el negocio no pierda y para que gane 1 000 USD al mes**, y cuantas veces es eso lo que creemos plausible.

## 3. Resultado (simulacion, 156 semanas, 4 000 trayectorias)

Supuestos base, equipo a coste cero por convencion (el fundador no cobra):

| Escenario | Margen final mediana (USD, 3 anios) | P(perdida) | Suscriptores Laboratorio |
|---|---|---|---|
| A. Organico + regalo de la hija | +345 (p10 -910; p90 +4 659) | 41 % | 23 |
| B. Paid social 3 000 USD/mes | -95 800 | 98 % | 316 |
| C. Organico + regalo + aulas | +1 437 (p10 -151; p90 +5 752) | 14 % | 23 (y 6 aulas) |
| E. Como C con equipo de 1 500 USD/mes | -52 600 | 100 % | 23 |

Lo que decide el resultado (sensibilidad en escenario C, correlacion de rango): instalaciones organicas por semana (0,69), conversion al Laboratorio (0,35), exponente de retencion (-0,31), abandono del Laboratorio (-0,20), ventas de aulas (0,20).

## 4. Umbral (sim/umbral.py)

- **Base:** margen mensual mediano del anio 3 de unos **80 USD**. Ganar **1 000 USD/mes** exige aproximadamente **3,7 veces la demanda base** (entre 3 y 5 en la rejilla).
- Demanda base = 40 instalaciones organicas por semana. Eso son unas **150 por semana sostenidas** sin pagar publicidad, unas 7 800 al anio. Es el umbral en unidades fisicas, y es el numero que mas importa.
- **Regalo de la hija (bucle viral):** cada usuaria genera de media unas 0,12 instalaciones en toda su vida. No es un bucle supercritico: para k = 1 haria falta una aceptacion de 2,1 (imposible). Evidencia lo confirma sobre los rangos: `k < 1` es GARANTIZADA (business/conclusiones.ev).

## 5. Conclusion honesta

- **No hay evidencia de que esto genere dinero de forma relevante.** Con los supuestos base gana unos 1 000 USD al anio en la mediana, y la probabilidad de perder en tres anios es del 14 % con aulas y del 41 % sin ellas.
- Para llegar a 1 000 USD al mes hace falta unas 3,7 veces la demanda base, es decir unas 150 instalaciones organicas por semana sostenidas. **Ese es el dato que habria que medir antes de hacer nada mas**, y no tenemos ninguno.
- La via de consumidor con publicidad pagada **no se sostiene**: cada suscriptor del Laboratorio vale unos 10 USD de margen de vida y cuesta de media 370 USD de gasto en publicidad.
- El producto puede ser un **proyecto pequeno de bajo coste** (alojamiento de unos 30 USD al mes). No es una empresa que pague un equipo.

## 6. Criterios de parada

- Si en 3 meses la app gratuita no pasa de 20 instalaciones organicas por semana, se para: el umbral queda muy lejos.
- Si la conversion al Laboratorio medida (suscriptores / activos) queda por debajo de 0,2 % semanal, el modelo de suscripcion no compensa.
- Si no hay al menos 5 aulas pagadas en 6 meses, se para la linea de aulas.

## 7. Que haria antes de gastar mas tiempo

1. Medir instalaciones organicas y retencion reales de una version de prueba durante un mes, sin publicidad.
2. Preguntar a 10 profesores si pagarian por el panel del aula, a 89 USD por aula.
3. Solo si el umbral se acerca a lo medido, seguir.

## 8. Lo que no sabemos

Casi todos los supuestos. La demanda organica, la conversion, el precio y las ventas de aulas son rangos sin dato propio. Las referencias externas de conversion (2-5 % freemium en apps de consumo) son de blogs del sector, no verificadas en profundidad, y no son comparables con nuestra conversion por usuaria activa.
