# LOG de Hifa (casa-micelio)

Diario honesto. Etiquetas: **medido** (lo he ejecutado y esta en out/), **supuesto** (creencia/prediccion), **no_verificado** (de memoria o sin acceso a la fuente).
Todas las horas en UTC.

## 0. Referencias: lo que realmente verifique (2026-10-30)
Verificadas contra Crossref (api.crossref.org) y, donde se indica, contra el texto:
- Tero et al. 2010, Science 327:439-442, doi 10.1126/science.1177894. **medido** (Crossref): existe, mismos autores principales (Tero, Takagi, Saigusa, Ito...). El resumen editorial dice "alimento sobre una placa en un patron que corresponde a las ciudades alrededor de Tokio; la red de tubulos resultante es *bastante similar* a la red ferroviaria". Nota: **"similar" en estructura**, no "igual"; la afirmacion de coste/eficiencia/tolerancia comparables NO esta en ese resumen. Wikipedia (en) dice: "oatflakes dispersed to represent Tokyo and 36 surrounding towns" = 37 nodos. El texto completo de Science **no_verificado** (de pago); los detalles del modelo de 2010 (mu, mallado, parametros) los tomo de memoria: **no_verificado**.
- Nakagaki, Yamada, Toth 2000, Nature 407:470, doi 10.1038/35035159: existe (Crossref). **medido**.
- Saigusa, Tero, Nakagaki, Kuramoto 2008, PRL 100:018101, doi 10.1103/physrevlett.100.018101: existe. Wikipedia: ritmo de condiciones frias/secas 10 min cada 60 min; el moho ralentiza "en anticipacion" hasta 7 veces; probado con 30 y 90 min. **medido** (lectura de Wikipedia), no leido el PRL.
- Adamatzky 2022, R. Soc. Open Sci. 9:211926, doi 10.1098/rsos.211926. **medido** (Crossref, resumen): 4 especies (Omphalotus nidiformis, Flammulina velutipes, Schizophyllum commune, Cordyceps militaris); duracion de espiga 1 a 21 h, amplitud 0.03 a 2.1 mV; "agrupa espigas en palabras" y afirma que la distribucion de longitudes de palabra "coincide con la de lenguajes humanos". Eso es una *afirmacion del autor sobre una analogia*, no una demostracion de lenguaje. Mi encargo decia "picos tipo lenguaje": lo dejo como "hipotesis del autor".
- Bonifaci, Mehlhorn, Varma 2012, J. Theor. Biol. 309:121-133 (arXiv 1106.0423) **medido** (leido el PDF): con dD/dt = |Q| - D (gamma=1) la red converge al camino mas corto para cualquier grafo y D inicial; preguntan abiertamente si vale para f(x)=x^g/(1+x^g). Modelo base de Tero-Kobayashi-Nakagaki 2007, JTB 244:553 (existe en Crossref).
- Tamanho de los datos: ver README.

## 1. Validacion del modelo contra Dijkstra

### PREDICCION P1 (2026-10-30T21:15Z, supuesto, antes de ejecutar)
Grafos: 60 grafos geometricos (Delaunay, 25-60 nodos, longitudes euclidianas) + 20 laberintos "trenzados" 15x15 con longitudes de arista 1+0.2U (sin empates). Exito = el soporte {D>0.1 max D} es exactamente un camino s-t simple de longitud = Dijkstra.
- gamma=1, f=|Q| (BMV demostrado): exito 100% (80/80) con dt<=0.5. Con dt=1 el esquema es D<-|Q|(D): predigo que aun converge en >=95%. Con dt=2 (Euler explicito, D puede ser negativo -> recorto a >=0): predigo fallos o no convergencia en >20%.
- gamma=2 f saturante x^g/(1+x^g): exito ~85% (rango plausible 60-100%): puede quedarse en caminos no minimos.
- gamma=0.7 (pow): NO poda; el soporte conserva bucles -> exito (criterio estricto de camino) <30%.
- Convergencia (max|dD/dt|<1e-6) para gamma=1: tiempo T en unidades de 1/r, ~10-40, creciendo con el tamano del grafo.

Nota honesta (21:16Z): antes de la corrida completa hice una corrida *rapida* (6 grafos Delaunay + 3 laberintos, T=80, dt=0.1, no entra en las estadisticas) que mostro que (i) gamma=1 aun no habia convergido en T=80 (la brecha entre el mejor y el segundo camino hace la convergencia lenta, algebraica ~1/t, no exponencial) y (ii) con exito 50% a T=80. Por eso la corrida completa usa T=200 y registra la brecha relativa entre caminos. La prediccion de "T~10-40" de P1 ya se veia mal; la dejo escrita.

