# LOG de Cartografa: casa-conectoma

## 1. Decisiones (y por que)

- **Punto de partida**: lei `casa-mosca/README.md` y `LOG.md` (el encargo pedia leer su codigo tambien).
  No abri `fly_mb.py` linea a linea: tome de el la forma del contrato JSON, los parametros de neurona
  (tau_m, umbral, refractario, sinapsis) y su tabla de resultados, que uso para comparar. Lo declaro aqui
  para que nadie crea que audite su codigo.
- **Datos**: los Feather planos de MaleCNS v1.0. Empece por las anotaciones (`body-annotations`) y los
  neurotransmisores porque son pequenos (14 MB y 43 MB). La matriz de pesos "significant-only" (502 MB) la
  baje en la misma sesion. Las versiones mas grandes (sinapsis puntuales, syn-partners, tbar) no las baje: no
  las necesito para la pregunta de la casa.
- **Foco**: no hice una lista de entregables. Elegi tres preguntas: (a) cuanto difieren los supuestos de
  Neuro de la anatomia; (b) si el cableado real cambia la dispersion de KC; (c) un mapa de tipos KC y DAN ->
  MBON. Descarte el "experimento loco" (camino sensorial a neuronas descendentes) por tiempo.
- **Umbral de 5 sinapsis** en los mapas y en la simulacion. Motivo: la mediana de KC->KC y DAN->KC es 1
  sinapsis, y ~95% de esas aristas tienen menos de 5. Sin umbral, los mapas estarian dominados por ruido.
- **Dos escalas, no una**: mi primera calibracion uso una sola escala para todo. Las KC se quedaban en
  silencio (<0.5%) mientras el APL disparaba 100-270 Hz. Causa: el APL recibe ~200 000 sinapsis de KC y con
  una sola escala su retroalimentacion inhibia a todas las KC. Solucion: separar la ganancia KC->APL (`g`)
  de la excitatoria (`s`) y calibrar las dos sobre la red real. Es la misma idea que los pesos separados de
  casa-mosca (`w_kc_apl` y `w_apl_kc`), pero aqui los saque de los datos y no a mano.
- **Nulo que conserva grados**: intercambios de aristas bipartitas (Maslov-Sneppen), 20 intercambios por arista.
  Lo use en lugar del nulo uniforme porque el grado de cada PN es muy heterogeneo (mediana 55, maximo 489).

## 2. Lo que intente y fallo

| Intento | Resultado | Que hice |
|---|---|---|
| `python3 -I` con `PYTHONPATH` para pyarrow | `ModuleNotFoundError` | `-I` ignora `PYTHONPATH`; anadi la ruta dentro del script. |
| Solapamiento medio de PN compartidas como prueba de aleatoriedad | Real 0.2556, nulo con grados 0.2556 (identico) | Es una identidad: la media depende solo de los grados de PN. Usé la fraccion de pares con >= 1 PN compartida. |
| Calibracion con una escala `s` (0.002 a 3.2) | KC silenciosas o APL saturado; `correlacion` con dos olores daba error de indices | Corregi la correlacion (`nan_to_num`) y separe `g`. |
| Test del LIF con peso 1.5 PN->KC | KC no disparaba | Es correcto: la media de V es tasa x peso x tau_syn (~0.2 < 1). Subi el peso de prueba a 10. |
| `scipy`, `matplotlib` | No instalados | Todo con numpy y SVG escrito a mano. |

## 3. Lo que me sorprendio

- **El 99.8% de las sinapsis PN->KC son ACh**, a pesar de que 209 de 686 ALPN estan predichas como GABA.
- **Solo el 19% de las KC tiene exactamente 6 PN.** El "6 por KC" de casa-mosca es una media aproximada, no
  una regla; la cola va de 4 a 8 y hay un maximo de 39.
- **Menos solapamiento del esperado**: 0.205 de pares con PN compartida frente a 0.228 en el nulo con grados.
- **Lesion del APL**: sin APL, KC activas pasan de 4.2% a 28%. Es la metrica mas sensible del modelo.
- **Los detalles del cableado no cambiaron las metricas gruesas**: topologia aleatoria y pesos uniformes dan
  lo mismo que el cableado real (4.2 a 4.4% de KC activas). No lo esperaba. Puede ser que esas metricas no sean
  sensibles a la topologia, o que el modelo sea demasiado simple para verlo.
- **KCg-m** aporta el 41% de las sinapsis KC->MBON fuertes, y el 74% de su salida va a cuatro MBON (09, 01, 05, 11).

## 4. Errores o supuestos de casa-mosca, con evidencia

1. **"4 MBON" y "4 DAN"**: en el conectoma hay 97 MBON (37 tipos) y 340 DAN (27 tipos). Su modelo promedia
   una neurona equivalente, lo que oculta que cuatro MBON (09, 01, 11, 05) reciben el 44% de las sinapsis KC->MBON fuertes.
2. **"Pesos iguales"** en PN->KC: el peso real es de 4 a 31 sinapsis (p10-p90). Cambia la respuesta de cada KC.
3. **"Sin KC->KC"**: hay 643 mil aristas, pero casi todas son de 1 sinapsis. No lo tomo como circuito. Cambiar
   su omision altera poco la dispersion (4.1% frente a 4.2%), pero sube el solapamiento entre olores (0.084 frente a 0.049).
4. **"1 APL"**: hay 2 (una por hemisferio). El efecto de dispersion es grande en ambos.
5. **"2000 KC"**: es correcto por cuerpo fungiforme. El conectoma completo tiene 4064 (dos hemisferios).
6. **"Todas las PN excitatorias"**: correcto para la gran mayoria de las sinapsis (99.8% ACh).
7. **Jaccard y dispersion**: los valores de casa-mosca (0.03 a 0.08 entre olores) son del mismo orden que los que
   obtengo con cableado real (0.049 a 0.056). Es decir, su resultado grueso no depende de haber usado datos
   sinteticos. Tampoco lo demuestra; las entradas son distintas.

## 5. Quien me ayudo

- **casa-mosca (Neuro)**: el formato del contrato `out/activity.json` (lo respeto en `out/activity.json`);
  los parametros LIF del README (tau_m 10 ms, umbral 1, refractario 2 ms, sinapsis tau 5 ms, dt 0.25 ms); la
  definicion de KC activa (>= 5 Hz) y la tabla de resultados para comparar. No copie codigo suyo.
- Nadie mas. No consulte a otros agentes ni al Alcalde. No use ninguna cuenta ni clave; solo el bucket publico
  de lectura.

## 6. Procedimiento y verificacion

- Descargas en el scratchpad de la sesion (no en `/tmp` fijo); los scripts del repo leen de
  `CONECTOMA_DATA` (por defecto `~/.cache/conectoma-male-cns`), fuera del repo.
- Ejecuciones con `PYTHONDONTWRITEBYTECODE=1`. Revisado: no hay `__pycache__` en la casa.
- `tests/test_casa_conectoma.py`: 6 de 6 pasan. Las dos de datos (auditoria y contrato) comprueban los
  numeros de `out/`.
- `out/` ocupa 612 KB (muy por debajo del tope de 10 MB).
- No hice `git add` ni `git commit`.
