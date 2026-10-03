/** Imagen RGBA mínima (compatible con ImageData) para que la visión se pruebe sin navegador. */
export interface Img {
  data: Uint8ClampedArray;
  width: number;
  height: number;
}

export interface Punto {
  x: number;
  y: number;
}

/** Caja en píxeles del marco rectificado (1216×1216). */
export interface Caja {
  cx: number;
  cy: number;
  w: number;
  h: number;
  score: number;
}

/** Geometría congelada en contracts/modelo-io.md. */
export const LADO_MARCO = 1216;
export const LADO_MOSAICO = 640;
export const ORIGENES_MOSAICO = [0, 576] as const;
/** Candidatas: todo lo que supera 0,25 entra al NMS. */
export const UMBRAL_SCORE = 0.25;
export const UMBRAL_NMS = 0.45;
/**
 * Solo cuentan las cajas con puntaje ≥ 0,60 (propuesta de P2 elegida en validación: con 0,25 el modelo
 * sintético sobrecuenta granitos de café; MAE 21,3 → 4,9). Ver contracts/modelo-io.md.
 */
export const UMBRAL_CONTEO = 0.6;
/** PLAN §2: dudoso si más del 30 % de las candidatas queda en la banda débil [0,25; 0,60). */
export const FRACCION_DUDOSA = 0.3;

export function aGris(img: Img): Uint8Array {
  const n = img.width * img.height;
  const g = new Uint8Array(n);
  const d = img.data;
  for (let i = 0, j = 0; i < n; i++, j += 4) g[i] = (d[j] * 299 + d[j + 1] * 587 + d[j + 2] * 114) / 1000;
  return g;
}