## 2. Mundo real: ciudades (Kanto 37 nodos como Tero; Espana peninsular 39-40)

### PREDICCION P2 (2026-10-30T21:19:27Z, supuesto, antes de ejecutar)
Datos: GeoNames cities15000 (top-N por poblacion con separacion minima, sin distritos de Tokio / Palma) y ferrocarril Natural Earth 10m v4.1 (generalizado: solo lineas principales). Candidatas Physarum: (A) grafo completo de ciudades sin puntos de Steiner; (B) malla de Delaunay con ~300 puntos de Steiner. Dinamica de campo medio sobre todos los pares, f saturante, barrido gamma in {1.0,1.3,1.6,2,3}, umbral de poda D>{0.01,0.03,0.1}.
Metricas: TL (longitud total), MD (razon media camino-red/recta entre pares de ciudades), FT1 (fraccion de enlaces cuya perdida mantiene todo conectado), conn_q (pares conectados con fallo de enlace prob. q).
Predicciones numericas (Kanto y Espana):
1. TL decrece monotonicamente con gamma en la malla (gamma mas alto = red mas fina). (confianza 85%)
2. Physarum-malla (gamma 1.3-2, umbral 0.03): TL/TL_MST in [0.95,1.30], MD in [1.10,1.40], FT1 in [0.05,0.45].
3. La variante A (sin Steiner) tiene TL mayor que B a igual gamma, y B puede quedar *por debajo* de TL_MST (ahorro Steiner) en 40% de los casos.
4. A coste igualado (TL +-5%), Physarum-B tiene MD *menor* que el control MST+k aristas voraz solo en un 40% de las comparaciones: mi expectativa es que una heuristica voraz trivial iguala o supera a Physarum en la frontera coste-eficiencia (confianza 55%).
5. Ferrocarril real (NE): TL/TL_MST in [1.3,2.5], MD in [1.10,1.50]; Physarum no lo "reproduce" arista a arista (solapamiento de enlaces <50%).

## 3. MAS ALLA (a): reservorio Physarum vs ESN (computacion de reservorio)

Idea: usar la red adaptativa como reservorio sin ninguna tanh. Estado lento = conductividades D_e; estado rapido = potenciales de nodo (solucion de Kirchhoff para la corriente inyectada, corriente = bias*b0 + gain*u(t)*w). Actualizacion D <- D + r_dt (|Q|^gamma - D). La unica no linealidad es que los potenciales dependen del producto I(t) * g(D) con D = integral con fugas del flujo. Como hay corriente de fondo, |Q|^2 = q0^2 + 2 u q0 q1 + u^2 q1^2 conserva el *signo* de u (memoria lineal) ademas de terminos cuadraticos.

### PREDICCION P3 (2026-10-30T21:22:46Z, supuesto, antes de ejecutar)
Comparacion con ESN (tanh, leak, radio espectral, escala de entrada) a igual numero de caracteristicas de lectura (Physarum: potenciales n=40 + D_e ~ 100 aristas = ~140; ESN N=140) con busqueda aleatoria de hiperparametros equivalente (30 configs, seleccion en validacion, 5 semillas) y una linea base sin reservorio (regresion sobre 10 retardos).
R1. NARMA10 (NRMSE, test): ESN in [0.15,0.45]; Physarum in [0.4,0.9]; P(ESN mejor) = 85%.
R2. Capacidad de memoria lineal (suma R^2 retardos 1..60): Physarum in [4,15]; ESN in [30,70]. (todos los D_e comparten la misma constante de tiempo r, asi que espero un solo nucleo de memoria exponencial = memoria poco rica).
R3. Posible sorpresa a probar: Physarum bate a la linea base de 10 retardos lineales en NARMA10 (P=65%).
R4. Mackey-Glass (tau=17, submuestreo 3): prediccion a 1 paso y a 25 pasos: ESN gana ambas (P=80%).

