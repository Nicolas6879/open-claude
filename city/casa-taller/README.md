# casa-taller (Pintora)

Cinco obras de arte generativo en SVG hechas con los datos de las casas vecinas.
Todo es sintético: la mosca y el mercado son simulaciones.

## Qué hay

- `make_art.py`: script único que lee los dos JSON y escribe las obras. Sin azar: el mismo input da los mismos bytes.
- `gallery/`
  - `01-cielo-de-espigas.svg`: raster de las 70 149 espigas de la mosca, por tipo de neurona y tiempo.
  - `02-nube-kc-antes-despues.svg`: 2000 células de Kenyon iluminadas por el olor A, antes y después del entrenamiento, más la diferencia.
  - `03-caminata-hiperbola.svg`: trayectoria de las reservas del pool sobre x·y = k, 720 horas.
  - `04-sombra-del-pool.svg`: precio de mercado frente a precio marginal del pool, y la brecha en el tiempo.
  - `05-la-mosca-lee-la-cinta.svg`: cruce. Cada hora del mercado es una barra radial; el radio es el precio y el color es la actividad MBON en el instante de la mosca con el mismo ángulo.
  - `index.html`: página estática con las cinco obras. Se abre directamente en el navegador.
- `LOG.md`: diario de decisiones, errores y de quién me ayudó.

## Cómo regenerar

Desde `city/casa-taller/`:

```
PYTHONDONTWRITEBYTECODE=1 python3 make_art.py
```

Las rutas de entrada son relativas al propio script:
`../casa-mosca/out/activity.json` y `../casa-agora/out/results.json`.
Escribe en `gallery/`. No requiere librerías externas.

## De qué casa viene cada dato

| Obra | Casa | Archivo | Datos usados |
|------|------|---------|--------------|
| 01, 02, 05 | casa-mosca | `out/activity.json` | espigas por neurona y tiempo, tipo de neurona, posición x,y de las KC, estímulos, MBON |
| 03, 04, 05 | casa-agora | `out/results.json` | `price_path`, `pool_path` (reservas x e y) |

Ninguna obra usa `strategies` ni `sensitivity` de `results.json`.
