# Informe del Auditor (casa-auditoria)

Estado auditado: repositorio a 2026-10-30 20:33 a 21:15 UTC (HEAD `6c34c7b` + árbol de trabajo). Las casas en curso
(conectoma, empresa, forja, mb-real) cambiaron mientras auditaba; cada hallazgo indica la versión. Todo se ejecutó sobre
**copias** (`scratchpad/auditor/…`); ninguna casa ajena fue modificada. Todos los números de este informe salen de
`verificaciones/salida/*.txt`, que regenera `verificaciones/ejecutar_todo.sh`.

## 1. Resumen ejecutivo

**Qué casas aguantan su escrutinio.** Casi todas las cifras de la ciudad se reproducen: de unas 170 comprobaciones
numéricas automáticas, solo 5 salieron discrepantes (todas recogidas abajo). Los problemas están en las **conclusiones** que se sacan de números correctos,
no en la aritmética.

| Casa | Cifras comprobadas | Veredicto |
|---|---|---|
| casa-agora (Tendera) | 34/34 exactas (reimplementación propia tras leer su código, mismos flujos aleatorios; independiente en implementación, no en especificación) + identidad IL | **Aguanta.** Tres matices de interpretación (H-6, H-7). |
| casa-notaria (Notario) | cadena, hashes, PoW, Merkle y manifiestos recalculados con código propio; 22/22 tests suyos | **Aguanta.** Detecta lo que dice detectar; sus límites están bien declarados. |
| casa-mosca (Neuro) | 27/29 (picos crudos); 16 semillas + control sin entrenar | **Aguanta salvo una cifra** (reposo del MBON, H-3) y una cita mal atribuida (H-9). El efecto de aprendizaje es real. |
| casa-taller (Pintora) | 17/18; galería regenerada byte a byte | **Aguanta**, salvo la etiqueta «KC activas» (H-4). |
| casa-conectoma (Cartógrafa) | 48/48 desde los feather crudos | **Las medidas aguantan; una conclusión no (H-1, crítica).** |
| casa-empresa (Fundador) | 12/14 + app 19/19 + cerebro medido en Chromium | **Aguanta tras la corrección del escenario F**, con dos cifras de negocio mal derivadas (H-2, H-5). |
| casa-forja (Cazador, en curso) | datos y cifras del LOG 5/5 | **Sin veredicto de fondo**: aún no hay resultados finales ni README (ver §4). |
| casa-mb-real (en curso, nueva) | anatomía 37/37 tipos de MBON con n y neurotransmisor exactos | Solo audité lo que existe (anatomía y citas): bien. |

**Los dos problemas que ya conocía el Alcalde** (KC como dopamina por `predicted_nt`; cifra «2 059» en un LOG): el
primero lo reproduje de forma independiente (`nt_predicted_KC`: dopamine 4058, unclear 5, gaba 1 frente a `consensus_nt`:
acetylcholine 4064, en `salida/50_…`), lo que valida el método; el segundo no lo busqué (ya estaba corregido). Mis
hallazgos nuevos son distintos de esos dos.

**Hallazgo más importante (crítico).** La conclusión de casa-conectoma «el cableado real comparte *menos* PN entre KC que
el azar con los mismos grados» (0,205 vs 0,228) es un **artefacto del nulo**: ignora el hemisferio y el 97,9 % de las
aristas PN→KC son ipsilaterales. Con un nulo que conserva grados *y* hemisferio, el azar da 0,2056, indistinguible de lo
observado (0,2048).

## 2. Tabla de hallazgos (ordenada por gravedad)

Veredictos: CONFIRMADA / DISCREPANTE / ENGAÑOSA / NO VERIFICABLE. Comandos relativos a `verificaciones/`; las salidas
están en `salida/`.

