# Ciudad viva

Una maqueta nocturna de la ciudad que se mueve con lo que pasa de verdad: cada casa se enciende cuando se modifican archivos suyos, cada mensaje del bus viaja como una carta de una casa a otra, cada commit levanta una bandera en la Alcaldía y las entregas lanzan un pulso rosa. Al lado, una lista con lo que va ocurriendo.

- `ciudad_viva.html`: la página (un artefacto con el canal `db`, que escucha la colección `eventos` en directo).
- `observador.py`: vigila el repo (bus, `git log`, archivos de `city/casa-*`) y escribe una línea JSON por evento. Solo lee.
- Funcionamiento: Monitor ejecuta el observador; cada línea despierta al Alcalde, que la escribe en la colección con `ArtifactData`. **No es una conexión directa del repo al navegador**: hay un salto manual (un agente) de unos segundos.

## Límites honestos
- La luz de una casa significa «cambiaron archivos suyos en los últimos segundos», no «el agente está pensando»; un agente que piensa sin tocar archivos aparece dormido.
- La actividad se agrega en una línea cada 30 s, así que el pulso de «trabajando» llega con ese retraso.
- Los mensajes del bus no tienen hora (el protocolo no usa reloj): la semilla de historial les pone horas inventadas y las marca `hist`; la lista las muestra con «·».
- Si el Alcalde deja de empujar eventos, la página sigue abierta pero se pone «en pausa».
