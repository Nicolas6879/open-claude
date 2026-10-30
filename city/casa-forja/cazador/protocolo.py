"""Protocolo de la caza. Todo lo que decide el resultado vive aqui.

Regla: este fichero se congela (hash sha256 en out/protocolo_congelado.json) ANTES de
ejecutar la seleccion sobre datos reales. Cambiarlo despues invalida la prueba final y
hay que contarlo en LOG.md como iteracion de desarrollo.
"""

# Particiones temporales. La muestra final (holdout) no se mira hasta congelar.
PRIMARIO = {
    "nombre": "sp500_1990_2022",
    "fin_seleccion": "2013-12-31",
    "inicio_holdout": "2014-01-01",
}
SECUNDARIOS = {
    # Replica de retorno total del S&P (SPY ajustado) con DTB3 real. Holdout reciente 2014-2026.
    "spy_tr": {"fin_seleccion": "2013-12-31", "inicio_holdout": "2014-01-01"},
    # BTCUSDT diario. Holdout 2023-2026, periodo no visto en ninguna otra prueba.
    "btc": {"fin_seleccion": "2022-12-31", "inicio_holdout": "2023-01-01"},
    "acciones20": {"fin_seleccion": "2013-12-31", "inicio_holdout": "2014-01-01"},
    "franceses": {"fin_seleccion": "1989-12-31", "inicio_holdout": "1990-01-01"},
    "momentum": {"fin_seleccion": "1989-12-31", "inicio_holdout": "1990-01-01"},
    "wti": {"fin_seleccion": "2002-12-31", "inicio_holdout": "2003-01-01"},
    "overnight": {"fin_seleccion": "2010-12-31", "inicio_holdout": "2011-01-01"},
}

# Costes (paper trading). Lineales en la rotacion, en puntos basicos por lado.
COSTE_IDA_BPS = 5.0
COSTE_BTC_BPS = 10.0     # cripto spot: comision ~10 pb por lado (supuesto declarado)
# Spread anual de financiacion sobre el apalancamiento (w>1) y las posiciones cortas.
SPREAD_FINANCIACION_ANUAL = 0.005
# No hay serie de tipos de corto plazo posterior a 2017 en el entorno: relleno anual.
RF_RELLENO_ANUAL = 0.0

PERIODOS_ANUALES = {"diario": 252, "mensual": 12}
# Longitud media de bloque del bootstrap estacionario (Politis-Romano).
BLOQUE = {"diario": 20, "mensual": 3}

B_BOOTSTRAP = 1000       # replicas de bootstrap
ALFA = 0.05              # nivel de significacion de la prueba final
Q_BH = 0.05              # tasa de falsos descubrimientos (Benjamini-Hochberg) en la final
K_FINALISTAS = 5         # finalistas que pasan de seleccion a muestra final
PUERTA_SPA = 0.10        # puerta: p de Hansen SPA (alfa vs B&H) en seleccion debe ser < esto
ANCLA_VOL_TSMOM = 0.10   # volatilidad objetivo de las variantes escaladas
SEMILLA = 20261030

# Mundos de control
N_MUNDOS_NULOS = 300
N_MUNDOS_PLANTADOS = 150
SR_PLANTADOS = (0.3, 0.6)  # SR bruto anual del efecto inyectado (TSMOM 60d)

# Veredicto. El primario decide la afirmacion principal; los secundarios se reportan y su
# muestra final se corrige JUNTA con BH (q = Q_BH) sobre todos los finalistas de todos los
# conjuntos (veredicto global). Un finalista secundario no sustituye al primario.
VEREDICTO_PRIMARIO_SOLO = "sp500_1990_2022"
CORRECCION_GLOBAL = True
