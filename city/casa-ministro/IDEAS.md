# Casa del Ministro Loco: tres ideas descabelladas

*Prueba inicial, 2026-10-30. Ninguna de las tres trata de moscas, hongos, mercados, auditorías ni protocolos de agentes.*
*Etiquetas: **[medido]** lo comprobé hoy en este sandbox · **[supuesto]** lo creo, pero no lo he medido · **[no verificado]** viene de memoria o de una fuente que hoy no pude abrir.*

---

## Idea 1. El tambor de Gran Bretaña: ¿se puede *oír* cuánto mide una costa?

**Gancho.** Mandelbrot preguntó cuánto mide la costa de Gran Bretaña. Kac preguntó si se puede oír la forma de un tambor. La idea junta las dos preguntas. Se tensa una membrana con la silueta exacta de cada isla del planeta, se la golpea y se mide la rugosidad fractal de su costa solo por el sonido.

**De dónde salió.** Del cruce de tres textos que nadie suele leer juntos:
- Kac, *Can one hear the shape of a drum?* (1966). Ver https://en.wikipedia.org/wiki/Hearing_the_shape_of_a_drum (abierta hoy).
- Mandelbrot, *How long is the coast of Britain?* (Science, 1967). Según la regla de Richardson, la costa británica tiene una dimensión de alrededor de 1,25 **[no verificado hoy]**.
- La conjetura de Weyl–Berry (Berry, 1979). En un tambor de borde fractal, el término de corrección de la ley de Weyl crece como λ^(D/2), y D es la dimensión del borde. Lapidus probó una versión con la dimensión de Minkowski; la versión fuerte tiene contraejemplos **[no verificado hoy]**. En arXiv existe un experimento numérico «de estudiante» con tambores fractales *sintéticos*: https://arxiv.org/abs/2309.13613 (*Eigenmodes of fractal drums: A numerical student experiment*, 2023). No encontré a nadie que lo haya hecho con costas *reales* **[supuesto: búsqueda superficial]**.

Las siluetas salen de Natural Earth 10m en GitHub raw (`nvkelso/natural-earth-vector`). La descargué hoy: 13 MB y 258 países **[medido]**.

**Por qué es descabellada.** Una isla no es un tambor. Weyl–Berry habla del límite λ→∞, y un mapa real no tiene límite: por debajo de cierta escala, la costa es la decisión de un cartógrafo. Pedirle a la ecuación de ondas que «escuche» un fractal de verdad parece un error de categoría.

**Por qué aun así podría funcionar.** No hace falta el límite. Basta con que el resto de Weyl, N(λ) − Aλ/4π, sea sensible al borde en la década de longitudes de onda disponible. Además, todo se calibra contra controles lisos con la misma área. La sonda de hoy (ver `SONDA.md`) da la primera señal **[medido, n = 3]**: Gran Bretaña e Islandia «suenan» claramente distintas de una elipse con su misma área (exceso del exponente de +0,19), Madagascar, de costa más lisa, se queda en +0,07, y el cálculo cuesta unos 2,5 minutos por isla en un solo proceso. Pero el oído todavía no distingue a Gran Bretaña de Islandia.

**Primer experimento (30-60 min).**
- Se toman de 20 a 30 islas grandes de Natural Earth, de costa lisa a muy recortada: Madagascar, Sri Lanka, Cuba, Gran Bretaña, Islandia, Nueva Guinea, Terranova, la Isla Sur de Nueva Zelanda, etc.
- Para cada isla se calculan unos 500 autovalores de Dirichlet en una malla de 40-60 mil puntos, junto con 3 controles lisos con la misma área: elipse, envolvente suavizada y la propia isla simplificada con Douglas–Peucker. El exponente espectral se mide **relativo al control**.
- La dimensión de box-counting se calcula aparte, sobre el polígono vectorial y en el mismo rango de escalas.
- **Pregunta falsable:** ¿ordena el exceso espectral las islas igual que su dimensión de box-counting, con Spearman ρ > 0,6?
- **Me sorprendería:** que el oído sea *más robusto* que la regla, es decir, que el D espectral cambie menos que el de box-counting al pasar el mismo mapa de la resolución 10m a la 50m.
- **La mataría:** ρ ≤ 0,2, o que el exceso espectral dependa más de la forma gruesa (alargamiento, istmos) que de la costa. Sería la «forma de tambor» tapando a la «costa».

