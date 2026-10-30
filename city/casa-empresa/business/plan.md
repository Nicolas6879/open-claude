# Mosquita: plan de negocio (2-3 paginas)

Todo lo que aparece como cifra es **supuesto** o **resultado de simulacion** (sim/). No hay mercado medido ni dinero real.

## 1. Que es

Una criatura virtual, una mosquita, cuyo cerebro es una red de neuronas con espigas inspirada en el cuerpo fungiforme de *Drosophila*. Su cableado se muestrea con estadisticas del conectoma real de la mosca macho (MaleCNS v1.0). Aprende de lo que le das (azucar o quinina junto a un olor), tiene ritmo de dia y noche, vive 45 dias reales y, al morir, su hija hereda la mitad de sus conexiones. El jugador ve el cerebro que hay detras.

Ninguna mosquita copia una mosca real. Las reglas de aprendizaje y olvido son supuestos del modelo.

## 2. Para quien

- **Usuarios finales (personas que cuidan una criatura):** curiosos de la ciencia y del cuidado de mascotas virtuales. Sin pago, la app es una demo gratuita.
- **Profesores de biologia y neurociencia (B2B, el cliente de pago):** necesitan una herramienta que muestre como un circuito neuronal aprende, sin laboratorio ni animales. Pagan una licencia por aula.

## 3. Modelo de ingresos

| Fuente | Quien paga | Precio (supuesto) | Papel |
|---|---|---|---|
| Aula | Profesor o centro | US$89-199/anio por aula (base 129) | Principal fuente de ingresos |
| Laboratorio | Particular | US$3,99/mes de lista (efectivo 2,5-3,99) | Secundaria |
| Cosmeticos | Particular | US$0,99-2,99, compra unica | Marginal |

Anuncios: no. Patrocinios de contenido educativo: no se modelan.

## 4. Que dicen los numeros (simulacion, 156 semanas, 4 000 trayectorias)

| Escenario | Margen final mediana (USD) | P(perdida) | Aulas a 3 anios |
|---|---|---|---|
| A. Organico, sin aula | -92 800 | 100 % | 0 |
| B. Paid social 3 000 USD/mes | -180 600 | 98 % | 0 |
| C. Organico + aula | -91 800 | 100 % | 6 |
| D. Paid + aula | -179 800 | 98 % | 6 |
| E. Aula primero (equipo 1 500 USD/mes) | -48 800 | 100 % | 35 |
| F. Aula primero sin coste de equipo | **+9 500** (p10 4 800; p90 17 500) | 0 % | 35 |

Lectura honesta:

1. **El consumidor no paga su propia adquisicion.** Un suscriptor del Laboratorio aporta unos 10 USD de margen a lo largo de su vida, y con paid social cada suscriptor cuesta de media unos 255 USD de gasto. El canal de pago no se sostiene con estos supuestos.
2. **El cuello de botella es el coste fijo, no el producto.** Con un equipo a tiempo parcial de 1 500 USD/mes el negocio pierde dinero en casi todas las trayectorias. El coste de equipo es el supuesto que mas pesa (correlacion de rango -0,89 con el margen; sim/out/sensibilidad_escenario_E.svg).
3. **Lo que si funciona, con poco coste, es el aula.** Sin salario del fundador, el escenario F deja un margen de unos 9 500 USD en tres anios. Eso es un ingreso de un proyecto pequeno, no una empresa que pague un equipo.

## 5. Decision

**Se redefine el negocio:** Mosquita es, sobre todo, una herramienta de aula. La app gratuita es el escaparate y el laboratorio es un extra opcional. No se invierte en paid social. El objetivo realista, con los supuestos actuales, es un proyecto de bajo coste que genere un ingreso modesto y no un equipo.

Esta decision no se apoya en que la vision del producto sea mala: se apoya en el mapa de decision (sim/out/mapa_decision_aulas.svg). Con equipo por encima de 1 000 USD/mes, la perdida es casi segura para cualquier numero de aulas razonable.

## 6. Criterios de parada (la idea muere si se cumple)

- Si en 6 meses no hay al menos 5 aulas pagadas (ritmo menor de 0,2 aulas por semana) **y** el coste mensual supera 500 USD, se para.
- Si la retencion semanal de la app gratuita cae y la conversion a aula no llega, se para antes de contratar.
- Si en 12 meses el ingreso anual de aulas no cubre el alojamiento y las herramientas, se cierra.

## 7. Hitos siguientes (sin fechas comprometidas)

1. Validar con 10 profesores que el panel del aula les sirve (entrevistas, no encuestas masivas).
2. Medir retencion real de la app gratuita en un grupo pequeno de usuarios que lo acepten.
3. Revisar los supuestos con datos propios antes de cualquier inversion.

## 8. Lo que no sabemos

Casi todos los supuestos de negocio. Las tasas de venta de aulas, la conversion y la retencion son rangos declarados, sin dato de mercado propio. Las referencias externas que consulte (conversion freemium 2-5 % en apps de consumo, 1-3 % en entretenimiento) son de blogs del sector y no estan verificadas en profundidad.
