"""Descarga datos publicos a un directorio de trabajo (NO al repo) y genera datos/*.csv|json pequenos.
Uso: python descargar.py DIRTRABAJO
Fuentes (solo lectura, publicas):
  GeoNames cities15000 (CC-BY 4.0): https://download.geonames.org/export/dump/cities15000.zip
  Natural Earth 10m railroads v4.1.0 (dominio publico): https://naciscdn.org/naturalearth/10m/cultural/ne_10m_railroads.zip
Los datos descargados se tratan como NO confiables: solo se parsean (zip/csv/dbf), nunca se ejecutan.
"""
import sys, os, io, json, zipfile, urllib.request, math, csv
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))


def fetch(url, dest):
    if os.path.exists(dest):
        return
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (research script)"})
    with urllib.request.urlopen(req, timeout=300) as r, open(dest, "wb") as f:
        f.write(r.read())


def hav(lat1, lon1, lat2, lon2):
    p = math.pi / 180
    a = math.sin((lat2 - lat1) * p / 2) ** 2 + math.cos(lat1 * p) * math.cos(lat2 * p) * math.sin((lon2 - lon1) * p / 2) ** 2
    return 12742 * math.asin(math.sqrt(a))


REGIONS = {
    # nombre: (pais, lat_min, lat_max, lon_min, lon_max, n, separacion_min_km)
    "espana": ("ES", 36.0, 44.0, -10.0, 4.6, 40, 20),
    "kanto": ("JP", 34.9, 37.0, 138.6, 141.0, 37, 15),
}


# Entradas de GeoNames que son distritos de Tokio o tienen coordenadas erroneas (comprobado a mano, ver LOG):
EXCLUIR = {"8469289": "Ota-ku (distrito de Tokio)", "11071717": "Edogawa-ku (distrito de Tokio)",
           "11836117": "Suginami: coordenadas de GeoNames erroneas (36.2N,140.3E; el distrito esta en Tokio)"}


EXCLUIR_NOMBRE = {"Palma"}  # isla (Baleares): sin conexion ferroviaria con la peninsula


def pick_cities(rows, spec):
    cc, la0, la1, lo0, lo1, n, sep = spec
    c = [r for r in rows if r["cc"] == cc and la0 <= r["lat"] <= la1 and lo0 <= r["lon"] <= lo1 and r["id"] not in EXCLUIR and r["name"] not in EXCLUIR_NOMBRE]
    c.sort(key=lambda r: -r["pop"])
    out = []
    for r in c:
        if all(hav(r["lat"], r["lon"], q["lat"], q["lon"]) >= sep for q in out):
            out.append(r)
        if len(out) == n:
            break
    return out


def main(work):
    os.makedirs(work, exist_ok=True)
    zg = os.path.join(work, "cities15000.zip")
    fetch("https://download.geonames.org/export/dump/cities15000.zip", zg)
    txt = zipfile.ZipFile(zg).read("cities15000.txt").decode("utf8").splitlines()
    rows = []
    for ln in txt:
        f = ln.split("\t")
        rows.append(dict(id=f[0], name=f[2], lat=float(f[4]), lon=float(f[5]), cc=f[8], pop=int(f[14])))
    for name, spec in REGIONS.items():
        sel = pick_cities(rows, spec)
        with open(os.path.join(HERE, f"ciudades_{name}.csv"), "w", newline="") as fh:
            w = csv.writer(fh)
            w.writerow(["geonameid", "nombre", "lat", "lon", "poblacion"])
            for r in sel:
                w.writerow([r["id"], r["name"], r["lat"], r["lon"], r["pop"]])
        print(name, len(sel), "ciudades; la mayor", sel[0]["name"], "la menor", sel[-1]["name"], sel[-1]["pop"])
    # ferrocarril
    import shapefile
    zr = os.path.join(work, "rail.zip")
    fetch("https://naciscdn.org/naturalearth/10m/cultural/ne_10m_railroads.zip", zr)
    d = os.path.join(work, "ne_rail")
    os.makedirs(d, exist_ok=True)
    zipfile.ZipFile(zr).extractall(d)
    r = shapefile.Reader(os.path.join(d, "ne_10m_railroads"))
    for name, spec in REGIONS.items():
        cc, la0, la1, lo0, lo1, n, sep = spec
        pad = 0.3
        lines = []
        for sh, rec in zip(r.iterShapes(), r.iterRecords()):
            bb = sh.bbox  # lon_min, lat_min, lon_max, lat_max
            if bb[2] < lo0 - pad or bb[0] > lo1 + pad or bb[3] < la0 - pad or bb[1] > la1 + pad:
                continue
            parts = list(sh.parts) + [len(sh.points)]
            for a, b in zip(parts[:-1], parts[1:]):
                pts = [(round(x, 4), round(y, 4)) for x, y in sh.points[a:b]]
                lines.append(pts)
        json.dump(lines, open(os.path.join(HERE, f"ferrocarril_{name}.json"), "w"), separators=(",", ":"))
        print(name, "polilineas ferrocarril:", len(lines))


if __name__ == "__main__":
    main(sys.argv[1])
