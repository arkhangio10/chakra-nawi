// Detección de las 4 esquinas negras de la tarjeta A5 (docs/tarjeta/README.md).
// Cada esquina es un cuadrado negro de 10×10 mm por FUERA del marco de 100×100 mm; el vértice del
// cuadrado que toca el marco es la esquina del marco. Ese vértice es el píxel del cuadrado más
// cercano al centro de los cuatro cuadrados.

import type { Punto } from './tipos';

interface Componente {
  etiqueta: number;
  area: number;
  minX: number; maxX: number; minY: number; maxY: number;
  cx: number; cy: number;
}

function mediana(gris: Uint8Array): number {
  const hist = new Uint32Array(256);
  for (let i = 0; i < gris.length; i++) hist[gris[i]]++;
  let acc = 0;
  for (let v = 0; v < 256; v++) if ((acc += hist[v]) >= gris.length / 2) return v;
  return 128;
}

/** Componentes conexas (4-vecindad) de los píxeles oscuros. */
function componentes(oscuro: Uint8Array, w: number, h: number) {
  const etiquetas = new Int32Array(w * h);
  const cola = new Int32Array(w * h);
  const lista: Componente[] = [];
  let siguiente = 0;
  for (let inicio = 0; inicio < oscuro.length; inicio++) {
    if (!oscuro[inicio] || etiquetas[inicio]) continue;
    const et = ++siguiente;
    let cabeza = 0, cola_n = 0;
    cola[cola_n++] = inicio;
    etiquetas[inicio] = et;
    const c: Componente = { etiqueta: et, area: 0, minX: w, maxX: 0, minY: h, maxY: 0, cx: 0, cy: 0 };
    while (cabeza < cola_n) {
      const p = cola[cabeza++];
      const x = p % w, y = (p - x) / w;
      c.area++; c.cx += x; c.cy += y;
      if (x < c.minX) c.minX = x; if (x > c.maxX) c.maxX = x;
      if (y < c.minY) c.minY = y; if (y > c.maxY) c.maxY = y;
      if (x > 0 && oscuro[p - 1] && !etiquetas[p - 1]) { etiquetas[p - 1] = et; cola[cola_n++] = p - 1; }
      if (x < w - 1 && oscuro[p + 1] && !etiquetas[p + 1]) { etiquetas[p + 1] = et; cola[cola_n++] = p + 1; }
      if (y > 0 && oscuro[p - w] && !etiquetas[p - w]) { etiquetas[p - w] = et; cola[cola_n++] = p - w; }
      if (y < h - 1 && oscuro[p + w] && !etiquetas[p + w]) { etiquetas[p + w] = et; cola[cola_n++] = p + w; }
    }
    c.cx /= c.area; c.cy /= c.area;
    lista.push(c);
  }
  return { etiquetas, lista };
}

function areaPoligono(p: Punto[]): number {
  let a = 0;
  for (let i = 0; i < p.length; i++) { const q = p[(i + 1) % p.length]; a += p[i].x * q.y - q.x * p[i].y; }
  return Math.abs(a) / 2;
}

/** Ordena 4 puntos como arriba-izquierda, arriba-derecha, abajo-derecha, abajo-izquierda (y hacia abajo). */
export function ordenar(p: Punto[]): [Punto, Punto, Punto, Punto] {
  const cx = p.reduce((a, q) => a + q.x, 0) / 4, cy = p.reduce((a, q) => a + q.y, 0) / 4;
  const porAngulo = [...p].sort((a, b) => Math.atan2(a.y - cy, a.x - cx) - Math.atan2(b.y - cy, b.x - cx));
  let k = 0;
  for (let i = 1; i < 4; i++) if (porAngulo[i].x + porAngulo[i].y < porAngulo[k].x + porAngulo[k].y) k = i;
  return [0, 1, 2, 3].map((i) => porAngulo[(k + i) % 4]) as [Punto, Punto, Punto, Punto];
}

/**
 * Busca las 4 esquinas del marco en una imagen en gris (idealmente ~1000 px de lado).
 * Devuelve [arriba-izq, arriba-der, abajo-der, abajo-izq] en coordenadas de esa imagen, o null.
 */
export function detectarEsquinas(gris: Uint8Array, w: number, h: number): [Punto, Punto, Punto, Punto] | null {
  const umbral = Math.min(90, mediana(gris) * 0.45);
  const oscuro = new Uint8Array(gris.length);
  for (let i = 0; i < gris.length; i++) oscuro[i] = gris[i] < umbral ? 1 : 0;
  const { etiquetas, lista } = componentes(oscuro, w, h);

  const total = w * h;
  const candidatos = lista
    .filter((c) => {
      const bw = c.maxX - c.minX + 1, bh = c.maxY - c.minY + 1;
      const aspecto = bw / bh, relleno = c.area / (bw * bh);
      return c.area > total * 0.0002 && c.area < total * 0.03 && aspecto > 0.5 && aspecto < 2 && relleno > 0.5;
    })
    .sort((a, b) => b.area - a.area)
    .slice(0, 8);
  if (candidatos.length < 4) return null;

  // De los mejores candidatos, el grupo de 4 con áreas parecidas que forme el cuadrilátero más grande.
  let mejor: Componente[] | null = null, mejorArea = 0;
  const n = candidatos.length;
  for (let a = 0; a < n; a++) for (let b = a + 1; b < n; b++) for (let c = b + 1; c < n; c++) for (let d = c + 1; d < n; d++) {
    const g = [candidatos[a], candidatos[b], candidatos[c], candidatos[d]];
    const areas = g.map((x) => x.area);
    if (Math.max(...areas) / Math.min(...areas) > 4) continue;
    const area = areaPoligono(ordenar(g.map((x) => ({ x: x.cx, y: x.cy }))));
    if (area > mejorArea) { mejorArea = area; mejor = g; }
  }
  if (!mejor || mejorArea < total * 0.05) return null;

  // Vértice interior de cada cuadrado = su píxel más cercano al centro del grupo.
  const centro = { x: mejor.reduce((s, c) => s + c.cx, 0) / 4, y: mejor.reduce((s, c) => s + c.cy, 0) / 4 };
  const vertices = mejor.map((c) => {
    let bx = c.cx, by = c.cy, bd = Infinity;
    for (let y = c.minY; y <= c.maxY; y++) for (let x = c.minX; x <= c.maxX; x++) {
      if (etiquetas[y * w + x] !== c.etiqueta) continue;
      const d = (x - centro.x) ** 2 + (y - centro.y) ** 2;
      if (d < bd) { bd = d; bx = x; by = y; }
    }
    return { x: bx + 0.5, y: by + 0.5 };
  });
  return ordenar(vertices);
}
