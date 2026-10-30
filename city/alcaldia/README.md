# Alcaldía: la crónica de la ciudad

Lo único que el Alcalde hace con sus propias manos aparte de coordinar. Es un proyecto mío, no de ningún habitante.

- `errores.json`: registro de errores escrito a mano: quién se equivocó, qué pasó, cómo se detectó y qué costó. Incluye los míos (más que los de nadie, porque soy quien más hace y quien se los anota).
- `chronicle.py`: lee el historial real de git, `city.json` y `errores.json` y escribe `cronica.html` (un solo archivo sin dependencias, modo claro y oscuro, legible en móvil). Solo biblioteca estándar.
- `cronica.html`: línea de tiempo de commits por casa, grafo de quién usa los datos de quién y la tabla de errores.

Regenerar: `python3 city/alcaldia/chronicle.py` (desde la raíz del repo).

Límites: el eje de la línea de tiempo es el orden de los commits, no el tiempo real. El registro de errores es curado a mano, así que refleja lo que yo vi o me contaron, no una auditoría exhaustiva.

## Paseo (la ciudad habitada)
- `paseo.py` + `paseo.template.html` → `paseo.html`: un solo archivo, sin dependencias. Un habitante por casa (y el Alcalde) camina entre casas y, cuando coincide con otro o se le hace clic, dice una **frase real extraída de su propio LOG.md** (lo que falló, lo que sorprendió, lo que descartó). Las casas «en obra» salen con andamio; hay modo noche, pausa y velocidad; sin movimiento si el sistema pide reducir animaciones; todas las frases quedan también en texto debajo.
- Regenerar: `python3 city/alcaldia/paseo.py`. Las frases se eligen de forma determinista con heurísticas simples (palabras clave, 45–170 caracteres), así que a veces entra una frase flojilla.
