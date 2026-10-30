# Casa Conectoma: el cableado real del cuerpo fungiforme de la mosca (MaleCNS v1.0)

Continuacion de `city/casa-mosca`. Alli no habia datos reales: la conectividad era sintetica porque se
creyo que el conectoma era inaccesible. Aqui se usa el conectoma completo del sistema nervioso central de
una mosca macho (Google Research + HHMI Janelia, MaleCNS v1.0, licencia CC-BY, ~166 000 neuronas) en sus
archivos planos. **Todo lo de aqui sale de esos datos o de simulaciones que usan esos datos.** Nada es un
modelo de comportamiento ni una medicion de un solo animal.

## Lo que encontre (numeros medidos)

Todos los numeros salen de `out/audit.json`, `out/map_*.csv` y `out/sim_summary.json`.

**1. Anatomia frente a los supuestos de casa-mosca**

| Supuesto de casa-mosca | Medido en MaleCNS v1.0 (minconf 0.5) |
|---|---|
| 2000 KC | 4064 KC en total (2019 izq., 2045 der.). Unas 2000 por hemisferio, asi que el "2000" es correcto **por cuerpo fungiforme**. |
| 1 APL | 2 APL, una por hemisferio (GABA). Cada KC envia a un APL y recibe de el (4063 KC en ambos sentidos). |
| 4 MBON "equivalentes" | 97 MBON en 37 tipos. Neurotransmisor predicho: 50 ACh, 26 glutamato, 21 GABA. |
| 4 DAN (2 recompensa, 2 castigo) | 340 DAN en 27 tipos (15 PAM, 12 PPL), casi todas dopaminergicas (338). |
| 6 PN por KC, exactamente | Mediana 6 PN distintas por KC, pero solo el 19% tiene exactamente 6. El 80% tiene entre 4 y 8. Maximo 39. |
| Sinapsis PN->KC iguales | 16 sinapsis por arista de mediana (p10-p90: 4-31; maximo 89). **No son iguales.** |
| PN->KC aleatorio y sin repetir | Ver punto 2: mas precisamente, menos solapamiento del esperado. |
| Sin KC->KC | Existen 642 933 aristas KC->KC, pero la mediana es 1 sinapsis; solo 33 247 (5%) tienen >= 5. |
| KC->MBON uniforme (4 MBON equivalentes) | Con >= 5 sinapsis, KCg-m aporta el 41% de las sinapsis KC->MBON. El 74% de su salida va a cuatro MBON (09, 01, 05, 11): KCg-m->MBON09 37 313, ->MBON01 30 635, ->MBON05 30 269, ->MBON11 24 165. Esos cuatro MBON reciben el 44% de todas las sinapsis KC->MBON fuertes. |

Dato que no esperaba: los PN "ALPN" predichos GABA son 209 de 686, pero **el 99.8% de las sinapsis PN->KC son
colinergicas** (390 321 de 390 928). Las PN GABA casi no tocan KC.

**2. Cableado PN->KC frente a un nulo que conserva grados**

Dos KC comparten en promedio 0.256 PN. Es lo mismo que da el nulo que conserva los grados de KC y de PN,
porque esa media solo depende de los grados de las PN (es una identidad, no un hallazgo). La metrica que si
discrimina es la fraccion de pares de KC con al menos una PN en comun:

- medido: **0.205**
- nulo que conserva grados (intercambios de aristas, 3 corridas): 0.228 (sd 0.00005)
- nulo uniforme (estilo casa-mosca, PN al azar): 0.106

Es decir, el cableado real comparte **menos** PN entre KC de lo que dicta el azar con la misma distribucion de
grados. Esto es una medicion, no una interpretacion: no explico el mecanismo.

**3. Simulacion LIF con el cableado real (`src/sim.py`)**

Mismos parametros de neurona que casa-mosca (tau_m 10 ms, umbral 1, refractario 2 ms, sinapsis tau 5 ms, dt 0.25
ms). Pesos = sinapsis reales. Signo por neurotransmisor (ACh +, GABA -). Dos escalas calibradas sobre la red real
(no por condicion): `s` = 0.2 para PN->KC y APL->KC; `g` = 0.01 para KC->APL. Objetivo: ~5% de KC activas (>= 5 Hz).
Entrada: 12 canales (glomerulos) activos por olor, amplitud al azar. 2 semillas x 8 olores.

| Condicion | KC activas | Jaccard entre olores (menos = mas distintos) | Correlacion de tasas KC |
|---|---|---|---|
| **real** (PN->KC + APL reales) | 4.2% | **0.049** | 0.058 |
| real + KC->KC (>= 5 sinapsis) | 4.1% | 0.084 | 0.084 |
| **sin APL** (lesion virtual) | 28.3% | 0.205 | 0.098 |
| pesos uniformes (misma topologia) | 4.4% | 0.052 | 0.101 |
| topologia aleatoria (grado conservado, pesos sobre la arista) | 4.2% | 0.056 | 0.081 |

Lectura honesta de esto:
- **La inhibicion del APL es lo que da la dispersion.** Quitarlo multiplica las KC activas por ~7.
- **Los detalles finos del cableado real (topologia y pesos heterogeneos) no cambian de forma medible estas metricas
  gruesas** en este modelo: las cuatro condiciones con APL quedan entre 4.2% y 4.4% y Jaccard entre 0.049 y 0.056.
  No he calculado barras de error entre semillas para esa diferencia; no la llamo significativa.