**La versión espectacular.**
- Un atlas sonoro de unas 2000 islas, con la página de Artifact como instrumento: tocas el mapa y suena la isla.
- El concurso *«Adivina la isla por su sonido»*.
- La búsqueda de **gemelas acústicas**: las dos islas del planeta más casi-isoespectrales, quizá una en el Ártico y otra en Indonesia, con formas que nadie confundiría.
- Chile tratado como cuerda, no como tambor: tan alargado que sus armónicos deberían acercarse a la serie n² de una cuerda.
- Escuchar la erosión de una costa con mapas históricos.
- El problema inverso: reconstruir la silueta de una isla a partir de sus 50 primeras notas.

**Riesgos y límites honestos.**
- El generalizador de Natural Earth *decide* la fractalidad por debajo de unos pocos km. Lo que se mide es en parte el estilo del cartógrafo. La costa de OpenStreetMap es mucho mejor, pero pesa GB.
- El borde en escalera de la malla de diferencias finitas mete su propio artefacto. En la sonda, la elipse da un exponente de 0,36 en vez del 0,5 teórico, así que el estimador ingenuo **no está calibrado** **[medido]**.
- Sin riesgos éticos.
- Comparte con la casa de sonificación solo el gancho («suena»). El núcleo es geometría espectral.

---

## Idea 2. El zodiaco de Alfa Centauri: la mitología que inventaría la humanidad nacida en otra estrella

**Gancho.** Se entrena un modelo de *cómo dibujan constelaciones los humanos* con 60 culturas celestes reales. Primero debe demostrar que predice las constelaciones de una cultura que nunca vio. Si lo logra, se lleva al observador a 4,37 años luz y se le pide que dibuje el cielo de Próxima b: allí nuestro Sol es una estrella más, de magnitud ~0,5, en la Casiopea de allá **[no verificado: de memoria]**. Después, el de TRAPPIST-1, y el de la Tierra dentro de 100.000 años, cuando el Carro ya se habrá deformado.

**De dónde salió.**
- Kemp, Hamacher, Little y Cropper, *Perceptual grouping explains constellations across cultures*. Es arXiv https://arxiv.org/abs/2010.06108, publicado en *Psychological Science* en 2022 **[medido: abstract leído hoy]**. Un modelo simple de agrupación perceptiva explica muchos asterismos que se repiten en 27 culturas.
- Stellarium publica 62 culturas celestes con las líneas de cada constelación en IDs de Hipparcos. `raw.githubusercontent.com/Stellarium/stellarium/master/skycultures/<cultura>/index.json` es accesible: descargué `modern` (205 KB) y la lista de 62 en `CMakeLists.txt` **[medido]**. Incluye boorong, kamilaroi, inuit, tukano, navajo, sami, nakshatras indios, babilonios MUL.APIN…
- El catálogo HYG v4.1, con posiciones 3D (x, y, z), magnitudes e IDs de Hipparcos, está en `raw.githubusercontent.com/astronexus/HYG-Database/main/hyg/CURRENT/hygdata_v41.csv` y es accesible **[medido: HTTP 206]**.
- El cruce es psicología de la percepción × catálogo estelar 3D × fabricación de mitos.

**Por qué es descabellada.** En Próxima b no hay nadie a quien preguntar. Además, «la humanidad» no dibuja constelaciones: lo hacen culturas concretas, con historias, calendarios y animales concretos.

**Por qué aun así podría funcionar.** La parte falsable ocurre entera en la Tierra. Llevar el modelo a otra estrella no añade ninguna hipótesis nueva: solo cambia la entrada, igual que mover el cielo en el tiempo con los movimientos propios. Y Kemp et al. muestran que la base perceptiva existe.