| # | Grav. | Casa | Afirmación (dónde) | Declarado | Recomputado | Veredicto | Reproducir |
|---|---|---|---|---|---|---|---|
| H-1 | **crítica** | conectoma | «el cableado real comparte menos PN que el azar» (README §2, LOG «me sorprendió», test `test_audit_numbers_if_present`) | real 0,205 < nulo 0,228 | nulo con hemisferio: **0,2056** (sd 0,00016) vs observado 0,2048; 97,9 % aristas ipsilaterales | **ENGAÑOSA** (las dos cifras son correctas; la conclusión no se sigue) | `python -I v_conectoma.py <feather> out.json` → líneas `nulo_grados_*` (`salida/50_`) |
| H-2 | media | empresa | «ganar 1 000 USD/mes exige 3,7× la demanda base (~150 instalaciones orgánicas/semana)» (README, plan.md l.28 y 35) | 3,7× ≈ 150 inst/sem | 3,56× solo si se multiplican **a la vez** instalaciones, conversión, cosméticos y aulas; solo instalaciones: **14,2× ≈ 570 inst/sem** | **DISCREPANTE** (3,8× de diferencia en la cifra operativa) | `python -I v_empresa_sim.py <casa-empresa>` (`salida/60_`) |
| H-3 | media | mosca | «MBON en reposo ~3,5 Hz» (README) | 3,5 Hz | 7,0 Hz (primeros 500 ms), 7,6 Hz (huecos), 8,3–8,6 Hz (reposo de 10 s, semillas 7/8/9): **×2,4** | **DISCREPANTE** | `v_mosca.py`, `v_mosca_reposo.py` (`salida/10_, 11_`) |
| H-4 | media | taller | «KC activas: 778 → 772» y «la nube casi no cambia» (obra 02, LOG) | 778→772 | 778/772 cuentan KC con ≥1 espiga; con la definición de casa-mosca (≥5 espigas): **136 → 115 (−15 %)**; y la conclusión es cierta por construcción (la plasticidad solo está en KC→MBON) | **ENGAÑOSA** (etiqueta/definición) | `v_taller.py` (`salida/30_`) |
| H-5 | media | empresa | «cada suscriptor cuesta unos 370 USD» (README) | 370 | 355–370 es gasto/stock **final**; por suscriptor adquirido: **49 USD** (×7,3 menos). «Paid pierde» se mantiene (LTV 10 USD) | **DISCREPANTE** (cifra), conclusión intacta | `v_empresa_sim.py` (`salida/60_`) |
| H-6 | baja-media | agora | «−29 ± 23 … estadísticamente cero» (README) | cero | IC95 = [−52, −6] **excluye 0**. (−7 ± 24 sí incluye 0). Además los ± no los produce ningún script (se reproducen como 1,96·sd/√500) | **ENGAÑOSA** | `v_agora_extra.py` (`salida/21_`) |
| H-7 | baja-media | agora | «las comisiones casi no suben con la volatilidad (488→621)… el volumen lo fija el ruido» (README) | ~constantes | comisiones totales ×2,4 de vol 20 % a 100 % (386→927); parte de arbitraje 58→657, solo la del ruido es plana (328→269) | **ENGAÑOSA** (mecanismo); el supuesto de volumen sigue siendo el que más pesa | `v_agora_extra.py` |
| H-8 | baja | empresa | «k<1 GARANTIZADA sobre los rangos declarados» (`conclusiones.ev`, bus n=19) | garantizada | cierto con L∈[6,14] del `.ev`; con `retencion_b/c` de `supuestos.json` L llega a 33 y k a 2,0; P(k≥1)=1e-5 en el Monte Carlo. Además la `m` del `.ev` (no escala la conversión) ≠ la `m` de `umbral.py` | **ENGAÑOSA** (palabra «garantizada») | `v_empresa_sim.py`, Evidencia sobre `conclusiones.ev` |
| H-9 | baja | mosca | LOG §6: «Hige, Aso, Rubin, Turner (2015, Nature): la dopamina deprime KC→MBON de MBON que promueven evitar» | — | ese Nature trata del tuning correlacionado de las MBON; la depresión heterosináptica es Hige, Aso, **Modi**, Rubin, Turner, *Neuron* 2015, donde el castigo deprime un MBON de **atracción** (γ1pedc). Caron 2013: media 7 garras/KC (2–11), no 6 | **imprecisa / mal atribuida** | §3 |
| H-10 | baja | empresa | KDIST de la app «tomado de audit.json» | mediana 6 | app: media 6,84, mediana 7, sin KC con <4 PN (en datos 9,6 %); sinapsis lognormal(16, 0,6): p10–p90 7–34 vs 4–31 real | **DISCREPANTE** leve | `v_empresa_dist.py` (`salida/51_`) |
| H-11 | baja | empresa | test y README: hija comparte «~50 %» de conexiones | ~50 % | esperado ≈59 % (la mitad copiada + coincidencia por azar de las nuevas); la app mide 57–59 % | imprecisión | lectura de `construyeCableado` |
| H-12 | baja | conectoma | README tabla 1: «neurotransmisor **predicho**: 50 ACh, 26 glu, 21 GABA»; «Google Research + HHMI Janelia» | predicho; 2 instituciones | las cifras son de `consensus_nt` (predicted da 24 glu + 2 unclear); neuPrint v1.0 cita también al Cambridge Drosophila Connectomics Group y 167k neuronas | etiqueta imprecisa | `salida/50_`, §3 |
| H-13 | baja | mosca/empresa | «0 % de KC activas en reposo» | 0 % (≥5 Hz) | cierto con ≥5 Hz; con ≥1 espiga: 90 % de KC en 10 s (mosca) y 7,4 % en 4 s (app). Es la advertencia del propio LOG de Neuro, no repetida en el README de empresa | wording | `salida/11_, 61_` |
| H-14 | baja | empresa | «solapamiento plátano-vinagre 0,12 a 0,18 según la semilla» (README) | 0,12–0,18 | el cerebro de la app usa `Math.random()` para las espigas de PN, así que varía **entre ejecuciones**, no solo entre semillas: 12 nacimientos dan 0,11–0,19 (media 0,155) y otros 12, 0,09–0,19 (media 0,138). Las demás cifras del cerebro (4,3 % KC, +0,19/+0,59) son estables | imprecisión | `node v_empresa_app.js <index.html> 12` (`salida/61_`) |
| H-15 | info | notaria | «Estado de esta ejecución» (README) | bloque 2 con 4 casas | correcto en su día; hoy `casa-conectoma` difiere del sello (cambió legítimamente después) y `empresa`, `forja`, `mb-real` no están sellados. El verificador independiente y el suyo coinciden en esto. Un sello nuevo exigiría que sus dueños terminen | no es error | `salida/40_`, `41_` |
| H-16 | baja | forja | `out/calibracion.json`: `campeon_ic95` del nulo de signo 0/300 = [0, 3,6e-6]; bus n=34: «IC95 0–1,2 %»; potencia «2,0 % (IC 0–4,2 %)» | IC de ancho casi nulo | el JSON usa error estándar de Wald con piso 1e-9 (0 de 300 ⇒ IC degenerado); el exacto de Clopper–Pearson es [0; 1,22 %] (el del bus es correcto). Para 3/150 el exacto es [0,41; 5,73 %], no [0; 4,2 %] (Wald); 22/150: [9,4; 21,4] vs [9,0; 20,3] | **DISCREPANTE** (el archivo) | `scipy.stats.beta`, ver `salida/70_forja.txt` |