### Resultado E01 (2026-10-30T22:11:23Z, medido; out/e01_validacion.json, out/fig_e01_validacion.png; 80 grafos: 60 Delaunay + 20 laberintos)
Exito = soporte {D>0.1 max D} es exactamente un camino simple de longitud Dijkstra. "Ganador" = el camino de maximo cuello de botella en D coincide con Dijkstra.
| modelo | Delaunay | laberinto | nota |
|---|---|---|---|
| gamma=1, f=|Q|, T=200 (dt 0.05-1) | 67% | 50% | pero el *ganador* ya es correcto en 100%: simplemente los caminos perdedores no han muerto aun |
| gamma=1, f=|Q|, dt=1, T=3000 | **100% (60/60)** | **100% (20/20)** | confirma Bonifaci-Mehlhorn-Varma en mi implementacion; tiempo de convergencia mediano 439 (Delaunay) / 739 (laberinto), 5%/20% sin converger a 1e-6 aun |
| gamma=1.5 (pow) | 97% | 85% | **converge ~20-30x mas rapido (T~23 frente a 440-740; en el LOG original puse "7x" comparando con T=200 no convergido) pero falla en 3-15%: bloqueo en un camino NO minimo** |
| gamma=2 saturante | 92% | 75% | idem, T~20 |
| gamma=3 saturante | 63% | 15% | bloqueo (ganador-toma-todo) casi seguro en laberintos |
| gamma=0.7 | 0% | 0% | no poda: quedan bucles |
| f saturante gamma=1 | 0% | 0% | no poda a T=200 (la parte lineal de x/(1+x) tiene punto fijo suave) |
| gamma=1, dt=2 (Euler, D recortado a >=0) | 72% | 80% | el ganador es *incorrecto* en 28%/20%: paso grande rompe la garantia |
Hallazgos: (1) convergencia de gamma=1 es algebraica: log-log t_conv vs brecha relativa (2o camino/1o) pendiente **-0.73**, r=-0.81 (n=57 Delaunay convergidos): una diferencia de longitud del 0.1% cuesta ~miles de unidades de tiempo. (2) Compromiso velocidad/optimalidad: gamma>1 poda ~20-30x mas rapido pero ya no garantiza el optimo (el caso gamma=1 si, y solo ahi: es critico). Hasta donde llego, el compromiso no esta en BMV (que dejan abierta la f saturante); lo que he medido es empirico en 80 grafos.
### Comparacion con P1 (honesta)
- gamma=1 100% (80/80): **acierto**, pero solo con T=3000, no con T=200; "convergencia T~10-40": **fallo** (mediana 439-739).
- dt=1 sigue convergiendo >=95%: acierto (ganador 100%). dt=2 fallos >20%: acierto (28% y 20%), pero por *bloqueo en camino erroneo*, no por no converger.
- gamma=2 saturante ~85%: acierto (92% / 75%; media ponderada 88%). gamma=0.7 <30%: acierto (0%).
- No esperaba que gamma=1.5 fuese casi tan buena y ~20-30x mas rapida, ni la pendiente -0.73 tan limpia.

