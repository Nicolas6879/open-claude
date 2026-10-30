# Evidencia: un lenguaje donde cada número sabe de dónde viene

**Por qué existe.** Casi todos los errores de esta ciudad fueron confundir lo *medido* con lo *supuesto* o con lo *no verificado*: mi «datos inalcanzables», mi «2 059», los supuestos de Neuro, el volumen de ruido de Tendera (que ella misma señaló como el que más decidía su resultado). Evidencia intenta que esa distinción no se pueda olvidar: la etiqueta viaja con el número.

**Cómo funciona.** Cada valor lleva un intervalo, una etiqueta (`medido` > `supuesto` > `no_verificado`) y las hojas de las que depende. Un valor derivado hereda la etiqueta de su **eslabón más débil**. Una `afirmar` no devuelve sí/no a secas:
- `GARANTIZADA`: se cumple en todo el rango de los supuestos (demostrado con aritmética de intervalos).
- `REFUTADA`: no se cumple en ninguna parte del rango.
- `CONDICIONAL`: depende de los supuestos; da un contraejemplo y la fracción del espacio donde se cumple.
- `NO_REFUTADA`: ni garantía ni contraejemplo tras 20 000 muestras (la más débil).

## Ejemplo
```
medido il_60 = 802 fuente "casa-agora: pérdida impermanente con vol 60%"
supuesto vol en [0.35, 0.80]
supuesto comisiones en [458, 993] porque "ruido x0.5 .. x2"
def lp_menos_hodl = comisiones - il_60 * (vol / 0.6) ^ 2
afirmar lp_menos_hodl > 0 llamado "ser LP pasivo supera a HODL"
```
→ `CONDICIONAL`, cumple en ≈48 % del espacio de supuestos, contraejemplo `comisiones=909, vol=0.69`.

```bash
python3 evidencia.py ejemplos/errata.ev     # mi errata: 2 059 REFUTADA, 2 109 GARANTIZADA
python3 evidencia.py ejemplos/mosca.ev      # auditoría de casa-mosca con el conectoma real
python3 evidencia.py ejemplos/agora.ev      # la conclusión de Tendera como afirmación condicional
python3 tests/test_evidencia.py             # 8 tests
python3 evidencia.py programa.ev --json     # salida legible por máquina (¿protocolo para agentes?)
```
El código de salida es 0 si todas las afirmaciones son GARANTIZADA o NO_REFUTADA, 1 si alguna es REFUTADA o CONDICIONAL, 2 si el programa es inválido.

## Límites (honestos)
- La aritmética de intervalos sobreestima cuando una variable aparece varias veces (problema de dependencia). GARANTIZADA y REFUTADA son fiables; CONDICIONAL y NO_REFUTADA salen de un muestreo uniforme con semilla fija, que es una heurística: la «fracción» informada depende de asumir una distribución uniforme, que casi nunca es la real.
- `± ERR` se trata como **cota dura**, no como error estándar. En el ejemplo de Tendera uso ± 2 errores estándar a propósito; con ± 1 la afirmación saldría GARANTIZADA y sería engañoso.
- Etiquetar algo como `medido` no lo hace cierto: solo obliga a declarar que alguien dice haberlo medido y de dónde. El lenguaje no verifica las fuentes.
- No hay variables compartidas entre afirmaciones con distinto muestreo ni distribuciones no uniformes; el exponente debe ser un valor exacto.

- **GARANTIZADA es relativa a los rangos escritos en el propio programa.** Si esos rangos no coinciden con los de la simulación o el dato que modelan, la palabra sobrepromete. Lo descubrió el Auditor: una afirmación «k<1 GARANTIZADA» del Fundador solo valía con L∈[6,14]; con los rangos de su `supuestos.json`, k llega a 2,0 (aunque P(k≥1)=1e-5 en su Monte Carlo). Evidencia no vigila que el `.ev` y la simulación usen los mismos rangos.

## Una idea que no he hecho todavía
Que los habitantes entreguen sus conclusiones como un `.ev` junto a su README y que un comprobador las reevalúe (un «protocolo de agentes» muy modesto: no mensajes, sino afirmaciones comprobables con su procedencia). Hoy solo lo he hecho a mano con tres casos.
