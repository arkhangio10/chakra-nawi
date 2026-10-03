// Posprocesado de contracts/modelo-io.md: puntaje ≥ 0,25 → coordenadas del marco → NMS global IoU 0,45.

import { FRACCION_DUDOSA, LADO_MARCO, UMBRAL_NMS, UMBRAL_SCORE, UMBRAL_SEGURO, type Caja } from './tipos';

/** Salida `output0` [1, 5, 8400] de un mosaico → cajas en coordenadas del marco. */
export function decodificar(salida: Float32Array, ox: number, oy: number, umbral = UMBRAL_SCORE): Caja[] {
  const n = salida.length / 5;
  const cajas: Caja[] = [];
  for (let i = 0; i < n; i++) {
    const score = salida[4 * n + i];
    if (score < umbral) continue;
    cajas.push({ cx: salida[i] + ox, cy: salida[n + i] + oy, w: salida[2 * n + i], h: salida[3 * n + i], score });
  }
  return cajas;
}

export function iou(a: Caja, b: Caja): number {
  const ix = Math.max(0, Math.min(a.cx + a.w / 2, b.cx + b.w / 2) - Math.max(a.cx - a.w / 2, b.cx - b.w / 2));
  const iy = Math.max(0, Math.min(a.cy + a.h / 2, b.cy + b.h / 2) - Math.max(a.cy - a.h / 2, b.cy - b.h / 2));
  const inter = ix * iy;
  return inter / (a.w * a.h + b.w * b.h - inter || 1);
}

export function nms(cajas: Caja[], umbral = UMBRAL_NMS): Caja[] {
  const orden = [...cajas].sort((a, b) => b.score - a.score);
  const quedan: Caja[] = [];
  for (const c of orden) if (quedan.every((q) => iou(c, q) <= umbral)) quedan.push(c);
  return quedan;
}

/** Formato de caso.conteo.cajas: [xc, yc, w, h] normalizado a 0–1 sobre el marco de 1216 px. */
export function normalizar(c: Caja): [number, number, number, number] {
  const r = (v: number) => Math.min(1, Math.max(0, Math.round((v / LADO_MARCO) * 1e4) / 1e4));
  return [r(c.cx), r(c.cy), r(c.w), r(c.h)];
}

/** PLAN §2: dudoso si más del 30 % de las detecciones quedan entre 0,25 y 0,45. */
export function esDudoso(cajas: Caja[]): boolean {
  if (cajas.length === 0) return false;
  return cajas.filter((c) => c.score < UMBRAL_SEGURO).length / cajas.length > FRACCION_DUDOSA;
}
