# Casa Mosca: cuerpo fungiforme sintetico de Drosophila

Simulacion en Python (solo numpy) de un circuito olfativo con aprendizaje asociativo, inspirado en el
cuerpo fungiforme (mushroom body, MB) de la mosca de la fruta. Es una **maqueta sintetica**: la
conectividad, los olores y la mayoria de los parametros son inventados o aproximados, no datos
medidos de ninguna mosca.

> **Aviso:** no hay datos reales en esta casa. No se pudo acceder a conectomas (ver `LOG.md`), asi que
> la anatomia es aleatoria con la estructura de la literatura (50 glomerulos, 6 PN por KC, 2000 KC,
> un APL, MBON y DAN). Ningun numero de aqui debe presentarse como medicion biologica.

## Que modela

- **ORN (50)**: un tipo por glomerulo. Cada olor es un vector de afinidades (12 glomerulos fuertes y
  ruido bajo). Disparo LIF con actividad espontanea subumbral.
- **PN (50)**: una por glomerulo, relevo 1:1 de las ORN.
- **KC (2000)**: cada KC recibe 6 PN elegidas al azar (sin repetir), con umbrales heterogeneos.
  Activacion dispersa por inhibicion global.
- **APL (1)**: recibe de todas las KC y las inhibe a todas (inhibicion global tipo APL).
- **MBON (4)**: reciben sinapsis KC->MBON plasticas. Su respuesta media es la salida del modelo.
  Se interpreta como un pool que promueve evitar el olor.
- **DAN (4)**: 2 de recompensa y 2 de castigo. Su actividad (espigas) genera una senal de dopamina
  con decaimiento. La dopamina de recompensa deprime las sinapsis KC->MBON de las KC que estuvieron
  activas (traza de elegibilidad); la de castigo las potenciaria. El experimento solo usa recompensa.
- **Neuronas**: LIF (tau_m = 10 ms, umbral 1, reset 0, refractario 2 ms) con corriente sinaptica
  exponencial (tau 5 ms). Ruido blanco. Paso dt = 0.25 ms. Las espigas son explicitas.

## Que NO modela

- Conectividad real (hemibrain, FlyWire, neuPrint). Todo es sintetico.
- Capa lateral (LN) de la antena: la normalizacion se delega en la inhibicion del APL.
- Oscilaciones de gamma, dinamica temporal de los olores, concentracion o intensidad variable.
- Tipos especificos de MBON (cada MBON es una neurona equivalente) ni los circuitos de salida hacia
  motor. No hay comportamiento, solo respuesta de la red.
- DAN de castigo: la regla existe en el codigo (`eta_pot`) pero no se ha probado con ningun experimento.
- Aprendizaje de olores de intensidad distinta, memoria a largo plazo ni extincion.
- Las reglas de plasticidad son una eleccion mia (ver LOG). La forma no lineal de la elegibilidad
  (umbral y cuadrado) es una suposicion del modelo, no un hecho biologico comprobado.

## Como ejecutarlo

Requisitos: Python 3 y numpy. Nada mas.

```bash
cd /home/user/open-claude/city/casa-mosca
OMP_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1 python3 run_experiment.py          # tabla + out/activity.json
OMP_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1 python3 run_experiment.py --seeds 8,9,10 --no-json
OMP_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1 python3 tests/test_basic.py
```

`OMP_NUM_THREADS=1` es importante: sin el, la misma simulacion tarda unas 6 veces mas (el BLAS de
varios hilos penaliza los productos pequenos). Tiempos medidos: el experimento tarda ~9 s con semilla 7; los
tests ~12 s.

Para reproducibilidad, dos ejecuciones con la semilla 7 generan `out/activity.json` identico (mismo md5).

## Resultados (ejecucion real, semilla 7)

Protocolo: pre-test A, B, C y A repetido; 4 pares [A + recompensa] y [B sin recompensa]; post-test A, B, C.
Cada ensayo: 1000 ms de olor y 500 ms en blanco. Respuesta del MBON = espigas/s medias de los 4 MBON durante el olor.

| Olor | Papel | MBON pre (Hz) | MBON post (Hz) | Cambio | KC activas (>=5 Hz) |
|------|-------|---------------|----------------|--------|---------------------|
| A | CS+ (recompensa) | 23.1 | 7.8 | **-66.5%** | 6.6% |
| B | CS- (sin premio) | 22.0 | 19.2 | -12.5% | 4.3% |
| C | control (olor nuevo) | 23.8 | 17.0 | -28.4% | 6.0% |

