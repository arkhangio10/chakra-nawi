"""
Generador de datos SINTÉTICOS para el contador de broca (Chakra Ñawi).

TODO LO QUE PRODUCE ESTE SCRIPT ES SINTÉTICO. No son fotos reales de broca
(Hypothenemus hampei) ni de gorgojos. El error medido con estos datos NO es
desempeño en broca real (ver ml/README.md y docs/LIMITES_DE_DATOS.md).

Qué genera
----------
Directamente el **marco rectificado** de 10×10 cm → 1216×1216 px (≈12,16 px/mm),
tal como lo entrega la homografía de la PWA (contracts/modelo-io.md):

- Fondo: papel blanco/hueso con textura, arrugas leves, manchas de agua/café,
  línea gris del marco y, a veces, una astilla de la esquina negra (error de
  homografía).
- Broca: escarabajo marrón oscuro/negro de ≈1,7 × 0,8 mm (≈21 × 10 px),
  elipsoide alargado con sombreado, brillo especular, sutura de élitros,
  rotación aleatoria, a veces agrupadas y solapadas parcialmente. Clase 0.
- Distractores (NO se etiquetan): granitos de café tostado molido, incluidos
  negativos alargados de 1–1,5 mm, restos
  vegetales (fibras y trocitos de hoja), moscas de 4–6 mm, mosquitas oscuras
  con alas, insectos claros pequeños y otros escarabajos más grandes. Entre el
  7 y el 22 % proporcionales a las brocas, más Poisson(8) insectos adicionales
  (55 % de los distractores sorteados son mosquitas oscuras).
- Fotometría: gradiente de iluminación, viñeteo, sombras suaves, dominante de
  color, desenfoque, pérdida de resolución, ruido y artefactos JPEG variables.

Densidades: 0, 1–49, 50–300 y >300 brocas por marco.

Salida (por defecto en ml/datasets/sint_v0/)
--------------------------------------------
    marcos/<split>/images/*.jpg      marcos completos 1216×1216
    marcos/<split>/labels/*.txt      etiquetas YOLO normalizadas al marco
    marcos/<split>/conteos.json      conteo real por marco (+ densidad)
    mosaicos/<split>/images/*.jpg    4 mosaicos 640×640, orígenes x,y ∈ {0, 576}
    mosaicos/<split>/labels/*.txt    etiquetas YOLO recortadas al mosaico
                                     (se descartan cajas con <50 % de área dentro)
    data.yaml                        para Ultralytics (entrena con mosaicos)
    LEEME_SINTETICO.txt              rótulo "datos sintéticos"

Uso
---
    python sintetico.py --salida datasets/sint_v0 --train 400 --val 60 --test 60
    python sintetico.py --vista 4      # solo guarda 4 ejemplos con cajas en datasets/vista/
"""

from __future__ import annotations

import argparse
import json
import math
import os
import time
from multiprocessing import Pool
from pathlib import Path

import cv2
import numpy as np

S = 1216                 # lado del marco rectificado (px)
PX_MM = S / 100.0        # 12,16 px por mm
TILE = 640
ORIGENES = (0, 576)      # orígenes x, y de los mosaicos (64 px de solape)

DENSIDADES = ("0", "1-49", "50-300", ">300")


def densidad_de(n: int) -> str:
    if n == 0:
        return "0"
    if n < 50:
        return "1-49"
    if n <= 300:
        return "50-300"
    return ">300"


# ---------------------------------------------------------------------------
# Utilidades de composición
# ---------------------------------------------------------------------------

class Parche:
    """Lienzo sobremuestreado (factor k) para dibujar un objeto con antialias.

    Guarda color premultiplicado y alfa; `pegar` lo reduce con INTER_AREA y lo
    compone sobre el marco con el operador "over".
    """

    def __init__(self, cx: float, cy: float, half: int, k: int):
        self.k = k
        self.half = half
        self.x0 = int(math.floor(cx)) - half
        self.y0 = int(math.floor(cy)) - half
        self.n = (2 * half + 1) * k
        self.pcx = (cx - self.x0) * k
        self.pcy = (cy - self.y0) * k
        self.colp = np.zeros((self.n, self.n, 3), np.float32)
        self.alfa = np.zeros((self.n, self.n), np.float32)

    def malla(self, ang: float):
        """Coordenadas locales (u a lo largo del cuerpo, v a lo ancho) en px*k."""
        yy, xx = np.mgrid[0:self.n, 0:self.n].astype(np.float32)
        dx = xx + 0.5 - self.pcx
        dy = yy + 0.5 - self.pcy
        c, s = math.cos(ang), math.sin(ang)
        return dx * c + dy * s, -dx * s + dy * c

    def a_parche(self, u: float, v: float, ang: float):
        """Punto local (px*k) → coordenadas del parche (px*k)."""
        c, s = math.cos(ang), math.sin(ang)
        return self.pcx + u * c - v * s, self.pcy + u * s + v * c

    def capa(self, m: np.ndarray, color, a: float = 1.0):
        """Compone una capa de color (escalar RGB o imagen) con máscara m∈[0,1]."""
        aa = (m * a).astype(np.float32)
        col = np.asarray(color, np.float32)
        if col.ndim == 1:
            col = col[None, None, :]
        self.colp = col * aa[..., None] + self.colp * (1 - aa[..., None])
        self.alfa = aa + self.alfa * (1 - aa)

    def mascara(self) -> np.ndarray:
        return np.zeros((self.n, self.n), np.uint8)

    def reducir(self, m: np.ndarray) -> np.ndarray:
        t = 2 * self.half + 1
        return cv2.resize(m.astype(np.float32), (t, t), interpolation=cv2.INTER_AREA)


