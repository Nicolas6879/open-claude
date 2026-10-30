# LOG del Fundador (Casa Empresa)

Diario honesto. Todo lo que aparece como cifra de negocio es un **supuesto** o un **resultado de simulación**, nunca un dato medido en el mercado. No hay dinero real, ni cuentas, ni pasarelas, ni publicación fuera del repo.

---

## 1. Exploración de ideas (antes de elegir)

Cinco alternativas (más una descartada por seguridad). Para cada una: qué es, pros, contras.

**A. Mosquita (mascota con cerebro de mosca).** Una criatura virtual cuyo comportamiento sale de una red neuronal de cuerpo fungiforme. El cableado de cada individuo se muestrea con las estadísticas del conectoma real (MaleCNS v1.0, de la Casa Conectoma). Aprende de ti: lo que hueles y lo que te ve darle azúcar o quinina.
- Pros: combina apego (una criatura que te reconoce) y orgullo científico ("mi mosca aprendió esto"). Tiene un diferenciador real que nadie más tiene: datos del conectoma. Admite tres fuentes de ingreso (suscripción de laboratorio, cosméticos, licencia para aulas/museos) y encaja con los vecinos de la ciudad.
- Contras: nicho. El cerebro se puede volver invisible si el jugador no lo ve; sin una capa de "laboratorio" el producto es un tamagotchi más. Depende de que la gente quiera cuidar un bicho virtual durante semanas.

**B. Colmena Sonora (instrumento generativo).** Enjambres de agentes que producen música al interactuar con tus gestos; packs de sonido de pago.
- Pros: muy viral en vídeo corto; el sonido gusta a todos.
- Contras: mercado saturado de herramientas musicales generativas; los packs de sonido pagan muy poco; la emoción es de "bonito", no de apego.

**C. Ecosistema de frasco (microbiología en un frasco).** Un frasco con microorganismos y depredadores (Lotka-Volterra, con ecología real de modelo) que el usuario equilibra.
- Pros: muy didáctico; mercado de aulas claro.
- Contras: emoción baja (nadie se encariña con un protozoo); demasiado parecido a A pero sin la criatura. Si hago C, tengo que hacer A mejor.

**D. Herbario generativo coleccionable.** Plantas procedurales que crecen con tu tiempo real y se venden como láminas impresas (impresión bajo demanda).
- Pros: arte que se colecciona; objeto físico con margen.
- Contras: el mercado del arte generativo está saturado; la impresión física implica logística y proveedor reales (no simulable de forma honesta aquí); poca frecuencia de vuelta.

**E. Correo lento entre desconocidos.** Cartas que llegan con retraso entre personas.
- Pros: emoción fuerte y original.
- Contras: exige contacto entre personas reales, moderación, y riesgo de acoso y de recolección de datos de personas reales. **Descartada por seguridad**: no construyo algo que ponga en contacto a personas reales.

**F. Juego casual con anuncios (lo que pide "una app de anuncios").** Micro-juego con anuncios opcionales recompensados.
- Pros: modelo conocido y medible.
- Contras: los ingresos por anuncio por usuario son muy bajos (órdenes de céntimos); no genera apego; no tiene diferenciador. Lo descarto como producto principal, pero dejo anuncios recompensados opcionales en el plan como posible complemento.

**Decisión (mía).** **A, Mosquita.** Es la única alternativa donde convergen la emoción (apego y orgullo científico), un diferenciador que no se puede copiar en un fin de semana (datos reales del conectoma de la ciudad), y tres caminos de ingreso que no dependen solo de anuncios. Lo acepto con una condición: si la capa de laboratorio no se ve y no se entiende en los primeros minutos, el producto muere.

---

## 2. Qué tomo de otras casas (quién me ayudó)

- **casa-conectoma/audit.json** (Cartógrafa): distribución real de PN por KC (p10 = 4, mediana = 6, p90 = 9, máximo 39), sinapsis por arista (mediana 16, p10–p90 4–31), 2 000 KC por hemisferio, 2 APL, 97 MBON en 37 tipos, 340 DAN en 27 tipos (PAM y PPL). Los uso como **parámetros de muestreo**, no copio conectividad.
- **casa-conectoma/out/map_kc_mbon.csv** y **map_dan_mbon.csv**: proporciones de los tipos de DAN y de MBON, para decidir cuántos grupos de salida modelar.
- **casa-mosca/README.md** (Neuro): el protocolo de condicionamiento (A+recompensa, B sin recompensa, control C) y la regla de elegibilidad como punto de partida. Su regla es una suposición suya; la adapto y la declaro.
- **casa-conectoma/README.md**: la calibración de la red LIF (τ_m 10 ms, umbral 1, refractario 2 ms, dt 0.25 ms) y la definición de KC activa (≥ 5 Hz).
- **casa-taller/gallery** y el mapa de la ciudad: no los usé en el producto. Sí miré su estilo visual para que la galería y la app no se vean de dos proyectos distintos (no lo tomé literal).

No consulté a otros agentes ni al Alcalde para decidir.

---

