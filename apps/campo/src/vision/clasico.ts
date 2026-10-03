// Contador clásico de manchas oscuras (PLAN §2): solo se usa para COMPARAR con el YOLO y como
// respaldo si el modelo no carga. No activa ninguna regla mientras no se calibre.
//
// 1. Fondo local con una media en caja (imagen integral, ventana de 41 px ≈ 3,4 mm).
// 2. Oscuro = píxel < 0,6 × fondo y < 140.
// 3. Componentes conexas; se cuentan las de tamaño de broca (≈ 20×10 px en el marco de 1216).
// 4. Manchas grandes (brocas pegadas) cuentan como área / área típica.

const VENTANA = 41;
const AREA_MIN = 40;
const AREA_TIPICA = 160;
const AREA_MAX_SOLA = 600;
const AREA_MAX_GRUPO = 6000;

export function contarClasico(gris: Uint8Array, lado: number): number {
  const w = lado, h = lado;
  const integral = new Float64Array((w + 1) * (h + 1));
  for (let y = 0; y < h; y++) {
    let fila = 0;
    for (let x = 0; x < w; x++) {
      fila += gris[y * w + x];
      integral[(y + 1) * (w + 1) + x + 1] = integral[y * (w + 1) + x + 1] + fila;
    }
  }
  const r = VENTANA >> 1;
  const oscuro = new Uint8Array(w * h);
  for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) {
    const x0 = Math.max(0, x - r), x1 = Math.min(w, x + r + 1), y0 = Math.max(0, y - r), y1 = Math.min(h, y + r + 1);
    const s = integral[y1 * (w + 1) + x1] - integral[y0 * (w + 1) + x1] - integral[y1 * (w + 1) + x0] + integral[y0 * (w + 1) + x0];
    const fondo = s / ((x1 - x0) * (y1 - y0));
    const v = gris[y * w + x];
    oscuro[y * w + x] = v < 0.6 * fondo && v < 140 ? 1 : 0;
  }
  const visto = new Uint8Array(w * h);
  const cola = new Int32Array(w * h);
  let total = 0;
  for (let i = 0; i < oscuro.length; i++) {
    if (!oscuro[i] || visto[i]) continue;
    let cab = 0, n = 0, area = 0;
    cola[n++] = i; visto[i] = 1;
    while (cab < n) {
      const p = cola[cab++];
      area++;
      const x = p % w;
      for (const q of [x > 0 ? p - 1 : -1, x < w - 1 ? p + 1 : -1, p - w, p + w]) {
        if (q >= 0 && q < oscuro.length && oscuro[q] && !visto[q]) { visto[q] = 1; cola[n++] = q; }
      }
    }
    if (area < AREA_MIN || area > AREA_MAX_GRUPO) continue;
    total += area <= AREA_MAX_SOLA ? 1 : Math.round(area / AREA_TIPICA);
  }
  return total;
}