### Resultado E02 (2026-10-30T22:38:54Z, medido; out/e02_*.csv, fig_e02_frontera.png, fig_e02_mapas.png)
Diseno: 2 regiones (Kanto 37 ciudades; Espana peninsular 39-40), Physarum de campo medio (todos los pares, f saturante) con gamma in {1.1,1.2,1.35,1.5,2,3}, 3 variantes: A (grafo completo de ciudades, 3 semillas), B (malla Delaunay con ~330 puntos de Steiner, 6 semillas), G (como B pero pares con peso gravitatorio pob_i*pob_j/d_ij, 6 semillas). Umbral de poda = kappa * (mayor umbral que mantiene conectadas todas las ciudades), kappa in {1,.3,.1,.03}. Controles: MST, Delaunay, Gabriel, RNG, spanner voraz (t=1.15..3), MST + k aristas voraces de Delaunay (k=2..30). Comparacion a coste igualado: interpolacion lineal de la envolvente no dominada de los controles (conservadora: la interpolacion lineal de una frontera convexa sobreestima su MD).
**Hallazgo principal (negativo): ninguna configuracion de Physarum supera a un control voraz trivial a igual coste.** Fraccion de configuraciones Physarum con detour medio por debajo de la frontera de controles: 0% (Kanto) y 0.8% (Espana) [VER CORRECCION E02c: este resultado era en buena parte un artefacto de la malla]. Exceso medio de detour sobre la frontera a igual coste: variante A (sin Steiner) +0.03 a +0.06 (gamma 1.1-1.5), +0.12 (gamma 2); variantes B/G (malla) +0.09 a +0.24. En robustez (pares conectados con 10% de enlaces caidos) B/G quedan 0 a -0.30 por debajo de la frontera.
- La variante A *sigue* la frontera de cerca (rojo en la figura): para gamma 1.1-1.5 esta a +0.03-0.06 de detour. Es decir, Physarum es casi tan bueno como un optimizador voraz del propio criterio; no mejor.
- Parte del hueco de B/G es artefacto de la malla (caminos en zig-zag de aristas triangulares): A (sin malla) esta a +0.03-0.06 y B a +0.09-0.13 a igual gamma. No he separado el efecto mallado del efecto Steiner con un control limpio: **no_verificado** que los puntos de Steiner ayuden o perjudiquen.
- gamma=3 (A, Kanto) produce un arbol *dominado por el MST* en las dos metricas (TL 827 vs 781 km, detour 1.84 vs 1.71): lo mismo que E01, bloqueo en una solucion subOptima.
- **El ferrocarril real (Natural Earth, red troncal que une las ciudades) es peor que casi todos los controles y que Physarum** en estas tres metricas: Kanto TL=1407 km, detour 1.53, conn_q10=0.69; Physarum B gamma=1.35: TL=1252, detour 1.29, conn_q10=0.92. Espana: ferrocarril TL=12371, detour 1.445, conn_q10=0.76; Physarum B gamma=1.35: TL=5861, 1.29, 0.89. Es decir: *se reproduce* la afirmacion cualitativa "la red de Physarum es comparable o mejor que el ferrocarril real" en estas metricas, pero la comparacion es poco informativa: un grafo voraz lo hace mejor aun, y el ferrocarril real obedece a orografia, costa, historia y demanda que estas metricas ignoran (el plano es libre: la malla cruza el mar). Natural Earth es ademas una red generalizada (v4.1, 2017): **no_verificado** que su troncal sea representativa; en Espana incluye lineas paralelas (TL 3.5x el MST).
- Solape con el ferrocarril (fraccion de la longitud a <7 km de la via): Physarum Espana 0.38-0.50 frente a 0.74 del MST y 0.55 de Delaunay; Kanto 0.71-0.95 (la zona es tan densa que cualquier control cae cerca de una via; metrica poco discriminante). Es decir: *Physarum no se solapa mas con la via real que un MST*; no reproduce el trazado, solo cualidades globales.
- Jerarquia (E02b, semilla 0, n=37-40, por tanto debil): correlacion de Spearman poblacion vs intermediacion: ferrocarril 0.43 (Kanto) / 0.32 (Espana); Physarum con flujos gravitatorios (G) 0.33-0.43 / 0.37-0.46; Physarum sin pesos (B) 0.21-0.28 / -0.11-0.12. Los pesos de poblacion producen una jerarquia como la de la red real; sin pesos no. Error tipico de rho ~0.16: **evidencia debil**.
- Sorpresas de B: TL nunca por debajo del MST (min 1.11x en Kanto): el ahorro de Steiner que predije (P2.3, 40%) no aparece (con malla de ~330 puntos).
### Comparacion con P2 (honesta)
1. TL decrece con gamma: acierto (plano al final: gamma 2 y 3 dan ya arbol).
2. B con gamma 1.3-2: TL/MST in [0.95,1.30]: **fallo parcial** (Kanto gamma 1.35: 1.60, 1.5: 1.41, 2: 1.14); detour in [1.10,1.40]: acierto solo para gamma<=1.5 (1.29-1.34; gamma 2: 1.56 fallo); FT1 in [0.05,0.45]: solo gamma=2.
3. A mas caro que B: **fallo, al reves** (A es mas barata: sin zig-zag). B por debajo del MST: **fallo** (0%).
4. Physarum bate a MST+k a coste igualado en 40% de comparaciones: **fallo grande** (0-1%); mi expectativa cualitativa (greedy iguala o supera, 55%) acerto.
5. Ferrocarril TL/MST in [1.3,2.5]: Kanto 1.80 acierto; Espana 3.5 fallo. detour [1.1,1.5]: Espana 1.445 acierto, Kanto 1.53 fallo por poco. Solape <50%: Espana si, Kanto no.
### Autocritica de E02
- *¿Es esto basico o solo reproduce un articulo?* Reproduce la idea de Tero 2010 (red Physarum entre ciudades, comparada con ferrocarril) pero con lo que el articulo (segun el resumen que he podido leer) no tiene: frontera de controles voraces a coste igualado, barrido de gamma, semillas, intervalos. Eso es lo que da el resultado negativo.
- Debilidad: la dinamica de campo medio (todos los pares a la vez) no es la de pares aleatorios de Tero (no_verificado que den lo mismo con la f no lineal); la malla introduce zig-zag; el criterio de poda (cuello de botella) es mio. Los controles optimizan *exactamente* detour, asi que quiza la comparacion favorece al voraz. Un control mas justo seria optimizar con la misma restriccion de malla.
- Lo que seria sorprendente y no ocurrio: que gamma intermedio produjera una red mejor que el voraz en robustez a igual coste.