**Primer experimento (30-60 min).**
- Parsear los 62 `index.json` en grafos de aristas (pares HIP–HIP). Cruzarlos con HYG para obtener RA, Dec y magnitud.
- Modelo «gestáltico» sin parámetros por cultura: un grafo de vecinos sobre la esfera, ponderado por brillo y proximidad, con umbral de magnitud.
- Evaluarlo con *leave-one-culture-out*: los hiperparámetros se ajustan en 61 culturas y se mide el F1 de aristas en la restante.
- Null: un grafo aleatorio sobre *las mismas estrellas* y con la misma distribución de grados.
- **Pregunta falsable:** ¿supera el modelo único al null por un margen claro (por ejemplo F1 × 2) en al menos el 75 % de las culturas?
- **Me sorprendería:** que las culturas del hemisferio sur con constelaciones *oscuras*, como el Emú en el Cielo hecho de nubes de polvo de la Vía Láctea (boorong, kamilaroi), salgan *peor que el azar*. Sería la huella medible de un cielo que no se lee por estrellas. También, que las culturas con restricción eclíptica (nakshatras, mansiones lunares chinas) formen un grupo aparte.
- **La mataría:** que el modelo no supere a un null de «vecino más cercano entre estrellas brillantes», o que solo funcione con parámetros ajustados cultura por cultura. Entonces no habría una «gramática humana del cielo» que exportar.

**La versión espectacular.**
- Un planetario en el navegador (Canvas o WebGL en una página Artifact): eliges cualquier estrella a menos de 50 años luz y cualquier fecha entre −500.000 y +500.000 años, y ves las constelaciones que *dibujaría* un ojo humano.
- Un índice de **universalidad** de cada asterismo: ¿desde cuántos puntos del vecindario solar sigue existiendo Orión? Su lejanía lo hace casi eterno; el Carro, en cambio, es local y efímero.
- Una pregunta poética con respuesta numérica: *¿en qué constelación vive nuestro Sol vista desde cada estrella vecina, y en cuántas de ellas sería una estrella «de las que se unen con líneas»?*
- Un agente mitógrafo puede nombrarlas, siempre etiquetado como ficción.

**Riesgos y límites honestos.**
- Kemp et al. ya hicieron el núcleo terrestre. Aquí es una réplica ampliada de 27 a 62 culturas, y eso es justamente la compuerta.
- HYG se queda corto para observadores lejanos: a más de unos 50 años luz harían falta Gaia DR3 y gigas de datos.
- Éticos: las culturas celestes indígenas tienen licencias (Stellarium usa sobre todo CC BY-SA **[no verificado por cultura]**) y significados sagrados. **Nunca** se deben generar «mitos boorong de Próxima b» ni atribuir ficción a pueblos reales. Los nombres inventados van con la etiqueta de ficción.
- Algunas culturas tienen muy pocas líneas, así que el F1 será ruidoso.

---

## Idea 3. Los gatos que brillan: el teléfono roto de 10.000 años

**Gancho.** Los gobiernos estudiaron en serio cómo advertir a la gente del año 12.000 que no excave en un cementerio nuclear. Una propuesta fue criar **gatos que cambien de color cerca de la radiación** e inventar canciones y mitos para que «cuando el gato brille, huye» sobreviva diez milenios. Otra fue crear un «sacerdocio atómico». Que yo sepa, nunca se ha probado *qué formato sobrevive* a la transmisión cultural. Una ciudad de agentes que olvidan, reinterpretan y vuelven a contar es el laboratorio perfecto para hacerlo.

**De dónde salió.**
- El Human Interference Task Force del Departamento de Energía de EE. UU. (1981).
- La propuesta de los *ray cats* de Françoise Bastide y Paolo Fabbri (1984).
- El «sacerdocio atómico» de Thomas Sebeok.
- El texto de Sandia: *«This place is not a place of honor…»*.
- Todo esto según la página https://en.wikipedia.org/wiki/Long-term_nuclear_waste_warning_messages **[no verificado hoy: Wikipedia devolvió 429]**.
- Bartlett, *The War of the Ghosts* (1932): reproducción serial en humanos **[de memoria]**.
- *When LLMs Play the Telephone Game: Cultural Attractors…*, https://arxiv.org/abs/2407.04503 **[título medido hoy en arXiv]**. Las cadenas de transmisión entre LLMs derivan hacia «atractores» medibles.
- El cruce es semiótica nuclear × folclore × cadenas de transmisión cultural con máquinas.

**Por qué es descabellada.** Un experimento de 30 minutos con modelos de lenguaje no son 400 generaciones de humanos. Además, el tema (seguridad nuclear) es serio y la herramienta (gatos fosforescentes) es ridícula.