- Discriminacion (cambio A menos cambio B): **-54 puntos porcentuales**.
- Actividad del MBON en reposo: ~3.5 Hz (medida en mi calibracion, no la imprime `run_experiment.py`); con olor: ~22 Hz.
- Solapamiento de KC activas (Jaccard, antes de aprender): A-B 0.03, A-C 0.05, B-C 0.08. Repetir A da 0.49.
  Las KC codifican los olores de forma distinta, aunque la repeticion no es perfecta (ruido).
- Peso KC->MBON medio: KC de A -76%, KC de B -14%.
- Curva de aprendizaje (Hz del MBON, par 1 a 4): A+R 16.2, 14.0, 10.2, 12.5; B 21.2, 18.2, 16.8, 21.5.
- Espigas simuladas en total: 70 149 (ORN 21 236, PN 6 602, KC 38 877, APL 1 807, MBON 1 308, DAN 319).

**Robustez entre semillas** (mismo protocolo, sin escribir JSON):

| Semilla | A (%) | B (%) | C (%) | KC activas A |
|---------|-------|-------|-------|--------------|
| 7 | -66.5 | -12.5 | -28.4 | 6.6% |
| 8 | -44.0 | -29.9 | -1.1 | 5.8% |
| 9 | -59.2 | -20.7 | -13.9 | 6.6% |
| 10 | -47.1 | -17.1 | -21.3 | 5.9% |

La reduccion de A aparece en las cuatro semillas, pero la **discriminacion no es siempre tan grande**:
con la semilla 8 la diferencia entre A y B es de solo 14 puntos. La semilla 7 es la mas favorable y
es la que sale en el contrato.

### Pruebas

`tests/test_basic.py`: 5 comprobaciones, todas pasan:
1. Reproducibilidad con semilla (y semilla distinta, resultado distinto).
2. Dispersion de KC: entre 2% y 12% durante el olor, casi nada en reposo.
3. Aprendizaje: la respuesta a A baja mas de un 25%, y el cambio de A es 30 puntos mayor que el de B.
4. Forma del JSON exportado (claves, tipos, ids, rangos).
5. `out/activity.json` si existe: contrato completo y menos de 3 MB.

## Contrato `out/activity.json`

Formato exacto: `{"meta": {description, synthetic, seed, dt_ms, duration_ms}, "neurons": [{id, type, x, y}],
"spikes": [[t_ms, id], ...], "stimuli": [{name, t_start, t_end}]}`.

- `synthetic: true`, `seed: 7`, `dt_ms: 0.25`, `duration_ms: 23000.0`.
- 2109 neuronas. Tipos: ORN, PN, KC, APL, MBON, DAN. Coordenadas en [0,1]: ORN a la izquierda,
  PN, nube de KC en el centro, APL, MBON y DAN a la derecha.
- Tiempos de espiga redondeados a 0.1 ms. Tamano 1.04 MB. Sin submuestreo.
- Estimulos: `pre_A`, `pre_B`, `pre_C`, `pre_A_rep`, `train_AR_1..4` (olor A), `train_B_1..4`,
  `reward_1..4` (ventana de la US), `post_A`, `post_B`, `post_C`.

## Parametros y origen

No hay parametros medidos. Todos son aproximaciones que ajuste a mano hasta obtener actividad realista
(ver el barrido de calibracion en `LOG.md`). Los mas importantes:

| Parametro | Valor | Nota |
|-----------|-------|------|
| `n_kc`, `k_pn_per_kc` | 2000, 6 | Dimensiones de la literatura (Caron et al. 2013, de memoria) |
| `w_pn_kc`, `bias_kc`, `w_apl_kc`, `w_kc_apl` | 2.0, 0.0, 1.5, 0.2 | Calibrados para ~5% de KC activas |
| `bias_mbon` | 0.5 | Calibrado para ~22 Hz con olor y ~3.5 Hz en reposo |
| `eta_dep` | 3e-5 | Calibrado para que A baje ~2/3 con 4 pares |
| `elig_thr` | 4.0 | Umbral de coincidencia de la traza de elegibilidad |

## Archivos

- `fly_mb.py`: simulador (`MushroomBody`, `Params`, `to_contract`, `write_contract`).
- `run_experiment.py`: protocolo, analisis, tabla, JSON de contrato.
- `tests/test_basic.py`: pruebas.
- `out/activity.json`: contrato para los vecinos.
- `LOG.md`: diario de decisiones, fallos e intentos de Internet.