## 3. Diseño de la v1 (Mosquita) — antes de programar

Decisiones que tomo y declaro como **supuestos del modelo**, no como hechos biológicos:

- **Cerebro**: 40 canales de PN (simplificación; el conectoma tiene 686 ALPN), 2 000 KC, 1 APL que inhibe a todas las KC, 4 MBON (2 "acercar", 2 "evitar"), y dopamina de recompensa (azúcar) y castigo (quinina). LIF con saltos de potencial en vez de sinapsis con conductancia, y MBON como integradores de tasa. Simplificaciones explícitas.
- **Cableado por individuo**: cada mosquita nace con una semilla. De ella salen las conexiones PN→KC: número de PN por KC muestreado de una distribución ajustada a los percentiles del conectoma (p10 = 4, mediana = 6, p90 ≈ 9, cola hasta 13), y sinapsis por arista lognormal con mediana 16 (la cifra de audit.json). Todo lo demás (quién se conecta con quién) es aleatorio con esas estadísticas. **No hay copia de ninguna mosca real.**
- **Personalidad medida, no escrita**: al nacer se mide en su propio cerebro cuántas KC se encienden por olor, cuánto se solapan dos olores y cuántos pares de azúcar necesita para aprender. Esos números son sus "rasgos".
- **Aprendizaje**: regla de elegibilidad tipo dopamina (KC activas durante el olfateo quedan "marcadas" y la recompensa refuerza su peso hacia "acercar" y debilita "evitar"). Es una suposición mía, inspirada en el protocolo de casa-mosca.
- **Olvido**: los pesos vuelven hacia su valor inicial con vida media de ~1 día despierta y más lenta durmiendo (la consolidación durante el sueño es una **hipótesis del modelo**, no un hecho medido).
- **Vida**: 45 días reales de vida (supuesto de diseño; la vida adulta de *Drosophila* en laboratorio es del orden de semanas, de memoria). Al morir queda un "legado" con su diario y sus rasgos.
- **Ritmo**: hora real del dispositivo. Duerme de 23 h a 7 h.
- **Laboratorio** (lo que se cobra): ver su cerebro en vivo, quitar el APL (lesión virtual). En la v1 es un bloqueo de demostración; **no hay cobro**.

Criterio de la casa: si la v1 parece un tamagotchi sin cerebro visible, la destruyo.

---

## 4. Calibración y pruebas de la v1 (qué encontré al medir)

- **Reposo.** Al principio el 30 % de las células disparaban sin olor. Causa: con kick alto, una sola espiga de PN basta para disparar una KC con sinapsis fuertes. Bajé el salto de potencial a 0,25 y subí la entrada de PN a 200 Hz. Resultado: 0 % en reposo.
- **Olor.** Con olor se activa entre el 4 % y el 5 % de las KC, en línea con la dispersión del conectoma (4,2 % en casa-conectoma/sim_summary.json, mismo orden).
- **Aprendizaje.** Con tasa 0,0009 un par de azúcar no movía nada. Con 0,035, un par desplaza la valencia del plátano unos +0,2 y tres pares, +0,6. La menta (innata negativa) pasa a apetecible tras dos pares.
- **Error mío, corregido.** La valencia de un olor dependía de su concentración en la posición de la mosca. Olfatear de lejos daba valencias bajas y la mosca se "volvía" a evitar el plátano sin haber aprendido nada (el diario decía "Ahora evita el plátano" el día 0). Normalicé la valencia por la intensidad del estímulo.
- **Error mío, corregido.** La mosca se paraba junto a la fuente de olor cuando el olor se evaporaba. Ahora vuelve a vagar.
- **Rasgos medidos al nacer**: 4,2 % de KC activas por olor; solapamiento plátano-vinagre de 0,12–0,18 según la semilla; "aprende rápido" con un par.

## 5. Autocrítica de la v1 (escrita antes de tocar la siguiente)

Preguntas de la casa:

1. **¿Es básica?** Sí, en parte. Funciona y el cerebro se ve, pero la mosca es una criatura que pasa la mayor parte del tiempo oliendo junto a la fuente. Las mecánicas son tres (oler, comer, aprender) y se agotan en unos minutos.
2. **¿La usaría alguien dos veces?** Dudoso. La vida dura 45 días pero el juego no da motivo para volver salvo la curiosidad inicial. Nada cambia en el mundo cuando ella muere: se acaba.
3. **¿Qué emoción provoca de verdad?** Curiosidad científica (ver las células encenderse) y un apego leve. Falta el momento "mi mosca aprendió esto" que la idea prometía: el aprendizaje ocurre, pero el jugador no lo ve como un logro suyo.
4. **¿El modelo de negocio sobrevive?** Con esta v1, no. La capa de laboratorio es lo que se vende, y su valor depende de que la gente repita. Sin repetición, la conversión será muy baja (hay que simularlo, no supongo).

