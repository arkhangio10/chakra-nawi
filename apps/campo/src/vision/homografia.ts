import type { Img, Punto } from './tipos';

/** Homografía H (9 valores, h33 = 1) que lleva cada punto de `de` al punto correspondiente de `a`. */
export function homografia(de: Punto[], a: Punto[]): number[] {
  const A: number[][] = [];
  for (let i = 0; i < 4; i++) {
    const { x: u, y: v } = de[i], { x, y } = a[i];
    A.push([u, v, 1, 0, 0, 0, -u * x, -v * x, x]);
    A.push([0, 0, 0, u, v, 1, -u * y, -v * y, y]);
  }
  // Eliminación de Gauss con pivoteo parcial sobre la matriz aumentada 8×9.
  for (let col = 0; col < 8; col++) {
    let piv = col;
    for (let f = col + 1; f < 8; f++) if (Math.abs(A[f][col]) > Math.abs(A[piv][col])) piv = f;
    [A[col], A[piv]] = [A[piv], A[col]];
    if (Math.abs(A[col][col]) < 1e-12) throw new Error('Esquinas degeneradas: no hay homografía');
    for (let f = 0; f < 8; f++) {
      if (f === col) continue;
      const k = A[f][col] / A[col][col];
      for (let c = col; c < 9; c++) A[f][c] -= k * A[col][c];
    }
  }
  return [...A.map((fila, i) => fila[8] / fila[i]), 1];
}

export function aplicar(H: number[], p: Punto): Punto {
  const z = H[6] * p.x + H[7] * p.y + H[8];
  return { x: (H[0] * p.x + H[1] * p.y + H[2]) / z, y: (H[3] * p.x + H[4] * p.y + H[5]) / z };
}

/**
 * Rectifica el marco de la tarjeta a `lado`×`lado` px (contracts/modelo-io.md: 1216).
 * `esquinas` = [arriba-izq, arriba-der, abajo-der, abajo-izq] en píxeles de `src`.
 */
export function rectificar(src: Img, esquinas: Punto[], lado: number): Img {
  const destino = [{ x: 0, y: 0 }, { x: lado, y: 0 }, { x: lado, y: lado }, { x: 0, y: lado }];
  const H = homografia(destino, esquinas); // marco → foto (muestreo inverso)
  const out = new Uint8ClampedArray(lado * lado * 4);
  const { data, width: w, height: h } = src;
  for (let v = 0; v < lado; v++) {
    for (let u = 0; u < lado; u++) {
      const z = H[6] * (u + 0.5) + H[7] * (v + 0.5) + H[8];
      const x = (H[0] * (u + 0.5) + H[1] * (v + 0.5) + H[2]) / z - 0.5;
      const y = (H[3] * (u + 0.5) + H[4] * (v + 0.5) + H[5]) / z - 0.5;
      const o = (v * lado + u) * 4;
      const x0 = Math.floor(x), y0 = Math.floor(y);
      if (x0 < 0 || y0 < 0 || x0 >= w - 1 || y0 >= h - 1) { out[o] = out[o + 1] = out[o + 2] = 255; out[o + 3] = 255; continue; }
      const fx = x - x0, fy = y - y0;
      const i00 = (y0 * w + x0) * 4, i10 = i00 + 4, i01 = i00 + w * 4, i11 = i01 + 4;
      for (let c = 0; c < 3; c++) {
        const top = data[i00 + c] * (1 - fx) + data[i10 + c] * fx;
        const bot = data[i01 + c] * (1 - fx) + data[i11 + c] * fx;
        out[o + c] = top * (1 - fy) + bot * fy;
      }
      out[o + 3] = 255;
    }
  }
  return { data: out, width: lado, height: lado };
}