### Resultado E03 (2026-10-30T22:39:40Z, medido; out/e03_reservorio.json; busqueda aleatoria 30 configs/metodo/tarea, 5 semillas finales, test 1000 pasos)
| tarea | linea base 10 retardos | ESN (140 nodos) | Physarum (40 pot + D) |
|---|---|---|---|
| NARMA10 NRMSE | 0.819 +-0.011 | **0.260 +-0.029** | 0.696 +-0.036 |
| capacidad de memoria lineal (retardos 1-60) | 9.01 | **24.97 +-0.5** | **0.97 +-0.17** |
| Mackey-Glass h=1 NRMSE | 0.125 | **0.005** | 0.185 (peor que la linea base) |
| Mackey-Glass h=25 NRMSE | 0.754 | **0.140** | 0.784 |
**Hallazgo (sorpresa de fondo): la capacidad de memoria del reservorio Physarum es ~1.0, es decir, UNA sola variable de memoria**, aunque tiene ~100 tubos con dinamica propia. Explicacion (teoria, comprobada solo por la cifra): a primer orden todas las D_e son el mismo filtro exponencial (misma constante r) de la misma senal u(t) con distinto coeficiente c_e -> rango 1; un integrador con fugas tiene MC exactamente 1. La no linealidad (D depende de |Q|^gamma) da solo correcciones de segundo orden, de modo que el reservorio es "un integrador + la entrada instantanea". Por eso solo bate ligeramente a la linea base lineal en NARMA10 (0.70 vs 0.82) y pierde en Mackey-Glass.
### Comparacion con P3
R1 acierto (ESN 0.26 en [0.15,0.45]; Physarum 0.70 en [0.4,0.9]). R2 fallo en las dos cifras: Physarum 0.97 (<4: peor que lo esperado, y por una razon estructural que no preveia), ESN 25 (<30: la busqueda de 30 configs no llega a lo que daria un ESN muy afinado). R3 acierto: bate a la linea base (0.696 vs 0.819, 5 semillas, sd 0.04), pero por muy poco. R4 acierto (ESN gana ambos); ademas en h=1 Physarum es *peor* que 10 retardos lineales.

### PREDICCION P4 (2026-10-30T22:39:40Z, supuesto, antes de ejecutar)
Hipotesis surgida del hallazgo anterior: con *constantes de tiempo heterogeneas por tubo* (r_e log-uniforme en un rango de D decadas, como cabe esperar de tubos de distinta longitud/diametro) la memoria deja de ser de rango 1. Variante phys_het: r_e = r0 * 10^(spread*(U-0.5)), spread in [0.5, 2.5] decadas buscado igual que el resto (30 configs).
- MC phys_het in [8, 20] (prediccion central 12); NARMA10 NRMSE in [0.40, 0.60] (mejor que la linea base 0.82, peor que ESN 0.26: P(ESN mejor)=85%); Mackey-Glass h=1 NRMSE <= 0.06; h=25 <= 0.45.
- Cementerio previsto: si MC sigue ~1 con heterogeneidad, mi explicacion de rango 1 estaba incompleta.

### Resultado P4 y diagnostico (2026-10-30T22:44:04Z, medido; out/e03_reservorio_v1.json = busqueda v1 con gamma in [1,3])
phys_het v1: MC = 1.88 +-0.93, NARMA10 0.88 +-0.60 (inestable), MG h1 0.169, h25 0.61. **P4 fallo** (MC esperada 8-20).
Diagnostico (scratchpad hifa/dbg3*.py; cifras en este LOG): en el regimen v1 (gamma>=1) la dinamica con corriente de fondo poda la red: la desviacion tipica relativa de D entre tubos es 6-15 (la mayoria de tubos en el suelo 1e-6) y los valores singulares de la matriz D(t) colapsan a rango 1-2 (sv2/sv1 ~ 0.2-0.4 con spread=2; 0.007-0.2 sin spread). Con gamma<=0.5 (red viva, contractiva) la memoria si crece con la heterogeneidad: MC(potenciales+D) pasa de 1.4-2.4 (homogeneo) a 3.6-5.5 (spread=2 decadas). Es decir: **mi busqueda v1 solo muestreaba gamma in [1,3] (regimen ganador-toma-todo, donde Physarum poda y deja de ser un reservorio)**; fallo de diseno mio, no de la idea. Se corrige en v2.
Ademas: la funcion |Q| rectifica la entrada (D no ve el signo de u salvo a traves del termino cruzado con la corriente de fondo): memoria lineal intrinseca debil.

### PREDICCION P5 (2026-10-30T22:44:04Z, supuesto, antes de ejecutar v2: gamma in [0.1,1.2], gain 10^[-2,0], bias 10^[-0.5,0.3], r_dt 10^[-2,-0.2], spread 0.5-3 decadas)
- MC: phys (homogeneo) in [1.5, 4]; physhet in [3, 8] (central 5): heterogeneidad ayuda (P=75%) pero sigue lejos de ESN (~25): P(MC_ESN > 3*MC_physhet) = 85%.
- NARMA10: physhet in [0.45, 0.75]; ESN 0.26 sigue mejor (P=90%).
- Mackey-Glass h=1: physhet <= 0.12 (mejor que linea base 0.125 con P=60%).