def tono(rng, v, g, b):
    """Color RGB correlacionado: brillo v (en R) y proporciones G/R y B/R (B ≤ G)."""
    vv = rng.uniform(*v)
    gg = rng.uniform(*g)
    bb = min(rng.uniform(*b), gg)
    return np.array([vv, vv * gg, vv * bb], np.float32)


def _recorte(x0, y0, h, w):
    X0, Y0 = max(x0, 0), max(y0, 0)
    X1, Y1 = min(x0 + w, S), min(y0 + h, S)
    if X1 <= X0 or Y1 <= Y0:
        return None
    return X0, Y0, X1, Y1, slice(Y0 - y0, Y1 - y0), slice(X0 - x0, X1 - x0)


def pegar(img: np.ndarray, p: Parche):
    t = 2 * p.half + 1
    colp = cv2.resize(p.colp, (t, t), interpolation=cv2.INTER_AREA)
    alfa = cv2.resize(p.alfa, (t, t), interpolation=cv2.INTER_AREA)
    r = _recorte(p.x0, p.y0, t, t)
    if r is None:
        return
    X0, Y0, X1, Y1, sy, sx = r
    reg = img[Y0:Y1, X0:X1]
    reg *= (1 - alfa[sy, sx, None])
    reg += colp[sy, sx]


def sombrear(img: np.ndarray, x0: int, y0: int, sombra: np.ndarray, fuerza: float):
    h, w = sombra.shape
    r = _recorte(x0, y0, h, w)
    if r is None:
        return
    X0, Y0, X1, Y1, sy, sx = r
    img[Y0:Y1, X0:X1] *= (1 - fuerza * sombra[sy, sx, None])


def elipse(m, centro, ejes, ang_deg, valor=255):
    """cv2.ellipse con subpíxel (shift=4) y antialias."""
    cv2.ellipse(m, (int(round(centro[0] * 16)), int(round(centro[1] * 16))),
                (max(1, int(round(ejes[0] * 16))), max(1, int(round(ejes[1] * 16)))),
                ang_deg, 0, 360, valor, -1, cv2.LINE_AA, 4)


def linea(m, p1, p2, grosor, valor=255):
    cv2.line(m, (int(round(p1[0] * 16)), int(round(p1[1] * 16))),
             (int(round(p2[0] * 16)), int(round(p2[1] * 16))), valor,
             max(1, int(round(grosor))), cv2.LINE_AA, 4)