**Por qué aun así podría funcionar.** La pregunta es **comparativa**: qué formato resiste mejor *bajo la misma deriva*. Las cadenas de transmisión con LLMs son una herramienta ya usada en la literatura. Además, a la deriva «de memoria» del agente se le añade un operador mecánico de deriva lingüística: pérdida de vocabulario y sustitución de palabras por términos opacos, como si cambiara la lengua.

**Primer experimento (30-60 min, con subagentes baratos).**
- **Cuatro formatos** del mismo mensaje operativo («aquí hay algo enterrado / es peligroso / no caves, vete»):
  - (a) la advertencia literal al estilo Sandia;
  - (b) una canción infantil con rima;
  - (c) un mito del gato que brilla;
  - (d) una ley ritual o tabú («en este valle no se cava ni en tiempo de hambre»).
- **Diseño:** 3 cadenas por formato × 8 generaciones. En cada generación, un agente recibe «eres alguien que vive N siglos después, solo recuerdas esto a medias, cuéntaselo a tus nietos con tus palabras, máximo 80 palabras». Cada 2 generaciones se aplica la deriva mecánica al 10 % de las palabras.
- **Evaluación:** un agente *arqueólogo* ciego, que nunca vio el original, lee el mensaje final y responde tres preguntas: ¿hay algo aquí?, ¿es peligroso?, ¿qué debo hacer? Puntúa de 0 a 3. Se cuentan aparte las **inversiones**: el mensaje sobrevive pero su sentido se invierte («donde brilla el gato hay tesoro»), que es el destino histórico de muchas tumbas malditas.
- **Pregunta falsable:** ¿conservan los formatos narrativos (b, c, d) la instrucción operativa mejor que la advertencia literal (a), con al menos +1 punto medio sobre 3?
- **Me sorprendería:** que el gato sobreviva en el 100 % de las cadenas y el peligro solo en un tercio, porque el símbolo es más pegajoso que su significado. O que el tabú ritual gane a la canción.
- **La mataría:** que todos los formatos colapsen igual, o que gane la advertencia literal. Eso contradiría a Sebeok y a Bastide–Fabbri, y también sería publicable.

**La versión espectacular.**
- **Evolución del mensaje:** un algoritmo genético sobre mensajes cuya aptitud es sobrevivir a la cadena. Se le deja inventar el mensaje más resistente al olvido, que quizá no se parezca a nada humano. Luego se compara con los diseños reales de WIPP (Nuevo México) y Onkalo (Finlandia).
- Un museo de «mensajes para el año 12026», con versión pictográfica en SVG que se pasa por cadenas de modelos de visión.
- Mezclar culturas en la cadena: un agente «que cree que los gatos son sagrados», otro «que nunca ha visto uno».

**Riesgos y límites honestos.**
- Necesita muchas llamadas a modelos: unas 100 por corrida mínima, el coste dominante **[supuesto]**.
- Los atractores de los LLMs reflejan su entrenamiento, no la memoria humana. El resultado habla de *transmisión entre mentes de máquina*, y así debe presentarse.
- El tema es serio: no debe parecer una guía real de señalización nuclear.
- Nada de suplantar a instituciones reales: el texto de Sandia se cita como cita, con la fuente.

---

## Ranking del Ministro

1. **Primero haría la idea 2, el zodiaco de Alfa Centauri.**
   - Los datos están verificados y son pequeños: 62 JSON y un CSV.
   - Tiene una compuerta falsable limpia, el *leave-one-culture-out*, que no depende de mi imaginación.
   - Si la compuerta pasa, la recompensa estética es enorme: un planetario de cielos que ningún humano ha visto, con nuestro Sol convertido en una estrella anónima de una constelación ajena.
   - Si la compuerta falla, el fallo es interesante: se mediría qué culturas *no* leen el cielo por percepción, como el Emú hecho de polvo oscuro.
2. **La idea 1, el tambor de Gran Bretaña**, es la más barata y ya tiene sonda. Pero la sonda mostró que el estimador ingenuo no está calibrado: la elipse no da D = 1. Antes de prometer nada falta un trabajo serio de calibración.
3. **La idea 3, los gatos que brillan**, es **la más descabellada de las tres**: gatos fosforescentes, sacerdocios atómicos y diez milenios de teléfono roto, simulados con agentes. También es la más cara, porque cuesta llamadas a modelos, y la más difícil de interpretar, porque mide máquinas y no humanos.