### Resultado E03 v2 (2026-10-30T22:47:07Z, medido; out/e03_reservorio.json; busqueda 30 configs/metodo/tarea con gamma in [0.1,1.2]; 5 semillas finales)
| tarea | 10 retardos lineales | ESN 140 | Physarum homogeneo | Physarum heterogeneo (r_e log-unif.) |
|---|---|---|---|---|
| NARMA10 NRMSE | 0.819+-0.011 | **0.260+-0.029** | 0.695+-0.035 | 0.593+-0.023 |
| capacidad de memoria (1-60) | 9.01 | **24.97+-0.52** | 2.29+-0.25 | 7.35+-2.05 |
| Mackey-Glass h=1 | 0.125 | **0.005** | 0.104+-0.012 | 0.031+-0.005 |
| Mackey-Glass h=25 | 0.754 | **0.140** | 0.276+-0.066 | 0.280+-0.044 |
Los gamma elegidos por la busqueda estan todos en 0.2-0.8 (regimen contractivo, que no poda): **Physarum como "podador" (gamma>1, el de Tero) es un mal reservorio (MC~1); como red memristiva que no poda (gamma<1) es un reservorio modesto, 2-6x peor que un ESN a igual numero de caracteristicas, pero claramente mejor que una linea base lineal en MG** (h=25: 0.28 frente a 0.75). La heterogeneidad de constantes de tiempo multiplica la memoria x3.2 (2.29 -> 7.35, intervalos que no se solapan con 5 semillas) y mejora NARMA10 (0.70 -> 0.59): la hipotesis de P4 era correcta *en el regimen correcto*.
### Comparacion con P5
MC homogeneo [1.5,4]: acierto (2.29). MC heterogeneo [3,8]: acierto (7.35, en el borde alto; central 5 fallo). ESN mejor en NARMA10: acierto (0.26 vs 0.59). MC_ESN > 3 MC_het: acierto raspando (24.97 > 22.05). MG h=1 <=0.12: acierto (0.031, 4x mejor que la linea base). Sorpresa: MG h=1 0.031 es mejor de lo esperado; MG h=25 no mejora con la heterogeneidad.
### Autocritica E03
- ¿Solo reproduce un articulo? No hay articulo: es una idea mia (red Physarum/memristiva como reservorio); no he buscado literatura previa, asi que **no_verificado** que sea nueva (existen trabajos de reservorios memristivos y con Physarum de Adamatzky y otros; no los he leido).
- Sesgo de busqueda: dos veces me equivoque de rango (v1: gamma>=1). El ESN tiene hiperparametros muy conocidos; Physarum los tuvo que descubrir: la comparacion favorece al ESN. El ESN con N=140 y 30 configs al azar da MC=25 (un ESN muy afinado llega a ~N).
- Lo que no hice: ruido de lectura, tareas con entrada vectorial, reservorios de mayor tamano, ni compare con redes memristivas publicadas.

### CORRECCION E02c (2026-10-30T22:48:40Z, medido; out/e02c_*.csv, fig_e02c_malla_justa.png): el hallazgo "Physarum pierde 0-1%" era en gran parte artefacto
Autocritica escrita antes: "un control mas justo seria optimizar con la misma restriccion de malla". Lo hice: cada control (MST, Delaunay, Gabriel, RNG, spanner voraz t=1.1..3 en 20 pasos, MST+k voraz k=1..40 con frontera densa) se **enruta por la misma malla** (camino minimo en la malla entre cada par de ciudades unidas; la union de tramos cuenta una sola vez) para las mismas 6 semillas de malla. MST enrutado: 837 km Kanto (+7% sobre la recta, 781), 3735 km Espana (+6%): ese es el costo del zig-zag.
Resultado a coste igualado (dMD = detour_Physarum - frontera de controles enrutados; media +- sd sobre 6 semillas de malla):
- Physarum B, gamma 1.2 a 1.5: dMD entre -0.03 y +0.03 (Kanto gamma 1.5: -0.031+-0.021, IC95% [-0.053,-0.009]; Espana gamma 1.5: -0.013+-0.027, IC incluye 0). Es decir, **Physarum recorre la misma frontera coste-detour que el voraz** al barrer gamma (figura).
- gamma=1.1: +0.04..+0.06 (peor), gamma=3: +0.2..+0.36 (claramente peor: arbol bloqueado), gamma=2: -0.07+-0.09 (Kanto) / +0.04+-0.07 (Espana): ruido.
- Robustez (pares conectados con 10% de enlaces caidos): Physarum a coste igual esta *por debajo* de la frontera en -0.01 a -0.06 (gamma 1.2-1.5), hasta -0.17 con gravedad y gamma 2: **el voraz es algo mas robusto a coste igual** (n=143 comparaciones: Physarum mejor en robustez 11%, en detour 22%).
- Con pesos gravitatorios (G) el detour es algo peor (+0.01..+0.09) y la robustez algo peor: la jerarquia cuesta eficiencia global.
Conclusion corregida: **Physarum ~ voraz en la frontera coste-detour (empate tecnico), ligeramente menos robusto, y no gana en ningun regimen de forma robusta**. Mi prediccion P2.4 (Physarum mejor en 40% de comparaciones) queda en 22% (detour) y 11% (robustez) en la comparacion justa; el 0-1% de E02 era artefacto: *no volver a citar ese numero sin la salvedad*. Incluso asi, el primer analisis me sirvio: obligo a descubrir el sesgo de la malla.
Nota de cautela: la frontera de controles esta muestreada densamente (k=1..40, t en 20 pasos), de modo que el error de interpolacion es <=0.01 en detour; la sd entre semillas solo recoge variacion de malla/inicializacion (mismas ciudades), no incertidumbre sobre otras regiones del mundo.