def ruido_suave(rng, h, w, celda):
    """Ruido de baja frecuencia en [-1, 1] (interpolación bicúbica)."""
    gh, gw = max(2, h // celda + 2), max(2, w // celda + 2)
    g = rng.standard_normal((gh, gw)).astype(np.float32)
    r = cv2.resize(g, (w, h), interpolation=cv2.INTER_CUBIC)
    return r / (np.abs(r).max() + 1e-6)


# ---------------------------------------------------------------------------
# Objetos
# ---------------------------------------------------------------------------

def elipsoide(rng, cx, cy, L, W, ang, base, luz, *, k=4, p_forma=2.4,
              ks=0.3, brillo=25.0, amb=0.45, kd=0.75, sutura=True, patas=0.25,
              color_patas=None):
    """Cuerpo de escarabajo (broca u otros) con sombreado tipo cilindro.

    Devuelve (parche, mascara_cuerpo_reducida, sombra_reducida, offset_sombra).
    """
    half = int(math.ceil(L * 0.5 + 4))
    p = Parche(cx, cy, half, k)
    u, v = p.malla(ang)
    a = L / 2 * k
    b0 = W / 2 * k
    zu = u / a
    b = b0 * (1 - 0.08 * np.clip(zu, 0, 1))          # frente un poco más angosto
    zv = v / b
    r = np.abs(zu) ** p_forma + np.abs(zv) ** p_forma
    cuerpo = (r <= 1).astype(np.float32)

    # Normal aproximada (cilindro con extremos redondeados)
    z = np.sqrt(np.clip(1 - 0.35 * zu ** 2 - zv ** 2, 0.02, 1))
    nu, nv, nz = 0.45 * zu, zv, z
    nn = np.sqrt(nu ** 2 + nv ** 2 + nz ** 2)
    nu, nv, nz = nu / nn, nv / nn, nz / nn
    lx, ly, lz = luz
    c, s = math.cos(ang), math.sin(ang)
    lu, lv = lx * c + ly * s, -lx * s + ly * c
    dif = np.clip(nu * lu + nv * lv + nz * lz, 0, 1)
    hu, hv, hz = lu, lv, lz + 1.0
    hn = math.sqrt(hu * hu + hv * hv + hz * hz)
    esp = np.clip((nu * hu + nv * hv + nz * hz) / hn, 0, 1) ** brillo

    textura = 1 + 0.08 * rng.standard_normal(u.shape).astype(np.float32)
    textura = cv2.GaussianBlur(textura, (0, 0), k * 0.6)
    fact = (amb + kd * dif) * textura
    if sutura:
        fact = np.where((np.abs(zv) < 0.08) & (zu < 0.25), fact * 0.72, fact)
        fact = np.where(np.abs(zu - 0.28) < 0.035, fact * 0.8, fact)
    col = np.asarray(base, np.float32)[None, None, :] * fact[..., None] + 255.0 * ks * esp[..., None]

    # Patas (no entran en la caja)
    if rng.random() < patas:
        mp = p.mascara()
        cp = color_patas if color_patas is not None else np.asarray(base) * 0.8
        for lado in (-1, 1):
            for uu in rng.uniform(-0.3, 0.4, size=rng.integers(1, 4)):
                ang_p = rng.uniform(-0.6, 0.6)
                lp = rng.uniform(0.15, 0.3) * PX_MM * k
                p1 = p.a_parche(uu * a, lado * b0 * 0.9, ang)
                p2 = p.a_parche(uu * a + lp * math.sin(ang_p), lado * (b0 * 0.9 + lp * math.cos(ang_p)), ang)
                linea(mp, p1, p2, 0.06 * PX_MM * k)
        p.capa(mp.astype(np.float32) / 255.0, cp)

    p.capa(cuerpo, col)
    m_red = p.reducir(cuerpo)
    return p, m_red


def sombra_de(m_red: np.ndarray, luz, desplaz: float, desenf: float):
    lx, ly, _ = luz
    n = math.hypot(lx, ly) + 1e-6
    dx, dy = -lx / n * desplaz, -ly / n * desplaz
    M = np.float32([[1, 0, dx], [0, 1, dy]])
    s = cv2.warpAffine(m_red, M, (m_red.shape[1], m_red.shape[0]))
    s = cv2.GaussianBlur(s, (0, 0), desenf)
    return np.clip(s, 0, 1)


def broca(rng, cx, cy, luz, escala, estilo):
    L = rng.normal(1.7, 0.11)
    if rng.random() < 0.06:                       # macho, más pequeño (raro en trampa)
        L = rng.uniform(1.1, 1.35)
    L = float(np.clip(L, 1.15, 2.1)) * PX_MM * escala
    W = L * rng.uniform(0.43, 0.53)
    if rng.random() < 0.1:                        # recién emergida: más clara
        base = tono(rng, (75, 120), (0.6, 0.72), (0.35, 0.5))
    else:
        base = tono(rng, (18, 62), (0.7, 0.9), (0.5, 0.8))
    return elipsoide(rng, cx, cy, L, W, rng.uniform(0, 2 * math.pi), base, luz,
                     p_forma=rng.uniform(2.0, 2.8), ks=rng.uniform(0.08, 0.45) * estilo["brillo"],
                     brillo=rng.uniform(12, 40), amb=rng.uniform(0.35, 0.6),
                     kd=rng.uniform(0.5, 0.9), patas=0.3)


def escarabajo_otro(rng, cx, cy, luz, escala):
    """Otros escarabajos más grandes (2,6–4,5 mm): no son broca."""
    L = rng.uniform(2.6, 4.5) * PX_MM * escala
    W = L * rng.uniform(0.4, 0.62)
    base = tono(rng, (40, 130), (0.5, 0.8), (0.3, 0.6))
    return elipsoide(rng, cx, cy, L, W, rng.uniform(0, 2 * math.pi), base, luz, k=3,
                     p_forma=rng.uniform(2.0, 2.6), ks=rng.uniform(0.1, 0.4), patas=0.7)


def insecto_claro(rng, cx, cy, luz, escala):
    """Insectos pequeños claros (1–2,5 mm): trips, psócidos, mosquitas pálidas."""
    L = rng.uniform(1.0, 2.5) * PX_MM * escala
    W = L * rng.uniform(0.28, 0.5)
    base = tono(rng, (170, 235), (0.88, 0.97), (0.6, 0.8))
    ang = rng.uniform(0, 2 * math.pi)
    p, m = elipsoide(rng, cx, cy, L, W, ang, base, luz, p_forma=rng.uniform(1.8, 2.4),
                     ks=0.1, sutura=False, patas=0.5, color_patas=base * 0.8)
    if rng.random() < 0.5:                         # alas translúcidas
        _alas(rng, p, ang, L, W, color=(225, 225, 220), a=rng.uniform(0.25, 0.45))
    return p, m


def mosquita_oscura(rng, cx, cy, luz, escala):
    """Mosquitas oscuras con alas (1,5–2,8 mm): distractor difícil, no es broca."""
    L = rng.uniform(1.5, 2.8) * PX_MM * escala
    W = L * rng.uniform(0.3, 0.42)
    base = tono(rng, (35, 95), (0.7, 0.85), (0.55, 0.75))
    ang = rng.uniform(0, 2 * math.pi)
    p, m = elipsoide(rng, cx, cy, L, W, ang, base, luz, k=4, p_forma=2.0, ks=0.15,
                     sutura=False, patas=0.8)
    _alas(rng, p, ang, L * 1.15, W, color=(200, 200, 205), a=rng.uniform(0.3, 0.55))
    return p, m


def _alas(rng, p: Parche, ang, L, W, color, a):
    k = p.k
    abiertas = rng.uniform(10, 45)
    for lado in (-1, 1):
        mw = p.mascara()
        aa = ang + lado * math.radians(abiertas)
        cen = p.a_parche(-0.15 * L * k - 0.25 * L * k * math.cos(math.radians(abiertas)),
                         lado * 0.3 * L * k * math.sin(math.radians(abiertas)), ang)
        elipse(mw, cen, (0.42 * L * k, 0.16 * L * k), math.degrees(aa + math.pi))
        mf = mw.astype(np.float32) / 255.0
        p.capa(mf, color, a)
        borde = cv2.morphologyEx(mw, cv2.MORPH_GRADIENT, np.ones((3, 3), np.uint8))
        p.capa(borde.astype(np.float32) / 255.0, (90, 90, 95), a * 0.8)


def mosca(rng, cx, cy, luz, escala):
    """Mosca de 4–6 mm: cabeza, tórax, abdomen, alas y patas. No es broca."""
    k = 2
    L = rng.uniform(4.0, 6.0) * PX_MM * escala
    half = int(math.ceil(L * 0.75 + 3))
    p = Parche(cx, cy, half, k)
    ang = rng.uniform(0, 2 * math.pi)
    Lk = L * k
    base = tono(rng, (20, 80), (0.9, 1.0), (0.85, 1.0))
    # patas
    mp = p.mascara()
    for lado in (-1, 1):
        for uu in (0.15, 0.05, -0.05):
            a1 = rng.uniform(0.3, 1.2)
            lp = rng.uniform(0.25, 0.4) * Lk
            p1 = p.a_parche(uu * Lk, lado * 0.08 * Lk, ang)
            p2 = p.a_parche(uu * Lk + lp * math.sin(a1 - 0.6), lado * (0.08 * Lk + lp * math.cos(a1)), ang)
            linea(mp, p1, p2, 0.025 * Lk)
    p.capa(mp / 255.0, base * 0.7)
    # abdomen, tórax, cabeza
    for (uu, la, an, fac) in ((-0.2, 0.25, 0.17, 1.0), (0.08, 0.15, 0.14, 0.85), (0.28, 0.08, 0.11, 0.9)):
        m = p.mascara()
        elipse(m, p.a_parche(uu * Lk, 0, ang), (la * Lk, an * Lk), math.degrees(ang))
        sh = 0.8 + 0.4 * rng.random()
        p.capa(m / 255.0, np.clip(base * fac * sh, 0, 255))
    if rng.random() < 0.6:                         # ojos rojizos
        for lado in (-1, 1):
            m = p.mascara()
            elipse(m, p.a_parche(0.3 * Lk, lado * 0.07 * Lk, ang), (0.05 * Lk, 0.04 * Lk), math.degrees(ang))
            p.capa(m / 255.0, (120, 40, 30))
    _alas(rng, p, ang, L, L * 0.3, color=(190, 190, 195), a=rng.uniform(0.25, 0.5))
    # máscara aproximada del cuerpo para ocupación
    m = p.mascara()
    elipse(m, p.a_parche(0, 0, ang), (0.42 * Lk, 0.16 * Lk), math.degrees(ang))
    return p, p.reducir(m / 255.0)


def granito_cafe(rng, img, cx, cy, escala, *, dificil=False):
    """Granito de café tostado molido: polígono irregular oscuro, 0,2–1,1 mm."""
    k = 4
    if dificil:
        # Largo físico 1–1,5 mm; bordes quebrados y textura, sin patas ni sutura.
        largo = rng.uniform(1.0, 1.5) * PX_MM * escala
        ancho = largo * rng.uniform(0.35, 0.6)
        p = Parche(cx, cy, int(math.ceil(largo / 2 + 3)), k)
        rot = rng.uniform(0, 2 * math.pi)
        angs = np.linspace(0, 2 * math.pi, 12, endpoint=False)
        pts = [p.a_parche(largo / 2 * k * math.cos(t) * rng.uniform(0.85, 1),
                          ancho / 2 * k * math.sin(t) * rng.uniform(0.7, 1), rot)
               for t in angs]
        m = p.mascara()
        cv2.fillPoly(m, [np.int32(np.round(np.array(pts) * 16))], 255, cv2.LINE_AA, 4)
        base = tono(rng, (20, 95), (0.6, 0.85), (0.4, 0.7))
        tex = 1 + 0.25 * ruido_suave(rng, p.n, p.n, 4)
        p.capa(m.astype(np.float32) / 255, base[None, None, :] * tex[..., None])
        pegar(img, p)
        return
    d = float(np.clip(rng.lognormal(math.log(0.45), 0.45), 0.15, 1.1)) * PX_MM * escala
    half = int(math.ceil(d * 0.9 + 2))
    p = Parche(cx, cy, half, k)
    nv = rng.integers(5, 10)
    angs = np.sort(rng.uniform(0, 2 * math.pi, nv))
    alarg = rng.uniform(1.0, 1.9)
    rot = rng.uniform(0, 2 * math.pi)
    radios = d / 2 * k * rng.uniform(0.55, 1.25, nv)
    pts = []
    for t, rr in zip(angs, radios):
        x, y = rr * math.cos(t) * alarg ** 0.5, rr * math.sin(t) / alarg ** 0.5
        pts.append(p.a_parche(x, y, rot))
    m = p.mascara()
    cv2.fillPoly(m, [np.int32(np.round(np.array(pts) * 16))], 255, cv2.LINE_AA, 4)
    base = tono(rng, (35, 105), (0.6, 0.75), (0.4, 0.55))
    mf = m / 255.0
    tex = 1 + 0.15 * rng.standard_normal(mf.shape).astype(np.float32)
    p.capa(mf, base[None, None, :] * tex[..., None])
    pegar(img, p)


def resto_vegetal(rng, img, cx, cy, escala):
    """Fibra o trocito de hoja/cáscara: marrón claro, verdoso o pajizo."""
    k = 2
    if rng.random() < 0.6:                         # fibra
        Lmm = rng.uniform(1.0, 8.0)
        L = Lmm * PX_MM * escala
        half = int(math.ceil(L * 0.6 + 4))
        p = Parche(cx, cy, half, k)
        m = p.mascara()
        nseg = rng.integers(1, 4)
        ang = rng.uniform(0, 2 * math.pi)
        pos = (-L / 2 * k, 0.0)
        grosor = rng.uniform(0.15, 0.6) * PX_MM * escala * k
        for _ in range(nseg):
            ang += rng.uniform(-0.5, 0.5)
            seg = L * k / nseg
            nuevo = (pos[0] + seg * math.cos(ang), pos[1] + seg * math.sin(ang))
            linea(m, p.a_parche(*pos, 0), p.a_parche(*nuevo, 0), grosor)
            pos = nuevo
    else:                                          # trocito de hoja / cáscara
        Lmm = rng.uniform(1.5, 6.0)
        L = Lmm * PX_MM * escala
        half = int(math.ceil(L * 0.7 + 4))
        p = Parche(cx, cy, half, k)
        m = p.mascara()
        nv = rng.integers(4, 9)
        angs = np.sort(rng.uniform(0, 2 * math.pi, nv))
        pts = [p.a_parche(L / 2 * k * rng.uniform(0.4, 1.0) * math.cos(t),
                          L / 2 * k * rng.uniform(0.3, 0.8) * math.sin(t), 0) for t in angs]
        cv2.fillPoly(m, [np.int32(np.round(np.array(pts) * 16))], 255, cv2.LINE_AA, 4)
    tipo = rng.integers(0, 3)
    if tipo == 0:
        base = tono(rng, (120, 195), (0.75, 0.82), (0.5, 0.6))   # marrón claro / pajizo
    elif tipo == 1:
        v = rng.uniform(95, 160)                                  # verdoso
        base = np.array([v * rng.uniform(0.75, 0.9), v, v * rng.uniform(0.5, 0.6)], np.float32)
    else:
        base = tono(rng, (70, 130), (0.65, 0.72), (0.4, 0.5))    # marrón medio
    mf = m / 255.0
    tex = 1 + 0.12 * ruido_suave(rng, mf.shape[0], mf.shape[1], 6)
    p.capa(mf, base[None, None, :] * tex[..., None], rng.uniform(0.75, 1.0))
    pegar(img, p)


# ---------------------------------------------------------------------------
# Fondo y fotometría
# ---------------------------------------------------------------------------

def fondo(rng) -> np.ndarray:
    v, w = rng.uniform(225, 252), rng.uniform(0, 1)               # brillo y calidez del papel
    papel = np.array([v, v * (0.985 - 0.02 * w), v * (0.97 - 0.08 * w + rng.uniform(-0.01, 0.02))], np.float32)
    img = np.empty((S, S, 3), np.float32)
    img[:] = papel
    baja = ruido_suave(rng, S, S, int(rng.integers(60, 200)))
    img *= (1 + rng.uniform(0.005, 0.03) * baja)[..., None]
    fibra = cv2.GaussianBlur(rng.standard_normal((S, S)).astype(np.float32), (0, 0), rng.uniform(0.6, 1.5))
    img += (rng.uniform(1.0, 5.0) * fibra / (fibra.std() + 1e-6))[..., None]
    return img


def manchas_agua(rng, img):
    """Manchas de agua/café: zonas ligeramente amarillentas con borde más oscuro."""
    for _ in range(rng.integers(0, 5)):
        R = rng.uniform(30, 320)
        cx, cy = rng.uniform(-0.1 * S, 1.1 * S, 2)
        h = int(2 * R * 1.4)
        x0, y0 = int(cx - h / 2), int(cy - h / 2)
        yy, xx = np.mgrid[0:h, 0:h].astype(np.float32)
        dist = np.hypot(xx - h / 2, yy - h / 2) / R
        dist += 0.35 * ruido_suave(rng, h, h, max(4, int(R / 3)))
        m = (dist < 1).astype(np.float32)
        m = cv2.GaussianBlur(m, (0, 0), rng.uniform(1.0, 4.0))
        borde = cv2.GaussianBlur(np.clip(m * (1 - m) * 4, 0, 1), (0, 0), 1.5)
        tinte = np.array([rng.uniform(0.0, 0.04), rng.uniform(0.02, 0.07), rng.uniform(0.05, 0.16)], np.float32)
        fuerza = rng.uniform(0.3, 1.0)
        efecto = 1 - fuerza * (m[..., None] * tinte + borde[..., None] * (tinte * 1.8 + 0.04))
        r = _recorte(x0, y0, h, h)
        if r is None:
            continue
        X0, Y0, X1, Y1, sy, sx = r
        img[Y0:Y1, X0:X1] *= efecto[sy, sx]


def arrugas(rng) -> np.ndarray:
    """Mapa multiplicativo de arrugas/pliegues leves."""
    altura = np.zeros((S, S), np.float32)
    for _ in range(rng.integers(0, 4)):
        p = rng.uniform(0, S, 2)
        ang = rng.uniform(0, math.pi)
        pts = []
        for t in np.linspace(-1, 1, 6):
            pts.append(p + t * S * np.array([math.cos(ang), math.sin(ang)]) + rng.normal(0, 25, 2))
        cv2.polylines(altura, [np.int32(pts)], False, 1.0, int(rng.integers(2, 8)), cv2.LINE_AA)
    if not altura.any():
        return np.ones((S, S), np.float32)
    altura = cv2.GaussianBlur(altura, (0, 0), rng.uniform(2, 8))
    gx = cv2.Sobel(altura, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(altura, cv2.CV_32F, 0, 1, ksize=3)
    a = rng.uniform(0, 2 * math.pi)
    sh = gx * math.cos(a) + gy * math.sin(a)
    sh /= (np.abs(sh).max() + 1e-6)
    return 1 + rng.uniform(0.02, 0.07) * sh


def borde_marco(rng, img):
    """Línea gris del marco y astillas de esquinas negras (error de homografía)."""
    if rng.random() < 0.6:
        gris = rng.uniform(165, 215)
        g = int(rng.integers(3, 8))
        for lado in range(4):
            off = int(rng.integers(-4, 7))
            if lado == 0:
                img[max(0, off - g // 2):max(0, off + g // 2 + 1), :] = gris
            elif lado == 1:
                img[S - max(1, off + g // 2 + 1):S - max(0, off - g // 2), :] = gris
            elif lado == 2:
                img[:, max(0, off - g // 2):max(0, off + g // 2 + 1)] = gris
            else:
                img[:, S - max(1, off + g // 2 + 1):S - max(0, off - g // 2)] = gris
    if rng.random() < 0.3:
        for (ex, ey) in ((0, 0), (S, 0), (0, S), (S, S)):
            if rng.random() < 0.5:
                t = rng.uniform(2, 10)
                pts = np.int32([[ex, ey], [ex + (t if ex == 0 else -t), ey], [ex, ey + (t if ey == 0 else -t)]])
                cv2.fillPoly(img, [pts], (20, 20, 20))


def iluminacion(rng, extra: np.ndarray) -> np.ndarray:
    yy, xx = np.mgrid[0:S, 0:S].astype(np.float32) / S - 0.5
    a = rng.uniform(0, 2 * math.pi)
    g = 1 + rng.uniform(0, 0.35) * (xx * math.cos(a) + yy * math.sin(a))
    g *= 1 - rng.uniform(0, 0.25) * (xx ** 2 + yy ** 2) * 2
    g *= rng.uniform(0.6, 1.05)
    for _ in range(rng.integers(0, 3)):            # sombras suaves (mano, teléfono)
        m = np.zeros((S, S), np.float32)
        c = rng.uniform(-0.2 * S, 1.2 * S, 2)
        pts = np.int32(c + rng.normal(0, rng.uniform(150, 500), (5, 2)))
        cv2.fillPoly(m, [cv2.convexHull(pts)], 1.0)
        m = cv2.GaussianBlur(m, (0, 0), rng.uniform(15, 80))
        g *= 1 - rng.uniform(0.1, 0.45) * m
    return g * extra


def fotometria(rng, img: np.ndarray) -> np.ndarray:
    tinte = np.array([1 + rng.normal(0, 0.04), 1.0, 1 + rng.normal(0, 0.05)], np.float32)
    img *= tinte
    gamma = rng.uniform(0.85, 1.2)
    img = 255.0 * np.clip(img / 255.0, 0, 1) ** gamma
    if rng.random() < 0.5:                         # pérdida de resolución (cámara/homografía)
        f = rng.uniform(0.5, 0.95)
        t = int(S * f)
        img = cv2.resize(cv2.resize(img, (t, t), interpolation=cv2.INTER_AREA), (S, S),
                         interpolation=cv2.INTER_LINEAR)
    r = rng.random()
    if r < 0.55:
        img = cv2.GaussianBlur(img, (0, 0), rng.uniform(0.3, 1.3))
    elif r < 0.7:                                  # movimiento
        ln = int(rng.integers(3, 6))
        kern = np.zeros((ln, ln), np.float32)
        kern[ln // 2, :] = 1.0 / ln
        M = cv2.getRotationMatrix2D((ln / 2 - 0.5, ln / 2 - 0.5), rng.uniform(0, 180), 1)
        kern = cv2.warpAffine(kern, M, (ln, ln))
        kern /= kern.sum() + 1e-6
        img = cv2.filter2D(img, -1, kern)
    img += rng.normal(0, rng.uniform(1.0, 6.0), img.shape).astype(np.float32)
    return np.clip(img, 0, 255).astype(np.uint8)


# ---------------------------------------------------------------------------
# Marco completo
# ---------------------------------------------------------------------------

def muestrear_n(rng, densidad: str) -> int:
    if densidad == "0":
        return 0
    if densidad == "1-49":
        return int(rng.integers(1, 50))
    if densidad == "50-300":
        return int(rng.integers(50, 301))
    return int(rng.integers(301, 651))


def posicion(rng, grupos, p_grupo, margen=-6):
    if grupos and rng.random() < p_grupo:
        cx, cy, sig = grupos[rng.integers(len(grupos))]
        x, y = rng.normal(cx, sig), rng.normal(cy, sig)
    else:
        x, y = rng.uniform(margen, S - margen, 2)
    return float(np.clip(x, margen, S - margen)), float(np.clip(y, margen, S - margen))


def colocar(rng, img, ocupado, crear, grupos, p_grupo, max_solape, intentos=15):
    """Intenta colocar un insecto sin solaparlo más de `max_solape` con otros."""
    for _ in range(intentos):
        cx, cy = posicion(rng, grupos, p_grupo)
        p, m = crear(cx, cy)
        cuerpo = m > 0.5
        area = cuerpo.sum()
        if area == 0:
            return None
        t = m.shape[0]
        r = _recorte(p.x0, p.y0, t, t)
        if r is None:
            continue
        X0, Y0, X1, Y1, sy, sx = r
        c = cuerpo[sy, sx]
        if (ocupado[Y0:Y1, X0:X1] & c).sum() > max_solape * area:
            continue
        ocupado[Y0:Y1, X0:X1] |= c
        return p, m
    return None


def generar_marco(semilla: int, densidad: str):
    """Devuelve (imagen uint8 RGB 1216×1216, cajas [x0,y0,x1,y1] en px del marco, info)."""
    rng = np.random.default_rng(semilla)
    img = fondo(rng)
    manchas_agua(rng, img)
    escala = rng.uniform(0.9, 1.1)                 # error de escala de la homografía/impresión
    el = math.radians(rng.uniform(35, 75))
    az = rng.uniform(0, 2 * math.pi)
    luz = (math.cos(el) * math.cos(az), math.cos(el) * math.sin(az), math.sin(el))
    estilo = {"brillo": rng.uniform(0.4, 1.3)}

    n_broca = muestrear_n(rng, densidad)
    # Grupos (el líquido se acumula y los insectos quedan amontonados)
    grupos = [(rng.uniform(80, S - 80), rng.uniform(80, S - 80), rng.uniform(25, 180))
              for _ in range(rng.integers(1, 7))]
    p_grupo = rng.uniform(0, 0.8)
    max_solape = rng.uniform(0.1, 0.35)

    # Fondo de restos: café molido y restos vegetales (debajo de los insectos)
    n_cafe = 0 if rng.random() < 0.3 else int(rng.integers(5, 350))
    n_veg = int(rng.integers(0, 30))
    for _ in range(n_cafe):
        x, y = posicion(rng, grupos, 0.4)
        granito_cafe(rng, img, x, y, escala)
    # También en marcos vacíos: aprender a rechazar café sin depender de brocas.
    n_cafe_dificil = int(rng.integers(15, 81)) if rng.random() < 0.85 else 0
    for _ in range(n_cafe_dificil):
        x, y = posicion(rng, grupos, 0.4)
        granito_cafe(rng, img, x, y, escala, dificil=True)
    for _ in range(n_veg):
        x, y = posicion(rng, grupos, 0.3)
        resto_vegetal(rng, img, x, y, escala)

    ocupado = np.zeros((S, S), bool)
    # Distractores insectos: 7–22 % de lo capturado + algunos fijos
    frac = rng.uniform(0.07, 0.22)
    n_otros = int(round(n_broca * frac / (1 - frac))) + int(rng.poisson(8.0))
    tipos = {"mosca": 0, "mosquita": 0, "claro": 0, "escarabajo": 0}
    for _ in range(n_otros):
        t = rng.choice(["mosca", "mosquita", "claro", "escarabajo"], p=[0.15, 0.55, 0.2, 0.1])
        crear = {
            "mosca": lambda x, y: mosca(rng, x, y, luz, escala),
            "mosquita": lambda x, y: mosquita_oscura(rng, x, y, luz, escala),
            "claro": lambda x, y: insecto_claro(rng, x, y, luz, escala),
            "escarabajo": lambda x, y: escarabajo_otro(rng, x, y, luz, escala),
        }[t]
        r = colocar(rng, img, ocupado, crear, grupos, p_grupo * 0.5, 0.2)
        if r is None:
            continue
        p, m = r
        sombrear(img, p.x0, p.y0, sombra_de(m, luz, 1.5, 1.5), rng.uniform(0.15, 0.4))
        pegar(img, p)
        tipos[t] += 1

    cajas = []
    for _ in range(n_broca):
        r = colocar(rng, img, ocupado, lambda x, y: broca(rng, x, y, luz, escala, estilo),
                    grupos, p_grupo, max_solape)
        if r is None:
            continue
        p, m = r
        sombrear(img, p.x0, p.y0, sombra_de(m, luz, rng.uniform(0.8, 2.0), rng.uniform(0.8, 1.6)),
                 rng.uniform(0.15, 0.45))
        pegar(img, p)
        ys, xs = np.nonzero(m > 0.35)
        bx0, by0 = p.x0 + xs.min(), p.y0 + ys.min()
        bx1, by1 = p.x0 + xs.max() + 1, p.y0 + ys.max() + 1
        # visible en el marco al menos al 50 %
        cx0, cy0, cx1, cy1 = max(bx0, 0), max(by0, 0), min(bx1, S), min(by1, S)
        if cx1 <= cx0 or cy1 <= cy0:
            continue
        if (cx1 - cx0) * (cy1 - cy0) < 0.5 * (bx1 - bx0) * (by1 - by0):
            continue
        cajas.append([float(cx0), float(cy0), float(cx1), float(cy1)])

    borde_marco(rng, img)
    img *= iluminacion(rng, arrugas(rng))[..., None]
    img = fotometria(rng, img)
    calidad = int(rng.integers(35, 96))
    ok, buf = cv2.imencode(".jpg", cv2.cvtColor(img, cv2.COLOR_RGB2BGR), [cv2.IMWRITE_JPEG_QUALITY, calidad])
    img = cv2.cvtColor(cv2.imdecode(buf, cv2.IMREAD_COLOR), cv2.COLOR_BGR2RGB)
    info = {"conteo": len(cajas), "densidad": densidad_de(len(cajas)), "densidad_pedida": densidad,
            "cafe": n_cafe, "cafe_alargado_dificil": n_cafe_dificil,
            "generador": "sint_dificiles_v1", "vegetal": n_veg, "otros_insectos": tipos, "jpeg": calidad,
            "escala": round(float(escala), 3)}
    return img, cajas, info


# ---------------------------------------------------------------------------
# Mosaicos y escritura
# ---------------------------------------------------------------------------

def cajas_en_mosaico(cajas, ox, oy):
    """Recorta las cajas al mosaico; descarta las que dejan <50 % de su área fuera."""
    out = []
    for x0, y0, x1, y1 in cajas:
        ix0, iy0 = max(x0, ox), max(y0, oy)
        ix1, iy1 = min(x1, ox + TILE), min(y1, oy + TILE)
        if ix1 <= ix0 or iy1 <= iy0:
            continue
        if (ix1 - ix0) * (iy1 - iy0) < 0.5 * (x1 - x0) * (y1 - y0):
            continue
        out.append([ix0 - ox, iy0 - oy, ix1 - ox, iy1 - oy])
    return out


def yolo_txt(cajas, lado):
    lineas = []
    for x0, y0, x1, y1 in cajas:
        lineas.append(f"0 {(x0 + x1) / 2 / lado:.6f} {(y0 + y1) / 2 / lado:.6f} "
                      f"{(x1 - x0) / lado:.6f} {(y1 - y0) / lado:.6f}")
    return "\n".join(lineas) + ("\n" if lineas else "")


def _trabajo(args):
    salida, split, nombre, semilla, densidad = args
    img, cajas, info = generar_marco(semilla, densidad)
    base = Path(salida)
    bgr = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
    cv2.imwrite(str(base / "marcos" / split / "images" / f"{nombre}.jpg"), bgr, [cv2.IMWRITE_JPEG_QUALITY, 97])
    (base / "marcos" / split / "labels" / f"{nombre}.txt").write_text(yolo_txt(cajas, S))
    for oy in ORIGENES:
        for ox in ORIGENES:
            t = f"{nombre}_x{ox}_y{oy}"
            cv2.imwrite(str(base / "mosaicos" / split / "images" / f"{t}.jpg"),
                        bgr[oy:oy + TILE, ox:ox + TILE], [cv2.IMWRITE_JPEG_QUALITY, 97])
            (base / "mosaicos" / split / "labels" / f"{t}.txt").write_text(
                yolo_txt(cajas_en_mosaico(cajas, ox, oy), TILE))
    return nombre, info


def plan_split(rng, n, estratificado):
    if estratificado:                              # val/test: 10 % ceros, resto en partes iguales
        n0 = max(1, round(n * 0.1))
        resto = n - n0
        ds = ["0"] * n0 + [["1-49", "50-300", ">300"][i % 3] for i in range(resto)]
    else:
        ds = list(rng.choice(DENSIDADES, size=n, p=[0.08, 0.32, 0.35, 0.25]))
    return ds


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--salida", default=str(Path(__file__).parent / "datasets" / "sint_v0"))
    ap.add_argument("--train", type=int, default=400)
    ap.add_argument("--val", type=int, default=60)
    ap.add_argument("--test", type=int, default=60)
    ap.add_argument("--semilla", type=int, default=20261003)
    ap.add_argument("--workers", type=int, default=max(1, (os.cpu_count() or 2) - 1))
    ap.add_argument("--vista", type=int, default=0, help="solo genera N ejemplos con cajas dibujadas")
    a = ap.parse_args()

    if a.vista:
        out = Path(__file__).parent / "datasets" / "vista"
        out.mkdir(parents=True, exist_ok=True)
        for i in range(a.vista):
            d = DENSIDADES[i % 4]
            t = time.time()
            img, cajas, info = generar_marco(a.semilla + 1000 + i, d)
            v = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
            cv2.imwrite(str(out / f"vista_{i}_{d.replace('>', 'mas')}.jpg"), v)
            for x0, y0, x1, y1 in cajas:
                cv2.rectangle(v, (int(x0), int(y0)), (int(x1), int(y1)), (0, 0, 255), 1)
            cv2.imwrite(str(out / f"vista_{i}_{d.replace('>', 'mas')}_cajas.jpg"), v)
            print(f"{i} densidad={d} conteo={len(cajas)} {time.time() - t:.2f}s {info}")
        return

    base = Path(a.salida)
    rng = np.random.default_rng(a.semilla)
    tareas = []
    for split, n, estrat, off in (("train", a.train, False, 0), ("val", a.val, True, 10 ** 6),
                                  ("test", a.test, True, 2 * 10 ** 6)):
        for sub in ("marcos", "mosaicos"):
            for d in ("images", "labels"):
                (base / sub / split / d).mkdir(parents=True, exist_ok=True)
        for i, dens in enumerate(plan_split(rng, n, estrat)):
            tareas.append((str(base), split, f"sint_{split}_{i:04d}", a.semilla + off + i, str(dens)))

    t0 = time.time()
    res = {"train": {}, "val": {}, "test": {}}
    with Pool(a.workers) as pool:
        for j, (nombre, info) in enumerate(pool.imap_unordered(_trabajo, tareas, chunksize=2)):
            res[nombre.split("_")[1]][nombre] = info
            if (j + 1) % 50 == 0:
                print(f"{j + 1}/{len(tareas)} marcos  {time.time() - t0:.0f}s", flush=True)

    for split, d in res.items():
        d = dict(sorted(d.items()))
        (base / "marcos" / split / "conteos.json").write_text(json.dumps(
            {"sintetico": True, "nota": "Datos SINTÉTICOS generados por ml/sintetico.py; no son fotos reales.",
             "marcos": d}, ensure_ascii=False, indent=1), encoding="utf-8")
    (base / "data.yaml").write_text(
        "# Datos SINTÉTICOS (ml/sintetico.py). Entrenamiento con mosaicos 640x640.\n"
        f"path: {base.resolve().as_posix()}\n"
        "train: mosaicos/train/images\nval: mosaicos/val/images\nnames:\n  0: broca\n", encoding="utf-8")
    (base / "LEEME_SINTETICO.txt").write_text(
        "TODOS los datos de esta carpeta son SINTÉTICOS (ml/sintetico.py).\n"
        "No son fotos reales de broca ni de gorgojos. El error medido aquí NO es desempeño en broca real.\n",
        encoding="utf-8")
    tot = {s: sum(v["conteo"] for v in d.values()) for s, d in res.items()}
    print(f"Listo en {time.time() - t0:.0f}s. Marcos: { {s: len(d) for s, d in res.items()} }  brocas: {tot}")


if __name__ == "__main__":
    main()