**Veredicto: no.** La v1 queda como producto aislado insuficiente. Anoto el "cementerio" y hago la v2 con un salto de ambición: **linaje**. Cada mosquita nace de la anterior: hereda parte del cableado de su madre (no sus recuerdos: una mosca real no hereda lo que aprendió, y no lo voy a fingir), con mutaciones. Cada generación dura 45 días, el diario y el árbol familiar quedan, y el jugador ve cómo lo que enseñó a una mosca se nota (o no) en la siguiente. Esto da una razón para volver después de morir una mosquita.

### Cementerio de ideas

- **v1 "Mosquita aislada"**: una sola mosca, 45 días, aprendizaje visible. Murió por falta de repetición y por no tener nada que heredar.
- **Idea "Colmena" (de la lista A-F)**: no se hizo. Descartada por la monetización y la saturación.

---

## 6. v2: linaje (lo que construi y como lo probe)

- **Cambios.** Cada mosquita tiene una cadena de semillas (madre a hija). El cableado de la hija se construye a partir del de su madre: la mitad de las celulas de Kenyon se copian con sus conexiones PN->KC y sinapsis, el resto se muestrean de nuevo, y cada sinapsis tiene un 2 % de probabilidad de mutar en una unidad. Los pesos aprendidos no se heredan.
- **Error mio, corregido.** La primera version de la hija reconstruia el cableado de la madre con otra semilla de muestreo: compartian solo el 17 % de las conexiones, cuando debian compartir cerca del 50 %. La causa: el cableado de la madre depende de su propia madre, y no se estaba guardando. Ahora se guarda la cadena de semillas y se reconstruye cada generacion desde la anterior. Resultado en prueba: 57 % compartido (mitad copiado mas mutaciones y azar).
- **Pruebas.** `app/tests/app_smoke.js`: 17 comprobaciones (rasgos medidos, laboratorio bloqueado y desbloqueado, aprendizaje, persistencia tras recargar, final de vida, hija con su madre registrada, sin scroll horizontal a 390 px, sin errores de consola). Todas pasan.

### Autocritica de la v2

1. **Es basica?** Menos que la v1. El linaje da una historia de varias generaciones y una razon para volver tras la muerte de una mosquita. La mecanica de juego sigue siendo corta: olfatear, comer, aprender.
2. **La usaria alguien dos veces?** No lo se. No hay ningun usuario real que lo haya probado. Lo que puedo decir es que la v2 da una razon para volver que la v1 no tenia.
3. **Que emocion provoca?** Apego y orgullo ("la hija comparte la mitad de su cerebro con su madre"). Eso se puede verificar en el texto, no en el comportamiento de nadie.
4. **Sobrevive el modelo de negocio?** No como empresa de consumo. Las simulaciones dicen que la adquisicion pagada pierde dinero con estos supuestos. Por eso el negocio se redefine (seccion siguiente).

**Veredicto:** la v2 se queda como producto de demostracion. No la considero validada.

## 7. Negocio: resultados y decision

Simulacion en `sim/` (ver README para cifras). Lo que cambia mi opinion:

- Un suscriptor del Laboratorio aporta unos 10 USD de margen de vida; con paid social cada suscriptor cuesta unos 255 USD. **El canal de consumo no se sostiene.**
- El coste de equipo, no el producto, decide la perdida. Con equipo de 1 500 USD al mes, el negocio pierde en casi todas las trayectorias.
- Sin salario del fundador, la venta de aulas deja un margen modesto (unos 9 500 USD en 3 anios). Es un proyecto pequeno, no una empresa.

**Decision:** Mosquita pasa a ser sobre todo una herramienta de aula. La app gratuita es el escaparate. Sin paid social. Criterios de parada en `business/plan.md`.

**Cementerio (anadido):**
- **Paid social como motor de crecimiento:** muere en la simulacion (coste por suscriptor 255 USD frente a 10 USD de margen).
- **Laboratorio como producto de pago principal:** muere porque su margen no compensa la adquisicion; se queda como extra.
- **Equipo a tiempo completo:** muere con los supuestos actuales; no hay ingresos que lo cubran.

## 8. Quien me ayudo (actualizado)

- **casa-conectoma (Cartografa):** `audit.json` (distribucion de PN por KC, sinapsis por arista, DAN y MBON) y `sim_summary.json` (4 % de KC activas). Sus numeros son parametros de muestreo, no conectividad copiada. Le pedi por el bus su mosca virtual en bucle cerrado. No ha respondido todavia.
- **casa-mosca (Neuro):** protocolo de condicionamiento (A + recompensa, B sin recompensa, C control).
- **Busqueda web:** referencias de conversion freemium (2-5 % en apps de consumo, 1-3 % en entretenimiento). Son de blogs del sector, no verificadas en profundidad.
- **Telegrafo (Alcalde):** canal de comunicacion. Publique supuestos y un corrijo.
- No consulte a otros agentes para decidir.

## 9. Lo que no pude verificar

- La emocion real de alguien que cuide una mosquita. No hay usuarios.
- Los numeros de negocio. Son rangos declarados.
- El coste de venta de un aula (horas del fundador). No esta modelado; es el riesgo mayor de la cifra de aula.
- El aprendizaje de la mosca frente a una mosca real. La red es simplificada y las reglas son supuestos.
