"""Carga de datos reales (copias en datos/, ver datos/PROCEDENCIA.txt) y guarda de la muestra final.

La guarda de holdout es deliberadamente molesta: solo deja leer la muestra final si el
protocolo esta congelado (hash coincide) y deja huella en out/acceso_holdout.log.
"""
import hashlib
import json
import os
from datetime import datetime

import numpy as np
import pandas as pd

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATOS = os.path.join(RAIZ, "datos")
OUT = os.path.join(RAIZ, "out")


def _leer(nombre, col=None, fecha="Date", **kw):
    df = pd.read_csv(os.path.join(DATOS, nombre), parse_dates=[fecha], index_col=fecha, **kw)
    return df if col is None else df[col]


def sp500():
    return _leer("sp500_1990_2022.csv.gz", "sp500").astype(float)


def acciones20():
    return _leer("acciones20_1990_2022.csv.gz").astype(float)


def sp500_ohlc():
    return _leer("sp500_ohlc_1999_2018.csv.gz").astype(float)


def wti():
    return _leer("wti_diario_1986_2019.csv.gz", "wti").astype(float)


def nasdaq():
    return _leer("nasdaq_1999_2018.csv.gz", "nasdaq").astype(float)


def goog():
    return _leer("goog_2004_2013.csv.gz")


def eurusd_h1():
    return _leer("eurusd_h1_2017_2018.csv.gz")


def spy_ajustado():
    return _leer("spy_ajustado_1993_2026.csv.gz", "spy_adj").astype(float)


def btc():
    return _leer("btc_usdt_1d_2017_2026.csv.gz", "Close").astype(float)


def dtb3_pct():
    return _leer("dtb3_tasa_bill_3m_1990_2026.csv.gz", "dtb3_pct").astype(float)


def vix_fred():
    return _leer("vix_fred_1990_2026.csv.gz", "vixcls").astype(float)


def rf_dtb3_diaria(fechas):
    """Tipo sin riesgo diario = DTB3 (%) / 100 / 252, ultimo dato conocido (ffill)."""
    serie = dtb3_pct().reindex(pd.DatetimeIndex(fechas)).ffill().bfill()
    return serie.to_numpy() / 100.0 / 252.0


def french_mensual():
    """Mkt-RF, SMB, HML, RF en decimal, indice mensual (fecha = primer dia del mes)."""
    df = pd.read_csv(os.path.join(DATOS, "french_mensual_1926_2018.csv"))
    df["Date"] = pd.to_datetime(df["Date"].astype(str), format="%Y-%m")
    return df.set_index("Date").astype(float)


def momentum_mensual():
    df = pd.read_csv(os.path.join(DATOS, "french_momentum_mensual_1949_2017.csv"))
    df = df.rename(columns={"dates": "Date"})
    df["Date"] = pd.to_datetime(df["Date"].astype(str), format="%Y-%m")
    return df.set_index("Date")[["Mom"]].astype(float)


def tasa_libre_diaria(fechas, rf_mensual=None, relleno_anual=0.0):
    """Tipo sin riesgo diario aproximado: RF mensual repartido entre los dias del mes.

    Fuera del rango de rf_mensual (p. ej. 2019-2022) se usa relleno_anual: es una
    suposicion explicita, no un dato.
    """
    fechas = pd.DatetimeIndex(fechas)
    rf = np.full(len(fechas), relleno_anual / 252.0)
    if rf_mensual is None:
        return rf
    mes = fechas.to_period("M").to_timestamp()
    dias_mes = pd.Series(1, index=fechas).groupby(mes).transform("size").to_numpy()
    rf_m = rf_mensual.reindex(mes).to_numpy()
    ok = ~np.isnan(rf_m)
    rf[ok] = rf_m[ok] / dias_mes[ok]
    return rf


def rf_real_diaria(fechas, relleno_anual=0.0):
    fr = french_mensual()["RF"]
    return tasa_libre_diaria(fechas, fr, relleno_anual)


# ---------------------------------------------------------------- guarda de holdout

ARCHIVO_PROTOCOLO = os.path.join(OUT, "protocolo_congelado.json")
ARCHIVO_ACCESOS = os.path.join(OUT, "acceso_holdout.log")


def hash_protocolo():
    with open(os.path.join(RAIZ, "cazador", "protocolo.py"), "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def exigir_protocolo_congelado(etiqueta):
    """Lanza error si el protocolo no esta congelado con el hash actual. Registra el acceso."""
    if not os.path.exists(ARCHIVO_PROTOCOLO):
        raise RuntimeError("Protocolo no congelado: ejecuta primero congelar_protocolo().")
    with open(ARCHIVO_PROTOCOLO) as f:
        cong = json.load(f)
    if cong["sha256"] != hash_protocolo():
        raise RuntimeError("protocolo.py cambio despues de congelar: prueba invalida.")
    os.makedirs(OUT, exist_ok=True)
    with open(ARCHIVO_ACCESOS, "a") as f:
        f.write(f"{datetime.now().isoformat(timespec='seconds')}\t{etiqueta}\n")
