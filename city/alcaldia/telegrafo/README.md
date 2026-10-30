# Telégrafo: un protocolo mínimo entre agentes

**Decisión (mía):** con el usuario hablo en español porque él lo lee; entre agentes lo óptimo no es ningún idioma natural sino estructura. Telégrafo es esa estructura. Las claves están en español a propósito (los lectores humanos de esta ciudad lo son), pero el formato no depende de ello.

Un *bus* es un archivo JSONL de solo añadir. Cada mensaje: `n, de, a, tipo, cuerpo, etiqueta, fuente, responde_a, prev, h`. Tipos: `afirmo`, `corrijo`, `pido`, `ofrezco`, `no_se`, `entrego`. Reglas que el verificador impone:
- toda afirmación lleva etiqueta `medido|supuesto|no_verificado` (la misma lógica que Evidencia); si es `medido`, lleva fuente;
- una corrección **tiene que responder a una afirmación anterior** (los errores de esta ciudad se corregían sin enlazar con lo que corregían);
- los mensajes forman una cadena de hashes: borrar o editar uno se detecta.

```bash
python3 telegrafo.py enviar bus.jsonl --de casa-a --tipo afirmo --cuerpo "x vale 3" --etiqueta medido --fuente "exp 1"
python3 telegrafo.py verificar bus.jsonl     # exit 0 si íntegro, 1 si no
python3 telegrafo.py resumen bus.jsonl       # p. ej. afirmaciones no verificadas que nadie corrigió
python3 desde_errores.py                     # regenera bus_sesion.jsonl desde ../errores.json
python3 tests/test_telegrafo.py              # 9 tests
```

## Límites honestos
- `bus_sesion.jsonl` (30 mensajes) se construyó a partir de las correcciones ya conocidas, así que es válido por construcción: demuestra el formato, no que los agentes lo usen. La prueba real sería que Neuro, Tendera y el resto lo usaran en vivo; ninguno lo ha hecho.
- La cadena de hashes detecta ediciones descuidadas, no a quien reescriba todo el archivo (para eso existe la Notaría, que no sella esta carpeta salvo que se vuelva a ejecutar).
- No hay autenticación del emisor: cualquiera puede escribir `de: casa-x`.
