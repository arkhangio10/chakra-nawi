// Control de calidad sin ML (PLAN §2): brillo y nitidez del marco rectificado.
// Los umbrales son provisionales hasta medirlos con fotos reales; se ajustan en el modo técnico.

export interface UmbralesCalidad {
  brilloMin: number;
  brilloMax: number;
  nitidezMin: number; // varianza del Laplaciano
}

export const CALIDAD_POR_DEFECTO: UmbralesCalidad = { brilloMin: 70, brilloMax: 240, nitidezMin: 25 };

export interface Calidad {
  brillo: number;
  nitidez: number;
  ok: boolean;
  motivo: 'ok' | 'oscura' | 'quemada' | 'movida';
}

/** `gris` del marco rectificado. Se mide sobre una versión a la mitad para que sea rápido. */
export function medirCalidad(gris: Uint8Array, lado: number, u: UmbralesCalidad = CALIDAD_POR_DEFECTO): Calidad {
  const m = lado >> 1;
  const g = new Float32Array(m * m);
  let suma = 0;
  for (let y = 0; y < m; y++) for (let x = 0; x < m; x++) {
    const v = gris[(2 * y) * lado + 2 * x];
    g[y * m + x] = v;
    suma += v;
  }
  const brillo = suma / (m * m);
  let s = 0, s2 = 0, n = 0;
  for (let y = 1; y < m - 1; y++) for (let x = 1; x < m - 1; x++) {
    const i = y * m + x;
    const lap = g[i - 1] + g[i + 1] + g[i - m] + g[i + m] - 4 * g[i];
    s += lap; s2 += lap * lap; n++;
  }
  const nitidez = s2 / n - (s / n) ** 2;
  const motivo = brillo < u.brilloMin ? 'oscura' : brillo > u.brilloMax ? 'quemada' : nitidez < u.nitidezMin ? 'movida' : 'ok';
  return { brillo, nitidez, ok: motivo === 'ok', motivo };
}