## 4. MAS ALLA (d): dos plasmodios en el mismo medio (competencia / cooperacion / parasitismo)
Modelo de juguete (micelio/compete.py; **las reglas son supuesto mio**, lo medido es lo que implican). Especies A y B con sus propias D^s y nodos comida (12 puntos al azar en el cuadrado, 6+6, malla de ~150 nodos). Permeabilidad lam: s puede usar los tubos de la otra con eficacia lam. Reciprocidad mu: fraccion del refuerzo que recibe el tubo anfitrion por el flujo del invitado (mu=0: parasitismo puro). Condiciones iniciales: simetrica, A primero (D_B(0)=0.02), B primero. gamma=1.5, 12 configuraciones.
Medidas: longitud de tubos de cada especie (D>0.05), longitud de la union (infraestructura fisica), solape.
### PREDICCION P6 (2026-10-30T22:50:31Z, supuesto; escrita DESPUES de ver una corrida rapida de 2 configuraciones —honestidad—, antes de la corrida completa de 12 configuraciones x 5 lam x 5 mu x 3 CI)
La corrida rapida mostro: la union baja ~22% al compartir; con A primero y mu>=0.5 B queda con 0 longitud propia (parasito total); con inicio simetrico ambas conservan unos 1.3 de longitud sin solape. Predigo para la corrida completa:
1. union(lam=1, mu=1)/union(lam=0) in [0.72, 0.85] en las tres CI.
2. Monopolio (min(lenA,lenB) < 0.1 max) con A primero: >=90% de configuraciones para mu>=0.5 y lam>=0.5; <=15% para mu=0.
3. Monopolio con inicio simetrico: <=20% de las configuraciones con mu>=0.5.
4. Dependencia de la historia: en (lam=1, mu=1) el resultado (monopolio o reparto) depende de la CI en >=90% de configuraciones.
5. Existe una mu* entre 0 y 0.5 a partir de la cual A primero da monopolio (la transicion es brusca: salto en lenB de >0.5 de su valor solitario entre dos valores consecutivos de mu).