- Los Jaccard de casa-mosca para pares de olores distintos (0.03 a 0.08, de su README) son del mismo orden que
  el de la red real aqui (0.05), aunque los olores y la calibracion no son los mismos.
- KC->KC con >= 5 sinapsis sube la actividad del APL (144 Hz frente a 63 Hz) y el solapamiento entre olores
  (0.084). Si esas aristas son reales o artefactos de deteccion no lo puedo verificar con estos datos.
- La sensibilidad a `g` es alta: con s=0.2 y g=0.003 hay 10% de KC activas; con g=0.03, 1.7%. El
  resultado de sparseness depende de esa ganancia, que es un parametro libre (en `out/sim_summary.json` esta la
  tabla completa de calibracion).

**4. Mapa tipo-a-tipo (`src/type_map.py`)**

- `out/map_kc_mbon.csv` y `out/map_kc_mbon.svg`: 402 850 sinapsis KC->MBON (>= 5 sinapsis) en 14 tipos de KC
  y 36 de MBON.
- `out/map_dan_mbon.csv`: 36 583 sinapsis DAN->MBON (>= 5). Mayores: PAM06->MBON03 (3292), PAM10->MBON06 (3274),
  PPL101->MBON11 (2311), PAM08->MBON05 (2176).
- DAN->KC tiene 129 113 aristas, pero solo 5 624 tienen >= 5 sinapsis (mediana 1). No lo interpreto como circuito.

## Como reproducirlo

Requisitos: Python 3, numpy, pyarrow (en un directorio propio fuera del repo):

```bash
cd /home/user/open-claude/city/casa-conectoma
pip install --target ~/.cache/conectoma-libs pyarrow && export CONECTOMA_LIBS=~/.cache/conectoma-libs
bash fetch_data.sh                    # ~560 MB en ~/.cache/conectoma-male-cns (sin cuenta ni claves)
export PYTHONDONTWRITEBYTECODE=1
python3 src/audit.py                  # ~20 s  -> out/audit.json
python3 src/type_map.py               # ~10 s  -> out/map_*.csv, out/map_kc_mbon.svg
python3 src/sim.py --seeds 1,2 --odors 8 --export   # ~90 s -> out/sim_summary.json, out/activity.json
python3 tests/test_casa_conectoma.py  # 6 pruebas; las de datos se saltan si falta algo
```

`fetch_data.sh --small` baja solo anotaciones y neurotransmisores; `audit.py`, `type_map.py` y `sim.py` necesitan
la matriz de pesos (502 MB). La primera ejecucion crea un cache `mb_subset_v1.npz` en la carpeta de datos (fuera
del repo). Ningun dato crudo esta en el repo.

## Archivos

- `fetch_data.sh`: descarga los Feather planos del bucket publico (solo lectura).
- `src/conectoma_io.py`: carga de anotaciones, neurotransmisores y del subcircuito MB (aristas entre KC, PN, APL, MBON, DAN y ALLN).
- `src/nulls.py`: intercambios de aristas bipartitas que conservan grados; solapamiento entre pares de KC.
- `src/audit.py`: auditoria de supuestos -> `out/audit.json`.
- `src/type_map.py`: mapas KC->MBON y DAN->MBON -> `out/map_*.csv`, `out/map_kc_mbon.svg`.
- `src/sim.py`: LIF con cableado real y controles -> `out/sim_summary.json`, `out/activity.json`.
- `out/activity.json`: contrato de casa-mosca (`meta`, `neurons`, `spikes`, `stimuli`), **con datos reales**
  (`meta.synthetic: false`). Espigas de 314 PN, 4064 KC y 2 APL en 3 olores, semilla 1. Las posiciones son
  coordenadas de soma reales normalizadas (vista x-y), no un diseno. Los `stimuli` tienen los canales activos.
- `tests/test_casa_conectoma.py`: pruebas del nulo, del LIF, del contrato y de los numeros de la auditoria.
- `LOG.md`: diario de decisiones, fallos y lo que tomo de casa-mosca.

## Limitaciones (lo que no esta verificado)

- **Conteos de sinapsis, no eficacia.** Un peso de 16 sinapsis no es 16 veces mas fuerte que uno de 1 sin medir
  la fisiologia. Lo mismo para el signo: un neurotransmisor predicho no es una medicion.
- **Signos simplificados.** Todas las PN->KC son excitatorias (99.8% son ACh). APL->KC: GABA y glutamato son
  inhibitorios; el APL es GABA en los dos casos.
- **Entrada sintetica.** Los olores son vectores aleatorios de 12 canales, no olores medidos. No hay ORN ni LN
  (ALLN esta extraido pero no simulado).
- **Sin MBON, sin DAN, sin plasticidad.** El mapa tipo-a-tipo es descriptivo: no sabemos si esas sinapsis
  producen la respuesta de evitacion de casa-mosca.
- **Filtro del archivo.** Se usa la matriz "significant-only" (minconf 0.5). 252 KC no tienen PN en ese archivo;
  puede ser una lesion/tracing incompleto o el filtro. No lo he comparado con la matriz completa (1 GB).
- **Parametros.** `s` y `g` se calibran una vez con la red real. La forma de la red LIF no se ajusta a datos
  de olor. No hay barras de error reales entre semillas.
- Literatura citada solo de memoria, sin enlaces: Caron et al. 2013 y Aso et al. 2014 (los cite en casa-mosca
  y no los he comprobado aqui).
