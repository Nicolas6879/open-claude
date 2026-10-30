"""Carga y limpieza de datos (HYG v4.1 + culturas celestes de Stellarium).

Todo lo descargado es NO CONFIABLE: aqui solo se parsea como JSON/CSV (nunca se ejecuta).
Las rutas de datos se pasan por variable de entorno ZODIACO_DATOS (directorio fuera del repo).
"""
import json
import os
import re
import numpy as np

DATOS = os.environ.get(
    "ZODIACO_DATOS",
    "/tmp/claude-0/-home-user-open-claude/e7f872ff-c04d-5af4-a3a1-8d2199c39026/scratchpad/zodiaco/data",
)

# Familias (linajes historicos/derivaciones), SUPUESTO del autor: se usan en la validacion
# "dejar fuera una familia" para evitar fugas (p. ej. 7 variantes de las 88 constelaciones IAU).
FAMILIAS = {
    "occidental": ["modern", "modern_iau", "modern_hlad", "modern_st", "modern_rey", "greek_almagest",
                   "greek_dante", "greek_farnese", "greek_leidenAratea", "arabic_al-sufi"],
    "babilonia": ["babylonian_mulapin", "babylonian_seleucid"],
    "china": ["chinese", "chinese_chenzhuo", "chinese_manchu", "chinese_song_dynasty", "chinese_xianglin",
              "chinese_yuan_dynasty", "modern_chinese", "modern_journey_to_the_west", "japanese", "korean"],
    "india": ["indian", "indian_nakshatras"],
    "arabe_popular": ["arabic_arabian_peninsula", "arabic_indigenous"],
    "polinesia": ["hawaiian_starlines", "maori", "ruanui_sky_tahiti_and_society_islands", "samoan", "tongan",
                  "anutan"],
    "nordica": ["norse", "norse_edda"],
}


def familia_de(cultura):
    for f, lst in FAMILIAS.items():
        if cultura in lst:
            return f
    return cultura  # cultura aislada = su propia familia


def lista_culturas(datos=DATOS):
    with open(os.path.join(datos, "lista_culturas.txt")) as fh:
        return [l.strip() for l in fh if l.strip()]


def cargar_hyg(datos=DATOS):
    """Devuelve dict de arrays numpy con TODAS las filas de HYG (incl. Sol, id=0)."""
    import pandas as pd
    df = pd.read_csv(os.path.join(datos, "hygdata_v41.csv"),
                     usecols=["id", "hip", "proper", "gl", "bf", "ra", "dec", "dist", "mag", "absmag", "x", "y", "z", "con", "spect"],
                     low_memory=False)
    return df


def licencia(cultura, datos=DATOS):
    p = os.path.join(datos, "desc", cultura + ".md")
    if not os.path.exists(p):
        return "desconocida"
    txt = open(p, encoding="utf-8", errors="replace").read()
    m = re.search(r"^## License\s*\n(.*?)(?=^## |\Z)", txt, flags=re.S | re.M)
    if not m:
        return "no declarada"
    s = " ".join(m.group(1).split())
    return s[:160] if s else "no declarada"


def parsear_cultura(cultura, hip_set, datos=DATOS, incluir_asterismos=True):
    """Devuelve (aristas, contab).

    aristas: lista de (a, b, grupo) con a<b IDs de Hipparcos, 'grupo' = indice de constelacion/asterismo
             (para bootstrap por cluster). Aristas unicas por par (se conserva el primer grupo).
    contab: contabilidad de perdidas.
    """
    d = json.load(open(os.path.join(datos, "cultures", cultura + ".json")))
    items = [("C", c) for c in d.get("constellations", [])]
    if incluir_asterismos:
        items += [("A", a) for a in d.get("asterisms", []) if not a.get("is_ray_helper")]
    c = dict(culturas=cultura, n_const=len(d.get("constellations", [])), n_aster=len(d.get("asterisms", [])),
             aristas_brutas=0, aristas_no_hip=0, aristas_autolazo=0, aristas_hip_fuera_hyg=0, aristas_duplicadas=0)
    vistos = {}
    for gi, (_, it) in enumerate(items):
        for linea in it.get("lines", []):
            for a, b in zip(linea[:-1], linea[1:]):
                c["aristas_brutas"] += 1
                if not (isinstance(a, int) and isinstance(b, int)):
                    c["aristas_no_hip"] += 1
                    continue
                if a == b:
                    c["aristas_autolazo"] += 1
                    continue
                if a not in hip_set or b not in hip_set:
                    c["aristas_hip_fuera_hyg"] += 1
                    continue
                k = (min(a, b), max(a, b))
                if k in vistos:
                    c["aristas_duplicadas"] += 1
                    continue
                vistos[k] = gi
    ar = [(a, b, g) for (a, b), g in vistos.items()]
    c["aristas_finales"] = len(ar)
    c["estrellas_finales"] = len({x for a, b, _ in ar for x in (a, b)})
    return ar, c


def radec_a_vec(ra_deg, dec_deg):
    ra = np.radians(ra_deg)
    de = np.radians(dec_deg)
    return np.stack([np.cos(de) * np.cos(ra), np.cos(de) * np.sin(ra), np.sin(de)], axis=-1)