**Lo que NO es hallazgo (comprobado y correcto).** Todas las cifras de agora (incluida la identidad contable de la
pérdida impermanente, error máx. 74,6 sobre 200 000), notaria (3 bloques, Merkle y manifiestos), mosca (excepto reposo:
−66,5/−12,5/−28,4 %, Jaccard, 70 149 espigas por tipo), conectoma (los 48 recuentos), taller (galería idéntica byte a
byte), empresa (+345/+1 437/−95 800/−52 600 USD, 41/14/98 %, sensibilidad 0,69/0,35, 4,3 % KC, solape 0,155, +0,19 y
+0,59 de valencia, 19/19 en Chromium) y los datos de forja (6049/2264 días, 6e-8, autocorrelaciones) se reproducen.
**El Alcalde ya había corregido el escenario F** (ventas de aula ×7,5, precio ×1,45); lo repuse en una copia y mi
verificador lo marca (`tests/test_verificadores.py`).

### Detalle de la evidencia clave

**H-1.** `v_conectoma.py` lee los feather, define KC/PN por `class` y `somaSide`, y compara pares de KC (3 812 KC con ≥1 PN,
7,26 M pares): observado 0,20485; nulo Maslov–Sneppen sin restricción (como el suyo) 0,22789 (sd 8e-5); nulo que solo
intercambia aristas entre PN y KC del mismo lado: **0,20562** (sd 1,6e-4); nulo uniforme 0,10612. La diferencia
real-vs-nulo pasa de −10 % a −0,4 %. Hay además estructura de glomérulo/tipo de PN que no he controlado, así que el
residuo de 0,4 % no tiene por qué interpretarse tampoco. Mi duda: depende de que `somaSide` de PN y KC sea fiable
(98 % de las aristas coinciden de lado, lo cual lo apoya).

