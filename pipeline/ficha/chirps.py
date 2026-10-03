"""Lectura puntual de CHIRPS v3 (COG en data.chc.ucsb.edu) sin GDAL.

Solo se descargan el encabezado del COG y la tesela que contiene los puntos (peticiones HTTP por rangos).
El LZW de TIFF se decodifica en Python puro: así no hay dependencias nativas además de numpy
(en algunas máquinas Windows, Control de aplicaciones bloquea las DLL de rasterio e imagecodecs).
"""
from __future__ import annotations

import io
import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
import requests
import tifffile

BASE = "https://data.chc.ucsb.edu/products/CHIRPS/v3.0"
TAM_ENCABEZADO = 1 << 16


def url_mensual(anio: int, mes: int) -> str:
    return f"{BASE}/monthly/global/cogs/chirps-v3.0.{anio}.{mes:02d}.cog"


def url_diaria(anio: int, mes: int, dia: int) -> str:
    # Diario 'sat': CHIRPS v3 desagregado con NASA IMERG Late V07
    return f"{BASE}/daily/final/sat/cogs/{anio}/chirps-v3.0.sat.{anio}.{mes:02d}.{dia:02d}.cog"


def lzw_decode(data: bytes) -> bytes:
    """LZW de TIFF (códigos MSB primero, 9–12 bits, 'early change')."""
    datos = data + b"\0\0\0"
    tabla = [bytes([i]) for i in range(256)] + [b"", b""]
    salida = bytearray()
    bit, ancho, previo = 0, 9, None
    total = len(data) * 8
    while bit + ancho <= total:
        i = bit >> 3
        palabra = (datos[i] << 16) | (datos[i + 1] << 8) | datos[i + 2]
        codigo = (palabra >> (24 - (bit & 7) - ancho)) & ((1 << ancho) - 1)
        bit += ancho
        if codigo == 257:  # EOI
            break
        if codigo == 256:  # CLEAR
            del tabla[258:]
            ancho, previo = 9, None
            continue
        if previo is None:
            entrada = tabla[codigo]
        else:
            entrada = tabla[codigo] if codigo < len(tabla) else previo + previo[:1]
            tabla.append(previo + entrada[:1])
        salida += entrada
        previo = entrada
        n = len(tabla)
        if n == 511:
            ancho = 10
        elif n == 1023:
            ancho = 11
        elif n == 2047:
            ancho = 12
    return bytes(salida)


def _rango(url: str, inicio: int, fin: int, sesion: requests.Session) -> bytes:
    r = sesion.get(url, headers={"Range": f"bytes={inicio}-{fin}"}, timeout=60)
    r.raise_for_status()
    return r.content


def leer_puntos(url: str, puntos: list[tuple[float, float]], sesion: requests.Session) -> list[float | None]:
    """Valor del píxel de cada (lat, lon). None si es nodata. Los puntos deben caer en la misma tesela o en pocas."""
    encabezado = _rango(url, 0, TAM_ENCABEZADO - 1, sesion)
    tif = tifffile.TiffFile(io.BytesIO(encabezado))
    pag = tif.pages[0]
    lon0, lat0 = pag.geotiff_tags["ModelTiepoint"][3:5]
    dx, dy = pag.geotiff_tags["ModelPixelScale"][:2]
    if pag.compression not in (1, 5) or pag.predictor != 1:
        raise ValueError(f"{url}: compresión {pag.compression} / predictor {pag.predictor} no soportados")
    tw, th = pag.tilewidth, pag.tilelength
    teselas_x = -(-pag.shape[1] // tw)
    dtype = np.dtype(pag.dtype).newbyteorder(tif.byteorder)
    cache: dict[int, np.ndarray] = {}
    valores = []
    for lat, lon in puntos:
        fila, col = int((lat0 - lat) / dy), int((lon - lon0) / dx)
        idx = (fila // th) * teselas_x + (col // tw)
        if idx not in cache:
            off, n = pag.dataoffsets[idx], pag.databytecounts[idx]
            crudo = _rango(url, off, off + n - 1, sesion)
            if pag.compression == 5:
                crudo = lzw_decode(crudo)
            cache[idx] = np.frombuffer(crudo, dtype=dtype, count=tw * th).reshape(th, tw)
        v = float(cache[idx][fila % th, col % tw])
        valores.append(None if v < -1 or not np.isfinite(v) else v)  # nodata de CHIRPS: -9999
    return valores


class CacheChirps:
    """Guarda en disco los valores ya leídos: volver a correr el pipeline no descarga nada."""

    def __init__(self, ruta: Path, puntos: list[tuple[float, float]]):
        self.ruta, self.puntos = ruta, puntos
        self.clave_puntos = json.dumps([[round(a, 5), round(b, 5)] for a, b in puntos])
        self.datos = {}
        if ruta.exists():
            guardado = json.loads(ruta.read_text(encoding="utf-8"))
            if guardado.get("puntos") == self.clave_puntos:
                self.datos = guardado["valores"]

    def obtener(self, urls: list[str], hilos: int = 6) -> dict[str, list[float | None]]:
        faltan = [u for u in urls if u not in self.datos]
        if faltan:
            sesion = requests.Session()

            def uno(u):
                return u, leer_puntos(u, self.puntos, sesion)

            with ThreadPoolExecutor(hilos) as ex:
                for i, (u, v) in enumerate(ex.map(uno, faltan), 1):
                    self.datos[u] = v
                    if i % 20 == 0 or i == len(faltan):
                        print(f"  CHIRPS: {i}/{len(faltan)} archivos")
                        self._guardar()
        return {u: self.datos[u] for u in urls}

    def _guardar(self):
        self.ruta.parent.mkdir(parents=True, exist_ok=True)
        self.ruta.write_text(json.dumps({"puntos": self.clave_puntos, "valores": self.datos}), encoding="utf-8")