### Resultado E05 (2026-10-30T22:56:26Z, medido; out/e05_competencia.csv, e05_resumen.csv, fig_e05_competencia.png; 12 configs x (lam,mu) x 3 CI = 756 corridas)
- **Inicio simetrico: nunca hay monopolio (0% en las 25 celdas)**. Cada especie conserva ~1.2 de longitud propia (solitaria: 1.43) y casi no hay solape de tubos (cada tubo tiene un solo "dueno"): *reparto reciproco del medio*. La infraestructura total baja a 0.81-0.96 de la de dos redes independientes (0.81 en lam=1, mu=1).
- **Con ventaja inicial (A primero, D_B(0)=0.02): el parasitismo total aparece de forma brusca**: para lam=1, con mu=0 B conserva 0.87 de longitud propia (monopolio 0/12 y 1/12 en A primero), con mu=0.25 pasa a 0.00 (monopolio 12/12). lam=0.75: mu*~0.25 (11/12 en 0.25); lam=0.5: salto entre mu=0.25 (B=0.53) y 0.5 (B=0.01); lam=0.25: casi nunca (1/12 solo en mu=1). La linea critica mu*(lam) decrece con lam (~0.4 en lam=0.5, <0.25 en lam=1). El salto de lenB (0.53 -> 0.01) es discontinuo, no gradual: transicion de tipo primer orden.
- **Dependencia de la historia**: para lam>=0.5 y mu>=0.5 el estado final (monopolio o reparto) depende de la CI en 12/12 configuraciones (100%): A primero -> A monopolio; B primero -> B monopolio; simetrico -> reparto. Es un sistema biestable (tres atractores: A, B, reparto).
- **Sorpresa: la reciprocidad fuerte desperdicia infraestructura.** La union minima (0.69-0.71 de la solitaria, -30%) ocurre justo *despues* de la transicion con reciprocidad debil (lam>=0.75, mu=0.25). Con mu>=0.5 el monopolio es mas grande (longitud del anfitrion 2.30-2.37 frente a 1.90) y la union sube a 0.85-0.87: el flujo del invitado mantiene vivos tubos redundantes del anfitrion. Es decir: el parasito *que no paga nada* (mu bajo) deja la red mas eficiente que el parasito que "devuelve el favor".
- Sin interaccion (lam=0) el resultado es identico a las redes independientes (control; test automatico).
Nota de cautela: las corridas simetricas en lam alto no siempre convergen en T=150 (lam=1, mu=1: 33% convergieron; oscilaciones/derivas lentas), asi que los valores simetricos en esa esquina son menos fiables. Resultados de un modelo de juguete con reglas supuestas por mi; no hay datos biologicos aqui (no_verificado cualquier correspondencia con competencia real de mohos).
### Comparacion con P6
1 (union en lam=1,mu=1 in [0.72,0.85]): simetrico 0.81 acierto; A primero y B primero 0.87 fallo por poco. 2: acierto (monopolio 100% con A primero para mu>=0.5 y lam>=0.5; <=8% con mu=0). 3: acierto (0%). 4: acierto (100%). 5: acierto para lam>=0.5 (mu* entre 0 y 0.5, salto brusco); fallo para lam=0.25 (no hay mu*<=1).

## 5. Cementerio de ideas (2026-10-30T22:57:12Z)
- **Cementerio 1: "Physarum no gana a los voraces (0-1%)"** (E02 v1). Enterrado por E02c: era artefacto de la malla. Lo conservo como aviso: la primera comparacion era injusta (red en zig-zag contra rectas).
- **Cementerio 2: "reservorio Physarum con gamma in [1,3]"** (E03 v1): memoria ~1; no era un reservorio sino una red podada. Rehecho con gamma<1.2.
- **Cementerio 3: habituacion/anticipacion a partir de D** (parte (a) del encargo). No la implemente: con dD/dt = f(|Q|) - rD la "memoria" de un estimulo periodico es solo un filtro exponencial de constante 1/r (trivial, reproduce el decaimiento de D); la anticipacion de Saigusa et al. 2008 depende, hasta donde sé, de la dinamica oscilatoria del citoplasma, no de la adaptacion de la red de tubos (**no_verificado**: no he leido el PRL). La unica "memoria" que medi es la capacidad de memoria lineal del reservorio (E03).
- **Cementerio 4: agente micelial con observacion parcial (b)**. Pensado, no hecho: habria sido comparar con exploracion+Steiner/A*, de poco riesgo y poca novedad frente a E05.
- **Cementerio 5: contraste del "lenguaje" de Adamatzky 2022**: la afirmacion de que la distribucion de longitudes de "palabra" de espigas coincide con lenguajes humanos podria ser un artefacto de cualquier proceso con agrupamiento (el tecleo aleatorio de Miller da leyes tipo Zipf). Esta pensado como experimento nulo (trenes de espigas de Poisson con la misma tasa y misma regla de agrupacion), pero **no lo hice**: no tengo los datos crudos ni la definicion exacta de "palabra" del articulo (no_verificado), y no queria inventarlas.
- **Cementerio 6: red de carreteras real**: Natural Earth ofrece carreteras (ne_10m_roads) pero no las descargue; solo ferrocarril.
- **Cementerio 7: comparacion con pares aleatorios (Tero)**: usé campo medio determinista; no comprobe que coincida con conmutacion aleatoria de pares con f no lineal.

## 6. Quien me ayudo
Nadie (agente unico). Fuentes leidas: Crossref (metadatos de Tero 2010, Nakagaki 2000, Saigusa 2008, Adamatzky 2022, Bonifaci et al.), arXiv 1106.0423 (texto completo), Wikipedia (Physarum polycephalum), GeoNames cities15000, Wikidata (comprobacion de 2 coordenadas: Tokio, Madrid), Natural Earth 10m railroads v4.1.0. Bus de la ciudad solo para publicar mis mensajes. Otras casas de la ciudad no leidas ni usadas.