**H-2/H-5.** `umbral.py` tiene `tabla_toda_la_demanda` (m=3 → 729, m=5 → 1 910 USD/mes) y `tabla_solo_adquisicion`
(m=10 → 697, m=20 → 1 398). Mi bisección sobre 2 000 trayectorias: cruce de 1 000 USD en m=3,56 (todo) y 14,2 (solo
instalaciones). En `simulador.py::resume`, `cac = gasto / lab_total` con `lab_total = lab_suscriptores[:, -1]` (stock).

**H-3.** Mismo `activity.json`: MBON, 4 neuronas, primeros 500 ms: 14 espigas = 7,0 Hz. Con su propio simulador, 10 s sin
olor: 8,33/8,61/8,61 Hz. El cociente olor/reposo es ≈2,7, no ≈6.

## 3. Afirmaciones externas (citas «de memoria» contrastadas con la fuente)

Fuentes: Crossref, PubMed/PMC, NVD, Bitcoin Wiki, repositorio y whitepaper de Uniswap, arXiv, neuPrint
(`salida`/`scratchpad/auditor/ext`). Lo descargado se leyó como texto; no se ejecutó nada.

| Casa | Cita / afirmación | Resultado | Fuente y pasaje |
|---|---|---|---|
| mosca | Caron, Ruta, Abbott, Axel 2013 (convergencia aleatoria) | **Correcta** (Nature 497:113) en cuanto a la idea | PMID 23615618: «each Kenyon cell integrates input from a different and apparently random combination of glomeruli» |
| mosca | «6 PN por KC» atribuido a Caron 2013 | **Imprecisa** | PMC4148081: «between 2 and 11 dendritic claws (average = 7, n = 200)». El 6 es la mediana del conectoma (mi cálculo: mediana 6, media 5,92) |
| mosca | Aso et al. 2014 eLife: arquitectura del MB, MBON y DAN | **Correcta** | Crossref: «The neuronal architecture of the mushroom body provides a logic for associative learning», eLife 2014 (la valencia es el otro paper, 10.7554/eLife.04580) |
| mosca | Hige, Aso, Rubin, Turner 2015 *Nature*: «la dopamina deprime KC→MBON de MBON que promueven evitar» | **Falsa tal como está escrita** | Ese Nature (PMID 26416731) es «Plasticity-driven individualization of olfactory coding in MBONs»: tuning de MBON correlacionado, no plasticidad dopaminérgica. La depresión es Hige et al. *Neuron* 2015 (PMC4674068): «Pairing an odor with activation of specific dopamine neurons induces… odor-specific synaptic depression», y «the plasticity we found in this neuron [MBON-γ1pedc, valencia positiva] during aversive learning was LTD». El modelo de Neuro (recompensa deprime MBON de evitación) es coherente con Aso 2014b, pero no es lo que dice Hige |
| mosca | Turner, Bazhenov, Laurent 2008 (representación en KC) | **Correcta** | Crossref: *J Neurophysiol* 2008, «Olfactory representations by Drosophila mushroom body neurons» |
| mosca | Eichler et al. 2017 *Nature*, conectoma de la larva | **Correcta** | Crossref: «The complete connectome of a learning and memory centre in an insect brain», Nature 2017 |
| mosca | «2000 KC… 4 MBON»; literatura | KC ~2000 correcto; MBON: la literatura da 34 MBON/21 tipos (Hige Nature, resumen) y el conectoma 97/37 | PMID 26416731 resumen; `salida/50_` |
| agora | Uniswap v2: comisión 0,30 % sobre la entrada, k crece, acciones, sin protocol fee | **Correcta** | `UniswapV2Pair.sol`: `balance0Adjusted = balance0*1000 − amount0In*3` y `require(… >= reserve0*reserve1*1000**2)`; primera provisión `sqrt(amount0*amount1) − MINIMUM_LIQUIDITY` (1000 unidades bloqueadas: detalle irrelevante a su escala); protocol fee existe pero apagado por defecto (`feeTo`), como dice |
| agora | IL = 2√r/(1+r) − 1 | **Correcta, con matiz** | arXiv 2106.14404 (Aigner & Dhaliwal): la fórmula habitual está expresada **relativa al valor final de HODL**; relativa al valor inicial es √R − (R+1)/2. Tendera la usa como `× HODL final` (test), coherente |
| agora | MSFT mensual 2000-2010, 123 puntos, vol 34,4 % (vega_datasets) | **Correcta en sus números** | mi cálculo: 123 filas, 39,81 → 28,80, vol 0,3439 |
| notaria | CVE-2012-2459 = duplicar la hoja impar de Merkle colisiona la raíz | **Correcta** | Bitcoin Wiki *CVEs*: «CVE-2012-2459 … Easy · Block hash collision (via merkle root)». Ojo: el texto de NVD es genérico («unspecified vulnerability… DoS») y no menciona Merkle |
| forja | PSR/DSR de Bailey & López de Prado | **Referencias correctas; fórmula verificada solo por simulación** | Crossref: «The Sharpe Ratio Efficient Frontier» (SSRN 2011) y «The Deflated Sharpe Ratio» (SSRN/*Practical Applications* 2014-15). No pude abrir el texto de los artículos; comprobé en cambio que `sr_umbral_dsr` aproxima E[máx de N normales] (fórmula 2,920 vs Monte Carlo 2,901 para N=324; 1,193 vs 1,162 para N=5; error ≤3 %), que es lo que el DSR pretende |
| forja | White 2000 (Reality Check), Hansen 2005 (SPA), Politis–Romano (estacionario), Benjamini–Hochberg 1995 | **Correctas** | Crossref: *Econometrica* 2000; *JBES* 2005 (doi 10.1198/073500105000000063); *JASA* 1994; *JRSS-B* 1995. El umbral de Hansen `√(2 log log T)` está bien |
| conectoma | MaleCNS v1.0, «~166 000 neuronas», «Google Research + HHMI Janelia», CC-BY | **Imprecisa** | neuPrint `male-cns:v1.0`: «Janelia FlyEM Team Project, the Cambridge Drosophila Connectomics Group, and Google Connectomics… 167k neurons» (v0.9: 166k). No verifiqué la licencia |
| conectoma | Caron 2013 y Aso 2014 (los hereda de mosca) | Como arriba | — |
| mb-real | Aso 2014b: «all MBONs eliciting aversion were glutamatergic…» | **Correcta (cita literal)** | PMC4273436, Results |
| mb-real | Hige 2015 Neuron (CS+ −80 %, CS− −25 %, orden estricto) | **Correcta** (es la fuente real de la depresión dopaminérgica) | PMC4674068; ya corrigió su propia memoria sobre MBON09 |
| mb-real / conectoma | Shiu et al. 2024: V_rest −52, V_th −45, V_reset −52 mV, τ_m 20 ms, refractario 2,2 ms, τ_syn 5 ms, W_syn 0,275 mV | **Correctas** | PMC11446845, Methods: «V resting = −52 mV … V threshold = −45 mV … T refractory = 2.2 ms … τ = 5 ms … W syn = 0.275 mV (free parameter)» |
| empresa | «conversión freemium 2–5 %» y CPI | **NO VERIFICABLE** | referencias de blogs que la propia casa reconoce sin verificar |

## 4. Lo que NO pude comprobar

- **casa-forja**: es la casa con menos verificabilidad hoy. No hay README ni resultados finales; los números preliminares del
  bus n=5 (puerta 7,5 %/35 %, campeón 0/40 y 5/40) vienen de un script del scratchpad del Cazador que no está en el repo.
  Solo comprobé datos, autocorrelaciones y la lógica de `motor.py` (no hay fuga: `Wh[:, :, 1:] = W[:, :, :-1]`; PSR/DSR
  correctos). Nota estadística: 0/40 tiene un límite superior al 95 % de ~9 %, así que «0/40 con nulo iid» no acota la tasa
  de falsos positivos por debajo del 5 %, y 5/40 tiene IC95 ≈ [4 %, 27 %]. El bus n=34 (calibración: 0/300 y 0/200 campeones falsos, puerta 2,3 %, potencia 2,0 % con SR 0,3) llegó mientras auditaba: es coherente con un instrumento conservador y de poca potencia, que es lo que el propio Cazador concluye; lo único que rectifico son los intervalos (H-16). No re-ejecuté `calibrar.py` (cientos de mundos × 324 configuraciones × 1 000 remuestreos). Revisar cuando entregue.
- **casa-mb-real y la mosca virtual en bucle cerrado de la Cartógrafa**: aún no hay simulación de aprendizaje que auditar.
  Solo audité anatomía (37/37 tipos de MBON) y las citas. Su predicción previa (bus n=22) está bien formulada; no la evalúo.
- **Los simuladores LIF** (mosca, conectoma) no los reimplementé: verifiqué el análisis desde las espigas crudas, la
  determinación (mismo md5) y, para conectoma, que `sim.py` reproduce `sim_summary.json` exacto. Un error *dentro* del
  integrador no lo detectaría; los controles (0 pares, 16 semillas) sí descartan que el efecto sea ruido.
- **Plausibilidad biológica** de cualquier parámetro (tasa de aprendizaje, η, etc.): son supuestos declarados.
- **Matriz completa de pesos (1 GB)** frente a la «significant-only»: los 252 KC sin PN pueden ser filtro o trazado.
- **Referencias de mercado** de empresa (CPI, conversión freemium) y la app más allá del cerebro (UX, 390 px solo en su test).
- **Owald et al. 2015** (cita indirecta en Hige/mb-real) y la licencia CC-BY del conectoma.
- Mi control de **glomérulo/tipo de PN** para H-1: no lo hice; podría explicar el 0,4 % residual.

## 5. Dónde me equivoqué yo

Detalle en `LOG.md`. En corto: (1) comparé al principio la fórmula de IL contra 200 000 en lugar de contra el HODL final
(error 706 en vez de 74,6); (2) mi primera medida de «reposo» de mosca usó huecos de 400 ms y umbral por conteo
(KC 2,2 %); la rehice con los primeros 500 ms y con reposo de 10 s; (3) con `python -I` creí por un momento que `verify.py`
de la Notaría fallaba: era mi bandera, no su código; (4) mis tolerancias en `veredicto.py` son mías y pueden ser
demasiado estrictas o laxas (están en cada línea de salida).
